"""A plan, a goal with the steps that reach it, kept as a table the agent grows.

The prose is the owner's and the agent's, the why and the done when.
The steps table is the tool's: rows are added and marked through here,
never renumbered and never deleted, a step that turned out wrong is
skipped with a word of why, so the plan reads as the record of how the
goal was reached. A step that points at a todo, a bug or a review takes
its mark from that entry, and only a step that points at nothing is
marked by hand.
"""

import re
from datetime import date
from typing import Optional

from . import frontmatter, schema, sections, steps, store, writes

# a step line may open with the key of the entry it points at
POINTER = re.compile(r"^([A-Za-z0-9][\w.-]*)[,:][ \t]+(.+)$")


class PlanError(Exception):
    """A plan the tool cannot file, grow or mark as asked, with the reason in the message."""


def create(
    brain: store.Brain,
    title: str,
    description: str,
    body: str,
    by: str = "owner",
    stamp: str = "",
) -> store.Entry:
    """File a plan from its prose, the steps it lists under Steps turned into the table, or an empty table when it lists none."""
    if by not in steps.BY:
        raise PlanError(f"a plan is set by {' or '.join(steps.BY)}, not '{by}'")

    stamp = stamp or date.today().isoformat()
    text = body if body.strip() else ""
    if not text:
        raise PlanError("a plan needs its prose on standard input, the Why and the Done when at least")

    listed = steps.listed(text)
    rows = [row_from(brain=brain, number=number, line=line, by=by) for number, line in enumerate(listed, 1)]
    text = with_table(body=text, rows=rows)

    return writes.create(
        brain=brain,
        kind=schema.kind_named("plan"),
        title=title,
        description=description,
        values={"by": by},
        body=text,
        stamp=stamp,
    )


def with_table(
    body: str,
    rows: list[steps.Step],
) -> str:
    """The body with its Steps section holding the table and nothing else, added before Done when where the prose had none."""
    found = sections.span(body=body, title="Steps")
    table_text = steps.TABLE_HEADER.rstrip("\n") + "".join("\n" + steps.render_row(step) for step in rows) + "\n"
    if found is not None:
        start, end = found
        return body[:start] + "\n\n" + table_text + "\n" + body[end:]

    closing = sections.span(body=body, title="Done when")
    if closing is None:
        raise PlanError("the body is missing the Done when heading")

    heading_start = body.rfind("## ", 0, closing[0])

    return body[:heading_start] + "## Steps\n\n" + table_text + "\n" + body[heading_start:]


def row_from(
    brain: store.Brain,
    number: int,
    line: str,
    by: str,
) -> steps.Step:
    """One step from one line, which may open with the key of the entry it points at, refused when that key reaches nothing of the right kind."""
    line = line.strip()
    if "|" in line:
        raise PlanError(f"step {number} cannot hold a pipe, the table's columns are pipes")

    points_at = ""
    match = POINTER.match(line)
    if match is not None and steps.pointed(brain=brain, key=match.group(1)) is not None:
        points_at = match.group(1)
        line = match.group(2).strip()
    elif match is not None and looks_like_a_key(match.group(1)):
        raise PlanError(f"step {number} points at '{match.group(1)}', which is not a todo, a bug or a review the brain knows")

    if not line:
        raise PlanError(f"step {number} has no text")

    step = steps.Step(number=number, text=line, points_at=points_at, by=by, status="pending")

    return steps.Step(number=number, text=line, points_at=points_at, by=by, status=steps.derived_status(brain=brain, step=step))


def looks_like_a_key(
    word: str,
) -> bool:
    """Whether a word opening a step line is meant as an id or a review's name rather than a word of prose."""
    return schema.FILENAME_WITH_ID.match(f"{word}-x.md") is not None or schema.is_review_folder(word)


def add(
    brain: store.Brain,
    key: str,
    lines: list[str],
    by: str = "agent",
) -> list[int]:
    """Append steps to the plan, numbered after the last, and hand back their numbers."""
    if by not in steps.BY:
        raise PlanError(f"a step is set by {' or '.join(steps.BY)}, not '{by}'")

    entry = plan_entry(brain=brain, key=key)
    if entry.field("status") != "open":
        raise PlanError(f"{entry.name} is {entry.field('status')}, a step is added to an open plan")

    rows = read_rows(entry)
    added = [row_from(brain=brain, number=len(rows) + offset, line=line, by=by) for offset, line in enumerate(lines, 1)]
    if not added:
        raise PlanError("no steps given, one per line")

    entry.document.body = steps.rewrite(body=entry.document.body, rows=rows + added)
    save(brain=brain, entry=entry)

    return [step.number for step in added]


def set_step(
    brain: store.Brain,
    key: str,
    number: int,
    status: str,
) -> None:
    """Mark a step that points at nothing done, skipped or pending again, since a pointed step takes its mark from what it points at."""
    if status not in steps.STEP_STATUSES:
        raise PlanError(f"a step is {' or '.join(steps.STEP_STATUSES)}, not '{status}'")

    entry = plan_entry(brain=brain, key=key)
    rows = read_rows(entry)
    step = step_numbered(rows=rows, number=number)
    if step.points_at:
        raise PlanError(f"step {number} points at {step.points_at}, so its mark follows that entry, close or drop it instead")

    rows[number - 1] = steps.Step(number=number, text=step.text, points_at="", by=step.by, status=status)
    entry.document.body = steps.rewrite(body=entry.document.body, rows=rows)
    save(brain=brain, entry=entry)


def step_numbered(
    rows: list[steps.Step],
    number: int,
) -> steps.Step:
    if number < 1 or number > len(rows):
        raise PlanError(f"the plan has {len(rows)} steps, and there is no step {number}")

    return rows[number - 1]


def read_rows(
    entry: store.Entry,
) -> list[steps.Step]:
    try:
        return steps.table(entry.document.body)
    except steps.StepsError as broken:
        raise PlanError(f"{entry.relative}: {broken}") from broken


def current_step(
    rows: list[steps.Step],
) -> Optional[int]:
    """The first step not yet done or skipped, or None when every step is settled or there are none."""
    for step in rows:
        if step.status == "pending":
            return step.number

    return None


def view(
    brain: store.Brain,
    key: str,
) -> str:
    """The plan in a few lines: its state, then one line per step with its mark."""
    entry = plan_entry(brain=brain, key=key)
    rows = read_rows(entry)
    settled = sum(1 for step in rows if step.status in ("done", "skipped"))
    lines = [f"{entry.name}, {entry.field('status')}, {settled} of {len(rows)} steps settled"]
    for step in rows:
        pointer = f", {step.points_at}" if step.points_at else ""
        lines.append(f"{step.number}. {step.text}{pointer}, {step.status}")

    return "\n".join(lines)


def plan_entry(
    brain: store.Brain,
    key: str,
) -> store.Entry:
    try:
        entry = brain.find(key)
    except store.Ambiguous as clash:
        raise PlanError(str(clash)) from clash

    if entry is None or entry.kind.name != "plan":
        raise PlanError(f"no plan answers to '{key}'")

    return entry


def save(
    brain: store.Brain,
    entry: store.Entry,
    stamp: str = "",
) -> None:
    entry.document.set(key="updated", value=stamp or date.today().isoformat())
    frontmatter.write(path=str(entry.path), document=entry.document)
    brain.refresh()
