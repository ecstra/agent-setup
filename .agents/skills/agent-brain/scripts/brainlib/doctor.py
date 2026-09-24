"""Checking the whole brain, fixing what is mechanical, flagging the rest.

Every check is a function that reads the brain and reports findings. A
finding that a machine can put right carries its own repair, and `run`
applies those before it reports, so what comes back is only what needs a
person or an agent to decide.
"""

import errno
import os
import re
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Optional

from . import autoack, frontmatter, index, links, schema, sections, steps, store, style, task, writes

SKIP_DIRS: frozenset[str] = frozenset({schema.SKILLS, ".worktrees"})

# A header block the parser refuses, taken off by its fences alone so
# the prose under it is still read.
HEADER_BLOCK = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)

MACHINE_PATH = re.compile(r"(/Users/|/home/|[A-Z]:\\)")

SECRET_SHAPES = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"),
    re.compile(r"(?i)\b(password|passwd|secret|token)\s*[:=]\s*\S{6,}"),
)

SKILL_LINKS = Path(".claude") / schema.SKILLS
SKILL_HOMES = Path(".agents") / schema.SKILLS

# How many repair passes one --fix may take. Two is the longest chain
# the checks can form, a name put right and then its index rebuilt.
PASSES = 5


@dataclass
class Finding:
    """One thing wrong, where it is, and whether the tool can put it right."""

    path: str
    check: str
    message: str
    repair: Optional[Callable[[], None]] = None

    @property
    def fixable(self) -> bool:
        return self.repair is not None

    def line(self) -> str:
        where = self.path or "."
        mark = "fixable" if self.fixable else "flag"

        return f"{where}: {self.check}: {self.message} [{mark}]"

    def as_dict(self) -> dict:
        """The finding as plain data, for the JSON form of doctor."""
        return {
            "path": self.path,
            "check": self.check,
            "message": self.message,
            "fixable": self.fixable,
        }


def run(
    brain: store.Brain,
    fix: bool = False,
) -> list[Finding]:
    """Every finding in the brain, after repairs when `fix` is set.

    Repairs run in passes. One pass applies every repair on offer, then
    the brain is read again, since one repair changes what another check
    sees, an index built before a name was put right for one. It stops
    when nothing fixable is left or a pass changed nothing. A repair
    that fails turns its finding into a flag that carries the reason.
    """
    found = check_all(brain)
    if not fix:
        return found

    failed: dict[tuple[str, str, str], str] = {}
    attempted: set[tuple[str, str, str]] = set()

    for _ in range(PASSES):
        pending = [finding for finding in found if finding.fixable and key_of(finding) not in failed]
        if not pending:
            break

        for finding in pending:
            attempted.add(key_of(finding))
            try:
                finding.repair()
            except (OSError, frontmatter.FrontmatterError, task.TaskError) as error:
                failed[key_of(finding)] = store.explain(error)

        brain.refresh()
        again = check_all(brain)
        if lines_of(again) == lines_of(found):
            break

        found = again

    return [flagged(finding=finding, failed=failed, attempted=attempted) for finding in found]


def key_of(
    finding: Finding,
) -> tuple[str, str, str]:
    """What makes a finding the same one across passes: its file, check and words."""
    return finding.path, finding.check, finding.message


def lines_of(
    found: list[Finding],
) -> list[str]:
    return [finding.line() for finding in found]


def flagged(
    finding: Finding,
    failed: dict[tuple[str, str, str], str],
    attempted: set[tuple[str, str, str]],
) -> Finding:
    """The finding as it stands, or as a flag when its repair failed or got nowhere.

    A finding still on offer as fixable after its repair ran is one no
    number of runs will clear, so it goes back as a flag that says so
    rather than an invitation to run --fix again.
    """
    key = key_of(finding)
    reason = failed.get(key)
    if reason is not None:
        return Finding(path=finding.path, check=finding.check, message=f"{finding.message}, and the repair failed: {reason}")

    if finding.fixable and key in attempted:
        return Finding(path=finding.path, check=finding.check, message=f"{finding.message}, and the repair ran without clearing it")

    return finding


def check_all(
    brain: store.Brain,
) -> list[Finding]:
    found: list[Finding] = []

    for check in CHECKS:
        found.extend(check(brain))

    return found


def markdown_files(
    brain: store.Brain,
) -> list[Path]:
    """The files the frontmatter checks look at: the entries and the kit's files.

    A file that is neither is a stray, reported once by its own check
    rather than measured against rules written for something else. The
    style and hygiene scans read every file regardless, since a pasted
    secret is most likely in exactly the file nobody filed.
    """
    accounted = brain.known()

    return [path for path in all_markdown(brain) if path in accounted or schema.is_kit_path(relative(brain=brain, path=path))]


