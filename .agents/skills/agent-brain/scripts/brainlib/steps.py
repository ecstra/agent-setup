"""The steps a piece of work is made of, a table the tool keeps on a plan, a todo or a bug.

The Steps section holds a table, one row per step, numbered from 1 and
never renumbered, each pointing at a todo, a bug or a review or standing
on its own. A plan always carries the table, a todo or a bug carries
one when its work has steps. Whoever files the entry lists the steps as
numbered lines, and the tool turns them into the table. Rows are added
and marked through here, never deleted, a step that turned out wrong is
skipped, so the file reads as the record of how the work went. A step
that points at an entry takes its mark from that entry, and only a step
that points at nothing is marked by hand.
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

from . import frontmatter, schema, sections, store

STEP_STATUSES: tuple[str, ...] = ("pending", "done", "skipped")
BY: tuple[str, ...] = ("owner", "agent")

# the kinds that carry a steps table
STEPPED_KINDS: tuple[str, ...] = ("plan", "todo", "bug")

# the kinds a step may point at, and what counts as done for each
POINTED_KINDS: dict[str, tuple[str, ...]] = {
    "todo": ("done",),
    "bug": ("fixed", "wontfix"),
    "review": ("closed",),
}
POINTED_GONE: dict[str, tuple[str, ...]] = {
    "todo": ("dropped", "refiled"),
    "bug": ("refiled",),
    "review": (),
}

# the statuses that keep work open, for the chain and for adding steps
OPEN_STATUSES: dict[str, tuple[str, ...]] = {
    "plan": ("open",),
    "todo": ("open",),
    "bug": ("open", "branched"),
    "review": ("open",),
}

# the status that closes each stepped kind once every step is settled
CLOSING: dict[str, str] = {
    "plan": "done",
    "todo": "done",
    "bug": "fixed",
}

TABLE_HEADER = "| # | Step | Points at | By | Status |\n|---|---|---|---|---|\n"
HEADER_LINE = re.compile(r"^\|[ \t]*#[ \t]*\|[ \t]*Step[ \t]*\|[ \t]*Points at[ \t]*\|[ \t]*By[ \t]*\|[ \t]*Status[ \t]*\|[ \t]*\n\|[-| \t]+\|[ \t]*$", re.MULTILINE)
# a cell runs to the next pipe, and a pipe written as \| is part of the cell
CELL = r"((?:\\.|[^|\n])*?)"
ROW = re.compile(
    rf"^\|[ \t]*(\d+)[ \t]*\|[ \t]*{CELL}[ \t]*\|[ \t]*{CELL}[ \t]*\|[ \t]*{CELL}[ \t]*\|[ \t]*{CELL}[ \t]*\|[ \t]*$",
    re.MULTILINE,
)
LISTED = re.compile(r"^(\d+)\.[ \t]+(.+?)[ \t]*$", re.MULTILINE)

# a step line may open with the key of the entry it points at
POINTER = re.compile(r"^([A-Za-z0-9][\w.-]*)[,:][ \t]+(.+)$")

# a heading meant as the Steps section that the readers would never find
STEPS_LOOKALIKE = re.compile(r"^#{1,6}[ \t]+steps:?[ \t]*$", re.IGNORECASE | re.MULTILINE)


class StepsError(Exception):
    """A steps table that does not read as one, or a step that cannot be added or marked as asked, with the reason in the message."""


@dataclass(frozen=True)
class Step:
    """One row of the table."""

    number: int
    text: str
    points_at: str
    by: str
    status: str


def table(
    body: str,
) -> list[Step]:
    """Every row of the steps table, in order, refused when the section or the table is not there or a row is broken."""
    rows = [
        Step(
            number=int(row.group(1)),
            text=unescaped(row.group(2)),
            points_at=unescaped(row.group(3)),
            by=unescaped(row.group(4)),
            status=unescaped(row.group(5)),
        )
        for row in located(body)[1]
    ]

    for expected, step in enumerate(rows, 1):
        if step.number != expected:
            raise StepsError(f"the steps are numbered 1 onward in order, and row {step.number} sits where {expected} should")

        if step.status not in STEP_STATUSES:
            raise StepsError(f"step {step.number} is {' or '.join(STEP_STATUSES)}, not '{step.status}'")

        if step.by not in BY:
            raise StepsError(f"step {step.number} is set by {' or '.join(BY)}, not '{step.by}'")

    return rows


def located(
    body: str,
) -> tuple[re.Match, list[re.Match]]:
    """The table's header and its rows, the lines right under the header outside code, the one reading every reader and every writer of the table shares.

    A row shaped line anywhere else in the section, outside code, is
    refused rather than read or ignored, since a table a hand edit
    pulled apart would otherwise be written back without the lines
    between.
    """
    found = sections.span(body=body, title="Steps")
    if found is None:
        raise StepsError("there is no Steps section")

    start, end = found
    spans = sections.code_spans(body)
    header: Optional[re.Match] = None
    for match in HEADER_LINE.finditer(string=body, pos=start, endpos=end):
        if not sections.in_code(spans=spans, position=match.start()):
            header = match
            break

    if header is None:
        raise StepsError("the Steps section has no table, its header is | # | Step | Points at | By | Status |, and brain steps <key> add fills one")

    rows: list[re.Match] = []
    position = header.end()
    while position < end and body[position] == "\n":
        line_start = position + 1
        row = ROW.match(string=body, pos=line_start, endpos=end)
        if row is None:
            if body[line_start:end].split("\n", 1)[0].lstrip().startswith("|"):
                raise StepsError("a line of the steps table is not a whole row, a row is | number | step | points at | by | status |")

            break

        rows.append(row)
        position = row.end()

    read = {row.start() for row in rows}
    for match in ROW.finditer(string=body, pos=start, endpos=end):
        if match.start() not in read and not sections.in_code(spans=spans, position=match.start()):
            raise StepsError("a step row sits apart from the table, put it directly under the header")

    return header, rows


def rows_of(
    entry: store.Entry,
) -> list[Step]:
    """The entry's steps, none for a todo or a bug without a Steps section, refused with the path named when the table does not read."""
    if entry.kind.name != "plan" and sections.span(body=entry.document.body, title="Steps") is None:
        return []

    try:
        return table(entry.document.body)
    except StepsError as broken:
        raise StepsError(f"{entry.relative}: {broken}") from broken


