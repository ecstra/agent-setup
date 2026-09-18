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
BATCH_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|[ \t]*$",
    re.MULTILINE,
)

BATCH_HEADER = "| # | Theme | Status | Ack |\n|---|---|---|---|\n"

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

    entry = ledger_entry(brain, key)
    number = max((row["number"] for row in batches(entry)), default=0) + 1
    row = batch_row(number=number, theme=theme, status="pending", ack="") + "\n"

    body = entry.document.body
    table_end = end_of_table(body)
    entry.document.body = body[:table_end] + row + body[table_end:]
    save(brain, entry)

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

    entry = ledger_entry(brain, key)
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
    save(brain, entry)


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
    if severity not in SEVERITIES:
        raise LedgerError(f"severity is {' or '.join(SEVERITIES)}, not '{severity}'")

    if found_by not in FOUND_BY:
        raise LedgerError(f"found-by is review or hunter, not '{found_by}'")

    claim = one_line(value=claim, what="claim")
    if not claim:
        raise LedgerError("a finding needs a claim")

    entry = ledger_entry(brain, key)
    number = max((int(record["id"][2:]) for record in findings(entry)), default=0) + 1
    identifier = f"F-{number:02d}"
    block = (
        f"\n### {identifier}: {claim}\n\n"
        f"- severity: {severity}\n"
        f"- found-by: {found_by}\n"
        f"- batch: {batch or ''}\n"
        "- status: open\n"
        "- fix:\n"
    )

    entry.document.body = entry.document.body.rstrip("\n") + "\n" + block
    save(brain, entry)

    return identifier


def set_finding(
    brain: store.Brain,
    key: str,
    identifier: str,
    changes: dict[str, str],
) -> None:
    status = changes.get("status")
    if status and status not in FINDING_STATUSES:
        raise LedgerError(f"a finding is {' or '.join(FINDING_STATUSES)}, not '{status}'")

    if status == "fixed" and not changes.get("fix", "").strip():
        raise LedgerError("a fixed finding names its commit, fix=<hash>")

    entry = ledger_entry(brain, key)
    body = entry.document.body
    span = finding_span(body, identifier)
    if span is None:
        raise LedgerError(f"{entry.name} has no finding {identifier}")

    start, end = span
    block = body[start:end]

    for field, value in changes.items():
        line = re.search(rf"^- {re.escape(field)}:.*$", block, re.MULTILINE)
        if line is None:
            raise LedgerError(f"a finding carries no '{field}' line")

        block = block[: line.start()] + f"- {field}: {one_line(value=value, what=field)}" + block[line.end() :]

    entry.document.body = body[:start] + block + body[end:]
    save(brain, entry)


def close(
    brain: store.Brain,
    key: str,
    stamp: str = "",
) -> None:
    entry = ledger_entry(brain, key)
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
    save(brain, entry, stamp=stamp)


def findings(
    entry: store.Entry,
) -> list[dict]:
    body = entry.document.body
    found: list[dict] = []

    for match in finding_headings(body):
        start, end = finding_span(body=body, identifier=match.group(1)) or (match.start(), match.end())
        block = body[start:end]
        record = {"id": match.group(1), "claim": match.group(2)}
        record.update({name: value for name, value in BULLET.findall(sections.prose_of(block))})
        found.append(record)

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
    """Every row of the batch table, read from the Batches section and nowhere else."""
    start, end = batches_section(body)
    spans = sections.code_spans(body)

    return [
        match
        for match in BATCH_ROW.finditer(body, start, end)
        if not sections.in_code(spans=spans, position=match.start())
    ]


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
    """The offset just past the last batch row, or past the table header."""
    rows = batch_rows(body)
    if rows:
        return rows[-1].end() + 1

    start, end = batches_section(body)
    header_at = body.find(BATCH_HEADER, start, end)
    if header_at < 0:
        raise LedgerError("the ledger has no batch table")

    return header_at + len(BATCH_HEADER)


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