def all_markdown(
    brain: store.Brain,
    with_skills: bool = False,
) -> list[Path]:
    """Every markdown file under the brain, the rulebook and dotfiles excepted, the skills only when asked.

    The skills folder is the tool's own, its files follow the Agent
    Skills standard rather than the specs, so only the prose and
    boundary checks (style and hygiene) read them.
    """
    found: list[Path] = []

    for path in sorted(brain.root.rglob("*.md")):
        relative_path = path.relative_to(brain.root)
        parts = relative_path.parts
        if store.hidden(relative_path):
            continue

        if parts[0] in SKIP_DIRS and not (with_skills and parts[0] == schema.SKILLS):
            continue

        if path.name in schema.NO_FRONTMATTER and len(parts) == 1:
            continue

        found.append(path)

    return found


def check_strays(
    brain: store.Brain,
) -> list[Finding]:
    """Files under the brain that neither the store nor the kit accounts for."""
    accounted = brain.known()
    found: list[Finding] = []

    for path in all_markdown(brain):
        where = relative(brain=brain, path=path)
        if path in accounted or schema.is_kit_path(where):
            continue

        found.append(Finding(path=where, check="stray", message=stray_reason(where)))

    return found


def check_leftovers(
    brain: store.Brain,
) -> list[Finding]:
    """What an interrupted write left beside its target, safe to remove.

    Only the tool's own shapes count, a real file named the way a write
    in flight is named and, inside the brain, a real folder named the
    way a put back scratch is named. A person's own dotfile is nobody's
    to delete, and a suffix of eight letters looks like the tail the
    writer draws, so a temp file counts only when its target is one the
    tool would write, a markdown or JSON file, VERSION, the word, the
    current work, a file that exists beside it, or one of the kit's own
    files at the top of the project. The places the tool writes to in
    every run are looked at, the whole brain with its skills, each
    agent's own folder down to its sub agent files, and the top of the
    project. The one time move from `.agent/` rewrites files anywhere
    in the project, cleans up after itself unless killed outright, and
    is not looked for.
    """
    found: list[Finding] = []
    project = style.project(brain=brain)
    candidates = [path for path in brain.root.rglob(".*") if path.relative_to(brain.root).parts[0] != ".worktrees"]
    candidates += list(project.glob(".*"))
    for folder in style.folders(brain):
        if store.quietly(folder.is_dir):
            candidates += list(folder.rglob(".*"))

    for path in sorted(candidates):
        if store.quietly(path.is_symlink):
            continue

        in_flight = store.quietly(path.is_file) and tools_own_write(path=path, project=project)
        scratch = brain.root in path.parents and store.quietly(path.is_dir) and links.SCRATCH_SHAPE.match(path.name) is not None
        if not in_flight and not scratch:
            continue

        found.append(
            Finding(
                path=where_of(brain=brain, path=path),
                check="leftover",
                message="left by an interrupted write, nothing in it is the brain's",
                repair=remove(path),
            )
        )

    return found


def tools_own_write(
    path: Path,
    project: Path,
) -> bool:
    """Whether the file is a write in flight of the tool's, by its shape and by a target the tool would write."""
    target = frontmatter.target_of(path.name)
    if target is None:
        return False

    if path.parent == project:
        return target in (*schema.ROOT_FILES, schema.IGNORE_FILE)

    if target.endswith((".md", ".json")) or target in (schema.VERSION_FILE, autoack.FILE, task.FILE):
        return True

    return store.quietly((path.parent / target).exists)


def where_of(
    brain: store.Brain,
    path: Path,
) -> str:
    """A path from the brain when it is inside it, else from the project."""
    if brain.root in path.parents:
        return relative(brain=brain, path=path)

    return str(path.relative_to(brain.root.parent))


def remove(
    path: Path,
) -> Callable[[], None]:
    """A repair that removes a leftover, a folder with whatever the tool left in it."""

    def repair() -> None:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    return repair


def stray_reason(
    where: str,
) -> str:
    parts = where.split("/")

    if parts[0] == "reviews" and parts[-1] == schema.LEDGER:
        return f"a ledger sits at reviews/<folder>/{schema.LEDGER}, one folder down, no more and no less"

    if parts[0] == "reviews":
        return f"a review folder holds {schema.LEDGER} and nothing else"

    if parts[-1] == schema.INDEX:
        return "no index belongs here, the tool builds one per tracker, docs/ and memory/"

    if parts[0] == "spec":
        return "spec/ holds its files directly, nothing nested"

    return "not a file the brain lists, file it with brain new or move it out"


def relative(
    brain: store.Brain,
    path: Path,
) -> str:
    return str(path.relative_to(brain.root))