def has_table(
    body: str,
) -> bool:
    """Whether the Steps section already holds the table's header, outside code."""
    found = sections.span(body=body, title="Steps")
    if found is None:
        return False

    spans = sections.code_spans(body)

    return any(not sections.in_code(spans=spans, position=match.start()) for match in HEADER_LINE.finditer(string=body, pos=found[0], endpos=found[1]))


def current_step(
    rows: list[Step],
) -> Optional[int]:
    """The first step not yet done or skipped, or None when every step is settled or there are none."""
    for step in rows:
        if step.status == "pending":
            return step.number

    return None


def render_row(
    step: Step,
) -> str:
    """One row of the table, an empty cell written as one space and a pipe in a cell written as \\|, the way markdown reads it."""
    cells = [str(step.number), escaped(step.text), escaped(step.points_at), step.by, step.status]

    return "|" + "|".join(f" {value} " if value else " " for value in cells) + "|"


def escaped(
    text: str,
) -> str:
    """A cell's text with its backslashes and pipes escaped, so a step ending in a backslash never swallows the pipe after it."""
    return text.replace("\\", "\\\\").replace("|", "\\|")


def unescaped(
    text: str,
) -> str:
    return re.sub(r"\\(.)", r"\1", text)


def rewrite(
    body: str,
    rows: list[Step],
) -> str:
    """The body with its steps table replaced by these rows, the prose and the code around it untouched."""
    header, old_rows = located(body)
    table_end = old_rows[-1].end() if old_rows else header.end()
    text = "".join("\n" + render_row(step) for step in rows)

    return body[: header.end()] + text + body[table_end:]


