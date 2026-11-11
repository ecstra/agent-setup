"""Building every INDEX.md from the files it lists.

The indexes are generated, never hand edited. The tool owns the whole
file, frontmatter included, so an index that disagrees with its folder
in its body or in its header is rebuilt on the next run. An index that
still says what the tool would write is left alone, which is how its
`updated` date moves only when the rest of the file does.
"""

from datetime import date
from pathlib import Path
from typing import Callable, Optional

from . import frontmatter, schema, store

SPINE_INTRO = "The spine. Read this first, then follow into the folder indexes.\nBuilt by the brain tool from the files it lists, so change those files\nrather than this one.\n"

SYSTEM_HOOK = "the rulebook every agent works by, reached through AGENTS.md"
VERSION_HOOK = "the Agent Setup release this brain is on"

# The ways a bug stops being open, in the order the index lists them.
CLOSED_BUG = ("fixed", "wontfix", "refiled")

SPINE_DESCRIPTION = "the spine of the agent directory, what exists and where"
SPINE_LINKS = ("README.md", "house-rules.md")

# The handover folder's line never changes, since the folder holds
# notes that the session start hook removes, so counting them would
# have the spine change under every session.
HANDOVER_LINE = f"- {schema.HANDOVER_FOLDER}/, the notes brain handover leaves for the next session, which the session start hook reads once and removes"


def build(
    brain: store.Brain,
) -> dict[Path, str]:
    """Every index path with the text it should hold right now.

    The spine is left out while the skills folder cannot be listed,
    since it cannot be built true then. Doctor names that, and a write
    leaves the file as it is rather than fail a command that has
    already filed its change.
    """
    wanted: dict[Path, str] = {}
    spine = spine_text(brain)
    if spine is not None:
        wanted[brain.root / "INDEX.md"] = render_index(
            brain=brain,
            body=spine,
            name="agent-index",
            description=SPINE_DESCRIPTION,
            links=list(SPINE_LINKS),
        )

    for kind in schema.KINDS.values():
        path = brain.root / kind.folder / "INDEX.md"
        wanted[path] = render_index(
            brain=brain,
            body=folder_body(brain=brain, kind=kind),
            name=f"{kind.folder}-index",
            description=kind.index_description,
            links=["INDEX.md"],
        )

    return wanted


def stale(
    brain: store.Brain,
) -> list[Path]:
    """The indexes on disk that no longer match what build() would write."""
    return stale_among(build(brain))


def spine_text(
    brain: store.Brain,
) -> Optional[str]:
    """The spine's body, or None while the skills folder cannot be listed and no true spine can be built."""
    try:
        return spine_body(brain)
    except OSError:
        return None


def stale_among(
    wanted: dict[Path, str],
) -> list[Path]:
    """The paths in one build whose file on disk says something else."""
    found: list[Path] = []

    for path, text in wanted.items():
        if fingerprint(current_text(path)) != fingerprint(text):
            found.append(path)

    return found


def fingerprint(
    text: str,
) -> tuple[list[str], str]:
    """Everything about an index but its date, which follows the rest."""
    try:
        document = frontmatter.parse(text)
    except frontmatter.FrontmatterError:
        return [], text

    lines = [line for line in document.lines if frontmatter.split_field(line)[0] != "updated"]

    return lines, document.body


def current_text(
    path: Path,
) -> str:
    """What the index holds now, or nothing when it is missing or unreadable."""
    if not store.readable_file(path):
        return ""

    try:
        return frontmatter.load(str(path))
    except frontmatter.FrontmatterError:
        return ""


def write(
    brain: store.Brain,
    stamp: str = "",
) -> list[Path]:
    """Rewrite the stale indexes and hand back the ones that changed.

    One build serves every index, since building reads the whole brain.
    """
    wanted = build(brain)

    # an index that cannot be written is passed over for the ones after it, whose folders may well be writable, and its failure is raised once every stale index has had its turn
    written: list[Path] = []
    first_failure: Optional[OSError] = None
    for path in stale_among(wanted):
        try:
            written.append(write_one(path=path, text=wanted[path], stamp=stamp))
        except OSError as error:
            first_failure = first_failure or error

    if first_failure is not None:
        raise first_failure

    return written


def write_one(
    path: Path,
    text: str,
    stamp: str = "",
) -> Path:
    """Write one index as built, stamped today unless told otherwise."""
    document = frontmatter.parse(text)
    document.set(key="updated", value=stamp or date.today().isoformat())
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter.write(path=str(path), document=document)

    return path