def check_frontmatter(
    brain: store.Brain,
) -> list[Finding]:
    found: list[Finding] = []

    for path in markdown_files(brain):
        where = relative(brain=brain, path=path)

        try:
            document = frontmatter.read(str(path))
        except frontmatter.FrontmatterError as error:
            found.append(Finding(path=where, check="frontmatter", message=str(error)))
            continue

        for item in schema.COMMON_FIELDS:
            value = document.get(item.name)
            if value:
                continue

            found.append(common_field_gap(path=path, where=where, name=item.name, present=value is not None))

        updated = document.get("updated")
        if updated and not schema.is_date(updated):
            found.append(
                Finding(path=where, check="frontmatter", message=f"updated reads '{updated}', not YYYY-MM-DD")
            )

    return found


def common_field_gap(
    path: Path,
    where: str,
    name: str,
    present: bool,
) -> Finding:
    """A common field that is missing or blank. The date and the links can be filled in."""
    if name == "updated":
        return Finding(path=where, check="frontmatter", message="no updated date", repair=stamp_today(path))

    if name == "links":
        return Finding(
            path=where,
            check="frontmatter",
            message="links is blank, none is written as []",
            repair=set_field(path=path, key="links", value="[]"),
        )

    state = "is blank" if present else "field is missing"

    return Finding(path=where, check="frontmatter", message=f"{name} {state}")


def stamp_today(
    path: Path,
) -> Callable[[], None]:
    def repair() -> None:
        document = frontmatter.read(str(path))
        document.set(key="updated", value=date.today().isoformat())
        frontmatter.write(path=str(path), document=document)

    return repair


def check_names(
    brain: store.Brain,
) -> list[Finding]:
    found: list[Finding] = []
    seen: dict[str, str] = {}

    for path, document in links.kit_documents(brain):
        name = document.get("name") or ""
        if name:
            seen[name] = relative(brain=brain, path=path)

    for entry in brain.entries():
        expected = writes.entry_name(path=entry.path, kind=entry.kind)
        actual = entry.document.get("name") or ""
        if not actual:
            continue

        if actual != expected:
            found.append(
                Finding(
                    path=entry.relative,
                    check="name",
                    message=f"name is '{actual}', the file says '{expected}'",
                    repair=set_name(brain=brain, entry=entry, actual=actual, expected=expected),
                )
            )

        if actual in seen:
            found.append(
                Finding(
                    path=entry.relative,
                    check="name",
                    message=f"name '{actual}' is also carried by {seen[actual]}",
                )
            )
        seen[actual] = entry.relative

    return found


def set_name(
    brain: store.Brain,
    entry: store.Entry,
    actual: str,
    expected: str,
) -> Callable[[], None]:
    """A repair that sets the name the file says, and moves the links that hold the old name with it: a plan's or a review's link on the chain, and the step cells that point at a review.

    The chain and the cells move first: the new name resolves by the
    file whether or not the field follows, and a chain that cannot be
    written leaves the field as it was, so the finding stays to report
    the failure. The links stay where they are when another file
    answers to the old name, a copy that kept it, since they mean that
    file.
    """
    set_the_field = set_field(path=entry.path, key="name", value=expected)
    follows = entry.kind.name in ("plan", "review") and not any(
        other.path != entry.path and actual in (other.name, task.file_key(other)) for other in brain.entries()
    )

    def repair() -> None:
        if follows:
            task.renamed(brain=brain, kind=entry.kind.name, old=actual, new=expected)

        if follows and entry.kind.name == "review":
            steps.repoint(brain=brain, keys={actual}, to=expected)

        set_the_field()

    return repair


def set_field(
    path: Path,
    key: str,
    value: str,
) -> Callable[[], None]:
    """A repair that changes one field and stamps the file, per the upkeep rule."""

    def repair() -> None:
        document = frontmatter.read(str(path))
        document.set(key=key, value=value)
        document.set(key="updated", value=date.today().isoformat())
        frontmatter.write(path=str(path), document=document)

    return repair


def check_kinds(
    brain: store.Brain,
) -> list[Finding]:
    found: list[Finding] = []

    for entry in brain.entries():
        actual = entry.document.get("kind")
        if not actual or actual == entry.kind.kind_value:
            continue

        found.append(
            Finding(
                path=entry.relative,
                check="kind",
                message=f"kind is '{actual}' but the file sits in {entry.kind.folder}/",
            )
        )

    return found


