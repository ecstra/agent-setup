"""Review ledgers, the one body the tool edits by design.

A ledger's batches and findings are structured records inside the body,
per spec/reviews.md, so numbering a finding or flipping its status is
bookkeeping rather than prose. Everything outside those records stays as
it was written.
"""

import re
from datetime import date
from typing import Optional

from . import frontmatter, schema, sections, store, writes

FINDING = re.compile(r"^### (F-\d+): (.+?)[ \t]*$", re.MULTILINE)
BULLET = re.compile(r"^- ([a-z-]+):[ \t]*(.*?)[ \t]*$", re.MULTILINE)
# One row of the batch table, on one line: the number, then three cells.
BATCH_ROW = re.compile(
    r"^\|[ \t]*(\d+)[ \t]*\|[ \t]*(.*?)[ \t]*\|[ \t]*(.*?)[ \t]*\|[ \t]*(.*?)[ \t]*\|[ \t]*$",
    re.MULTILINE,
)

BATCH_HEADER = "| # | Theme | Status | Ack |\n|---|---|---|---|\n"

# The batch table's header line and the rule under it, however the words
# are cased. It ends at the end of the rule line.
TABLE_HEADER = re.compile(
    r"^\|[ \t]*#[ \t]*\|[ \t]*theme[ \t]*\|[ \t]*status[ \t]*\|[ \t]*ack[ \t]*\|[ \t]*\n\|[ \t]*:?-+:?[ \t]*\|[^\n]*$",
    re.MULTILINE | re.IGNORECASE,
)

FIELDS = ("severity", "found-by", "batch", "status", "fix")
SEVERITIES = ("breaks", "bug", "debt", "nit")
FOUND_BY = ("review", "hunter")
FINDING_STATUSES = ("open", "fixed", "wontfix", "deferred")
BATCH_STATUSES = ("pending", "fixing", "verified", "done")


class LedgerError(Exception):
    """The ledger change was refused, with the reason in the message."""


def open_ledger(
    brain: store.Brain,
    branch: str,
    summary: str,
    stamp: str = "",
) -> store.Entry:
    stamp = stamp or date.today().isoformat()
    title = f"{stamp[:7]} {branch}"
    body = (
        "## Summary\n\n"
        f"{summary.strip()}\n\n"
        "## Batches\n\n"
        f"{BATCH_HEADER}\n"
        "## Findings\n"
    )

    return writes.create(
        brain=brain,
        kind=schema.kind_named("review"),
        title=title,
        description=f"review of {branch}",
        values={"branch": branch},
        body=body,
        stamp=stamp,
    )


def add_batch(
    brain: store.Brain,
    key: str,
    theme: str,
) -> int:
    theme = cell(value=theme, what="theme")
    if not theme:
        raise LedgerError("a batch needs a theme")

    entry = ledger_entry(brain=brain, key=key)
    number = max((row["number"] for row in batches(entry)), default=0) + 1
    row = "\n" + batch_row(number=number, theme=theme, status="pending", ack="")

    body = entry.document.body
    table_end = end_of_table(body)
    entry.document.body = body[:table_end] + row + body[table_end:]
    save(brain=brain, entry=entry)

    return number


def set_batch(
    brain: store.Brain,
    key: str,
    number: int,
    status: str = "",
    ack: str = "",
    theme: str = "",
) -> None:
    if status and status not in BATCH_STATUSES:
        raise LedgerError(f"a batch is {' or '.join(BATCH_STATUSES)}, not '{status}'")

    ack = cell(value=ack, what="ack")
    theme = cell(value=theme, what="theme")
    if not (status or ack or theme):
        raise LedgerError("nothing to set, give a status, an ack or a theme")

    entry = ledger_entry(brain=brain, key=key)
    body = entry.document.body
    replaced = False

    for match in batch_rows(body):
        if int(match.group(1)) != number:
            continue

        row = batch_row(
            number=number,
            theme=theme or match.group(2),
            status=status or match.group(3),
            ack=ack or match.group(4),
        )
        body = body[: match.start()] + row + body[match.end() :]
        replaced = True
        break

    if not replaced:
        raise LedgerError(f"{entry.name} has no batch {number}")

    entry.document.body = body
    save(brain=brain, entry=entry)


def batch_row(
    number: int,
    theme: str,
    status: str,
    ack: str,
) -> str:
    """One row of the batch table, an empty cell written as one space."""
    cells = [str(number), theme, status, ack]

    return "|" + "|".join(f" {value} " if value else " " for value in cells) + "|"


