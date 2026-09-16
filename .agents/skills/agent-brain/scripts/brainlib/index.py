"""Building every INDEX.md from the files it lists.

The indexes are generated, never hand edited. Each one keeps its own
frontmatter and gets a fresh body from the folder it describes, so an
index can never disagree with its folder for longer than one run.
"""

from datetime import date
from pathlib import Path
from typing import Callable

from . import frontmatter, schema, store

SPINE_INTRO = (
    "The spine. Read this first, then follow into the folder indexes.\n"
    "Built by the brain tool from the files it lists, so change those files\n"
    "rather than this one.\n"
)

SYSTEM_HOOK = "the rulebook every agent works by, reached through AGENTS.md"

SEVERITY_ORDER = ("breaks", "bug", "debt", "nit")


def build(
    brain: store.Brain,
) -> dict[Path, str]:
    """Every index path with the text it should hold right now."""
    wanted: dict[Path, str] = {
        brain.root / "INDEX.md": with_body(
            brain=brain,
            path=brain.root / "INDEX.md",
            body=spine_body(brain),
            name="agent-index",
            description="the spine of the agent directory, what exists and where",
        ),
    }

    for folder in schema.INDEXED_FOLDERS:
        kind = schema.kind_for_folder(folder)
        if kind is None:
            continue

        path = brain.root / folder / "INDEX.md"
        wanted[path] = with_body(
            brain=brain,
            path=path,
            body=folder_body(brain=brain, kind=kind),
            name=f"{folder}-index",
            description=f"index of {folder}, built from the folder",
        )

    return wanted


def stale(
    brain: store.Brain,
) -> list[Path]:
    """The indexes on disk that no longer match what build() would write."""
    found: list[Path] = []

    for path, text in build(brain).items():
        current = path.read_text(encoding="utf-8") if path.is_file() else ""
        if body_of(current) != body_of(text):
            found.append(path)

    return found


def write(
    brain: store.Brain,
    stamp: str = "",
) -> list[Path]:
    """Rewrite the stale indexes and hand back the ones that changed."""
    stamp = stamp or date.today().isoformat()
    changed: list[Path] = []

    for path in stale(brain):
        document = frontmatter.parse(build(brain)[path])
        document.set(key="updated", value=stamp)
        path.parent.mkdir(parents=True, exist_ok=True)
        frontmatter.write(path=str(path), document=document)
        changed.append(path)

    return changed


def with_body(
    brain: store.Brain,
    path: Path,
    body: str,
    name: str,
    description: str,
) -> str:
    """The index's existing frontmatter, or a fresh one, over the new body.

    An index somebody pasted over, or truncated, gets the fresh one, so a
    broken index is rebuilt by the next run instead of stopping it.
    """
    document = frontmatter.Document(
        lines=[
            f"name: {name}",
            "kind: doc",
            f"description: {description}",
            f"updated: {date.today().isoformat()}",
            "links: []",
        ],
        body="",
    )

    if path.is_file():
        try:
            document = frontmatter.read(str(path))
        except frontmatter.FrontmatterError:
            pass

    document.body = "\n" + body

    return frontmatter.render(document)


def body_of(
    text: str,
) -> str:
    try:
        return frontmatter.parse(text).body
    except frontmatter.FrontmatterError:
        return text


def spine_body(
    brain: store.Brain,
) -> str:
    lines = ["# Index", "", SPINE_INTRO.rstrip("\n"), "", "## The directory itself", ""]
    lines.append(f"- [SYSTEM.md](SYSTEM.md), {SYSTEM_HOOK}")

    for relative in kit_listing(brain):
        lines.append(f"- [{relative}]({relative}), {hook_of(brain.root / relative)}")

    lines += ["", "## The knowledge", ""]
    lines.append(spine_line(brain, "doc", "the knowledge library", count_docs))

    lines += ["", "## The trackers", ""]
    lines.append(spine_line(brain, "todo", "the work tracker", count_by_status))
    lines.append(spine_line(brain, "bug", "the defect tracker", count_bugs))
    lines.append(spine_line(brain, "decision", "the decision record", count_by_status))
    lines.append(spine_line(brain, "review", "code review ledgers", count_by_status))

    lines += ["", "## Memory and handovers", ""]
    lines.append(spine_line(brain, "memory", "project facts", count_plain))
    lines.append(handover_line(brain))

    return "\n".join(lines) + "\n"