def listed(
    body: str,
) -> list[str]:
    """The steps of a Steps section as someone filed it, one per numbered line with its indented continuation lines joined on, refused when the section holds anything else, since a line the table cannot carry is never dropped without a word."""
    text = sections.block(body=body, title="Steps")
    if text is None:
        return []

    found: list[str] = []
    for line in text.split("\n"):
        if not line.strip():
            continue

        match = LISTED.match(line)
        if match is not None:
            if int(match.group(1)) != len(found) + 1:
                raise StepsError(f"the steps are numbered 1 onward in order, and {match.group(1)} sits where {len(found) + 1} should")

            found.append(match.group(2))
            continue

        if found and line[0] in " \t":
            found[-1] = f"{found[-1]} {line.strip()}"
            continue

        raise StepsError(f"the Steps section holds a line that is not a numbered step, one per line with its wrapped lines indented under it: {line.strip()!r}")

    return found


def tabled(
    brain: store.Brain,
    body: str,
    by: str,
    kind: schema.Kind,
) -> str:
    """The body with the numbered lines under Steps turned into the table, or as it was when it has no Steps section or already holds the table."""
    if sections.span(body=body, title="Steps") is None:
        return body

    if has_table(body):
        return checked(brain=brain, body=body)

    return converted(brain=brain, body=body, by=by, kind=kind)


def checked(
    brain: store.Brain,
    body: str,
) -> str:
    """The body with a table someone typed by hand read, its pointers resolved, its marks derived and a step line left outside it refused, so a filed table passes every check a listed step does."""
    rows = table(body)
    fresh: list[Step] = []
    for step in rows:
        if step.points_at and pointed(brain=brain, key=step.points_at) is None:
            raise StepsError(f"step {step.number} points at '{step.points_at}', which is not a todo, a bug or a review the brain knows")

        fresh.append(Step(number=step.number, text=step.text, points_at=step.points_at, by=step.by, status=derived_status(brain=brain, step=step)))

    start, end = sections.span(body=body, title="Steps") or (0, 0)
    spans = sections.code_spans(body)
    for match in LISTED.finditer(string=body, pos=start, endpos=end):
        if not sections.in_code(spans=spans, position=match.start()):
            raise StepsError(f"step lines go in the table, and {match.group(0).strip()!r} sits outside it")

    return rewrite(body=body, rows=fresh)


def refuse_lookalike(
    body: str,
) -> None:
    """Refuse a heading meant as a plan's Steps section that no reader would find, so its steps are never left behind as prose, a plan being the one kind whose Steps section is required, where a todo or a bug may hold such a heading as prose."""
    spans = sections.code_spans(body)
    for match in STEPS_LOOKALIKE.finditer(body):
        if not sections.in_code(spans=spans, position=match.start()):
            raise StepsError(f"the steps go under a level two heading, ## Steps, and {match.group(0).strip()!r} is not one")


def converted(
    brain: store.Brain,
    body: str,
    by: str,
    kind: schema.Kind,
    status: str = "pending",
) -> str:
    """The body with the list under Steps turned into the table, each row marked as given unless it points at an entry, which gives the mark."""
    rows = [row_from(brain=brain, number=number, line=line, by=by) for number, line in enumerate(listed(body), 1)]
    if status != "pending":
        rows = [step if step.points_at else Step(number=step.number, text=step.text, points_at="", by=step.by, status=status) for step in rows]

    return with_table(body=body, rows=rows, kind=kind)


def settled_as(
    entry: store.Entry,
) -> str:
    """The mark a step of a closed entry takes when its list becomes the table: done for an entry done or fixed, skipped for one dropped, refiled or wontfix, pending while it is open."""
    status = entry.field("status") or ""
    if status in OPEN_STATUSES[entry.kind.name]:
        return "pending"

    return "done" if status in ("done", "fixed") else "skipped"


def with_table(
    body: str,
    rows: list[Step],
    kind: schema.Kind,
) -> str:
    """The body with its Steps section holding the table and nothing else, added where the kind's sections put it when the prose had none."""
    found = sections.span(body=body, title="Steps")
    table_text = TABLE_HEADER.rstrip("\n") + "".join("\n" + render_row(step) for step in rows) + "\n"
    if found is not None:
        start, end = found
        return body[:start] + "\n\n" + table_text + "\n" + body[end:]

    titles = [section.title for section in kind.sections]
    for title in titles[titles.index("Steps") + 1 :]:
        following = sections.span(body=body, title=title)
        if following is not None:
            heading_start = body.rfind("\n", 0, following[0]) + 1
            return body[:heading_start] + "## Steps\n\n" + table_text + "\n" + body[heading_start:]

    return body.rstrip("\n") + "\n\n## Steps\n\n" + table_text