def check_fields(
    brain: store.Brain,
) -> list[Finding]:
    found: list[Finding] = []

    for entry in brain.entries():
        fields = entry.document.fields()
        try:
            writes.check_own(kind=entry.kind, fields=fields)
        except writes.WriteError as error:
            found.append(Finding(path=entry.relative, check="fields", message=str(error)))

        found += [Finding(path=entry.relative, check="fields", message=slip) for slip in common_slips(fields)]

    for path, document in links.kit_documents(brain):
        where = relative(brain=brain, path=path)
        found += [Finding(path=where, check="fields", message=slip) for slip in common_slips(document.fields())]

    return found


def common_slips(
    fields: dict[str, str],
) -> list[str]:
    """What the house style bans in the common header values, since each flows into an index."""
    return [
        f"{item.name} {slip}"
        for item in schema.COMMON_FIELDS
        for slip in sections.style_slips(fields.get(item.name, ""))
    ]


def check_sections(
    brain: store.Brain,
) -> list[Finding]:
    found: list[Finding] = []

    for entry in brain.entries():
        body = entry.document.body
        for title in sections.missing(body=body, kind=entry.kind):
            # a plan's missing Steps section is the steps check's finding, which carries the repair that adds the empty table
            if entry.kind.name == "plan" and title == "Steps":
                continue

            found.append(
                Finding(path=entry.relative, check="sections", message=f"no {title} heading")
            )

        for message in sections.lifecycle_gaps(kind=entry.kind, fields=entry.document.fields(), body=body):
            found.append(Finding(path=entry.relative, check="lifecycle", message=message))

    return found


def check_steps(
    brain: store.Brain,
) -> list[Finding]:
    """The steps table a plan, a todo or a bug carries, per spec/plans.md.

    The table must read as one, a list in its place turned into one on
    a plan or a todo and a plan's missing section given an empty table,
    every step that points at an entry must reach one, a pointed step's
    mark must be the one its entry gives and its pointer the entry's
    id, moved on from a refiled one, both repaired, a became field must
    name what took the entry's place, two entries must not wait on each
    other, and an entry done or fixed with a step still pending is
    reported, since a closed table is its record.
    """
    found: list[Finding] = []

    for kind_name in steps.STEPPED_KINDS:
        for entry in brain.entries_of(schema.kind_named(kind_name)):
            found += check_table(brain=brain, entry=entry)

    return found


def check_table(
    brain: store.Brain,
    entry: store.Entry,
) -> list[Finding]:
    found: list[Finding] = []
    try:
        rows = steps.stored_rows(entry)
    except steps.StepsError as broken:
        message = str(broken).split(": ", 1)[1]
        if entry.kind.name == "bug" and not steps.has_table(entry.document.body):
            message += ", a bug's Steps being the fix's steps and a reproduction going under Evidence, so move it there by hand, or on an open bug run brain steps <key> add to keep it as the fix's"

        return [Finding(path=entry.relative, check="steps", message=message, repair=convert_steps(brain=brain, entry=entry))]

    found += [Finding(path=entry.relative, check="steps", message=message) for message in steps.became_slips(brain=brain, entry=entry)]

    if not steps.is_open(entry):
        pending = [step.number for step in rows if step.status == "pending"]
        if pending and entry.field("status") == steps.CLOSING[entry.kind.name]:
            numbers = ", ".join(str(number) for number in pending)
            found.append(Finding(path=entry.relative, check="steps", message=f"the entry is {entry.field('status')} with step {numbers} still pending, so reopen it and close it again once the step is settled"))

        return found

    derived: list[steps.Step] = []
    own = steps.own_keys(entry)
    for step in rows:
        fresh = steps.derived_row(brain=brain, step=step, own=own)
        derived.append(fresh)
        if step.points_at and steps.pointed(brain=brain, key=step.points_at) is None:
            why = f"which two files carry, so it reaches nothing while the {steps.doubled_word(step.points_at)} is doubled" if steps.doubled(brain=brain, key=step.points_at) else "which reaches no todo, bug or review"
            found.append(Finding(path=entry.relative, check="steps", message=f"step {step.number} points at '{step.points_at}', {why}, and brain steps <key> step {step.number} done or skipped marks it by hand meanwhile"))
        elif fresh.points_at != step.points_at:
            target = steps.pointed(brain=brain, key=step.points_at)
            moved = target is not None and target.field("status") == "refiled"
            why = f"which was refiled as {fresh.points_at}" if moved else f"and the tool keeps the id {fresh.points_at}, which a retitle never moves"
            found.append(
                Finding(
                    path=entry.relative,
                    check="steps",
                    message=f"step {step.number} points at {step.points_at}, {why}",
                    repair=refresh_steps(brain=brain, entry=entry),
                )
            )
        elif fresh.status != step.status:
            found.append(
                Finding(
                    path=entry.relative,
                    check="steps",
                    message=f"step {step.number} is marked {step.status} while {step.points_at} says {fresh.status}",
                    repair=refresh_steps(brain=brain, entry=entry),
                )
            )

    found += [Finding(path=entry.relative, check="steps", message=message) for message in steps.looping(brain=brain, entry=entry, rows=derived)]

    return found


