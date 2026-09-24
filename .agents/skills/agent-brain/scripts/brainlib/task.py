"""The current work, a chain from the plan down to the step the agent is on.

One chain at a time, kept in a local file the tool writes and every
hook prints, so the model always knows the task, the plan it serves,
the step inside it and the review running on it. A plan, a todo, a bug
or a review is the root. A todo or a bug pushes under the plan step
that points at it, a review pushes under the todo or bug it reviews,
and a link whose entry closes drops off with everything under it. The
rule in SYSTEM.md 8.3 is that multi step work starts with `brain task
on`, and the step moves as the work moves.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from . import clock, frontmatter, ledger, plans, schema, steps, store

FILE = ".task"
NONE = "task none"
BROKEN = f"{FILE} does not read as a chain and brain task off --all clears it"

# the kinds a chain may hold, and the statuses that keep each one open
OPEN_STATUSES: dict[str, tuple[str, ...]] = {
    "plan": ("open",),
    "todo": ("open",),
    "bug": ("open", "branched"),
    "review": ("open",),
}

# the word each kind is printed under
WORDS: dict[str, str] = {
    "plan": "plan",
    "todo": "task",
    "bug": "bug",
    "review": "review",
}


class TaskError(Exception):
    """The chain could not be set as asked, with the reason in the message."""


@dataclass(frozen=True)
class Item:
    """One link of the chain: what is being worked on and, where it has steps, which one."""

    kind: str
    key: str
    step: Optional[int] = None


def path_of(
    brain: store.Brain,
) -> Path:
    return brain.root / FILE


def read(
    brain: store.Brain,
) -> Optional[list[Item]]:
    """The chain as written, an empty list when there is no file, or None when the file does not read as a chain."""
    path = path_of(brain)
    if not store.readable_file(path):
        return [] if not store.quietly(path.exists) and not store.quietly(path.is_symlink) else None

    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
        items = [Item(kind=str(link["kind"]), key=str(link["key"]), step=link.get("step")) for link in data["chain"]]
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
        return None

    if not all(is_link(item) for item in items):
        return None

    return items


def is_link(
    item: Item,
) -> bool:
    return item.kind in OPEN_STATUSES and bool(item.key) and (item.step is None or (type(item.step) is int and item.step >= 1))


def write(
    brain: store.Brain,
    chain: list[Item],
) -> None:
    """Record the chain, whole or not at all, or take the file away when the chain is empty."""
    path = path_of(brain)
    if not chain:
        if store.quietly(path.exists) or store.quietly(path.is_symlink):
            path.unlink()
        return

    text = json.dumps({"chain": [asdict(item) for item in chain], "since": clock.now().isoformat()}) + "\n"
    frontmatter.write_text(path=str(path), text=text)


def current(
    brain: store.Brain,
    chain: Optional[list[Item]] = None,
) -> list[Item]:
    """The chain as it stands, with a link whose entry has closed or gone dropped along with everything under it.

    A link whose entry cannot be read this time stays, since a folder
    the process could not list is not a closed todo. What was dropped
    is written back, and a folder that cannot be written this time is
    left as it was, since the same reading gives the same chain next
    time.
    """
    if chain is None:
        chain = read(brain) or []

    kept: list[Item] = []
    for item in chain:
        entry = entry_of(brain=brain, item=item)
        if entry is None and unreadable(brain=brain, item=item):
            kept.append(item)
            continue

        if entry is None or not is_open(entry):
            break

        kept.append(item)

    if kept != chain:
        try:
            write(brain=brain, chain=kept)
        except OSError:
            pass

    return kept


def entry_of(
    brain: store.Brain,
    item: Item,
) -> Optional[store.Entry]:
    try:
        entry = brain.find(item.key)
    except store.Ambiguous:
        return None

    return entry if entry is not None and entry.kind.name == item.kind else None


def unreadable(
    brain: store.Brain,
    item: Item,
) -> bool:
    """Whether the link's entry may be there unread, in a file or a folder the brain could not read this time."""
    folder = brain.folder(schema.kind_named(item.kind))
    for path, trouble in brain.unreadable.items():
        if path.stem == item.key or path.stem.startswith(f"{item.key}-") or path.parent.name == item.key:
            return True

        if trouble == store.UNLISTED and (path == folder or folder in path.parents):
            return True

    return False


