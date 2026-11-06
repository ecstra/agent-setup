"""Checking the whole brain, fixing what is mechanical, flagging the rest.

Every check is a function that reads the brain and reports findings. A
finding that a machine can put right carries its own repair, and `run`
applies those before it reports, so what comes back is only what needs a
person or an agent to decide.
"""

import errno
import json
import os
import posixpath
import re
import shutil
import stat
from collections import deque
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Optional, Union

from . import autoack, conclude, frontmatter, guard, handover, index, links, people, rules, rust, schema, sections, steps, store, style, task, writes

# The folders the markdown walk leaves out. It never enters the worktree
# home, and it enters the skills, which follow their own standard, only
# where a scan asks for them. The handover folder is a dotted one, which
# the walk skips with every dotted path.
SKIP_DIRS: frozenset[str] = frozenset({schema.SKILLS, ".worktrees"})

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

        return store.shown(f"{where}: {self.check}: {self.message} [{mark}]")

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
            except (OSError, frontmatter.FrontmatterError, task.TaskError, steps.StepsError) as error:
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
    hygiene scan reads every file the walk takes, filed or not, since a
    pasted secret is most likely in exactly the file nobody filed.
    """
    accounted = brain.known()

    return [path for path in all_markdown(brain) if path in accounted or schema.is_kit_path(relative(brain=brain, path=path))]


def all_markdown(
    brain: store.Brain,
    with_skills: bool = False,
) -> list[Path]:
    """Every markdown file under the brain but the rulebook and what the walk skips, the skills only when asked.

    The walk skips a dotted path and the folders in SKIP_DIRS. The
    skills folder is the tool's own, its files follow the Agent Skills
    standard rather than a kind's, so only the boundary check, hygiene,
    reads them. A skipped folder is known by its name as
    `links.names_folder` reads it, and git is asked once per run, as
    `links.case_flag` keeps its answer.
    """
    skipped_folders = [folder for folder in SKIP_DIRS if not (with_skills and folder == schema.SKILLS)]
    found: list[Path] = []

    # a glob ignores case on Windows, and the brain's suffix is `.md` in lower case on every system
    for path in store.in_order(path for path in brain.root.rglob("*.md") if path.name.endswith(".md")):
        relative_path = path.relative_to(brain.root)
        parts = relative_path.parts
        if store.hidden(relative_path):
            continue

        if any(
            links.names_folder(
                brain=brain,
                top=parts[0],
                folder=folder,
            )
            for folder in skipped_folders
        ):
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

    for path in store.in_order(candidates):
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
            ),
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

    if target.endswith((".md", ".json")) or target in (schema.VERSION_FILE, autoack.FILE, guard.FILE, conclude.FILE, task.FILE):
        return True

    return store.quietly((path.parent / target).exists)


def where_of(
    brain: store.Brain,
    path: Path,
) -> str:
    """A path from the brain when it is inside it, else from the project."""
    if brain.root in path.parents:
        return relative(brain=brain, path=path)

    return path.relative_to(brain.root.parent).as_posix()


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

    return "not a file the brain lists, file it with brain new or move it out"


def relative(
    brain: store.Brain,
    path: Path,
) -> str:
    return path.relative_to(brain.root).as_posix()


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
                Finding(
                    path=where,
                    check="frontmatter",
                    message=f"updated reads '{updated}', not YYYY-MM-DD",
                ),
            )

    return found


def common_field_gap(
    path: Path,
    where: str,
    name: str,
    present: bool,
) -> Finding:
    """A common field that is missing or blank. The date and the links can be filled in."""
    entry = not schema.is_kit_path(where)
    if name == "updated":
        return Finding(path=where, check="frontmatter", message="no updated date", repair=stamp_today(path=path, entry=entry))

    if name == "links":
        return Finding(
            path=where,
            check="frontmatter",
            message="links is blank, none is written as []",
            repair=set_field(path=path, key="links", value="[]", entry=entry),
        )

    state = "is blank" if present else "field is missing"

    return Finding(path=where, check="frontmatter", message=f"{name} {state}")


def stamp_today(
    path: Path,
    entry: bool,
) -> Callable[[], None]:
    def repair() -> None:
        document = frontmatter.read(str(path))
        document.set(key="updated", value=date.today().isoformat())
        if entry:
            people.stamp(document=document, folder=path.parent)
        frontmatter.write(path=str(path), document=document)

    return repair


def check_people(
    brain: store.Brain,
) -> list[Finding]:
    """Every entry names who made it and who last changed it, and a gap is filled from one walk of git's history."""
    gaps = [entry for entry in brain.entries() if people.missing(entry.document)]
    if not gaps:
        return []

    known = people.history(brain.root)
    if known.unread:
        return [Finding(path=entry.relative, check="frontmatter", message=people.UNREAD) for entry in gaps]

    found: list[Finding] = []
    for entry in gaps:
        repair = people.filler(path=entry.path, known=known)
        author, _ = people.names_for(path=entry.path, known=known)
        if author is None and not entry.document.get(people.AUTHOR):
            found.append(Finding(path=entry.relative, check="frontmatter", message=people.SHALLOW, repair=repair if not entry.document.get(people.EDITOR) else None))
            continue

        found.append(Finding(path=entry.relative, check="frontmatter", message="no author or editor, which brain doctor --fix fills from git", repair=repair))

    return found


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
                ),
            )

        if actual in seen:
            found.append(
                Finding(
                    path=entry.relative,
                    check="name",
                    message=f"name '{actual}' is also carried by {seen[actual]}",
                ),
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
    set_the_field = set_field(path=entry.path, key="name", value=expected, entry=True)
    # a review is pointed at by its name, and so is a todo or a bug with no id, a file the tool never wrote, so their cells follow the name too
    pointed_by_name = entry.kind.name == "review" or (entry.kind.name in ("todo", "bug") and entry.identifier is None)
    follows = (entry.kind.name == "plan" or pointed_by_name) and not any(other.path != entry.path and actual in (other.name, task.file_key(other)) for other in brain.entries())

    def repair() -> None:
        if follows and entry.kind.name in ("plan", "review"):
            task.renamed(brain=brain, kind=entry.kind.name, old=actual, new=expected)

        if follows and pointed_by_name:
            steps.repoint(brain=brain, keys={actual}, to=expected)

        set_the_field()

    return repair


def set_field(
    path: Path,
    key: str,
    value: str,
    entry: bool,
) -> Callable[[], None]:
    """A repair that changes one field and stamps the file, per the upkeep rule, an entry's editor among it."""

    def repair() -> None:
        document = frontmatter.read(str(path))
        document.set(key=key, value=value)
        document.set(key="updated", value=date.today().isoformat())
        if entry:
            people.stamp(document=document, folder=path.parent)
        frontmatter.write(path=str(path), document=document)

    return repair


def check_kinds(
    brain: store.Brain,
) -> list[Finding]:
    found: list[Finding] = []

    for entry in brain.entries():
        actual = entry.document.get("kind")
        if not actual or actual == entry.kind.name:
            continue

        found.append(
            Finding(
                path=entry.relative,
                check="kind",
                message=f"kind is '{actual}' but the file sits in {entry.kind.folder}/",
            ),
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
    return [f"{item.name} {slip}" for item in schema.COMMON_FIELDS for slip in sections.style_slips(fields.get(item.name, ""))]


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
                Finding(
                    path=entry.relative,
                    check="sections",
                    message=f"no {title} heading",
                ),
            )

        for message in sections.lifecycle_gaps(kind=entry.kind, fields=entry.document.fields(), body=body):
            found.append(Finding(path=entry.relative, check="lifecycle", message=message))

    return found


def check_steps(
    brain: store.Brain,
) -> list[Finding]:
    """The steps table a plan, a build spec, a todo or a bug carries.

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
        rows = steps.stored_rows_of(kind=entry.kind.name, body=entry.document.body)
    except steps.StepsError as broken:
        message = str(broken)
        if entry.kind.name == "bug" and not steps.has_table(entry.document.body):
            message += ", a bug's Steps being the fix's steps and a reproduction going under Evidence, so move it there by hand, or make it a numbered list and on an open bug run brain steps <key> add to keep it as the fix's"

        offered = convert_steps(brain=brain, entry=entry)
        if isinstance(offered, str):
            return [Finding(path=entry.relative, check="steps", message=f"{message}, and the list is refused as it stands, {offered}")]

        return [Finding(path=entry.relative, check="steps", message=message, repair=offered)]

    found += [Finding(path=entry.relative, check="steps", message=message) for message in steps.became_slips(brain=brain, entry=entry)]
    found += [Finding(path=entry.relative, check="steps", message=f"step {step.number} has no text, which no write should have let stand, so fill it in by hand") for step in rows if not step.text.strip()]

    if not steps.is_open(entry):
        pending = [step.number for step in rows if step.status == "pending"]
        if pending and entry.field("status") == steps.CLOSING[entry.kind.name]:
            numbers = ", ".join(str(number) for number in pending)
            # nothing points at a plan, so only a todo or a bug can have its reopen refused for a loop, while steps on the way that do not read refuse it for any kind
            if entry.kind.name == "plan":
                way_round = ", and when the set to open is refused for steps that do not read, mend them first"
            else:
                way_round = ", and when the set to open is refused, mend the steps it says do not read, or close the entry whose steps point back here first"

            found.append(
                Finding(
                    path=entry.relative,
                    check="steps",
                    message=f"the entry is {entry.field('status')} with step {numbers} still pending, so reopen it and close it again once the step is settled{way_round}",
                ),
            )

        return found

    derived: list[steps.Step] = []
    own = steps.own_keys(entry)
    for step in rows:
        fresh = steps.derived_row(brain=brain, step=step, own=own)
        derived.append(fresh)
        if step.points_at and steps.pointed(brain=brain, key=step.points_at) is None:
            if steps.doubled(brain=brain, key=step.points_at):
                why = f"which two files carry, so it reaches nothing while the {steps.doubled_word(step.points_at)} is doubled"
            else:
                why = "which reaches no todo, bug or review"

            found.append(
                Finding(
                    path=entry.relative,
                    check="steps",
                    message=f"step {step.number} points at '{step.points_at}', {why}, and brain steps <key> step {step.number} done or skipped marks it by hand meanwhile",
                ),
            )
        elif fresh.points_at != step.points_at:
            target = steps.pointed(brain=brain, key=step.points_at)
            moved = target is not None and target.field("status") == "refiled"
            if moved:
                why = refiled_word(brain=brain, kept=fresh.points_at)
            elif target is not None and target.kind.name == "review":
                why = f"and the tool keeps the name {fresh.points_at}, which a review keeps as its branch's"
            elif target is not None and target.identifier is None:
                why = f"and the tool keeps the name {fresh.points_at}, the file carrying no id, which doctor reports"
            else:
                why = f"and the tool keeps the id {fresh.points_at}, which a retitle never moves"
            found.append(
                Finding(
                    path=entry.relative,
                    check="steps",
                    message=f"step {step.number} points at {step.points_at}, {why}",
                    repair=refresh_steps(brain=brain, entry=entry),
                ),
            )
        elif fresh.status != step.status:
            found.append(
                Finding(
                    path=entry.relative,
                    check="steps",
                    message=f"step {step.number} is marked {step.status} while {step.points_at} says {fresh.status}",
                    repair=refresh_steps(brain=brain, entry=entry),
                ),
            )

    found += [Finding(path=entry.relative, check="steps", message=message) for message in steps.looping(brain=brain, entry=entry, rows=derived)]

    return found


def refiled_word(
    brain: store.Brain,
    kept: str,
) -> str:
    """Why a cell at a refiled entry reads as the tool would write it, handed on to the entry filed in its place, at whatever remove, or kept at a refiled one, whose successor's steps lead back here or do not read, or which has no successor the brain knows."""
    landed = steps.pointed(brain=brain, key=kept)
    if landed is None or landed.field("status") != "refiled":
        return f"which was refiled as {kept}"

    successor = steps.refiled_to(brain=brain, entry=landed)
    if successor is None:
        became = landed.field("became") or ""
        if became and steps.doubled(brain=brain, key=became):
            return f"which was refiled as {became}, which two files carry, so the tool keeps the key {kept} and the step stands skipped while the {steps.doubled_word(became)} is doubled"

        return f"which was refiled as nothing the brain knows, so the tool keeps the key {kept} and the step stands skipped"

    handed_on = steps.pointer_of(successor)
    if successor.field("status") == "refiled":
        return f"which sits in a loop of refiles through {kept} and {handed_on}, so the tool keeps the key {kept} and the step stands skipped until the loop is undone"

    if steps.doubled(brain=brain, key=handed_on):
        return f"which was refiled as {handed_on}, which two files carry, so the tool keeps the key {kept} and the step stands skipped while the {steps.doubled_word(handed_on)} is doubled"

    broken = steps.unreadable_reached(brain=brain, key=handed_on)
    if broken is not None:
        where = handed_on if broken == handed_on else f"{handed_on}, whose steps lead to {broken}"

        return f"which was refiled as {where}, whose steps do not read, so the tool keeps the key {kept} and the step stands skipped until they are put right"

    return f"which was refiled as {handed_on}, whose steps lead back here, so the tool keeps the key {kept} and the step stands skipped"


def convert_steps(
    brain: store.Brain,
    entry: store.Entry,
) -> Union[Callable[[], None], str, None]:
    """A repair that turns a list under Steps into the table, its rows marked by the entry's own status, the reason when the tool refuses the list as it stands, so the finding says why no run of --fix clears it, or none when there is no list to turn.

    A bug gets no repair, since a list under its Steps from before the
    table may be the reproduction, which SKILL.md puts under Evidence,
    and only whoever filed it can say which it is, though the reason
    the section would not turn is named for it too, so the line to
    move by hand is known.
    """
    body = entry.document.body
    if steps.has_table(body):
        return None

    own = steps.own_keys(entry)
    try:
        steps.converted(brain=brain, body=body, by=entry.field("by") or "agent", kind=entry.kind, status=steps.settled_as(entry), own=own)
    except steps.StepsError as refused:
        return str(refused)

    if entry.kind.name == "bug":
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
                    ),
                )
            continue

        for folder in Path(entry.relative).parts[1:-1]:
            if not schema.is_slug(folder):
                found.append(
                    Finding(
                        path=entry.relative,
                        check="filename",
                        message=f"sits in a folder that is not a slug, '{folder}'",
                    ),
                )

        if entry.kind.has_ids and entry.identifier is None:
            found.append(
                Finding(
                    path=entry.relative,
                    check="filename",
                    message=f"a {entry.kind.name} is named {entry.kind.id_prefix}-###-<slug>.md",
                ),
            )
            continue

        if not schema.is_slug(entry.slug):
            found.append(
                Finding(
                    path=entry.relative,
                    check="filename",
                    message=f"'{entry.slug}' is not a slug",
                ),
            )

        if entry.identifier is None:
            continue

        if entry.identifier in numbers:
            found.append(
                Finding(
                    path=entry.relative,
                    check="filename",
                    message=f"{entry.identifier} is also {numbers[entry.identifier]}",
                ),
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
                said = (
                    links.handover_reason(
                        brain=brain,
                        reference=link,
                    )
                    or links.REACHES_NOTHING
                )
                found.append(
                    Finding(
                        path=where,
                        check="link",
                        message=f"'{link}' {said}",
                    ),
                )
            canonical.append(resolved or link)

        if canonical != current:
            found.append(
                Finding(
                    path=where,
                    check="link",
                    message="links not written as paths relative to .agents/, each once",
                    repair=set_links(path=path, values=canonical, entry=not schema.is_kit_path(where)),
                ),
            )

    for path, document in documents:
        for target, said in links.broken_in_body(
            brain=brain,
            path=path,
            document=document,
        ):
            found.append(
                Finding(
                    path=relative(
                        brain=brain,
                        path=path,
                    ),
                    check="link",
                    message=f"body link '{target}' {said}",
                ),
            )

    return found


def set_links(
    path: Path,
    values: list[str],
    entry: bool,
) -> Callable[[], None]:
    def repair() -> None:
        document = frontmatter.read(str(path))
        document.set_list(key="links", values=values)
        document.set(key="updated", value=date.today().isoformat())
        if entry:
            people.stamp(document=document, folder=path.parent)
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
                message=f"the skills folder cannot be listed, so only the kit's skill stubs were checked: {reason}",
            ),
        )
        listed = False

    inside = skills_folder_in_brain(brain)
    for name in wanted:
        trouble = skill_stub_trouble(
            project=project,
            name=name,
            shared=shared,
            kits=name in shipped,
        )
        if trouble is None:
            continue

        message = trouble.message
        repair = trouble.repair
        if repair is not None:
            sheet = project / SKILL_HOMES / name / schema.SKILL_FILE
            guard = SHARED_FOLDER if shared else INTO_THE_BRAIN if inside else ON_THE_WAY if on_the_way(path=sheet, entry=trouble.touches) else None
            if guard is not None:
                message += guard
                repair = None

        found.append(
            Finding(
                path=trouble.path.as_posix(),
                check="layout",
                message=message,
                repair=repair,
            ),
        )

    if listed:
        strays = stray_skill_links(
            project=project,
            wanted=wanted,
            shared=shared,
            inside=inside,
        )
        found.extend(strays)

    found.extend(check_style_copies(brain))
    found.extend(check_launcher(brain))

    return found


