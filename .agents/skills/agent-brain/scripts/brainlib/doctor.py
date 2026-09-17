"""Checking the whole brain, fixing what is mechanical, flagging the rest.

Every check is a function that reads the brain and reports findings. A
finding that a machine can put right carries its own repair, and `run`
applies those before it reports, so what comes back is only what needs a
person or an agent to decide.
"""

import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Optional

from . import frontmatter, index, links, schema, sections, store, style, writes

SKIP_DIRS: frozenset[str] = frozenset({"skills", ".worktrees"})

EM_DASH = "—"
EN_DASH = "–"

FENCED = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")

MACHINE_PATH = re.compile(r"(/Users/|/home/|[A-Z]:\\)")

SECRET_SHAPES = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"),
    re.compile(r"(?i)\b(password|passwd|secret|token)\s*[:=]\s*\S{6,}"),
)

SKILL_LINK = Path(".claude") / "skills" / "agent-brain"
SKILL_HOME = Path(".agents") / "skills" / "agent-brain"

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
            except (OSError, frontmatter.FrontmatterError) as error:
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
) -> list[Path]:
    """Every markdown file under the brain, the skills and the rulebook excepted."""
    found: list[Path] = []

    for path in sorted(brain.root.rglob("*.md")):
        parts = path.relative_to(brain.root).parts
        if parts[0] in SKIP_DIRS:
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


def stray_reason(
    where: str,
) -> str:
    parts = where.split("/")

    if parts[0] == "reviews" and parts[-1] == schema.LEDGER:
        return f"a ledger sits directly in its review folder, reviews/<folder>/{schema.LEDGER}, nothing deeper"

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
        where = relative(brain, path)

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
            repair=set_field(path, "links", "[]"),
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
                    repair=set_field(entry.path, "name", expected),
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
        try:
            writes.check_own(kind=entry.kind, fields=entry.document.fields())
        except writes.WriteError as error:
            found.append(Finding(path=entry.relative, check="fields", message=str(error)))

    return found


def check_sections(
    brain: store.Brain,
) -> list[Finding]:
    found: list[Finding] = []

    for entry in brain.entries():
        body = entry.document.body
        for title in sections.missing(body=body, kind=entry.kind):
            found.append(
                Finding(path=entry.relative, check="sections", message=f"no {title} heading")
            )

        for message in lifecycle_gaps(entry):
            found.append(Finding(path=entry.relative, check="lifecycle", message=message))

    return found


def lifecycle_gaps(
    entry: store.Entry,
) -> list[str]:
    """What a file in its current status is required to carry and does not."""
    status = entry.field("status")
    body = entry.document.body
    gaps: list[str] = []

    if entry.kind.name == "bug" and status == "fixed":
        if not sections.is_filled(body=body, title="Fix"):
            gaps.append("fixed, with nothing under Fix")

    if entry.kind.name == "bug" and status == "wontfix":
        if not sections.is_filled(body=body, title="Problem"):
            gaps.append("wontfix, with no reason under Problem")

    if entry.kind.name == "todo" and status in ("done", "dropped"):
        if not entry.field("done"):
            gaps.append(f"{status}, with no done date")

    if entry.kind.name == "todo" and status == "done":
        if not sections.is_filled(body=body, title="Done when"):
            gaps.append("done, with nothing under Done when")

    if entry.kind.name == "decision" and status == "superseded":
        if not entry.field("superseded-by"):
            gaps.append("superseded, with no superseded-by")

    return gaps