def is_open(
    entry: store.Entry,
) -> bool:
    return (entry.field("status") or "") in OPEN_STATUSES.get(entry.kind.name, ())


def resolve(
    brain: store.Brain,
    key: str,
) -> store.Entry:
    """The one open plan, todo, bug or review the key answers to, refused otherwise."""
    try:
        entry = brain.find(key)
    except store.Ambiguous as clash:
        raise TaskError(str(clash)) from clash

    if entry is None:
        raise TaskError(f"nothing in the brain answers to '{key}'")

    if entry.kind.name not in OPEN_STATUSES:
        raise TaskError(f"the work is a plan, a todo, a bug or a review, and {entry.name} is a {entry.kind.name}")

    if not is_open(entry):
        raise TaskError(f"{entry.name} is {entry.field('status')}, and the work is on something open")

    return entry


def key_of(
    entry: store.Entry,
) -> str:
    """The key the chain stores, the id for a todo or a bug, the name for a plan or a review."""
    return entry.identifier or entry.name


def turn_on(
    brain: store.Brain,
    key: str,
    step: Optional[int] = None,
    replace: bool = False,
) -> list[Item]:
    """Start work on the entry: as the root of a fresh chain, pushed under the innermost link where the rules allow, or in place of the chain when told to replace it."""
    entry = resolve(brain=brain, key=key)
    item = Item(kind=entry.kind.name, key=key_of(entry), step=first_step(brain=brain, entry=entry, wanted=step))

    chain: list[Item] = []
    if not replace:
        written = read(brain)
        if written is None:
            raise TaskError(BROKEN)

        chain = current(brain=brain, chain=written)

    if chain and not may_push(brain=brain, chain=chain, entry=entry):
        raise TaskError(f"the work is on {describe_item(brain=brain, item=chain[-1])}, finish or clear it first, or say --replace")

    chain.append(item)
    write(brain=brain, chain=chain)

    return chain


def may_push(
    brain: store.Brain,
    chain: list[Item],
    entry: store.Entry,
) -> bool:
    """Whether the entry may go under the innermost link: a review under a todo or a bug, or the entry the plan's current step points at under that plan."""
    innermost = chain[-1]
    if innermost.kind in ("todo", "bug"):
        return entry.kind.name == "review"

    if innermost.kind != "plan":
        return False

    plan = entry_of(brain=brain, item=innermost)
    if plan is None:
        return False

    rows = plans.read_rows(plan)
    step = plan_step(rows=rows, step=innermost.step)
    if step is None:
        return False

    pointer = rows[step - 1].points_at

    return bool(pointer) and pointer in (entry.identifier, entry.name)


def plan_step(
    rows: list[steps.Step],
    step: Optional[int],
) -> Optional[int]:
    """The step a plan link stands on: the one picked, or where the table stands when none was, as with a goal that got its steps after the work started."""
    if step is not None and step <= len(rows):
        return step

    return plans.current_step(rows)


def first_step(
    brain: store.Brain,
    entry: store.Entry,
    wanted: Optional[int],
) -> Optional[int]:
    """The step the work starts on: the one asked for, checked against the entry's steps, or the first one still to do."""
    if entry.kind.name == "review":
        if wanted is not None:
            raise TaskError("a review's step is its batch, read off the ledger, so give none")

        return None

    count = step_count(entry)
    if wanted is None:
        if entry.kind.name == "plan":
            return plans.current_step(plans.read_rows(entry))

        return 1 if count else None

    if wanted < 1 or wanted > count:
        raise TaskError(f"{entry.name} has {count} steps, and there is no step {wanted}")

    return wanted