def kit_listing(
    brain: store.Brain,
) -> list[str]:
    """The kit files the spine names, in the order a reader meets them."""
    listing = ["README.md", "house-rules.md", "spec/conventions.md"]

    for kind in schema.KINDS.values():
        spec = f"spec/{kind.folder}.md"
        if spec not in listing and (brain.root / spec).is_file():
            listing.append(spec)

    return [relative for relative in listing if (brain.root / relative).is_file()]


def hook_of(
    path: Path,
) -> str:
    try:
        return frontmatter.read(str(path)).get("description") or path.name
    except frontmatter.FrontmatterError:
        return path.name


def spine_line(
    brain: store.Brain,
    kind_name: str,
    label: str,
    counter: Callable[[list[store.Entry]], str],
) -> str:
    kind = schema.kind_named(kind_name)
    entries = brain.entries_of(kind)
    summary = counter(entries) if entries else "empty"

    return f"- [{kind.folder}/INDEX.md]({kind.folder}/INDEX.md), {label}: {summary}"


def handover_line(
    brain: store.Brain,
) -> str:
    entries = brain.entries_of(schema.kind_named("handover"))
    if not entries:
        return "- handover/ is born with its first handoff (spec/handover.md)"

    noun = "handover" if len(entries) == 1 else "handovers"

    return f"- handover/, {len(entries)} {noun}, newest [{entries[-1].name}]({entries[-1].relative})"


def count_docs(
    entries: list[store.Entry],
) -> str:
    noun = "doc" if len(entries) == 1 else "docs"

    return f"{len(entries)} {noun}"


def count_plain(
    entries: list[store.Entry],
) -> str:
    noun = "fact" if len(entries) == 1 else "facts"

    return f"{len(entries)} {noun}"


def count_by_status(
    entries: list[store.Entry],
) -> str:
    counts: dict[str, int] = {}

    for entry in entries:
        status = entry.field("status") or "unknown"
        counts[status] = counts.get(status, 0) + 1

    return ", ".join(f"{count} {status}" for status, count in counts.items())


def count_bugs(
    entries: list[store.Entry],
) -> str:
    open_ones = [entry for entry in entries if entry.field("status") in ("open", "branched")]
    parts = [f"{len(open_ones)} open"]
    if open_ones:
        by_severity: dict[str, int] = {}
        for entry in open_ones:
            severity = entry.field("severity") or "unknown"
            by_severity[severity] = by_severity.get(severity, 0) + 1

        inner = ", ".join(f"{by_severity[s]} {s}" for s in SEVERITY_ORDER if s in by_severity)
        parts[0] += f" ({inner})"

    for status in ("fixed", "wontfix"):
        count = sum(1 for entry in entries if entry.field("status") == status)
        if count:
            parts.append(f"{count} {status}")

    return ", ".join(parts)


def folder_body(
    brain: store.Brain,
    kind: schema.Kind,
) -> str:
    renderers = {
        "doc": docs_body,
        "memory": memory_body,
        "todo": todos_body,
        "bug": bugs_body,
        "decision": decisions_body,
        "review": reviews_body,
    }

    return renderers[kind.name](brain.entries_of(kind))


def line_for(
    entry: store.Entry,
    from_folder: Path,
) -> str:
    label = entry.identifier or entry.name
    relative = entry.path.relative_to(from_folder)
    hook = entry.field("description") or entry.name

    return f"- [{label}]({relative}), {hook}"


def header(
    title: str,
    intro: str,
    spec: str,
) -> list[str]:
    return [
        f"# {title}",
        "",
        intro,
        f"Filed per [spec/{spec}.md](../spec/{spec}.md).",
        "Built by the brain tool from the folder it lists.",
        "",
    ]


def docs_body(
    entries: list[store.Entry],
) -> str:
    lines = header(
        title="Docs Index",
        intro="The knowledge library, one line per doc, grouped by category folder.",
        spec="docs",
    )
    if not entries:
        lines.append("Nothing here yet.")
        return "\n".join(lines) + "\n"

    folder = entries[0].root / "docs"
    by_category: dict[str, list[store.Entry]] = {}
    for entry in entries:
        category = entry.path.parent.relative_to(folder)
        key = str(category) if str(category) != "." else "uncategorized"
        by_category.setdefault(key, []).append(entry)

    for category in sorted(by_category):
        lines += [f"## {category}", ""]
        lines += [line_for(entry, folder) for entry in by_category[category]]
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def memory_body(
    entries: list[store.Entry],
) -> str:
    lines = header(
        title="Memory Index",
        intro="Project facts, one line each.",
        spec="memory",
    )
    if not entries:
        lines.append("Nothing here yet.")
        return "\n".join(lines) + "\n"

    folder = entries[0].root / "memory"
    lines += [line_for(entry, folder) for entry in sorted(entries, key=lambda e: e.name)]

    return "\n".join(lines) + "\n"