def render_index(
    brain: store.Brain,
    body: str,
    name: str,
    description: str,
    links: list[str],
) -> str:
    """The whole index as the tool writes it, header and body.

    The date here is a placeholder: `write` stamps the real one and
    `fingerprint` ignores it. A link to a file of Agent Setup's is carried only while
    that file exists, so a project that dropped one does not get a
    dangling link rebuilt forever. The link to the spine is always
    carried, since the tool writes the spine in the same run.
    """
    present = [link for link in links if link == "INDEX.md" or store.readable_file(brain.root / link)]
    document = frontmatter.Document(
        lines=[
            f"name: {name}",
            "kind: doc",
            f"description: {description}",
            f"updated: {date.today().isoformat()}",
            f"links: {frontmatter.render_list(present)}",
        ],
        body="\n" + body,
    )

    return frontmatter.render(document)


def spine_body(
    brain: store.Brain,
) -> str:
    lines = ["# Index", "", SPINE_INTRO.rstrip("\n"), "", "## The directory itself", ""]
    lines.append(f"- [SYSTEM.md](SYSTEM.md), {SYSTEM_HOOK}")

    for relative in kit_listing(brain):
        lines.append(f"- [{relative}]({relative}), {hook_of(brain.root / relative)}")

    shipped = store.kit_skills_shipped(brain.root)
    skills = [(f"{schema.SKILLS}/{skill.name}/{schema.SKILL_FILE}", skill.hook) for skill in schema.KIT_SKILLS if skill.name in shipped]
    skills += [
        (
            f"{schema.SKILLS}/{name}/{schema.SKILL_FILE}",
            hook_of(
                path=brain.root / schema.SKILLS / name / schema.SKILL_FILE,
                fallback=f"the project's own {name} skill",
            ),
        )
        for name in store.project_skills(
            brain=brain.root,
            shipped=shipped,
        )
    ]

    for relative, hook in (*skills, (schema.VERSION_FILE, VERSION_HOOK)):
        if store.readable_file(brain.root / relative):
            lines.append(f"- [{relative}]({relative}), {hook}")

    lines += ["", "## The rules", ""]
    lines.append(spine_line(brain=brain, kind_name="rule", label="the project's own rules, each a system instruction", counter=count_rules))

    lines += ["", "## The knowledge", ""]
    lines.append(spine_line(brain=brain, kind_name="doc", label="the knowledge library", counter=count_docs))

    lines += ["", "## The trackers", ""]
    lines.append(spine_line(brain=brain, kind_name="plan", label="the plans", counter=count_by_status))
    lines.append(spine_line(brain=brain, kind_name="build-spec", label="the build specs", counter=count_by_status))
    lines.append(spine_line(brain=brain, kind_name="todo", label="the work tracker", counter=count_by_status))
    lines.append(spine_line(brain=brain, kind_name="bug", label="the defect tracker", counter=count_bugs))
    lines.append(spine_line(brain=brain, kind_name="decision", label="the decision record", counter=count_by_status))
    lines.append(spine_line(brain=brain, kind_name="review", label="code review ledgers", counter=count_by_status))

    lines += ["", "## Memory and the handover", ""]
    lines.append(spine_line(brain=brain, kind_name="memory", label="project facts", counter=count_plain))
    lines.append(HANDOVER_LINE)

    return "\n".join(lines) + "\n"


def kit_listing(
    brain: store.Brain,
) -> list[str]:
    """Agent Setup's files the spine names, in the order a reader meets them."""
    listing = ["README.md", "house-rules.md"]

    return [relative for relative in listing if store.readable_file(brain.root / relative)]


def hook_of(
    path: Path,
    fallback: str = "",
) -> str:
    """The description a file's header carries, else the fallback, else the file's name."""
    try:
        description = frontmatter.read(str(path)).get("description")
    except frontmatter.FrontmatterError:
        description = None

    return description or fallback or path.name


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
        status = entry.field("status") or schema.UNKNOWN
        counts[status] = counts.get(status, 0) + 1

    return ", ".join(f"{count} {status}" for status, count in counts.items())


def severity_of(
    entry: store.Entry,
) -> str:
    """A known severity, or the one word for anything else."""
    severity = entry.field("severity")
    return severity if severity in schema.SEVERITIES else schema.UNKNOWN


def count_bugs(
    entries: list[store.Entry],
) -> str:
    open_ones = [entry for entry in entries if entry.field("status") in ("open", "branched")]
    parts = [f"{len(open_ones)} open"]
    if open_ones:
        by_severity: dict[str, int] = {}
        for entry in open_ones:
            severity = severity_of(entry)
            by_severity[severity] = by_severity.get(severity, 0) + 1

        inner = ", ".join(f"{by_severity[s]} {s}" for s in (*schema.SEVERITIES, schema.UNKNOWN) if s in by_severity)
        parts[0] += f" ({inner})"

    for status in CLOSED_BUG:
        count = sum(1 for entry in entries if entry.field("status") == status)
        if count:
            parts.append(f"{count} {status}")

    return ", ".join(parts)