def check_launcher(
    brain: store.Brain,
) -> list[Finding]:
    """The launcher the rules and the hooks send the agent to, which an upgrade through a tool older than it never writes.

    A missing one is written from the text the tool holds, a link in its
    place, dangling or not, replaced rather than written through. One
    that differs is the upgrade's to write back, not doctor's.
    """
    launcher = brain.root / schema.LAUNCHER
    if store.readable_file(launcher):
        return []

    return [Finding(path=schema.LAUNCHER, check="layout", message=LAUNCHER_MISSING, repair=write_launcher(launcher))]


def write_launcher(
    path: Path,
) -> Callable[[], None]:
    def repair() -> None:
        frontmatter.write_text(path=str(path), text=schema.LAUNCHER_TEXT, newline="")
        # so it runs by its own name too where the system reads its first line
        os.chmod(path, 0o755)

    return repair


CANNOT_SEE = ", so Claude Code cannot see the skill"
REAL_FOLDER_WITHOUT_SKILL = "a folder with no SKILL.md sits where the skill's stub belongs" + CANNOT_SEE
ANOTHER_SKILL = "a skill of its own sits where the skill's stub belongs, so Claude Code loads that one instead"
SHARED_FOLDER = ", and the skills folder sits outside the project, so the stub is yours to write"
SHARED_REMOVAL = ", and the skills folder sits outside the project, so it is yours to remove"
INTO_THE_BRAIN = ", and the skills folder is a link into the brain's own, so a stub written there would land on the sheet, make .claude/skills a real folder first"
SKILL_GONE = "the stub or the link here is for a skill that is gone"
STUB_MISSING = "the stub Claude Code finds this skill through is missing"
STUB_BEHIND = "the stub is behind the skill's sheet"
A_LINK = "is a link, where the kit writes a stub Claude Code finds the skill through"
A_PLAIN_FILE = "is a plain file, where the kit writes a stub Claude Code finds the skill through"
A_COPY = "is a copy of the skill's sheet, where the kit writes a stub Claude Code finds the skill through"
ON_THE_WAY = ", and the brain reaches the skill's sheet through it, so the fix leaves it, keep the sheet under .agents/skills with no link through .claude/skills first"
STUB_IN_THE_MAKING = ".stub"
LAUNCHER_MISSING = "the launcher python3 .agents/brain runs is missing, which brain doctor --fix writes"
# More links than this on the way to one sheet is a loop, or a way the
# check cannot follow, and the repair is kept back as for one on the way.
LINK_HOPS = 40

