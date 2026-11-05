"""Checking the whole brain, fixing what is mechanical, flagging the rest.

Every check is a function that reads the brain and reports findings. A
finding that a machine can put right carries its own repair, and `run`
applies those before it reports, so what comes back is only what needs a
person or an agent to decide.
"""

import errno
import json
import os
import re
import shutil
import stat
from collections import deque
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Optional, Union

from . import autoack, conclude, frontmatter, handover, index, links, people, schema, sections, steps, store, style, task, writes

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

    for path in sorted(brain.root.rglob("*.md")):
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

    if target.endswith((".md", ".json")) or target in (schema.VERSION_FILE, autoack.FILE, conclude.FILE, task.FILE):
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
                why = refiled_word(brain=brain, target=target, kept=fresh.points_at)
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
    target: store.Entry,
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
                message=f"the skills folder cannot be listed, so only the kit's skill links were checked: {reason}",
            ),
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
        )
        found.extend(strays)

    found.extend(check_style_copies(brain))

    return found


CANNOT_SEE = ", so Claude Code cannot see the skill"
# a skill link is made under this name beside its place and moved into it, so a refused link touches nothing
LINK_IN_THE_MAKING = ".link"
# what the system says when it refuses a symbolic link: Windows without Developer Mode in its own number, a disk with no links elsewhere
PRIVILEGE_NOT_HELD = 1314
LINKS_REFUSED = frozenset({errno.EPERM, errno.ENOTSUP, errno.EOPNOTSUPP, errno.ENOSYS})
NO_SYMBOLIC_LINKS = "this system refuses symbolic links, so turn on Windows Developer Mode, run git config core.symlinks true, then git checkout -- .claude/skills to bring the skill links back as links, and run brain doctor --fix"
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
    return f"the skill itself is missing from {(SKILL_HOMES / name).as_posix()}, reinstall the kit"


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
                path=(SKILL_LINKS / link.name).as_posix(),
                check="layout",
                message=SKILL_GONE + (SHARED_REMOVAL if shared else ""),
                repair=None if shared else remove_link(link),
            ),
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


def make_skill_link(
    project: Path,
    name: str,
) -> Callable[[], None]:
    """A repair that puts the named skill's symlink in place, clearing a dead link or a stray file first, git's stand in for a link among them.

    A real folder is never removed here. It is somebody's, and the check
    leaves it for a person. The link is made under a name of its own and
    moved into place, so where the system refuses a symbolic link, as
    Windows does without Developer Mode, what stood there, git's stand in
    among them, stays as it was and the failure says how to get links.
    """

    def repair() -> None:
        link = project / SKILL_LINKS / name
        link.parent.mkdir(parents=True, exist_ok=True)
        if not os.access(str(link.parent), os.W_OK):
            raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(link.parent))

        target = skill_target(
            project=project,
            link=link,
            name=name,
        )
        made = link.with_name(f".{link.name}{LINK_IN_THE_MAKING}")
        if os.path.lexists(made):
            made.unlink()

        try:
            os.symlink(target, str(made))
        except OSError as error:
            if getattr(error, "winerror", None) == PRIVILEGE_NOT_HELD or error.errno in LINKS_REFUSED:
                raise OSError(error.errno, NO_SYMBOLIC_LINKS) from error
            raise

        # the new link stands, so what stood in its place goes first, since Windows moves nothing over a link to a folder
        if link.is_symlink() or (link.exists() and not link.is_dir()):
            link.unlink()
        os.replace(str(made), str(link))

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
) -> list[Finding]:
    """What is wrong with the import an import line holds, judged as every agent reads it.

    A path with an escaped space or a fragment, or with emphasis markers
    after it, is passed over, since the agents read it more than one
    way. A mention, a handle or a package that names no file, is no
    import. Glue comes first, then a backslash, a home folder, the root
    of the disk and a climb back in, and last the target, which has to
    be there, under its own case, a regular file that can be read and
    holds text. A target git ignores is each clone's own, so its absence
    is never named.
    """
    if "\\ " in token or "#" in token or MARKED.search(token):
        return []

    bare = GLUE.sub("", token)
    if not bare:
        return []

    if "\\" in bare:
        if not is_import(bare=bare.replace("\\", "/"), project=project):
            return []

        return [import_finding(name=name, message=f"imports @{token} with a backslash in its path, which no agent reads as a folder's slash, so write it with slashes")]

    if not is_import(bare=bare, project=project):
        return []

    if bare != token:
        return [glued_on(name=name, path=token)]

    if token.startswith("~"):
        return []

    if token.startswith("/"):
        return [from_root(name=name, path=token)]

    if climbs_back_in(path=token, project=project):
        return [back_in_by_name(name=name, path=token)]

    spelled = spelled_on_disk(base=project, path=token)
    if spelled is None:
        if os.path.lexists(project / token):
            return [import_finding(name=name, message=f"imports @{token}, which is not a regular file, so no agent loads it")]

        if ignored_by_git(project=project, path=token):
            return []

        fixed = ", and brain doctor --fix writes it" if fix_writes(project=project, path=token) else ""
        return [import_finding(name=name, message=f"imports @{token}, which is not there{fixed}")]

    if spelled != token:
        return [spelled_otherwise(name=name, path=token, spelled=spelled)]

    trouble = target_trouble(project / spelled)

    return [] if trouble is None else [import_finding(name=name, message=f"imports @{token}, which {trouble}")]


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
            if not path or path.startswith(("/", "~")) or "\\" in path or climbs_back_in(path=path, project=folder):
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
) -> Finding:
    """An import that opens with a slash is never looked up, since it is there on one machine and missing on the next, and so never counts as the rules import."""
    return import_finding(
        name=name,
        message=f"imports @{path} from the root of the disk, which is there on one machine and missing on the next, so write it from the project's folder",
    )


def back_in_by_name(
    name: str,
    path: str,
) -> Finding:
    """An import that climbs out of the project's folder and comes back in by its name is never looked up, since another checkout of the project may go by another name, and so never counts as the rules import."""
    return import_finding(
        name=name,
        message=f"imports @{path} out of the project's folder and back in by its name, which another checkout may not share, so write it from the project's folder",
    )


def climbs_back_in(
    path: str,
    project: Path,
) -> bool:
    """Whether the path climbs above the project's folder and comes back into it by retracing the names it climbed out of.

    It is decided from the path's parts and the names of the project's
    own folder and its parents, never from the disk. The path is walked
    over those names, a `..` stepping up one and a name stepping down
    into that name, and it comes back in only when, after climbing above
    the project, its steps down lead to the project's own folder again.
    A path that climbs out and stays out is looked up like any other.
    """
    home = list(project.parts)
    trail = list(home)
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
    check_read_guard,
)