def convert_steps(
    brain: store.Brain,
    entry: store.Entry,
) -> Optional[Callable[[], None]]:
    """A repair that turns a list under Steps into the table, its rows marked by the entry's own status, or none when the section does not read as a list either.

    A bug gets no repair, since a list under its Steps from before the
    table may be the reproduction, which the spec puts under Evidence,
    and only whoever filed it can say which it is.
    """
    body = entry.document.body
    if entry.kind.name == "bug" or steps.has_table(body):
        return None

    own = {entry.identifier, entry.name} - {None}
    try:
        steps.converted(brain=brain, body=body, by=entry.field("by") or "agent", kind=entry.kind, status=steps.settled_as(entry), own=own)
    except steps.StepsError:
        return None

    def repair() -> None:
        fresh = brain.read(path=entry.path, kind=entry.kind)
        fresh.document.body = steps.converted(brain=brain, body=fresh.document.body, by=fresh.field("by") or "agent", kind=fresh.kind, status=steps.settled_as(fresh), own=own)
        steps.save(brain=brain, entry=fresh)

    return repair


def refresh_steps(
    brain: store.Brain,
    entry: store.Entry,
) -> Callable[[], None]:
    """A repair that brings an entry's pointed marks in line with what they point at, stamping the file."""

    def repair() -> None:
        steps.refresh(brain=brain, entry=brain.read(path=entry.path, kind=entry.kind))

    return repair


def check_filenames(
    brain: store.Brain,
) -> list[Finding]:
    found: list[Finding] = []
    numbers: dict[str, str] = {}

    for entry in brain.entries():
        if entry.kind.name == "review":
            if not schema.is_review_folder(entry.slug):
                found.append(
                    Finding(
                        path=entry.relative,
                        check="filename",
                        message=f"a review folder is named <yyyy-mm>-<branch-slug>, not '{entry.slug}'",
                    )
                )
            continue

        for folder in Path(entry.relative).parts[1:-1]:
            if not schema.is_slug(folder):
                found.append(
                    Finding(path=entry.relative, check="filename", message=f"sits in a folder that is not a slug, '{folder}'")
                )

        if entry.kind.has_ids and entry.identifier is None:
            found.append(
                Finding(
                    path=entry.relative,
                    check="filename",
                    message=f"a {entry.kind.name} is named {entry.kind.id_prefix}-###-<slug>.md",
                )
            )
            continue

        if not schema.is_slug(entry.slug):
            found.append(
                Finding(path=entry.relative, check="filename", message=f"'{entry.slug}' is not a slug")
            )

        if entry.identifier is None:
            continue

        if entry.identifier in numbers:
            found.append(
                Finding(
                    path=entry.relative,
                    check="filename",
                    message=f"{entry.identifier} is also {numbers[entry.identifier]}",
                )
            )
        numbers[entry.identifier] = entry.relative

    return found


def check_links(
    brain: store.Brain,
) -> list[Finding]:
    found: list[Finding] = []
    documents = links.documents(brain)

    for path, document in documents:
        where = relative(brain=brain, path=path)
        current = document.get_list("links")
        canonical: list[str] = []

        for link in current:
            resolved = links.canonical(brain=brain, reference=link)
            if (resolved or link) in canonical:
                continue

            if resolved is None:
                found.append(Finding(path=where, check="link", message=f"'{link}' reaches nothing"))
            canonical.append(resolved or link)

        if canonical != current:
            found.append(
                Finding(
                    path=where,
                    check="link",
                    message="links not written as paths relative to .agents/, each once",
                    repair=set_links(path=path, values=canonical),
                )
            )

    for path, document in documents:
        for target in links.broken_in_body(path=path, document=document):
            found.append(
                Finding(path=relative(brain=brain, path=path), check="link", message=f"body link '{target}' reaches nothing")
            )

    return found


def set_links(
    path: Path,
    values: list[str],
) -> Callable[[], None]:
    def repair() -> None:
        document = frontmatter.read(str(path))
        document.set_list(key="links", values=values)
        document.set(key="updated", value=date.today().isoformat())
        frontmatter.write(path=str(path), document=document)

    return repair