def row_from(
    brain: store.Brain,
    number: int,
    line: str,
    by: str,
) -> Step:
    """One step from one line, which may open with the key of the entry it points at, refused when that key reaches nothing of the right kind."""
    if by not in BY:
        raise StepsError(f"a step is set by {' or '.join(BY)}, not '{by}'")

    line = line.strip()
    if "\n" in line or "\r" in line:
        raise StepsError(f"step {number} is one line, and a line break would split its row")

    points_at = ""
    match = POINTER.match(line)
    if match is not None and pointed(brain=brain, key=match.group(1)) is not None:
        points_at = match.group(1)
        line = match.group(2).strip()
    elif match is not None and looks_like_a_key(match.group(1)):
        raise StepsError(f"step {number} points at '{match.group(1)}', which is not a todo, a bug or a review the brain knows")

    if not line:
        raise StepsError(f"step {number} has no text")

    step = Step(number=number, text=line, points_at=points_at, by=by, status="pending")

    return Step(number=number, text=line, points_at=points_at, by=by, status=derived_status(brain=brain, step=step))


def looks_like_a_key(
    word: str,
) -> bool:
    """Whether a word opening a step line is meant as an id or a review's name rather than a word of prose."""
    return schema.FILENAME_WITH_ID.match(f"{word}-x.md") is not None or schema.is_review_folder(word)


def pointed(
    brain: store.Brain,
    key: str,
) -> Optional[store.Entry]:
    """The todo, bug or review a step points at, or None when the key reaches nothing or more than one file."""
    try:
        entry = brain.find(key)
    except store.Ambiguous:
        return None

    if entry is None or entry.kind.name not in POINTED_KINDS:
        return None

    return entry


def derived_status(
    brain: store.Brain,
    step: Step,
) -> str:
    """The status a pointed step should carry, read off the entry it points at, or its own when it points at nothing."""
    if not step.points_at:
        return step.status

    entry = pointed(brain=brain, key=step.points_at)
    if entry is None:
        return step.status

    status = entry.field("status") or ""
    if status in POINTED_KINDS[entry.kind.name]:
        return "done"

    if status in POINTED_GONE[entry.kind.name]:
        return "skipped"

    return "pending"


def add(
    brain: store.Brain,
    key: str,
    lines: list[str],
    by: str = "agent",
) -> list[int]:
    """Append steps to the entry, numbered after the last, and hand back their numbers."""
    entry = stepped_entry(brain=brain, key=key)
    status = entry.field("status") or ""
    if status not in OPEN_STATUSES[entry.kind.name]:
        raise StepsError(f"{entry.name} is {status}, a step is added while it is open")

    body = entry.document.body
    if sections.span(body=body, title="Steps") is None:
        body = with_table(body=body, rows=[], kind=entry.kind)
    elif not has_table(body):
        body = converted(brain=brain, body=body, by=entry.field("by") or "agent", kind=entry.kind)

    rows = table(body)
    added = [row_from(brain=brain, number=len(rows) + offset, line=line, by=by) for offset, line in enumerate(lines, 1)]
    if not added:
        raise StepsError("no steps given, one per line")

    own = {entry.identifier, entry.name}
    for step in added:
        if step.points_at in own:
            raise StepsError(f"step {step.number} points at {entry.name} itself, and a step points at other work")

    entry.document.body = rewrite(body=body, rows=rows + added)
    save(brain=brain, entry=entry)

    return [step.number for step in added]