# The body of the stub Claude Code finds a skill through under
# .claude/skills, below the sheet's own header, so the agent reads the
# sheet under .agents/skills, the one place its text lives, on every
# system and with no link.
STUB_BODY = "\n<!-- The brain tool writes this file from .agents/skills/{name}/SKILL.md, and brain doctor --fix keeps it in step, so edit the sheet and never this file. -->\n\nRead `.agents/skills/{name}/SKILL.md` and follow it. Its links, such as `references/...`, count from that file's folder.\n"


@dataclass(frozen=True)
class Trouble:
    """What is wrong with one skill's stub: the message, the path the finding names, the repair when doctor may make one, and the entry that repair takes away or writes over."""

    message: str
    path: Path
    repair: Optional[Callable[[], None]] = None
    touches: Optional[Path] = None


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

    # by the disk's identity, since a link may name the project's folder in another case on a disk that folds case
    return folder is not None and root is not None and store.below(path=folder, root=root) is None


def skills_folder_in_brain(
    brain: store.Brain,
) -> bool:
    """Whether `.claude/skills` resolves into the brain, where a stub written or removed would land on the brain's own files, the sheets among them."""
    folder = resolved(brain.root.parent / SKILL_LINKS)
    root = resolved(brain.root)

    return folder is not None and root is not None and store.below(path=folder, root=root) is not None


def on_the_way(
    path: Path,
    entry: Optional[Path],
) -> bool:
    """Whether the system passes through the entry on its way to the path, so taking the entry away or writing over it would take the path's file with it.

    A stub's repair takes away the entry at its place, or writes over the
    SKILL.md in the folder the place leads to, and either may be a step
    of the brain's way to its sheet, through a link, a file link or a
    folder that leaves the brain and comes back. One walk of that way,
    link by link, answers for every such layout. A way the walk cannot
    follow to its end counts as on the way, so the repair waits.
    """
    if entry is None:
        return False

    steps = steps_to(path)
    if steps is None:
        return True

    return any(same_entry(one=step, other=entry) for step in steps)


def steps_to(
    path: Path,
) -> Optional[list[Path]]:
    """Every entry the system passes through to reach the path, each link followed by what it holds the way the system follows it, or None past LINK_HOPS links."""
    parts = list(Path(os.path.abspath(path)).parts)
    current = Path(parts[0])
    pending = parts[1:]
    steps: list[Path] = []
    hops = 0
    while pending:
        part = pending.pop(0)
        if part in ("", "."):
            continue

        if part == "..":
            current = current.parent
            continue

        step = current / part
        steps.append(step)
        try:
            held = Path(os.readlink(step))
        except OSError:
            current = step
            continue

        hops += 1
        if hops > LINK_HOPS:
            return None

        if held.is_absolute():
            current = Path(held.anchor)
            pending = list(held.parts[1:]) + pending
        else:
            pending = list(held.parts) + pending

    return steps


def same_entry(
    one: Path,
    other: Path,
) -> bool:
    """Whether the two paths name one entry, a link as itself, by the file system's own ids where it gives them and by the spelling of the real folder above it where it does not.

    An entry is a name in a folder, so the file and the folder holding it
    must both be the same, and two hard links of one file in two folders
    stay two entries, a write over one leaving the other as it was.
    """
    try:
        first = os.lstat(one)
        second = os.lstat(other)
        first_folder = os.stat(os.path.dirname(one))
        second_folder = os.stat(os.path.dirname(other))
    except OSError:
        first = second = first_folder = second_folder = None

    if first is not None and second is not None and first_folder is not None and second_folder is not None and first.st_ino != 0 and first_folder.st_ino != 0:
        same_file = (first.st_dev, first.st_ino) == (second.st_dev, second.st_ino)
        same_folder = (first_folder.st_dev, first_folder.st_ino) == (second_folder.st_dev, second_folder.st_ino)

        return same_file and same_folder

    def spelled(path: Path) -> str:
        return os.path.normcase(os.path.join(os.path.realpath(os.path.dirname(path)), os.path.basename(path)))

    return spelled(one) == spelled(other)


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
    return f"the skill itself is missing from {(SKILL_HOMES / name).as_posix()}, reinstall the kit"