def step_count(
    entry: store.Entry,
) -> int:
    if entry.kind.name == "plan":
        return len(plans.read_rows(entry))

    return len(steps.listed(entry.document.body))


def set_step(
    brain: store.Brain,
    number: int,
) -> list[Item]:
    """Move the innermost link to another of its steps."""
    written = read(brain)
    if written is None:
        raise TaskError(BROKEN)

    chain = current(brain=brain, chain=written)
    if not chain:
        raise TaskError("no work is on, start it with brain task on")

    innermost = chain[-1]
    entry = entry_of(brain=brain, item=innermost)
    if entry is None:
        raise TaskError(f"{innermost.key} cannot be read right now")

    chain[-1] = Item(kind=innermost.kind, key=innermost.key, step=first_step(brain=brain, entry=entry, wanted=number))
    write(brain=brain, chain=chain)

    return chain


def turn_off(
    brain: store.Brain,
    everything: bool = False,
) -> list[Item]:
    """Drop the innermost link, or the whole chain, and hand back what remains."""
    written = read(brain)
    if written is None:
        if not everything:
            raise TaskError(BROKEN)

        path_of(brain).unlink()
        return []

    chain = [] if everything else current(brain=brain, chain=written)[:-1]
    write(brain=brain, chain=chain)

    return chain


def describe(
    brain: store.Brain,
) -> str:
    """The chain as lines, one per link, outermost first, or the one line that says no work is on."""
    written = read(brain)
    if written is None:
        return f"{NONE}, {BROKEN}"

    chain = current(brain=brain, chain=written)
    if not chain:
        return NONE

    return "\n".join(f"{WORDS[item.kind]} {describe_item(brain=brain, item=item)}" for item in chain)


def describe_item(
    brain: store.Brain,
    item: Item,
) -> str:
    """One link in words: the key, then where it stands, the step and its text, the batch and its status, or what is missing."""
    entry = entry_of(brain=brain, item=item)
    if entry is None:
        return f"{item.key}, cannot be read right now"

    if item.kind == "review":
        return f"{item.key}, {batch_text(entry)}"

    if item.kind == "plan":
        return f"{item.key}, {plan_text(entry=entry, step=item.step)}"

    listed = steps.listed(entry.document.body)
    if not listed or item.step is None or item.step > len(listed):
        return item.key

    return f"{item.key}, step {item.step} of {len(listed)}, {listed[item.step - 1]}"


def plan_text(
    entry: store.Entry,
    step: Optional[int],
) -> str:
    try:
        rows = plans.read_rows(entry)
    except plans.PlanError:
        return "the steps table cannot be read"

    if not rows:
        return "no steps yet"

    step = plan_step(rows=rows, step=step)
    if step is None:
        return "every step settled"

    row = rows[step - 1]
    text = f"step {step} of {len(rows)}, {row.text}"
    if row.status != "pending":
        text += f", {row.status}, move on with brain task step"

    return text


def batch_text(
    entry: store.Entry,
) -> str:
    """Where a review stands, the first batch not yet done with its status, read off the ledger."""
    try:
        rows = ledger.batches(entry)
    except ledger.LedgerError:
        return "the batch table cannot be read"

    for row in rows:
        if row["status"] != "done":
            return f"batch {row['number']} of {len(rows)}, {row['status']}"

    return f"every batch done, {len(rows)} in all" if rows else "no batches yet"


def push_review(
    brain: store.Brain,
    name: str,
) -> Optional[str]:
    """Put a review that just opened on the chain, and say why when the rules keep it off, since the ledger opened either way."""
    try:
        turn_on(brain=brain, key=name)
    except (TaskError, plans.PlanError, OSError) as reason:
        return str(reason)

    return None