def check_indexes(
    brain: store.Brain,
) -> list[Finding]:
    """One build of the brain serves the check and every repair it hands out.

    A brain whose skills folder cannot be listed has no spine the tool
    can build, so the build leaves it out and the spine is reported as
    unbuildable and left as it is rather than rewritten without the
    project's skills.
    """
    wanted = index.build(brain)
    found = [
        Finding(
            path=relative(brain=brain, path=path),
            check="index",
            message="differs from what the tool builds for its folder",
            repair=write_index(path=path, text=wanted[path]),
        )
        for path in index.stale_among(wanted)
    ]
    if brain.root / schema.INDEX not in wanted:
        found.append(Finding(path=schema.INDEX, check="index", message="cannot be rebuilt while the skills folder cannot be listed"))

    return found


def write_index(
    path: Path,
    text: str,
) -> Callable[[], None]:
    def repair() -> None:
        index.write_one(path=path, text=text)

    return repair


def check_style(
    brain: store.Brain,
) -> list[Finding]:
    """The prose rules over every file but the indexes.

    An index is the tool's rendering of other files' header values and
    of the folders they sit in, checked at their source by the fields
    and filename checks, so a slip is named on the file a person can
    put right rather than on one nobody may edit.
    """
    found: list[Finding] = []

    for path in all_markdown(brain=brain, with_skills=True):
        if path.name == schema.INDEX:
            continue

        prose = prose_in(path)
        if prose is None:
            continue

        where = relative(brain=brain, path=path)
        found += [Finding(path=where, check="style", message=slip) for slip in sections.style_slips(prose)]

    return found