def stray_skill_links(
    project: Path,
    wanted: list[str],
    shared: bool,
    inside: bool,
) -> list[Finding]:
    """A stub the kit wrote, or a link an older kit made, under .claude/skills for a project skill now gone from the brain, with its removal as the repair.

    A stub is the kit's to remove once the sheet it names is gone, and
    its folder goes with it when nothing else is left there, so a file a
    copy or a person left beside it stays. A link is when it points into the
    brain's skills folder and dangles, leading to nothing at all. One
    that leads to a folder or a file still there is somebody's and is
    left alone, whatever it holds, and so is one the process cannot
    reach, and so is a link the project made elsewhere, and so is
    everything when .claude/skills itself leads into the brain, since
    its entries are then the brain's own. In a skills folder shared
    outside the project the trouble is named and the removal is left to
    a person. The caller skips this pass when the skills folder could
    not be listed.
    """
    places = project / SKILL_LINKS
    found: list[Finding] = []

    homes = resolved(project / SKILL_HOMES)
    if homes is None or inside or resolved(places) is None:
        return found

    try:
        entries = store.in_order(places.iterdir())
    except OSError:
        return found

    for place in entries:
        if place.name in wanted:
            continue

        if is_link(place):
            target = resolved(place)
            if not skill_gone(place) or target is None or not target.is_relative_to(homes):
                continue
            removal = remove_link(place)
        elif stray_stub(project=project, place=place):
            removal = remove_stub(place)
        else:
            continue

        found.append(
            Finding(
                path=(SKILL_LINKS / place.name).as_posix(),
                check="layout",
                message=SKILL_GONE + (SHARED_REMOVAL if shared else ""),
                repair=None if shared else removal,
            ),
        )

    return found


def stray_stub(
    project: Path,
    place: Path,
) -> bool:
    """Whether the real folder holds a stub for a skill whose sheet is gone, whatever else sits beside it."""
    if store.quietly((project / SKILL_HOMES / place.name).exists) or not store.quietly(place.is_dir):
        return False

    return is_stub(path=place / schema.SKILL_FILE, name=place.name)


def remove_stub(
    place: Path,
) -> Callable[[], None]:
    def repair() -> None:
        (place / schema.SKILL_FILE).unlink()
        if not any(place.iterdir()):
            place.rmdir()

    return repair


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


def skill_stub_trouble(
    project: Path,
    name: str,
    shared: bool,
    kits: bool,
) -> Optional[Trouble]:
    """What is wrong with the named skill's stub under `.claude/skills`, or None when Claude Code finds this skill through it.

    What Claude Code needs is `.claude/skills/<name>/SKILL.md`, and the
    kit puts there a stub, the sheet's header over a body that sends the
    agent to the sheet. A stub whose header has fallen behind the
    sheet's is rewritten. A link of any kind, a Windows junction among
    them, a plain file git left in a link's place, and a copy of the
    sheet are replaced by the stub, a copy being one byte for byte or,
    for a skill the stamp says the kit shipped, `kits`, any SKILL.md of
    the skill's name, the copy an older release kept up to date. A real
    folder with no SKILL.md, or one whose SKILL.md is a skill of its
    own, is a person's and is left. The caller keeps every repair back
    where the skills folder is shared or leads into the brain, or where
    what the repair touches is on the brain's way to its sheet. In a skills folder shared
    outside the project, a link, a copy or a stub of this skill from
    another checkout is how the sharing works and passes. A stub can
    only be written while the sheet is there to copy, and a copy with
    nothing left to copy from is all there is, so it passes.
    """
    place = project / SKILL_LINKS / name
    sheet = project / SKILL_HOMES / name / schema.SKILL_FILE
    at_place = SKILL_LINKS / name

    if not store.readable_file(sheet):
        held = place / schema.SKILL_FILE
        if store.readable_file(held) and not is_stub(path=held, name=name):
            return None

        return Trouble(
            message=skill_missing(name),
            path=SKILL_HOMES / name,
        )

    try:
        wanted = stub_text(sheet_text=frontmatter.load(str(sheet)), name=name)
    except frontmatter.FrontmatterError as error:
        return Trouble(
            message=f"the skill's sheet cannot give its stub a header: {error}",
            path=SKILL_HOMES / name,
        )

    write = write_stub(place=place, text=wanted)
    if is_link(place):
        if shared and carries_skill(folder=place, name=name):
            return None

        return Trouble(message=A_LINK, path=at_place, repair=write, touches=place)

    if store.quietly(place.is_dir):
        held = place / schema.SKILL_FILE
        if not store.readable_file(held):
            return Trouble(message=REAL_FOLDER_WITHOUT_SKILL, path=at_place)

        if holds_text(path=held, text=wanted):
            return None

        if shared and carries_skill(folder=place, name=name):
            return None

        if is_stub(path=held, name=name):
            return Trouble(message=STUB_BEHIND, path=at_place, repair=write, touches=held)

        if store.same_bytes(one=held, other=sheet) or (kits and carries_skill(folder=place, name=name)):
            return Trouble(message=A_COPY, path=at_place, repair=write, touches=held)

        return Trouble(message=ANOTHER_SKILL, path=at_place)

    if os.path.lexists(place):
        return Trouble(message=A_PLAIN_FILE, path=at_place, repair=write, touches=place)

    return Trouble(message=STUB_MISSING, path=at_place, repair=write, touches=place)


def stub_text(
    sheet_text: str,
    name: str,
) -> str:
    """The whole text of a skill's stub, the sheet's header block exactly as the sheet writes it over the stub's fixed body."""
    header, _ = split_at_header(sheet_text)

    return header + STUB_BODY.format(name=name)


def split_at_header(
    text: str,
) -> tuple[str, str]:
    """The header block exactly as written, both fences included, and the body after it.

    It goes by the fences alone and never reads the lines between, so a
    header a skill may carry that the brain's own files never do, a
    folded value or a list among them, splits like any other.
    """
    if not text.startswith(frontmatter.FENCE + "\n"):
        raise frontmatter.FrontmatterError("the sheet does not open with a --- fence")

    closing = frontmatter.find_closing_fence(text[len(frontmatter.FENCE) + 1 :])
    if closing is None:
        raise frontmatter.FrontmatterError("the sheet's header fence is never closed")

    end = len(frontmatter.FENCE) + 1 + closing + len(frontmatter.FENCE) + 1

    return text[:end], text[end:]


def is_stub(
    path: Path,
    name: str,
) -> bool:
    """Whether the file is a stub the kit wrote for this skill, by its body, whatever its header says."""
    try:
        _, body = split_at_header(frontmatter.load(str(path)))
    except frontmatter.FrontmatterError:
        return False

    return body == STUB_BODY.format(name=name)


def is_link(
    place: Path,
) -> bool:
    """Whether the place is a link of any kind, known by its resolving somewhere other than where it sits, since a Windows junction is no symbolic link to `islink`."""
    if store.quietly(place.is_symlink):
        return True

    if not os.path.lexists(place):
        return False

    target = resolved(place)
    folder = resolved(place.parent)

    return target is not None and folder is not None and os.path.normcase(target) != os.path.normcase(folder / place.name)


def holds_text(
    path: Path,
    text: str,
) -> bool:
    try:
        return frontmatter.load(str(path)) == text
    except frontmatter.FrontmatterError:
        return False


def write_stub(
    place: Path,
    text: str,
) -> Callable[[], None]:
    """A repair that puts the stub at its place as a real file, never written through a link.

    Into a real folder the stub is written in place, the one file swapped
    whole. Where a link of any kind, a plain file or nothing stands, the
    stub is made in a folder of its own beside the place, named
    `.<name>.stub`, and only once it is written is what stood there taken
    away and the folder moved in, so a write that fails leaves the place
    as it was.
    """

    def repair() -> None:
        folder = place.parent
        folder.mkdir(parents=True, exist_ok=True)
        if not os.access(str(folder), os.W_OK):
            raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(folder))

        if not is_link(place) and store.quietly(place.is_dir):
            frontmatter.write_text(path=str(place / schema.SKILL_FILE), text=text, newline="")
            return

        made = folder / f".{place.name}{STUB_IN_THE_MAKING}"
        clear(made)
        try:
            made.mkdir()
            frontmatter.write_text(path=str(made / schema.SKILL_FILE), text=text, newline="")
            if os.path.lexists(place):
                os.unlink(place)
            os.replace(str(made), str(place))
        except BaseException:
            clear(made)
            raise

    return repair


def clear(
    path: Path,
) -> None:
    """Take away whatever stands at the path, a link of any kind as the link alone and never what it leads to."""
    if is_link(path) or (os.path.lexists(path) and not path.is_dir()):
        os.unlink(path)
    elif os.path.lexists(path):
        shutil.rmtree(path)


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


