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
from typing import Callable, Optional, Union

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
    # a review is pointed at by its name, and so is a todo or a bug with no id, a file the tool never wrote, so their cells follow the name too
    pointed_by_name = entry.kind.name == "review" or (entry.kind.name in ("todo", "bug") and entry.identifier is None)
    follows = (entry.kind.name == "plan" or pointed_by_name) and not any(
        other.path != entry.path and actual in (other.name, task.file_key(other)) for other in brain.entries()
    )

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
                )
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
                )
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
    table may be the reproduction, which the spec puts under Evidence,
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


# In the import parsers of Claude Code and Gemini CLI, an `@` at the
# start of a text, after whitespace or right after an emphasis marker
# opens a path that runs to the next whitespace, so a full stop or a
# comma glued to the path becomes part of it and the file silently never
# loads. Both step over code and HTML comments, and Claude Code reads a
# backslash before a space as part of the path.
IMPORT = re.compile(r"(?<![^\s*_])@((?:[^\s\\]|\\ )+)")
HTML_COMMENT = re.compile(
    r"<!--.*?-->",
    re.DOTALL,
)
GLUED = ".,;:!?)"
ESCAPED_SPACE = "\\ "
RULES = "AGENTS.md"

# An emphasis marker closing on the path, and any punctuation after it,
# which the lexer leaves outside the text the parser reads.
EMPHASIS_END = re.compile(f"[*_]+[{re.escape(GLUED)}]*$")

# The markdown lexer both agents read with. A fence opens on a line of
# three or more backticks or tildes indented at most three spaces, a
# backtick fence's info string holding no backtick, and only a fence of
# the same character at least as long closes it.
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
FENCE_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})\s*$")
BACKTICKS = re.compile(r"`+")
PARAGRAPH_BREAK = re.compile(r"\n[ \t\r]*\n")
NOT_A_LINE_END = re.compile(r"[^\n]")
CODE_INDENT = 4

# The front doors an agent reads only where the project keeps that
# agent's folder, and the ones Gemini CLI reads, whose parser ends a
# path at the first whitespace and knows no escape.
AGENT_FOLDERS: dict[str, str] = {
    "CLAUDE.md": ".claude",
    "GEMINI.md": ".gemini",
}
GEMINI_READS: tuple[str, ...] = (RULES, "GEMINI.md")

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
    """The imports in the root files the agents read, each reaching a file, none glued to punctuation, and the rules imported.

    A slip here unloads the rulebook in two of the three agents with
    nothing said, which is what bit the kit once, so doctor reads the
    front doors the way the parsers do. CLAUDE.md is read only while the
    project keeps a .claude folder and GEMINI.md only while it keeps a
    .gemini folder, since a project without one runs no such agent. A
    front door that is a link to AGENTS.md is that file, read once under
    its own name. A front door that is not there is named, AGENTS.md
    always and the other two while their agent's folder is there.
    """
    found: list[Finding] = []
    project = brain.root.parent

    for name in schema.FRONT_DOORS:
        folder = AGENT_FOLDERS.get(name)
        if folder is not None and not store.quietly((project / folder).is_dir):
            continue

        spelled = spelling_of(
            project=project,
            name=name,
        )
        if spelled is None:
            found.append(
                Finding(
                    path=name,
                    check="import",
                    message=MISSING[name],
                )
            )
            continue

        if spelled != name:
            found.append(
                Finding(
                    path=name,
                    check="import",
                    message=f"is spelled {spelled}, and only {name} is read, so rename it",
                )
            )
            continue

        door = resolved(project / name)
        if name != RULES and door is not None and door == resolved(project / RULES):
            continue

        try:
            text = (project / name).read_bytes().decode(
                encoding="utf-8-sig",
                errors="replace",
            )
        except OSError as error:
            found.append(
                Finding(
                    path=name,
                    check="import",
                    message=f"cannot be read: {store.explain(error)}",
                )
            )
            continue

        found += import_slips(
            name=name,
            text=text,
            project=project,
        )

    return found