def prose_in(
    path: Path,
) -> Optional[str]:
    """The file's prose, its header block and its code stepped over, or None when it cannot be read.

    A header the tool can read is taken off by the parser, one it
    cannot, the Agent Skills shape in `skills/` for one, by its fences.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    try:
        body = frontmatter.parse(text).body
    except frontmatter.FrontmatterError:
        body = HEADER_BLOCK.sub("", text, count=1)

    return sections.prose_of(body)


def check_hygiene(
    brain: store.Brain,
) -> list[Finding]:
    found: list[Finding] = []

    for path in all_markdown(brain=brain, with_skills=True):
        try:
            text = path.read_bytes().decode("utf-8", errors="replace")
        except OSError:
            continue

        where = relative(brain=brain, path=path)

        if MACHINE_PATH.search(sections.prose_of(text)):
            found.append(Finding(path=where, check="hygiene", message="names a machine's local path"))

        for shape in SECRET_SHAPES:
            if shape.search(text):
                found.append(Finding(path=where, check="hygiene", message="carries something shaped like a secret"))
                break

    return found


def check_layout(
    brain: store.Brain,
) -> list[Finding]:
    found: list[Finding] = []
    project = brain.root.parent

    if not store.readable_file(brain.root / schema.VERSION_FILE):
        found.append(Finding(path=schema.VERSION_FILE, check="layout", message="no kit version stamp, run the upgrade"))
    elif store.stamp_of(brain.root) is None:
        found.append(Finding(path=schema.VERSION_FILE, check="layout", message="the kit version stamp is not a version like 1.0.0, write the kit's release in it"))

    shared = skills_folder_outside(project)
    shipped = store.kit_skills_shipped(brain.root)
    wanted = list(shipped)
    listed = True
    try:
        wanted += store.project_skills(
            brain=brain.root,
            shipped=shipped,
        )
    except OSError as error:
        reason = error.strerror or str(error)
        found.append(
            Finding(
                path=schema.SKILLS,
                check="layout",
                message=f"the skills folder cannot be listed, so only the kit's skill links were checked: {reason}",
            )
        )
        listed = False

    for name in wanted:
        trouble = skill_link_trouble(
            project=project,
            name=name,
            shared=shared,
            kits=name in shipped,
        )
        if trouble is None:
            continue

        message = trouble.message
        repair = trouble.repair
        if shared and repair is not None:
            message += SHARED_FOLDER
            repair = None

        found.append(
            Finding(
                path=str(trouble.path),
                check="layout",
                message=message,
                repair=repair,
            )
        )

    if listed:
        strays = stray_skill_links(
            project=project,
            wanted=wanted,
            shared=shared,
        )
        found.extend(strays)

    found.extend(check_style_copies(brain))

    return found


CANNOT_SEE = ", so Claude Code cannot see the skill"
REAL_FOLDER_WITHOUT_SKILL = "a folder with no SKILL.md sits where the skill link belongs" + CANNOT_SEE
ANOTHER_SKILL = "a skill of its own sits where the skill link belongs, so Claude Code loads that one instead"
STALE_COPY = "a copy of the skill sits where the skill link belongs and is behind the brain's, so Claude Code loads the old text"
SHARED_FOLDER = ", and the skills folder sits outside the project, so the link is yours to make"
SHARED_REMOVAL = ", and the skills folder sits outside the project, so the link is yours to remove"
SKILL_GONE = "the skill link points at a skill that is gone"


@dataclass(frozen=True)
class Trouble:
    """What is wrong with one skill link: the message, the path the finding names, and the repair when doctor may make one."""

    message: str
    path: Path
    repair: Optional[Callable[[], None]] = None


def skills_folder_outside(
    project: Path,
) -> bool:
    """Whether `.claude/skills` resolves to a folder outside the project.

    Such a folder is shared with other checkouts on the machine, and a
    link made here would point every one of them at this project's
    skills, so doctor names the trouble and leaves the link to a person.
    """
    folder = resolved(project / SKILL_LINKS)
    root = resolved(project)

    return folder is not None and root is not None and not folder.is_relative_to(root)


def resolved(
    path: Path,
) -> Optional[Path]:
    """The path resolved, or None when it reaches nothing.

    A link that loops raises RuntimeError up to 3.12 and resolves to
    itself from 3.13 on, a folder the process cannot search raises
    OSError, and a name the system refuses raises ValueError. Each is
    a path that reaches nothing, answered here once for every check
    that resolves one.
    """
    try:
        return path.resolve()
    except (OSError, RuntimeError, ValueError):
        return None


def skill_missing(
    name: str,
) -> str:
    return f"the skill itself is missing from {SKILL_HOMES / name}, reinstall the kit"


def stray_skill_links(
    project: Path,
    wanted: list[str],
    shared: bool,
) -> list[Finding]:
    """A link under .claude/skills that doctor once made for a project skill now gone from the brain, with its removal as the repair.

    Only a link that points into the brain's skills folder and dangles,
    leading to nothing at all, is doctor's to remove. One that leads to
    a folder or a file still there is somebody's and is left alone,
    whatever it holds, and so is one the process cannot reach, and so
    is a link the project made elsewhere, and so is everything when
    .claude/skills is itself a link into the brain, since its entries
    are then the brain's own. In a skills folder shared outside the
    project the trouble is named and the removal is left to a person.
    The caller skips this pass when the skills folder could not be
    listed.
    """
    links = project / SKILL_LINKS
    found: list[Finding] = []

    homes = resolved(project / SKILL_HOMES)
    folder = resolved(links)
    if homes is None or folder is None or folder.is_relative_to(homes):
        return found

    try:
        entries = sorted(links.iterdir())
    except OSError:
        return found

    for link in entries:
        if link.name in wanted or not store.quietly(link.is_symlink) or not skill_gone(link):
            continue

        target = resolved(link)
        if target is None or not target.is_relative_to(homes):
            continue

        found.append(
            Finding(
                path=str(SKILL_LINKS / link.name),
                check="layout",
                message=SKILL_GONE + (SHARED_REMOVAL if shared else ""),
                repair=None if shared else remove_link(link),
            )
        )

    return found


def skill_gone(
    link: Path,
) -> bool:
    """Whether the link dangles, leading to nothing at all, as against to something the process cannot reach."""
    try:
        link.stat()
    except (FileNotFoundError, NotADirectoryError):
        return True
    except (OSError, RuntimeError, ValueError):
        return False

    return False


def remove_link(
    link: Path,
) -> Callable[[], None]:
    def repair() -> None:
        link.unlink()

    return repair


def skill_link_trouble(
    project: Path,
    name: str,
    shared: bool,
    kits: bool,
) -> Optional[Trouble]:
    """What is wrong with the named skill's link, or None when Claude Code loads this skill through it.

    What Claude Code needs is `.claude/skills/<name>/SKILL.md`, and it
    must be this skill: a link that resolves to the skill's own folder,
    or a real copy of its SKILL.md, the way a ZIP download or a checkout
    without symlinks leaves one. A link that lands elsewhere is dead or
    points at another skill and is remade, except in a skills folder
    shared outside the project, where a link or a real copy of this
    skill from another checkout is how the sharing works and passes. A
    real folder whose SKILL.md names a skill the stamp says the kit
    shipped, `kits`, but differs from the brain's is a copy that fell
    behind and is refreshed, since the folder is the kit's. Under a
    project skill's name, a kit name the stamp predates included, the
    same folder holds a person's own text, and it is left for them like
    a folder naming another skill, and like a real folder with no
    SKILL.md at all. A link can only be made when the skill itself is
    in the brain to point at, and a copy with nothing left to point at
    is all there is, so it passes.
    """
    link = project / SKILL_LINKS / name
    home = project / SKILL_HOMES / name
    at_link = SKILL_LINKS / name
    remake = make_skill_link(
        project=project,
        name=name,
    )

    if not store.readable_file(home / schema.SKILL_FILE):
        if store.readable_file(link / schema.SKILL_FILE):
            return None

        return Trouble(
            message=skill_missing(name),
            path=SKILL_HOMES / name,
        )

    if store.quietly(link.is_symlink):
        reached = reaches(
            link=link,
            home=home,
        )
        if reached:
            return None

        if shared and carries_skill(folder=link, name=name):
            return None

        return Trouble(
            message="the skill link does not reach the skill" + CANNOT_SEE,
            path=at_link,
            repair=remake,
        )

    if store.quietly(link.is_dir):
        if not store.readable_file(link / schema.SKILL_FILE):
            return Trouble(
                message=REAL_FOLDER_WITHOUT_SKILL,
                path=at_link,
            )

        copied = store.same_bytes(
            one=link / schema.SKILL_FILE,
            other=home / schema.SKILL_FILE,
        )
        if copied:
            return None

        if shared and carries_skill(folder=link, name=name):
            return None

        if kits and carries_skill(folder=link, name=name):
            return Trouble(
                message=STALE_COPY,
                path=at_link,
                repair=refresh_skill_copy(
                    home=home,
                    copy=link,
                ),
            )

        return Trouble(
            message=ANOTHER_SKILL,
            path=at_link,
        )

    if store.quietly(link.exists):
        return Trouble(
            message="something that is not a link sits where the skill link belongs" + CANNOT_SEE,
            path=at_link,
            repair=remake,
        )

    return Trouble(
        message="the skill link is missing" + CANNOT_SEE,
        path=at_link,
        repair=remake,
    )


def carries_skill(
    folder: Path,
    name: str,
) -> bool:
    """Whether the folder's SKILL.md is a skill of this name, by the name its frontmatter gives."""
    try:
        document = frontmatter.read(str(folder / schema.SKILL_FILE))
    except frontmatter.FrontmatterError:
        return False

    return document.get("name") == name