def folder_body(
    brain: store.Brain,
    kind: schema.Kind,
) -> str:
    return RENDERERS[kind.name](entries=brain.entries_of(kind))


def line_for(
    entry: store.Entry,
    from_folder: Path,
) -> str:
    label = entry.identifier or entry.name
    # a markdown link takes forward slashes on every system
    relative = entry.path.relative_to(from_folder).as_posix()
    hook = entry.field("description") or entry.name

    return f"- [{label}]({relative}), {hook}"


def header(
    title: str,
    intro: str,
) -> list[str]:
    return [f"# {title}", "", intro, "Built by the brain tool from the folder it lists.", ""]


def docs_body(
    entries: list[store.Entry],
) -> str:
    lines = header(
        title="Docs Index",
        intro="The knowledge library, one line per doc, grouped by category folder.",
    )
    if not entries:
        lines.append("Nothing here yet.")
        return "\n".join(lines) + "\n"

    folder = entries[0].root / "docs"
    by_category: dict[str, list[store.Entry]] = {}
    for entry in entries:
        category = entry.path.parent.relative_to(folder).as_posix()
        key = category if category != "." else "uncategorized"
        by_category.setdefault(key, []).append(entry)

    for category in sorted(by_category):
        lines += [f"## {category}", ""]
        lines += [line_for(entry=entry, from_folder=folder) for entry in by_category[category]]
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def rules_body(
    entries: list[store.Entry],
) -> str:
    lines = header(
        title="Rules Index",
        intro="The project's own rules, one line each, every one a system instruction AGENTS.md imports.",
    )
    if not entries:
        lines.append("Nothing here yet.")
        return "\n".join(lines) + "\n"

    folder = entries[0].root / "rules"
    lines += [line_for(entry=entry, from_folder=folder) for entry in sorted(entries, key=lambda e: (e.path.name != "project.md", e.name))]

    return "\n".join(lines) + "\n"


def count_rules(
    entries: list[store.Entry],
) -> str:
    noun = "rule" if len(entries) == 1 else "rules"

    return f"{len(entries)} {noun}"


def memory_body(
    entries: list[store.Entry],
) -> str:
    lines = header(
        title="Memory Index",
        intro="Project facts, one line each.",
    )
    if not entries:
        lines.append("Nothing here yet.")
        return "\n".join(lines) + "\n"

    folder = entries[0].root / "memory"
    lines += [line_for(entry=entry, from_folder=folder) for entry in sorted(entries, key=lambda e: e.name)]

    return "\n".join(lines) + "\n"