def check_read_guard(
    brain: store.Brain,
) -> list[Finding]:
    """A project's Claude Code settings carry the rules that keep the agent out of the tool's code and the folders the sandbox may read, which an older tool's upgrade leaves out.

    The kit's own checkout carries neither, since its code is the work
    there, and it is known by the tool's tests, which never ship to a
    project.
    """
    # the upgrade reads doctor, so the guard's rules come from it once both are loaded
    from . import upgrade

    settings = brain.root.parent / upgrade.CLAUDE_SETTINGS
    if store.quietly(question=(brain.root / schema.SKILLS / "agent-brain" / "scripts" / "tests").is_dir) or not store.readable_file(path=settings):
        return []

    where = upgrade.CLAUDE_SETTINGS.as_posix()
    try:
        have = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return []

    # a shape Claude Code cannot read is the upgrade's to refuse in words, so doctor says nothing of it
    if not isinstance(have, dict):
        return []

    permissions = have.get("permissions", {})
    sandbox = have.get("sandbox", {})
    filesystem = sandbox.get("filesystem", {}) if isinstance(sandbox, dict) else None
    deny = permissions.get("deny", []) if isinstance(permissions, dict) else None
    allowed = filesystem.get("allowRead", []) if isinstance(filesystem, dict) else None
    if not isinstance(deny, list) or not isinstance(allowed, list):
        return []

    if all(rule in deny for rule in upgrade.READ_GUARDS) and all(entry in allowed for entry in upgrade.READ_OPENINGS):
        return []

    # a .claude linked into another checkout, the kit's own among them, is that checkout's to guard, as the upgrade refuses it
    out = upgrade.leads_out(project=upgrade.Project(root=brain.root.parent), relative=upgrade.CLAUDE_SETTINGS)
    if out is not None:
        return [Finding(path=where, check="layout", message=f"the read guard is missing from {where}, which sits behind a link that leads out of the project, to {out}, so move the link aside and run brain upgrade, which writes the project its own")]

    return [Finding(path=where, check="layout", message=f"the read guard is missing from {where}, which brain doctor --fix writes", repair=write_guard(path=settings, where=where))]