def add_finding(
    brain: store.Brain,
    key: str,
    claim: str,
    severity: str,
    found_by: str = "review",
    batch: int = 0,
) -> str:
    severity = checked(field="severity", value=severity)
    found_by = checked(field="found-by", value=found_by)
    batch_cell = checked(field="batch", value=str(batch) if batch else "")
    claim = one_line(value=claim, what="claim")
    if not claim:
        raise LedgerError("a finding needs a claim")

    entry = ledger_entry(brain=brain, key=key)
    number = max((int(record["id"][2:]) for record in findings(entry)), default=0) + 1
    identifier = f"F-{number:02d}"
    block = (
        f"\n### {identifier}: {claim}\n\n"
        f"- severity: {severity}\n"
        f"- found-by: {found_by}\n"
        f"- batch: {batch_cell}\n"
        "- status: open\n"
        "- fix:\n"
    )

    body = entry.document.body
    section_start = section_span(body=body, title="Findings")[0]
    section_end = sections.heading_after(body=body, start=section_start, depth=2)
    entry.document.body = body[:section_end].rstrip("\n") + "\n" + block + ("\n" if section_end < len(body) else "") + body[section_end:]
    save(brain=brain, entry=entry)

    return identifier


def set_finding(
    brain: store.Brain,
    key: str,
    identifier: str,
    changes: dict[str, str],
) -> None:
    changes = {field: checked(field=field, value=value) for field, value in changes.items()}

    entry = ledger_entry(brain=brain, key=key)
    body = entry.document.body
    span = finding_span(body=body, identifier=identifier)
    if span is None:
        raise LedgerError(f"{entry.name} has no finding {identifier}")

    start, end = span
    block = body[start:end]
    after = dict(bullets(block))
    after.update(changes)
    if after.get("status") == "fixed" and not after.get("fix"):
        raise LedgerError("a fixed finding names its commit, fix=<hash>")

    for field, value in changes.items():
        block = with_bullet(block=block, field=field, value=value)

    entry.document.body = body[:start] + block + body[end:]
    save(brain=brain, entry=entry)


def with_bullet(
    block: str,
    field: str,
    value: str,
) -> str:
    """The block with its `- field:` line saying `value`.

    The first such line outside code is rewritten. A block that lost the
    line gets it back, after the last bullet it still has, so a finding
    edited by hand can be put right through the tool.
    """
    line = f"- {field}: {value}"
    spans = sections.code_spans(block)
    lines = [match for match in BULLET.finditer(block) if not sections.in_code(spans=spans, position=match.start())]

    for match in lines:
        if match.group(1) == field:
            return block[: match.start()] + line + block[match.end() :]

    if lines:
        at = lines[-1].end()
        return block[:at] + "\n" + line + block[at:]

    heading_end = block.index("\n") if "\n" in block else len(block)
    return block[:heading_end] + "\n\n" + line + block[heading_end:]


def close(
    brain: store.Brain,
    key: str,
    stamp: str = "",
) -> None:
    entry = ledger_entry(brain=brain, key=key)
    if entry.field("status") == "closed":
        raise LedgerError(f"{entry.name} is already closed")

    still_open = [item for item in findings(entry) if (item.get("status") or "open") == "open"]
    if still_open:
        names = ", ".join(item["id"] for item in still_open)
        raise LedgerError(f"{names} still open, a ledger closes when every finding has landed")

    counts = tally(findings(entry))
    summary_end = end_of_section(body=entry.document.body, title="Summary")
    line = f"Closed with {counts}.\n\n"
    entry.document.body = (
        entry.document.body[:summary_end].rstrip("\n") + "\n\n" + line + entry.document.body[summary_end:]
    )
    entry.document.set(key="status", value="closed")
    save(brain=brain, entry=entry, stamp=stamp)


def findings(
    entry: store.Entry,
) -> list[dict]:
    body = entry.document.body
    found: list[dict] = []

    for match in finding_headings(body):
        start, end = finding_span(body=body, identifier=match.group(1)) or (match.start(), match.end())
        block = body[start:end]
        record = {"id": match.group(1), "claim": match.group(2)}
        record.update(bullets(block))
        found.append(record)

    return found


def bullets(
    block: str,
) -> dict[str, str]:
    """The `- name: value` lines of a block that sit outside code, each value as written.

    A name that appears twice counts once, by its first line, which is
    the line a change rewrites, so reading and writing agree.
    """
    spans = sections.code_spans(block)
    found: dict[str, str] = {}

    for match in BULLET.finditer(block):
        if not sections.in_code(spans=spans, position=match.start()):
            found.setdefault(match.group(1), match.group(2))

    return found


def finding_headings(
    body: str,
) -> list[re.Match]:
    """Every finding heading outside code, in order."""
    spans = sections.code_spans(body)

    return [match for match in FINDING.finditer(body) if not sections.in_code(spans=spans, position=match.start())]


def batches(
    entry: store.Entry,
) -> list[dict]:
    return [
        {"number": int(match.group(1)), "theme": match.group(2), "status": match.group(3), "ack": match.group(4)}
        for match in batch_rows(entry.document.body)
    ]


def batch_rows(
    body: str,
) -> list[re.Match]:
    """Every row of the batch table, the lines right under its header and nothing else."""
    return batch_table(body)[1]