def todos_body(
    entries: list[store.Entry],
) -> str:
    lines = header(
        title="Todos Index",
        intro=("Open items first, grouped by area. Done, dropped and refiled are\nsummarized by area with counts."),
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
    for area, group in grouped(entries=open_ones, field="area").items():
        lines += [f"### {area}", ""]
        lines += [line_for(entry=entry, from_folder=folder) for entry in group]
        lines.append("")

    lines += ["## Closed", ""]
    if not closed:
        lines.append("Nothing closed yet.")
    for area, group in grouped(entries=closed, field="area").items():
        done = sum(1 for entry in group if entry.field("status") == "done")
        dropped = sum(1 for entry in group if entry.field("status") == "dropped")
        refiled = sum(1 for entry in group if entry.field("status") == "refiled")
        unknown = len(group) - done - dropped - refiled
        summary = f"- {area}: {done} done, {dropped} dropped"
        if refiled:
            summary += f", {refiled} refiled"
        if unknown:
            summary += f", {unknown} {schema.UNKNOWN}"
        lines.append(summary)

    return "\n".join(lines).rstrip("\n") + "\n"


def bugs_body(
    entries: list[store.Entry],
) -> str:
    lines = header(
        title="Bugs Index",
        intro="Open bugs first, grouped by severity. Fixed, wontfix and refiled below.",
    )
    if not entries:
        lines.append("Nothing here yet.")
        return "\n".join(lines) + "\n"

    folder = entries[0].root / "bugs"
    open_ones = [entry for entry in entries if entry.field("status") in ("open", "branched")]

    lines += ["## Open", ""]
    if not open_ones:
        lines += ["Nothing open.", ""]
    for severity in (*schema.SEVERITIES, schema.UNKNOWN):
        group = [entry for entry in open_ones if severity_of(entry) == severity]
        if not group:
            continue

        lines += [f"### {severity}", ""]
        for entry in group:
            suffix = " (branched)" if entry.field("status") == "branched" else ""
            lines.append(line_for(entry=entry, from_folder=folder) + suffix)
        lines.append("")

    for status in CLOSED_BUG:
        group = [entry for entry in entries if entry.field("status") == status]
        if not group:
            continue

        lines += [f"## {status.title()}", ""]
        lines += [line_for(entry=entry, from_folder=folder) for entry in group]
        lines.append("")

    stray = [entry for entry in entries if entry.field("status") not in ("open", "branched", *CLOSED_BUG)]
    if stray:
        lines += [f"## {schema.UNKNOWN.title()}", ""]
        lines += [line_for(entry=entry, from_folder=folder) for entry in stray]
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def decisions_body(
    entries: list[store.Entry],
) -> str:
    lines = header(
        title="Decisions Index",
        intro="Every decision taken, newest first.",
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
        line = line_for(entry=entry, from_folder=folder)
        if entry.field("status") == "superseded":
            line += f" (superseded by {entry.field('superseded-by') or 'a later one'})"
        lines.append(line)

    return "\n".join(lines) + "\n"


def plans_body(
    entries: list[store.Entry],
) -> str:
    lines = header(
        title="Plans Index",
        intro="The plans, each a goal with its steps, open first.",
    )
    if not entries:
        lines.append("Nothing here yet.")
        return "\n".join(lines) + "\n"

    folder = entries[0].root / "plans"
    for status in ("open", "done", "dropped", schema.UNKNOWN):
        if status == schema.UNKNOWN:
            group = [entry for entry in entries if entry.field("status") not in ("open", "done", "dropped")]
        else:
            group = [entry for entry in entries if entry.field("status") == status]
        if not group:
            continue

        lines += [f"## {status.title()}", ""]
        lines += [line_for(entry=entry, from_folder=folder) for entry in sorted(group, key=lambda e: e.name)]
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def build_specs_body(
    entries: list[store.Entry],
) -> str:
    lines = header(
        title="Build Specs Index",
        intro="One build spec per branch, what it builds and how it proves it, open first.",
    )
    if not entries:
        lines.append("Nothing here yet.")
        return "\n".join(lines) + "\n"

    folder = entries[0].root / "build-specs"
    statuses = ("draft", "acked", "closed", "dropped")
    for status in (*statuses, schema.UNKNOWN):
        if status == schema.UNKNOWN:
            group = [entry for entry in entries if entry.field("status") not in statuses]
        else:
            group = [entry for entry in entries if entry.field("status") == status]
        if not group:
            continue

        lines += [f"## {status.title()}", ""]
        # by the id's number, since an id runs past three digits, and a spec with no id by its name after every one with an id, where its lower case name sorted already
        lines += [line_for(entry=entry, from_folder=folder) for entry in sorted(group, key=lambda e: (e.number is None, e.number or 0, e.name))]
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def reviews_body(
    entries: list[store.Entry],
) -> str:
    lines = header(
        title="Reviews Index",
        intro="Code review ledgers, open first.",
    )
    if not entries:
        lines.append("Nothing here yet.")
        return "\n".join(lines) + "\n"

    folder = entries[0].root / "reviews"
    for status in ("open", "closed", schema.UNKNOWN):
        if status == schema.UNKNOWN:
            group = [entry for entry in entries if entry.field("status") not in ("open", "closed")]
        else:
            group = [entry for entry in entries if entry.field("status") == status]
        if not group:
            continue

        lines += [f"## {status.title()}", ""]
        lines += [line_for(entry=entry, from_folder=folder) for entry in sorted(group, key=lambda e: e.name, reverse=True)]
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


# The body writer for each kind, every one of which carries an INDEX.md.
# A kind added to the schema needs an entry here, and a test holds the
# two tables together.
RENDERERS: dict[str, Callable[..., str]] = {
    "doc": docs_body,
    "memory": memory_body,
    "todo": todos_body,
    "bug": bugs_body,
    "decision": decisions_body,
    "plan": plans_body,
    "build-spec": build_specs_body,
    "review": reviews_body,
    "rule": rules_body,
}


def grouped(
    entries: list[store.Entry],
    field: str,
) -> dict[str, list[store.Entry]]:
    groups: dict[str, list[store.Entry]] = {}

    for entry in entries:
        groups.setdefault(entry.field(field) or "unsorted", []).append(entry)

    return dict(sorted(groups.items()))
