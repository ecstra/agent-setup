"""The steps a piece of work is made of: a plan's table and a todo's list.

A plan's Steps section holds a table the tool keeps, one row per step,
numbered from 1 and never renumbered, each pointing at a todo, a bug or
a review or standing on its own. A todo's or a bug's Steps section holds
a plain numbered list the agent writes by hand. This module reads both
and rewrites the table, and nothing else touches the table's shape.
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

from . import frontmatter, schema, sections, store

STEP_STATUSES: tuple[str, ...] = ("pending", "done", "skipped")
BY: tuple[str, ...] = ("owner", "agent")

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

TABLE_HEADER = "| # | Step | Points at | By | Status |\n|---|---|---|---|---|\n"
HEADER_LINE = re.compile(r"^\|[ \t]*#[ \t]*\|[ \t]*Step[ \t]*\|[ \t]*Points at[ \t]*\|[ \t]*By[ \t]*\|[ \t]*Status[ \t]*\|[ \t]*\n\|[-| \t]+\|[ \t]*$", re.MULTILINE)
ROW = re.compile(
    r"^\|[ \t]*(\d+)[ \t]*\|[ \t]*(.*?)[ \t]*\|[ \t]*(.*?)[ \t]*\|[ \t]*(.*?)[ \t]*\|[ \t]*(.*?)[ \t]*\|[ \t]*$",
    re.MULTILINE,
)
LISTED = re.compile(r"^(\d+)\.[ \t]+(.+?)[ \t]*$", re.MULTILINE)


class StepsError(Exception):
    """A steps table or list that does not read as one, with the line and the fix in the message."""


@dataclass(frozen=True)
class Step:
    """One row of a plan's table."""

    number: int
    text: str
    points_at: str
    by: str
    status: str


def table(
    body: str,
) -> list[Step]:
    """Every row of the plan's steps table, in order, refused when the section or the table is not there or a row is broken."""
    found = sections.span(body=body, title="Steps")
    if found is None:
        raise StepsError("the plan has no Steps section")

    start, end = found
    spans = sections.code_spans(body)
    header: Optional[re.Match] = None
    for match in HEADER_LINE.finditer(string=body, pos=start, endpos=end):
        if not sections.in_code(spans=spans, position=match.start()):
            header = match
            break

    if header is None:
        raise StepsError("the plan has no steps table, its header is | # | Step | Points at | By | Status |")

    rows: list[Step] = []
    position = header.end()
    while position < end and body[position] == "\n":
        line_start = position + 1
        row = ROW.match(string=body, pos=line_start, endpos=end)
        if row is None:
            if body[line_start:end].split("\n", 1)[0].lstrip().startswith("|"):
                raise StepsError("a line of the steps table is not a whole row, a row is | number | step | points at | by | status |")

            break

        rows.append(
            Step(
                number=int(row.group(1)),
                text=row.group(2),
                points_at=row.group(3),
                by=row.group(4),
                status=row.group(5),
            )
        )
        position = row.end()

    read = {row.number for row in rows}
    for match in ROW.finditer(string=body, pos=start, endpos=end):
        if int(match.group(1)) not in read and not sections.in_code(spans=spans, position=match.start()):
            raise StepsError("a step row sits apart from the table, put it directly under the header")

    for expected, step in enumerate(rows, 1):
        if step.number != expected:
            raise StepsError(f"the steps are numbered 1 onward in order, and row {step.number} sits where {expected} should")

        if step.status not in STEP_STATUSES:
            raise StepsError(f"step {step.number} is {' or '.join(STEP_STATUSES)}, not '{step.status}'")

        if step.by not in BY:
            raise StepsError(f"step {step.number} is set by {' or '.join(BY)}, not '{step.by}'")

    return rows


def render_row(
    step: Step,
) -> str:
    """One row of the table, an empty cell written as one space."""
    cells = [str(step.number), step.text, step.points_at, step.by, step.status]

    return "|" + "|".join(f" {value} " if value else " " for value in cells) + "|"


def rewrite(
    body: str,
    rows: list[Step],
) -> str:
    """The body with its steps table replaced by these rows, the prose around it untouched."""
    start, end = sections.span(body=body, title="Steps") or (None, None)
    if start is None:
        raise StepsError("the plan has no Steps section")

    header = next(match for match in HEADER_LINE.finditer(string=body, pos=start, endpos=end))
    old_rows = list(ROW.finditer(string=body, pos=header.end(), endpos=end))
    table_end = old_rows[-1].end() if old_rows else header.end()
    text = "".join("\n" + render_row(step) for step in rows)

    return body[: header.end()] + text + body[table_end:]


def listed(
    body: str,
) -> list[str]:
    """The numbered lines of a todo's or a bug's Steps section, in order, or none where there is no such section."""
    text = sections.block(body=body, title="Steps")
    if text is None:
        return []

    return [match.group(2) for match in LISTED.finditer(text)]


def list_slips(
    body: str,
) -> list[str]:
    """What is wrong with a todo's or a bug's Steps list, in words, or nothing when it reads as one."""
    text = sections.block(body=body, title="Steps")
    if text is None:
        return []

    numbers = [int(match.group(1)) for match in LISTED.finditer(text)]
    loose = [line for line in text.strip().split("\n") if line.strip() and LISTED.match(line) is None]
    slips: list[str] = []
    if loose:
        slips.append("the Steps section holds only numbered lines, one step each")

    if numbers != list(range(1, len(numbers) + 1)):
        slips.append("the steps are numbered 1 onward in order")

    return slips


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


def refresh(
    brain: store.Brain,
    entry: store.Entry,
    stamp: str = "",
) -> bool:
    """Bring every pointed step's mark of the plan in line with the entry it points at, and say whether anything changed."""
    rows = table(entry.document.body)
    fresh = [
        Step(number=step.number, text=step.text, points_at=step.points_at, by=step.by, status=derived_status(brain=brain, step=step))
        for step in rows
    ]
    if fresh == rows:
        return False

    entry.document.body = rewrite(body=entry.document.body, rows=fresh)
    entry.document.set(key="updated", value=stamp or date.today().isoformat())
    frontmatter.write(path=str(entry.path), document=entry.document)
    brain.refresh()

    return True


def refresh_pointing(
    brain: store.Brain,
    key: str,
    stamp: str = "",
) -> list[str]:
    """Refresh every plan with a step that points at the entry, and name the plans that changed."""
    entry = pointed(brain=brain, key=key)
    if entry is None:
        return []

    keys = {entry.identifier, entry.name} - {None}
    changed: list[str] = []
    for plan in brain.entries_of(schema.kind_named("plan")):
        try:
            rows = table(plan.document.body)
        except StepsError:
            continue

        if any(step.points_at in keys for step in rows) and refresh(brain=brain, entry=plan, stamp=stamp):
            changed.append(plan.name)

    return changed


def all_settled(
    rows: list[Step],
) -> bool:
    """Whether every step is done or skipped, and there is at least one."""
    return bool(rows) and all(step.status in ("done", "skipped") for step in rows)


def plan_gaps(
    kind: schema.Kind,
    fields: dict[str, str],
    body: str,
) -> list[str]:
    """What a plan in its status falls short of, the one rule its table sets: done means every step is done or skipped."""
    if kind.name != "plan" or fields.get("status", "") != "done":
        return []

    try:
        rows = table(body)
    except StepsError as broken:
        return [str(broken)]

    if not all_settled(rows):
        return ["a plan goes done once every step is done or skipped, and one of its steps still stands"]

    return []