def refresh_skill_copy(
    home: Path,
    copy: Path,
) -> Callable[[], None]:
    """A repair that brings a real folder copy of a skill up to the brain's, for a checkout where a link is not an option."""

    def repair() -> None:
        shutil.copytree(home, copy, dirs_exist_ok=True)

    return repair


def reaches(
    link: Path,
    home: Path,
) -> bool:
    """Whether the link resolves to the skill's own folder."""
    target = resolved(link)

    return target is not None and target == resolved(home)


def check_style_copies(
    brain: store.Brain,
) -> list[Finding]:
    """Codex and Gemini CLI carry the chat style as copies of the Claude Code one.

    A copy is owed only where the project keeps that agent's folder. The
    source is read once, and each stale copy gets a repair that writes
    only itself.
    """
    if not style.expected(brain):
        return []

    try:
        wanted = style.source_body(brain)
    except style.StyleError as error:
        return [Finding(path=str(style.SOURCE), check="layout", message=str(error))]

    return [
        Finding(
            path=str(relative),
            check="layout",
            message="the chat style copy does not match the Claude Code one",
            repair=write_copy(target=style.project(brain) / relative, text=wanted),
        )
        for relative in style.stale_against(brain=brain, wanted=wanted)
    ]


def write_copy(
    target: Path,
    text: str,
) -> Callable[[], None]:
    def repair() -> None:
        style.write_one(target=target, text=text)

    return repair


def make_skill_link(
    project: Path,
    name: str,
) -> Callable[[], None]:
    """A repair that puts the named skill's symlink in place, clearing a dead link or a stray file first.

    A real folder is never removed here. It is somebody's, and the check
    leaves it for a person.
    """

    def repair() -> None:
        link = project / SKILL_LINKS / name
        link.parent.mkdir(parents=True, exist_ok=True)
        if not os.access(str(link.parent), os.W_OK):
            raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(link.parent))

        if link.is_symlink() or (link.exists() and not link.is_dir()):
            link.unlink()

        target = skill_target(
            project=project,
            link=link,
            name=name,
        )
        os.symlink(target, str(link))

    return repair


def skill_target(
    project: Path,
    link: Path,
    name: str,
) -> str:
    """The named skill's folder, relative to where the link really sits.

    On the shipped layout that is `../../.agents/skills/<name>`. When
    `.claude/skills` is itself a symlink the link lands elsewhere, and a
    target counted from there is the one that still resolves.
    """
    return os.path.relpath(str(project / SKILL_HOMES / name), str(link.parent.resolve()))


CHECKS: tuple[Callable[[store.Brain], list[Finding]], ...] = (
    check_leftovers,
    check_strays,
    check_frontmatter,
    check_names,
    check_kinds,
    check_fields,
    check_sections,
    check_steps,
    check_filenames,
    check_links,
    check_indexes,
    check_style,
    check_hygiene,
    check_layout,
)