def check_filenames(
    brain: store.Brain,
) -> list[Finding]:
    found: list[Finding] = []
    numbers: dict[str, str] = {}

    for entry in brain.entries():
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
    documents = [(entry.path, entry.document) for entry in brain.entries()]
    documents += links.kit_documents(brain)

    for path, document in documents:
        where = relative(brain, path)
        current = document.get_list("links")
        canonical: list[str] = []

        for link in current:
            resolved = links.canonical(brain, link)
            if resolved is None:
                found.append(Finding(path=where, check="link", message=f"'{link}' reaches nothing"))
            canonical.append(resolved or link)

        if canonical != current:
            found.append(
                Finding(
                    path=where,
                    check="link",
                    message="links not written as paths relative to .agents/",
                    repair=set_links(path, canonical),
                )
            )

    for entry in brain.entries():
        for target in links.broken_in_body(entry):
            found.append(
                Finding(path=entry.relative, check="link", message=f"body link '{target}' reaches nothing")
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
    """One build of the brain serves the check and every repair it hands out."""
    wanted = index.build(brain)

    return [
        Finding(
            path=relative(brain, path),
            check="index",
            message="differs from what the tool builds for its folder",
            repair=write_index(path, wanted[path]),
        )
        for path in index.stale_among(wanted)
    ]


def write_index(
    path: Path,
    text: str,
) -> Callable[[], None]:
    def repair() -> None:
        index.write_one(path=path, text=text)

    return repair


def prose_of(
    text: str,
) -> str:
    """The text with code taken out, since code keeps its own punctuation."""
    return INLINE_CODE.sub("", FENCED.sub("", text))


def check_style(
    brain: store.Brain,
) -> list[Finding]:
    found: list[Finding] = []

    for path in all_markdown(brain):
        try:
            body = prose_of(frontmatter.read(str(path)).body)
        except frontmatter.FrontmatterError:
            continue

        where = relative(brain, path)

        if EM_DASH in body or EN_DASH in body:
            found.append(Finding(path=where, check="style", message="carries a dash the house style bans"))

        if ";" in body:
            found.append(Finding(path=where, check="style", message="carries a semicolon"))

    return found


def check_hygiene(
    brain: store.Brain,
) -> list[Finding]:
    found: list[Finding] = []

    for path in all_markdown(brain):
        try:
            text = path.read_bytes().decode("utf-8", errors="replace")
        except OSError:
            continue

        where = relative(brain, path)

        if MACHINE_PATH.search(prose_of(text)):
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

    if not store.readable_file(brain.root / "VERSION"):
        found.append(Finding(path="VERSION", check="layout", message="no kit version stamp, run the upgrade"))

    trouble = skill_link_trouble(project)
    if trouble is not None:
        found.append(
            Finding(
                path=str(SKILL_HOME if trouble == SKILL_ITSELF_MISSING else SKILL_LINK),
                check="layout",
                message=trouble,
                repair=None if trouble in LINK_TROUBLE_FOR_A_PERSON else make_skill_link(project),
            )
        )

    found.extend(check_style_copies(brain))

    return found


CANNOT_SEE = ", so Claude Code cannot see the skill"
REAL_FOLDER_WITHOUT_SKILL = "a folder with no SKILL.md sits where the skill link belongs" + CANNOT_SEE
SKILL_ITSELF_MISSING = "the skill itself is missing from .agents/skills/agent-brain, reinstall the kit"
LINK_TROUBLE_FOR_A_PERSON = (REAL_FOLDER_WITHOUT_SKILL, SKILL_ITSELF_MISSING)


def skill_link_trouble(
    project: Path,
) -> Optional[str]:
    """What is wrong with the skill link, or None when Claude Code can load the skill.

    What Claude Code needs is `.claude/skills/agent-brain/SKILL.md`,
    through the link or as a real copy, and that is asked first. Then:
    a dead link still counts as a symlink, a ZIP download or a checkout
    without symlinks leaves a plain file in the link's place, a real
    folder is fine only while it carries the skill, and a link can only
    be made when the skill itself is in the brain to point at.
    """
    link = project / SKILL_LINK

    if store.readable_file(link / "SKILL.md"):
        return None

    if not store.readable_file(project / SKILL_HOME / "SKILL.md"):
        return SKILL_ITSELF_MISSING

    if store.quietly(link.is_symlink):
        return "the skill link does not reach the skill" + CANNOT_SEE

    if store.quietly(link.is_dir):
        return REAL_FOLDER_WITHOUT_SKILL

    if store.quietly(link.exists):
        return "something that is not a link sits where the skill link belongs" + CANNOT_SEE

    return "the skill link is missing" + CANNOT_SEE


def check_style_copies(
    brain: store.Brain,
) -> list[Finding]:
    """Codex and Gemini CLI carry the chat style as copies of the Claude Code one.

    The source is read once, and each stale copy gets a repair that
    writes only itself.
    """
    try:
        wanted = style.source_body(brain)
    except style.StyleError as error:
        return [Finding(path=str(style.SOURCE), check="layout", message=str(error))]

    return [
        Finding(
            path=str(relative),
            check="layout",
            message="the chat style copy does not match the Claude Code one",
            repair=write_copy(style.project(brain) / relative, wanted),
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
) -> Callable[[], None]:
    """A repair that puts the symlink in place, clearing a dead link or a stray file first.

    A real folder is never removed here. It is somebody's, and the check
    leaves it for a person.
    """

    def repair() -> None:
        link = project / SKILL_LINK
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink() or (link.exists() and not link.is_dir()):
            link.unlink()
        os.symlink(skill_target(project=project, link=link), str(link))

    return repair


def skill_target(
    project: Path,
    link: Path,
) -> str:
    """The skill folder, relative to where the link really sits.

    On the shipped layout that is `../../.agents/skills/agent-brain`.
    When `.claude/skills` is itself a symlink the link lands elsewhere,
    and a target counted from there is the one that still resolves.
    """
    return os.path.relpath(str(project / SKILL_HOME), str(link.parent.resolve()))


CHECKS: tuple[Callable[[store.Brain], list[Finding]], ...] = (
    check_strays,
    check_frontmatter,
    check_names,
    check_kinds,
    check_fields,
    check_sections,
    check_filenames,
    check_links,
    check_indexes,
    check_style,
    check_hygiene,
    check_layout,
)