def batch_table(
    body: str,
) -> tuple[re.Match, list[re.Match]]:
    """The batch table's header and its rows.

    The header is the first one in the Batches section outside code, and
    the rows are the lines directly under it, the way markdown reads a
    table. A row shaped line anywhere else in the section is refused
    rather than read or ignored, since a table a hand edit pulled apart
    would otherwise be numbered twice.
    """
    start, end = batches_section(body)
    spans = sections.code_spans(body)
    header = None

    for match in TABLE_HEADER.finditer(string=body, pos=start, endpos=end):
        if not sections.in_code(spans=spans, position=match.start()):
            header = match
            break

    if header is None:
        raise LedgerError("the ledger has no batch table")

    rows: list[re.Match] = []
    position = header.end()

    while position < end and body[position] == "\n":
        line_start = position + 1
        row = BATCH_ROW.match(string=body, pos=line_start, endpos=end)
        if row is None:
            if body[line_start:end].split("\n", 1)[0].lstrip().startswith("|"):
                raise LedgerError("a line of the batch table is not a whole row, a row is | number | theme | status | ack |")

            break

        rows.append(row)
        position = row.end()

    read = {row.start() for row in rows}
    for match in BATCH_ROW.finditer(string=body, pos=start, endpos=end):
        if match.start() not in read and not sections.in_code(spans=spans, position=match.start()):
            raise LedgerError("a batch row sits apart from the table, put it directly under the header")

    return header, rows


def batches_section(
    body: str,
) -> tuple[int, int]:
    """Where the Batches section's text starts and ends."""
    return section_span(body=body, title="Batches")


def section_span(
    body: str,
    title: str,
) -> tuple[int, int]:
    """Where the named section's text starts and ends, refused when the ledger has none."""
    found = sections.span(body=body, title=title)
    if found is None:
        raise LedgerError(f"the ledger has no {title} section")

    return found


def tally(
    items: list[dict],
) -> str:
    counts: dict[str, int] = {}
    for item in items:
        status = item.get("status") or schema.UNKNOWN
        counts[status] = counts.get(status, 0) + 1

    total = len(items)
    noun = "finding" if total == 1 else "findings"
    parts = ", ".join(f"{count} {status}" for status, count in counts.items())

    return f"{total} {noun}" + (f", {parts}" if parts else "")


def one_line(
    value: str,
    what: str,
) -> str:
    """The value trimmed, refused when it would break the record it goes into."""
    value = value.strip()
    if "\n" in value or "\r" in value:
        raise LedgerError(f"the {what} is one line")

    return value


def checked(
    field: str,
    value: str,
) -> str:
    """A finding's value as the record takes it, refused when the spec has no room for it."""
    if field not in FIELDS:
        raise LedgerError(f"a finding has no '{field}' field, its fields are {', '.join(FIELDS)}")

    value = one_line(value=value, what=field)
    if field == "severity" and value not in SEVERITIES:
        raise LedgerError(f"severity is {' or '.join(SEVERITIES)}, not '{value}'")

    if field == "found-by" and value not in FOUND_BY:
        raise LedgerError(f"found-by is review or hunter, not '{value}'")

    if field == "status" and value not in FINDING_STATUSES:
        raise LedgerError(f"a finding is {' or '.join(FINDING_STATUSES)}, not '{value}'")

    if field == "batch" and value and not re.fullmatch(pattern=r"[1-9][0-9]*", string=value):
        raise LedgerError(f"batch is a number from 1, or blank, not '{value}'")

    return value


def cell(
    value: str,
    what: str,
) -> str:
    """One line with no pipe, since the batch table's columns are pipes."""
    value = one_line(value=value, what=what)
    if "|" in value:
        raise LedgerError(f"the {what} cannot hold a pipe, the batch table's columns are pipes")

    return value


def ledger_entry(
    brain: store.Brain,
    key: str,
) -> store.Entry:
    try:
        entry = brain.find(key)
    except store.Ambiguous as clash:
        raise LedgerError(str(clash)) from clash

    if entry is None or entry.kind.name != "review":
        raise LedgerError(f"no review ledger answers to '{key}'")

    return entry


def save(
    brain: store.Brain,
    entry: store.Entry,
    stamp: str = "",
) -> None:
    entry.document.set(key="updated", value=stamp or date.today().isoformat())
    frontmatter.write(path=str(entry.path), document=entry.document)
    brain.refresh()


def finding_span(
    body: str,
    identifier: str,
) -> Optional[tuple[int, int]]:
    """Where one finding's block starts and ends, up to the next heading outside code."""
    for match in finding_headings(body):
        if match.group(1) != identifier:
            continue

        return match.start(), sections.heading_after(body=body, start=match.end())

    return None


def end_of_table(
    body: str,
) -> int:
    """The offset at the end of the last batch row's line, or of the table header's, before the line break."""
    header, rows = batch_table(body)

    return rows[-1].end() if rows else header.end()


def end_of_section(
    body: str,
    title: str,
) -> int:
    """The offset where the named section ends, at the next heading outside code."""
    return section_span(body=body, title=title)[1]


def is_ledger_body(
    body: str,
) -> bool:
    return all(sections.has(body=body, title=title) for title in ("Summary", "Batches", "Findings"))