def write_guard(
    path: Path,
    where: str,
) -> Callable[[], None]:
    from . import upgrade

    def repair() -> None:
        frontmatter.write_text(path=str(path), text=upgrade.guarded(text=path.read_text(encoding="utf-8"), where=where))

    return repair


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
        return [Finding(path=style.SOURCE.as_posix(), check="layout", message=str(error))]

    return [
        Finding(
            path=relative.as_posix(),
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


# The front doors the agents read their rules through. Claude Code reads
# CLAUDE.md while the project keeps a .claude folder, Gemini CLI reads
# GEMINI.md while it keeps a .gemini folder, and every agent reads
# AGENTS.md, which carries the rulebook in .agents/SYSTEM.md.
OWN_DOORS: dict[str, str] = {
    "CLAUDE.md": ".claude",
    "GEMINI.md": ".gemini",
}
RULES = "AGENTS.md"
RULEBOOK = Path(".agents") / "SYSTEM.md"
NO_RULES = "does not import AGENTS.md, so the rules never load"
NO_RULEBOOK = "does not import .agents/SYSTEM.md, so the rulebook never loads"
NOT_REGULAR = "is not a regular file, so no agent reads it"
GEMINI_SETTINGS = Path(".gemini") / "settings.json"

# How deep the rules import is followed through the files a door imports,
# as deep as Claude Code follows them.
DEEPEST = 5

# How much of an imported file is read to tell text from anything else.
SNIFF = 8192

# A path runs to the next whitespace in both agents, so a full stop or a
# comma glued to it becomes part of the name and the file never loads.
# Emphasis markers after a path come off it only when an opener earlier
# in its paragraph pairs them, which a line alone cannot tell.
GLUED = ".,;:!?)"
GLUE = re.compile(f"[{re.escape(GLUED)}]+$")
MARKED = re.compile(f"[*_]+[{re.escape(GLUED)}]*$")

# An import line, one `@path` and nothing else once code, comments and raw
# HTML are blanked, behind list and quote markers or neither.
# a path that opens with a drive, which Windows reads from that drive's root
DRIVE = re.compile(r"^[A-Za-z]:[/\\]")

IMPORT_LINE = re.compile(
    r"^[ \t]*(?:>[ \t]*)*(?:(?:[-*+]|\d{1,9}[.)])[ \t]+)?@(\S+)[ \t]*$",
    re.MULTILINE,
)

# Any `@` an agent may open, at a line's start, after whitespace or after
# an emphasis marker or a bracket, which the rules imports count wherever
# it stands, since an agent may load it there.
ANY_IMPORT = re.compile(
    r"(?:^|(?<=[\s*_(\[>]))@(\S+)",
    re.MULTILINE,
)

# A line comment or a block comment in Gemini CLI's settings, which it
# takes out before it reads them, and a string, which keeps what it holds.
JSON_COMMENT = re.compile(r'"(?:[^"\\]|\\.)*"|//[^\n]*|/\*.*?\*/', re.DOTALL)

# CommonMark's raw HTML blocks hold no import. The first kind opens with
# pre, script, style or textarea and runs to its closing tag. The sixth
# opens with a block tag, even inside a paragraph, and the seventh with a
# lone complete tag where no paragraph is open, each to a blank line.
RAW_TEXT = re.compile(r"^[ \t]{0,3}<(pre|script|style|textarea)(?=[\s>]|$)", re.IGNORECASE)
BLOCK_TAG = re.compile(r"^[ \t]{0,3}</?([A-Za-z][A-Za-z0-9-]*)(?=[\s/>]|$)")
LONE_TAG = re.compile(r"^[ \t]{0,3}(?:<[A-Za-z][A-Za-z0-9-]*(?:\s+[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s\"'=<>`]+))?)*\s*/?>|</[A-Za-z][A-Za-z0-9-]*\s*>)[ \t]*$")
BLOCK_TAGS = frozenset(
    "address article aside base basefont blockquote body caption center col colgroup dd details dialog dir div dl dt fieldset figcaption figure footer form frame frameset h1 h2 h3 h4 h5 h6 head header hr html iframe legend li link main menu menuitem nav noframes ol optgroup option p param search section summary table tbody td tfoot th thead title tr track ul".split(),
)


# What a front door that is not there costs, since the rules then never
# load in the agent that reads it.
MISSING: dict[str, str] = {
    RULES: "is not there, so no agent finds the rules, and the next upgrade writes it back",
    "CLAUDE.md": "is not there, so Claude Code loads no rules, and the next upgrade writes it back",
    "GEMINI.md": "is not there, so Gemini CLI loads no rules, and the next upgrade writes it back",
}


def check_front_doors(
    brain: store.Brain,
) -> list[Finding]:
    """The findings on the imports of the root files the agents read.

    A slip here unloads the rulebook with nothing said, which is what
    bit the kit once. CLAUDE.md is read only while the project keeps a
    .claude folder and GEMINI.md only while it keeps a .gemini folder,
    since a project without one runs no such agent. A front door that is
    a link to AGENTS.md is that file, read once under its own name. A
    front door that is not there is named, AGENTS.md always and the
    other two while their agent's folder is there, and one that is not a
    regular file is named and never opened, so a named pipe never holds
    doctor waiting.
    """
    found: list[Finding] = []
    project = brain.root.parent

    for name in schema.FRONT_DOORS:
        folder = OWN_DOORS.get(name)
        if folder is not None and not keeps(project=project, folder=folder):
            continue

        spelled = spelling_of(
            folder=project,
            name=name,
        )
        if spelled is None:
            found.append(
                import_finding(
                    name=name,
                    message=MISSING.get(name, "is not there, so no agent finds the rules there"),
                ),
            )
            continue

        if spelled != name:
            found.append(
                import_finding(
                    name=name,
                    message=f"is spelled {spelled}, and only {name} is read, so rename it",
                ),
            )
            continue

        door = resolved(project / name)
        if name != RULES and door is not None and door == resolved(project / RULES):
            continue

        text, trouble = text_of_door(project / name)
        if text is None:
            found.append(
                import_finding(
                    name=name,
                    message=trouble,
                ),
            )
            continue

        found += import_slips(
            name=name,
            text=text,
            project=project,
        )

    return found


def check_rule_imports(
    brain: store.Brain,
) -> list[Finding]:
    """The findings on the import lines inside each rule, every path read from the rules folder, as Claude Code and Gemini CLI read an import from the folder of the file that holds it.

    A project's section 0 sat in AGENTS.md before 3.0.0, where the front
    door check read its imports, and it is a rule now, so a slip there is
    named the same way, under the rule's path in the brain.
    """
    project = brain.root.parent
    folder = brain.root / rules.FOLDER
    found: list[Finding] = []
    for rule in rules.names(brain.root):
        name = f"{rules.FOLDER}/{rule}"
        text, _ = text_of_door(folder / rule)
        # a rule that cannot be read is the header check's to name, so it is named once
        if text is None:
            continue

        found += [finding for line in IMPORT_LINE.finditer(visible_text(text)) for finding in line_slips(name=name, token=line.group(1), project=project, base=folder)]

    return found


def text_of_door(
    path: Path,
) -> tuple[Optional[str], str]:
    """A front door's text, or None and the words for why there is none, a door that is not a regular file never opened."""
    try:
        if not stat.S_ISREG(os.stat(path).st_mode):
            return None, NOT_REGULAR

        return path.read_bytes().decode(encoding="utf-8-sig", errors="replace"), ""
    except OSError as error:
        return None, f"cannot be read: {store.explain(error)}"


def spelling_of(
    folder: Path,
    name: str,
) -> Optional[str]:
    """The name an entry goes by in the folder, another case of it when only that is there, or None when neither is.

    The folder is listed rather than the entry opened, since a file
    system blind to case opens Claude.md for CLAUDE.md where Linux does
    not, and the answer has to be the same on every machine. A folder
    that cannot be listed leaves the read to say what is wrong.
    """
    try:
        entries = sorted(os.listdir(folder))
    except OSError:
        return name

    if name in entries:
        return name

    for entry in entries:
        if entry.casefold() == name.casefold():
            return entry

    return None


def import_slips(
    name: str,
    text: str,
    project: Path,
) -> list[Finding]:
    """The import findings of one front door's text, read against the project's files, so the upgrade can ask the same of the kit's own text.

    Only an import line is judged, one `@path` alone on its line once
    code, comments and raw HTML are blanked, and every other `@` is left
    alone, since each agent reads the rest by rules of its own and a
    check that cannot tell says nothing. Each import line gives its own
    findings, a slip written twice named twice, which the upgrade counts
    on to tell the kit's slips from the project's. The rules imports are
    the one question asked of the whole door. CLAUDE.md and GEMINI.md
    are named when no `@` an agent may open leads to AGENTS.md, by
    itself or through the files the door imports, and GEMINI.md not
    while Gemini CLI's settings name AGENTS.md as a context file. And
    AGENTS.md is named when the brain's rulebook is there and no `@`
    leads to it. A carriage return before a line's end, or alone as one,
    reads as the line's end, as both agents read it.
    """
    visible = visible_text(text)
    found = [finding for line in IMPORT_LINE.finditer(visible) for finding in line_slips(name=name, token=line.group(1), project=project)]

    door = resolved(project / name)
    walked = set() if door is None else {door}
    if name in OWN_DOORS and not leads_to(visible=visible, wanted=project / RULES, base=project, depth=DEEPEST, seen=walked) and not in_gemini_context(name=name, project=project):
        found.append(
            import_finding(
                name=name,
                message=NO_RULES,
            ),
        )

    rulebook = project / RULEBOOK
    if name == RULES and store.readable_file(rulebook) and not leads_to(visible=visible, wanted=rulebook, base=project, depth=1):
        found.append(
            import_finding(
                name=name,
                message=NO_RULEBOOK,
            ),
        )

    return found


def line_slips(
    name: str,
    token: str,
    project: Path,
    base: Optional[Path] = None,
) -> list[Finding]:
    """What is wrong with the import an import line holds, judged as every agent reads it, from `base`, the folder of the file that holds it, the project's own by default.

    A path with an escaped space or a fragment, or with emphasis markers
    after it, is passed over, since the agents read it more than one
    way. A mention, a handle or a package that names no file, is no
    import. Glue comes first, then a backslash, a home folder, the root
    of the disk and a climb back in, and last the target, which has to
    be there, under its own case, a regular file that can be read and
    holds text. A target git ignores is each clone's own, so its absence
    is never named, and git and the fix are asked by its path from the
    project's root. In a rule, a path that leads nowhere from the rules
    folder but to a file from the project's root is an import written
    from the wrong folder, named with the path that reaches it, whatever
    git ignores inside the rules folder.
    """
    base = project if base is None else base
    # the folder the path is read from, as text from the project's root, so no path of the disk is ever compared across drives
    folder = "" if base == project else base.relative_to(project).as_posix()
    inside = f" in {folder}/" if folder else ""
    home = f"{folder}/, the folder the rule is read from" if folder else "the project's folder"
    climb = "../" * len(folder.split("/")) if folder else ""
    if folder and "#" in token and "\\ " not in token and not MARKED.search(token):
        # an agent cuts the path at its fragment, so a rule's import of a file at the project's root is named with the path that reaches it, the fragment kept,
        # which a section 0 the 3.0.0 move left unrebased still holds
        path, _, fragment = token.partition("#")
        reached = root_spelling(project=project, base=base, path=path) if path else None
        if reached is None:
            return []

        return [import_finding(name=name, message=f"imports @{token}, which is not there{inside}, though the project's root holds it, so write @{climb}{reached}#{fragment}")]

    if "\\ " in token or "#" in token or MARKED.search(token):
        return []

    bare = GLUE.sub("", token)
    if not bare:
        return []

    if "\\" in bare:
        if not is_import(bare=bare.replace("\\", "/"), project=base):
            return []

        return [import_finding(name=name, message=f"imports @{token} with a backslash in its path, which no agent reads as a folder's slash, so write it with slashes")]

    at_the_root = root_spelling(project=project, base=base, path=bare)
    if at_the_root is None and not is_import(bare=bare, project=base):
        return []

    if bare != token:
        return [glued_on(name=name, path=token)]

    if token.startswith("~"):
        return []

    if token.startswith("/") or DRIVE.match(token):
        return [from_root(name=name, path=token, home=home)]

    if climbs_back_in(path=token, project=project, base=base):
        return [back_in_by_name(name=name, path=token, home=home)]

    spelled = spelled_on_disk(base=base, path=token)
    if spelled is None:
        if os.path.lexists(base / token):
            return [import_finding(name=name, message=f"imports @{token}, which is not a regular file, so no agent loads it")]

        if at_the_root is not None:
            return [import_finding(name=name, message=f"imports @{token}, which is not there{inside}, though the project's root holds it, so write @{climb}{at_the_root}")]

        from_the_root = posixpath.normpath(f"{folder}/{token}") if folder else token
        if ignored_by_git(project=project, path=from_the_root):
            return []

        fixed = ", and brain doctor --fix writes it" if fix_writes(project=project, path=from_the_root) else ""
        return [import_finding(name=name, message=f"imports @{token}, which is not there{inside}{fixed}")]

    if spelled != token:
        return [spelled_otherwise(name=name, path=token, spelled=spelled)]

    trouble = target_trouble(base / spelled)

    return [] if trouble is None else [import_finding(name=name, message=f"imports @{token}, which {trouble}")]


def root_spelling(
    project: Path,
    base: Path,
    path: str,
) -> Optional[str]:
    """The path as the project's root spells it, where a file that holds imports outside the root, a rule, writes it from the root by mistake, else None.

    It is one only where the path leads to no file from the file's own
    folder and to a file from the root. A path with a `..` was written
    from some folder on purpose, and one from the disk's root, a drive
    or the home folder is no path from the project's root, so none is.
    """
    if base == project or path.startswith(("/", "~")) or DRIVE.match(path) is not None or ".." in path.split("/"):
        return None

    if spelled_on_disk(base=base, path=path) is not None:
        return None

    return spelled_on_disk(base=project, path=path)


def fix_writes(
    project: Path,
    path: str,
) -> bool:
    """Whether `brain doctor --fix` writes the missing file, a chat style copy the project owes beside its agent's folder while the Claude Code style it copies reads, as `check_style_copies` asks before it offers the repair."""
    if Path(path) not in style.COPIES or not store.quietly((project / Path(path).parent).is_dir):
        return False

    try:
        style.body_at(project)
    except style.StyleError:
        return False

    return True


def target_trouble(
    path: Path,
) -> Optional[str]:
    """Why an imported regular file never loads, it cannot be read or holds no text, which its first bytes tell, or None."""
    try:
        with open(path, "rb") as handle:
            head = handle.read(SNIFF)
    except OSError:
        return "cannot be read"

    # text in another encoding than UTF-8 is still text, as a front door in one is, so a NUL byte alone tells
    if b"\0" in head:
        return "is not a text file, so Claude Code never loads it"

    return None


def ignored_by_git(
    project: Path,
    path: str,
) -> bool:
    """Whether git ignores the path in the project, which makes it each clone's own, and no where git cannot answer."""
    try:
        reply = handover.git(project=project, arguments=["check-ignore", "-q", "--", path])
    except handover.Unanswered:
        return False

    return reply.code == 0


def leads_to(
    visible: str,
    wanted: Path,
    base: Path,
    depth: int,
    seen: Optional[set[Path]] = None,
) -> bool:
    """Whether an `@` an agent may open in the text leads to the wanted file, in a sentence or not, through any spelling of its case and with emphasis, glue and a fragment set aside, or, while `depth` allows, through a markdown file it imports, read from that file's own folder.

    A path from the root of the disk or the home folder, or one that
    climbs out and back in by the folders' names, never counts, since it
    leads there on one machine alone. The imported files are walked
    breadth first, so each is reached first by its shortest path and
    read once, and `seen` holds the files already read, the door's own
    among them.
    """
    target = resolved(wanted)
    if target is None:
        return False

    seen = set() if seen is None else seen
    waiting: deque[tuple[str, Path, int]] = deque([(visible, base, depth)])
    while waiting:
        text, folder, left = waiting.popleft()
        for match in ANY_IMPORT.finditer(text):
            path = GLUE.sub("", MARKED.sub("", match.group(1).partition("#")[0]))
            if not path or path.startswith(("/", "~")) or DRIVE.match(path) is not None or "\\" in path or climbs_back_in(path=path, project=folder):
                continue

            # a path that reaches the wanted file counts even where that is no file to load, since its import line names that trouble already
            spelled = spelled_on_disk(base=folder, path=path)
            found = folder / (spelled or path)
            place = resolved(found)
            if place == target:
                return True

            if spelled is None or left <= 1 or not spelled.casefold().endswith(".md") or place is None or place in seen:
                continue

            seen.add(place)
            nested = nested_text(found)
            if nested is not None:
                waiting.append((nested, found.parent, left - 1))

    return False


def nested_text(
    path: Path,
) -> Optional[str]:
    """An imported markdown file's text as `visible_text` gives it, or None for one that cannot be read."""
    try:
        text = path.read_bytes().decode(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None

    return visible_text(text)


def visible_text(
    text: str,
) -> str:
    """The text an agent reads its imports in, every line ended by a line feed alone and its code, comments and raw HTML blanked."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    return sections.blanked(
        text=text,
        spans=hidden_spans(text),
    )


def in_gemini_context(
    name: str,
    project: Path,
) -> bool:
    """Whether Gemini CLI's settings name AGENTS.md as a context file, which loads the rules without GEMINI.md importing them."""
    if name != "GEMINI.md":
        return False

    try:
        written = (project / GEMINI_SETTINGS).read_text(encoding="utf-8")
        settings = json.loads(JSON_COMMENT.sub(lambda part: part.group() if part.group().startswith('"') else "", written))
    except (OSError, ValueError):
        return False

    context = settings.get("context") if isinstance(settings, dict) else None
    named = context.get("fileName") if isinstance(context, dict) else None
    names = [named] if isinstance(named, str) else named if isinstance(named, list) else []

    return RULES in names


def keeps(
    project: Path,
    folder: str,
) -> bool:
    """Whether the project keeps the agent's folder, and so runs that agent."""
    return store.quietly((project / folder).is_dir)


def import_finding(
    name: str,
    message: str,
) -> Finding:
    return Finding(
        path=name,
        check="import",
        message=message,
    )


def glued_on(
    name: str,
    path: str,
) -> Finding:
    return import_finding(
        name=name,
        message=f"imports @{path} with the punctuation glued on, so the parser looks for that name and the file never loads, end the path with a space or a line break",
    )


def from_root(
    name: str,
    path: str,
    home: str = "the project's folder",
) -> Finding:
    """An import that opens with a slash is never looked up, since it is there on one machine and missing on the next, and so never counts as the rules import."""
    return import_finding(
        name=name,
        message=f"imports @{path} from the root of the disk, which is there on one machine and missing on the next, so write it from {home}",
    )


def back_in_by_name(
    name: str,
    path: str,
    home: str = "the project's folder",
) -> Finding:
    """An import that climbs out of the project's folder and comes back in by its name is never looked up, since another checkout of the project may go by another name, and so never counts as the rules import."""
    return import_finding(
        name=name,
        message=f"imports @{path} out of the project's folder and back in by its name, which another checkout may not share, so write it from {home}",
    )


def climbs_back_in(
    path: str,
    project: Path,
    base: Optional[Path] = None,
) -> bool:
    """Whether the path, read from `base`, the project's folder by default, climbs above the project's folder and comes back into it by retracing the names it climbed out of.

    It is decided from the path's parts and the names of the project's
    own folder and its parents, never from the disk. The path is walked
    over those names, a `..` stepping up one and a name stepping down
    into that name, and it comes back in only when, after climbing above
    the project, its steps down lead to the project's own folder again.
    A path that climbs out and stays out is looked up like any other.
    """
    home = list(project.parts)
    trail = list((project if base is None else base).parts)
    climbed_out = False

    for part in path.split("/"):
        if part in ("", "."):
            continue

        if part == "..":
            if len(trail) > 1:
                trail.pop()
            climbed_out = climbed_out or len(trail) < len(home)
            continue

        trail.append(part)
        if climbed_out and trail == home:
            return True

    return False


def spelled_otherwise(
    name: str,
    path: str,
    spelled: str,
) -> Finding:
    return import_finding(
        name=name,
        message=f"imports @{path}, which is spelled {spelled}, so it loads only where the file system ignores case",
    )


def is_import(
    bare: str,
    project: Path,
) -> bool:
    """Whether a token, its trailing punctuation set aside, is an import and not a mention.

    It is one when it opens with `~`, `/`, `./` or `../`, when it names a
    markdown file, or when its target is there under any spelling of its
    case. Anything else that leads nowhere, a handle, a package or a
    decorator, is a mention.
    """
    if bare.startswith(("~", "/", "./", "../")) or bare.casefold().endswith(".md"):
        return True

    spelled = spelled_on_disk(
        base=project,
        path=bare,
    )

    return spelled is not None


def spelled_on_disk(
    base: Path,
    path: str,
) -> Optional[str]:
    """The path as the files spell it, or None when it leads to no file.

    It is walked part by part from `base`, and each part is looked up in
    its folder's listing, by its exact name first and then by its case.
    Asking the file system for the whole path would follow the machine's
    case rule, and the answer has to be the same on every machine. A
    path from the root of the disk never comes here, for the same
    reason.
    """
    current = base
    spelled: list[str] = []

    for part in path.split("/"):
        if part in ("", ".", ".."):
            spelled.append(part)
            current = current / part
            continue

        entry = spelling_of(
            folder=current,
            name=part,
        )
        if entry is None:
            return None

        spelled.append(entry)
        current = current / entry

    if not store.readable_file(current):
        return None

    return "/".join(spelled)


def hidden_spans(
    text: str,
) -> list[tuple[int, int]]:
    """Where the code, the HTML comments and the raw HTML blocks sit, which hold no import an agent opens, by the one reading of markdown the rest of the tool uses.

    A comment that opens a line and never closes hides the rest of the
    text, as it does from the agents that read the file.
    """
    shared = sections.blocks_of(
        text=text,
        unclosed_hides_rest=True,
    )
    spans, comments = sections.inline_of(text=text, stretches=shared.inline)
    hidden = merged(shared.code + spans + shared.comments + comments)

    return merged(hidden + html_blocks(text=sections.blanked(text=text, spans=hidden), original=text, continued=continued_lines(text=text, stretches=shared.inline)))


def continued_lines(
    text: str,
    stretches: list[tuple[int, int]],
) -> set[int]:
    """Where each line starts that carries on a paragraph, a heading or a row the shared reader found begun on an earlier line, the lines a lone tag cannot open a raw HTML block on."""
    found: set[int] = set()
    for start, end in stretches:
        at = text.find("\n", start, end)
        while at != -1 and at + 1 < end:
            found.add(at + 1)
            at = text.find("\n", at + 1, end)

    return found


def html_blocks(
    text: str,
    original: str,
    continued: set[int],
) -> list[tuple[int, int]]:
    """Where CommonMark's raw HTML blocks sit, read in a text whose code and comments are blanked, each from the line that opens it.

    A line is blank only where the original text holds nothing on it,
    so a comment inside a block never ends it. A lone tag opens a block
    only on a line that carries on no paragraph, which the shared reader
    says, since it already knows what a comment, a fence or a heading
    of either kind ends.
    """
    found: list[tuple[int, int]] = []
    opened: Optional[int] = None
    closer: Optional[re.Pattern] = None

    for line in sections.LINE.finditer(text):
        content = line.group()
        blank = not original[line.start() : line.end()].strip()
        if opened is not None:
            if closer is None and blank:
                found.append((opened, line.start()))
                opened = None
            elif closer is not None and closer.search(content):
                found.append((opened, line.end()))
                opened, closer = None, None
            continue

        if not content.strip():
            continue

        raw = RAW_TEXT.match(content)
        tag = BLOCK_TAG.match(content)
        if raw is not None:
            closer = re.compile(rf"</{raw.group(1)}\s*>", re.IGNORECASE)
            if closer.search(content, raw.end()):
                found.append((line.start(), line.end()))
                closer = None
            else:
                opened = line.start()
        elif (tag is not None and tag.group(1).lower() in BLOCK_TAGS) or (line.start() not in continued and LONE_TAG.match(content)):
            opened, closer = line.start(), None

    if opened is not None:
        found.append((opened, len(text)))

    return found


def merged(
    spans: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """The spans in order, each that overlaps the one before joined to it, so a stretch is blanked once."""
    found: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if found and start <= found[-1][1]:
            found[-1] = (found[-1][0], max(found[-1][1], end))
            continue

        found.append((start, end))

    return found


# No check here holds a file's prose to the house style. That is
# brainlib/check.py's, which the post write hook and the gates run and
# which names each slip by its line, so one slip is named once. Doctor
# holds only the header values to it, where the check never looks.
def check_rules(
    brain: store.Brain,
) -> list[Finding]:
    """The findings on AGENTS.md's imports of the rules, every rule imported once in load order below the mark and nothing else, which the fix writes.

    AGENTS.md is the kit's, and the lines after its mark are the tool's,
    so a rule added, renamed or deleted by hand gets its import put
    right. An AGENTS.md from before the rules carries no mark, which the
    upgrade writes, so that is named and left alone. A missing or
    unreadable AGENTS.md is the front door check's to name. A markdown
    file in a folder below the rules is named too, since a rule loads
    only from the rules folder itself, a dotted path aside.
    """
    folder = brain.root / rules.FOLDER
    try:
        below = store.in_order(path for path in folder.rglob("*.md") if path.name.endswith(".md") and path.parent != folder and not any(part.startswith(".") for part in path.relative_to(folder).parts))
    except OSError:
        below = []
    nested = [Finding(path=path.relative_to(brain.root).as_posix(), check="rules", message=f"sits in a folder below {rules.FOLDER}/, where no rule loads, so move it up into {rules.FOLDER}/") for path in below]

    agents = brain.root.parent / rules.AGENTS
    if not store.readable_file(agents):
        return nested

    try:
        text = agents.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return nested

    imported: Optional[list[str]] = rules.imports_in(text)
    if imported is None:
        return [*nested, Finding(path=rules.AGENTS, check="rules", message="has no line the rules are imported below, so no rule loads, and the upgrade writes it")]

    on_disk: list[str] = rules.names(brain.root)
    # every line below the mark is the tool's, so anything there but a rule's import, a merge's conflict markers among them, goes
    prefix = rules.IMPORT.format(name="")
    strays = [line.strip() for line in text.split(rules.MARK, 1)[1].splitlines() if line.strip() and not line.strip().startswith(prefix)]

    def repair() -> None:
        rules.write_imports(brain.root)

    findings = [Finding(path=rules.AGENTS, check="rules", message=f"carries `{line}` below the line the rules are imported under, where the tool writes their imports alone", repair=repair) for line in strays]
    findings += [Finding(path=rules.AGENTS, check="rules", message=f"does not import .agents/rules/{name}, so the rule never loads", repair=repair) for name in on_disk if name not in imported]
    findings += [Finding(path=rules.AGENTS, check="rules", message=f"imports .agents/rules/{name}, which is no rule", repair=repair) for name in dict.fromkeys(imported) if name not in on_disk]
    findings += [Finding(path=rules.AGENTS, check="rules", message=f"imports .agents/rules/{name} more than once", repair=repair) for name in dict.fromkeys(imported) if imported.count(name) > 1]
    if not findings and imported != on_disk:
        findings.append(Finding(path=rules.AGENTS, check="rules", message="imports the rules out of their load order, the project's own first and the others by name", repair=repair))

    return nested + findings


def check_rust(
    brain: store.Brain,
) -> list[Finding]:
    """The findings on the kit's Rust rule, which stands exactly while the project's root holds a Cargo.toml, and on what a Rust project lacks of the rule's asks.

    The rule is written from the template the tool carries, with its
    import and the configs the project lacks, rewritten where it says
    other than the template, and retired where Rust is gone, unless it
    says more than the kit's words, which the project moves first. A
    toolchain pin and the lints tables are the project's to write, from
    the reference copy, so they are named and left alone.
    """
    project = brain.root.parent
    rule = brain.root / rules.FOLDER / rust.RULE
    where = f"{rules.FOLDER}/{rust.RULE}"
    has_rule = store.readable_file(rule)
    if not has_rule and not rust.is_rust(project):
        return []

    try:
        kits = rust.template_body()
    except (OSError, UnicodeDecodeError) as error:
        return [Finding(path=where, check="rust", message=f"cannot be held to the kit's words, since the tool's template of them cannot be read, {store.explain(error)}, and the upgrade writes it back")]

    # the words below the header, which doctor's own fills of people and dates never touch, or None where the file does not read as text
    try:
        says: Optional[str] = rust.body_of(rule.read_text(encoding="utf-8-sig")).strip() if has_rule else ""
    except (OSError, UnicodeDecodeError):
        says = None

    if not rust.is_rust(project):
        if says != kits.strip():
            return [Finding(path=where, check="rust", message=rust.NO_RUST_CHANGED)]

        return [Finding(path=where, check="rust", message=rust.NO_RUST, repair=lambda: rust.retire(brain.root))]

    if not has_rule:
        holder = rust.holder_of_the_name(entries=brain.entries(), rule=rule)
        if holder is not None:
            found = [Finding(path=where, check="rust", message=rust.NAME_TAKEN.format(path=holder))]
        else:
            found = [Finding(path=where, check="rust", message=rust.MISSING, repair=lambda: rust.write_rule(brain.root))]
    elif says is None:
        # the file is the kit's whole, so one that does not read as text is written again from the template
        found = [Finding(path=where, check="rust", message=rust.CHANGED, repair=lambda: rust.write_rule(brain.root))]
    elif says != kits.strip():
        found = [Finding(path=where, check="rust", message=rust.CHANGED, repair=lambda: rust.rewrite_body(brain.root))]
    else:
        found = []

    if not (project / rust.TOOLCHAIN).exists():
        found.append(Finding(path=rust.TOOLCHAIN, check="rust", message=rust.NO_TOOLCHAIN))

    try:
        found += [Finding(path=path, check="rust", message=message) for path, message in rust.lint_trouble(project)]
    except (OSError, UnicodeDecodeError) as error:
        found.append(Finding(path=rust.MANIFEST, check="rust", message=f"cannot be read for its lints, {store.explain(error)}"))

    return found


CHECKS: tuple[Callable[[store.Brain], list[Finding]], ...] = (
    check_leftovers,
    check_strays,
    check_frontmatter,
    check_names,
    check_kinds,
    check_fields,
    check_people,
    check_sections,
    check_steps,
    check_filenames,
    check_links,
    check_indexes,
    check_hygiene,
    check_layout,
    check_front_doors,
    check_rule_imports,
    check_rust,
    check_rules,
    check_read_guard,
)