def todos_body(
    entries: list[store.Entry],
) -> str:
    lines = header(
        title="Todos Index",
        intro=(
            "Open items first, grouped by area. Done and dropped are summarized\n"
            "by area with counts."
        ),
        spec="todos",
    )
    if not entries:
        lines.append("Nothing here yet.")
        return "\n".join(lines) + "\n"

    folder = entries[0].root / "todos"
    open_ones = [entry for entry in entries if entry.field("status") == "open"]
    closed = [entry for entry in entries if entry.field("status") != "open"]

    lines += ["## Open", ""]
    if not open_ones:
        lines += ["Nothing open.", ""]
    for area, group in grouped(open_ones, "area").items():
        lines += [f"### {area}", ""]
        lines += [line_for(entry, folder) for entry in group]
        lines.append("")

    lines += ["## Done and dropped", ""]
    if not closed:
        lines.append("Nothing closed yet.")
    for area, group in grouped(closed, "area").items():
        done = sum(1 for entry in group if entry.field("status") == "done")
        dropped = len(group) - done
        lines.append(f"- {area}: {done} done, {dropped} dropped")

    return "\n".join(lines).rstrip("\n") + "\n"


def bugs_body(
    entries: list[store.Entry],
) -> str:
    lines = header(
        title="Bugs Index",
        intro="Open bugs first, grouped by severity. Fixed and wontfix below.",
        spec="bugs",
    )
    if not entries:
        lines.append("Nothing here yet.")
        return "\n".join(lines) + "\n"

    folder = entries[0].root / "bugs"
    open_ones = [entry for entry in entries if entry.field("status") in ("open", "branched")]

    lines += ["## Open", ""]
    if not open_ones:
        lines += ["Nothing open.", ""]
    for severity in SEVERITY_ORDER:
        group = [entry for entry in open_ones if entry.field("severity") == severity]
        if not group:
            continue

        lines += [f"### {severity}", ""]
        for entry in group:
            suffix = " (branched)" if entry.field("status") == "branched" else ""
            lines.append(line_for(entry, folder) + suffix)
        lines.append("")

    for status in ("fixed", "wontfix"):
        group = [entry for entry in entries if entry.field("status") == status]
        if not group:
            continue

        lines += [f"## {status.title()}", ""]
        lines += [line_for(entry, folder) for entry in group]
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def decisions_body(
    entries: list[store.Entry],
) -> str:
    lines = header(
        title="Decisions Index",
        intro="Every decision taken, newest first.",
        spec="decisions",
    )
    if not entries:
        lines.append("Nothing here yet.")
        return "\n".join(lines) + "\n"

    folder = entries[0].root / "decisions"
    newest_first = sorted(
        entries,
        key=lambda e: (e.field("date") or "", e.number or 0),
        reverse=True,
    )

    for entry in newest_first:
        line = line_for(entry, folder)
        if entry.field("status") == "superseded":
            line += f" (superseded by {entry.field('superseded-by') or 'a later one'})"
        lines.append(line)

    return "\n".join(lines) + "\n"


def reviews_body(
    entries: list[store.Entry],
) -> str:
    lines = header(
        title="Reviews Index",
        intro="Code review ledgers, open first.",
        spec="reviews",
    )
    if not entries:
        lines.append("Nothing here yet.")
        return "\n".join(lines) + "\n"

    folder = entries[0].root / "reviews"
    for status in ("open", "closed"):
        group = [entry for entry in entries if entry.field("status") == status]
        if not group:
            continue

        lines += [f"## {status.title()}", ""]
        lines += [line_for(entry, folder) for entry in sorted(group, key=lambda e: e.name, reverse=True)]
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def grouped(
    entries: list[store.Entry],
    field: str,
) -> dict[str, list[store.Entry]]:
    groups: dict[str, list[store.Entry]] = {}

    for entry in entries:
        groups.setdefault(entry.field(field) or "unsorted", []).append(entry)

    return dict(sorted(groups.items()))