def mark(
    brain: store.Brain,
    key: str,
    number: int,
    status: str,
) -> None:
    """Mark a step that points at nothing done, skipped or pending again, since a pointed step takes its mark from what it points at."""
    if status not in STEP_STATUSES:
        raise StepsError(f"a step is {' or '.join(STEP_STATUSES)}, not '{status}'")

    entry = stepped_entry(brain=brain, key=key)
    rows = rows_of(entry)
    step = step_numbered(entry=entry, rows=rows, number=number)
    if step.points_at:
        raise StepsError(f"step {number} points at {step.points_at}, so its mark follows that entry, close or drop it instead")

    rows[number - 1] = Step(number=number, text=step.text, points_at="", by=step.by, status=status)
    entry.document.body = rewrite(body=entry.document.body, rows=rows)
    save(brain=brain, entry=entry)


def step_numbered(
    entry: store.Entry,
    rows: list[Step],
    number: int,
) -> Step:
    if number < 1 or number > len(rows):
        raise StepsError(f"{entry.name} has {len(rows)} steps, and there is no step {number}")

    return rows[number - 1]


def view(
    brain: store.Brain,
    key: str,
) -> str:
    """The entry's steps in a few lines: its state, then one line per step with its mark."""
    entry = stepped_entry(brain=brain, key=key)
    rows = rows_of(entry)
    settled = sum(1 for step in rows if step.status in ("done", "skipped"))
    lines = [f"{entry.name}, {entry.field('status')}, {settled} of {len(rows)} steps settled"]
    for step in rows:
        pointer = f", {step.points_at}" if step.points_at else ""
        lines.append(f"{step.number}. {step.text}{pointer}, {step.status}")

    return "\n".join(lines)


def stepped_entry(
    brain: store.Brain,
    key: str,
) -> store.Entry:
    try:
        entry = brain.find(key)
    except store.Ambiguous as clash:
        raise StepsError(str(clash)) from clash

    if entry is None or entry.kind.name not in STEPPED_KINDS:
        raise StepsError(f"no plan, todo or bug answers to '{key}'")

    return entry


def save(
    brain: store.Brain,
    entry: store.Entry,
    stamp: str = "",
) -> None:
    entry.document.set(key="updated", value=stamp or date.today().isoformat())
    frontmatter.write(path=str(entry.path), document=entry.document)
    brain.refresh()


def refresh(
    brain: store.Brain,
    entry: store.Entry,
    stamp: str = "",
) -> bool:
    """Bring every pointed step's mark in line with the entry it points at, and say whether anything changed."""
    rows = rows_of(entry)
    fresh = [
        Step(number=step.number, text=step.text, points_at=step.points_at, by=step.by, status=derived_status(brain=brain, step=step))
        for step in rows
    ]
    if fresh == rows:
        return False

    entry.document.body = rewrite(body=entry.document.body, rows=fresh)
    save(brain=brain, entry=entry, stamp=stamp)

    return True


def refresh_pointing(
    brain: store.Brain,
    key: str,
    stamp: str = "",
) -> list[str]:
    """Refresh every plan, todo and bug with a step that points at the entry, and name the ones that changed."""
    entry = pointed(brain=brain, key=key)
    if entry is None:
        return []

    keys = {entry.identifier, entry.name} - {None}
    changed: list[str] = []
    for kind_name in STEPPED_KINDS:
        for holder in brain.entries_of(schema.kind_named(kind_name)):
            try:
                rows = rows_of(holder)
            except StepsError:
                continue

            if any(step.points_at in keys for step in rows) and refresh(brain=brain, entry=holder, stamp=stamp):
                changed.append(holder.name)

    return changed


def all_settled(
    rows: list[Step],
) -> bool:
    """Whether every step is done or skipped, which holds of no steps at all, a goal alone closing on its Done when."""
    return all(step.status in ("done", "skipped") for step in rows)


def gaps(
    kind: schema.Kind,
    fields: dict[str, str],
    body: str,
) -> list[str]:
    """What an entry closing falls short of, the one rule its table sets: closed means every step is done or skipped."""
    status = fields.get("status", "")
    if kind.name not in CLOSING or status != CLOSING[kind.name]:
        return []

    if kind.name != "plan" and sections.span(body=body, title="Steps") is None:
        return []

    try:
        rows = table(body)
    except StepsError as broken:
        return [str(broken)]

    if not all_settled(rows):
        return [f"a {kind.name} goes {status} once every step is done or skipped, and one of its steps still stands"]

    return []
