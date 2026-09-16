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
BATCH_ROW = re.compile(r"^\| (\d+) \| (.*?) \| (.*?) \| (.*?) \|[ \t]*$", re.MULTILINE)

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
    entry = ledger_entry(brain, key)
    number = len(batches(entry)) + 1
    row = f"| {number} | {theme} | pending | |\n"

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
) -> None:
    if status and status not in BATCH_STATUSES:
        raise LedgerError(f"a batch is {' or '.join(BATCH_STATUSES)}, not '{status}'")

    entry = ledger_entry(brain, key)
    body = entry.document.body
    replaced = False

    for match in BATCH_ROW.finditer(body):
        if int(match.group(1)) != number:
            continue

        theme = match.group(2)
        new_status = status or match.group(3)
        new_ack = ack or match.group(4)
        row = f"| {number} | {theme} | {new_status} | {new_ack} |"
        body = body[: match.start()] + row + body[match.end() :]
        replaced = True
        break

    if not replaced:
        raise LedgerError(f"{entry.name} has no batch {number}")

    entry.document.body = body
    save(brain, entry)


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

    entry = ledger_entry(brain, key)
    number = len(findings(entry)) + 1
    identifier = f"F-{number:02d}"
    block = (
        f"\n### {identifier}: {claim.strip()}\n\n"
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

    if status == "fixed" and not changes.get("fix"):
        raise LedgerError("a fixed finding names its commit, fix=<hash>")

    entry = ledger_entry(brain, key)
    body = entry.document.body
    span = finding_span(body, identifier)
    if span is None:
        raise LedgerError(f"{entry.name} has no finding {identifier}")

    start, end = span
    block = body[start:end]

    for field, value in changes.items():
        pattern = re.compile(rf"^- {re.escape(field)}:.*$", re.MULTILINE)
        if pattern.search(block) is None:
            raise LedgerError(f"a finding carries no '{field}' line")

        block = pattern.sub(f"- {field}: {value}", block, count=1)

    entry.document.body = body[:start] + block + body[end:]
    save(brain, entry)


def close(
    brain: store.Brain,
    key: str,
    stamp: str = "",
) -> None:
    entry = ledger_entry(brain, key)
    still_open = [item for item in findings(entry) if item["status"] == "open"]
    if still_open:
        names = ", ".join(item["id"] for item in still_open)
        raise LedgerError(f"{names} still open, a ledger closes when every finding has landed")

    counts = tally(findings(entry))
    summary_end = end_of_section(entry.document.body, "Summary")
    line = f"Closed with {counts}.\n"
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

    for match in FINDING.finditer(body):
        span = finding_span(body, match.group(1))
        block = body[span[0] : span[1]] if span else ""
        record = {"id": match.group(1), "claim": match.group(2)}
        record.update({name: value for name, value in BULLET.findall(block)})
        found.append(record)

    return found


def batches(
    entry: store.Entry,
) -> list[dict]:
    return [
        {"number": int(number), "theme": theme, "status": status, "ack": ack}
        for number, theme, status, ack in BATCH_ROW.findall(entry.document.body)
    ]


def tally(
    items: list[dict],
) -> str:
    counts: dict[str, int] = {}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1

    total = len(items)
    noun = "finding" if total == 1 else "findings"
    parts = ", ".join(f"{count} {status}" for status, count in counts.items())

    return f"{total} {noun}" + (f", {parts}" if parts else "")


def ledger_entry(
    brain: store.Brain,
    key: str,
) -> store.Entry:
    entry = brain.find(key)
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
    """Where one finding's block starts and ends, up to the next heading."""
    for match in FINDING.finditer(body):
        if match.group(1) != identifier:
            continue

        rest = body[match.end() :]
        following = re.search(r"^#{1,6}[ \t]", rest, re.MULTILINE)
        end = match.end() + (following.start() if following else len(rest))

        return match.start(), end

    return None


def end_of_table(
    body: str,
) -> int:
    """The offset just past the last batch row, or past the table header."""
    rows = list(BATCH_ROW.finditer(body))
    if rows:
        return rows[-1].end() + 1

    header_at = body.find(BATCH_HEADER)
    if header_at < 0:
        raise LedgerError("the ledger has no batch table")

    return header_at + len(BATCH_HEADER)


def end_of_section(
    body: str,
    title: str,
) -> int:
    """The offset where the named section ends, at the next heading."""
    match = re.search(rf"^## {re.escape(title)}[ \t]*$", body, re.MULTILINE)
    if match is None:
        raise LedgerError(f"the ledger has no {title} section")

    rest = body[match.end() :]
    following = re.search(r"^#{1,6}[ \t]", rest, re.MULTILINE)

    return match.end() + (following.start() if following else len(rest))


def is_ledger_body(
    body: str,
) -> bool:
    return all(sections.has(body=body, title=title) for title in ("Summary", "Batches", "Findings"))