def spelling_of(
    project: Path,
    name: str,
) -> Optional[str]:
    """The name the front door goes by in the project folder, another case of it when only that is there, or None when neither is.

    The folder is listed rather than the file opened, since a file
    system blind to case opens Claude.md for CLAUDE.md where Linux does
    not, and the answer has to be the same on every machine. A folder
    that cannot be listed leaves the read to say what is wrong.
    """
    try:
        entries = sorted(os.listdir(project))
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

    A token is an import only when it holds a dot or opens with `~` or
    `/`, so a mention such as @alice or @tanstack/query is passed over.
    The path is cut at its first `#`, the way Claude Code drops a
    fragment. An import from the home folder is personal, there on one
    machine and missing on the next, so it is never looked for. The
    rules load when any import resolves to the project's AGENTS.md.
    """
    found: list[Finding] = []
    rules = resolved(project / RULES)
    imports_rules = False
    prose = HTML_COMMENT.sub(
        repl=" ",
        string=code_blanked(text),
    )

    for match in IMPORT.finditer(prose):
        token = EMPHASIS_END.sub(
            repl="",
            string=match.group(1),
        ).partition("#")[0]
        if not import_shaped(token.rstrip(GLUED)):
            continue

        if ESCAPED_SPACE in token and name in GEMINI_READS:
            found.append(
                Finding(
                    path=name,
                    check="import",
                    message=f"imports @{token} with an escaped space, which Gemini CLI does not read, so the path ends at the backslash there",
                )
            )
            continue

        if token[-1] in GLUED:
            found.append(
                Finding(
                    path=name,
                    check="import",
                    message=f"imports @{token} with the punctuation glued on, so the parser looks for that name and the file never loads, end the path with a space or a line break",
                )
            )
            continue

        if token.startswith("~"):
            continue

        target = project / token.replace(
            ESCAPED_SPACE,
            " ",
        )
        if rules is not None and resolved(target) == rules:
            imports_rules = True

        if not store.readable_file(target):
            found.append(
                Finding(
                    path=name,
                    check="import",
                    message=f"imports @{token}, which is not there",
                )
            )

    if name != RULES and not imports_rules:
        found.append(
            Finding(
                path=name,
                check="import",
                message="does not import AGENTS.md, so the rules never load",
            )
        )

    return found


def import_shaped(
    bare: str,
) -> bool:
    """Whether a token, its trailing punctuation set aside, reads as a path, with a dot in it, `./` included, or an opening `~` or `/`."""
    return "." in bare or bare.startswith(("~", "/"))


def code_blanked(
    text: str,
) -> str:
    """The text with its code blanked where the agents' markdown lexer finds code, blocks line by line and spans by backtick runs."""
    return spans_blanked(blocks_blanked(text))


def blocks_blanked(
    text: str,
) -> str:
    """The text with each code block's lines emptied.

    A fence runs to the closer that matches it or to the end of the
    text. An indented line is code when it follows a blank line, another
    indented code line, a fence or the start of the text, since there is
    then no paragraph for it to carry on.
    """
    kept: list[str] = []
    fence: Optional[str] = None
    after_break = True

    for line in text.split("\n"):
        if fence is not None:
            closer = FENCE_CLOSE.match(line)
            if closer is not None and closer.group(1)[0] == fence[0] and len(closer.group(1)) >= len(fence):
                fence = None

            kept.append("")
            continue

        opener = FENCE_OPEN.match(line)
        if opener is not None and not (opener.group(1)[0] == "`" and "`" in opener.group(2)):
            fence = opener.group(1)
            after_break = True
            kept.append("")
            continue

        blank = not line.strip()
        if not blank and after_break and indent_of(line) >= CODE_INDENT:
            kept.append("")
            continue

        kept.append(line)
        after_break = blank

    return "\n".join(kept)


def indent_of(
    line: str,
) -> int:
    """How many columns the line's leading whitespace spans, a tab reaching the next multiple of four."""
    columns = 0
    for character in line:
        if character == " ":
            columns += 1
        elif character == "\t":
            columns += CODE_INDENT - columns % CODE_INDENT
        else:
            break

    return columns


def spans_blanked(
    text: str,
) -> str:
    """The text with each code span turned to spaces, a run of backticks closed by the next run as long inside its paragraph.

    An opener with no such closer is literal backticks, and the search
    moves on to the next run.
    """
    runs = list(BACKTICKS.finditer(text))
    kept: list[str] = []
    cursor = 0
    index = 0

    while index < len(runs):
        opener = runs[index]
        closing = closing_run(
            runs=runs,
            opener=index,
        )
        if closing is None or PARAGRAPH_BREAK.search(text[opener.end() : runs[closing].start()]):
            index += 1
            continue

        closer = runs[closing]
        kept.append(text[cursor : opener.start()])
        kept.append(
            NOT_A_LINE_END.sub(
                repl=" ",
                string=text[opener.start() : closer.end()],
            )
        )
        cursor = closer.end()
        index = closing + 1

    kept.append(text[cursor:])

    return "".join(kept)


def closing_run(
    runs: list[re.Match],
    opener: int,
) -> Optional[int]:
    """The index of the first run after the opener that is as long as it, or None when there is none."""
    width = len(runs[opener].group())

    for offset, run in enumerate(runs[opener + 1 :]):
        if len(run.group()) == width:
            return opener + 1 + offset

    return None


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
    check_front_doors,
)
