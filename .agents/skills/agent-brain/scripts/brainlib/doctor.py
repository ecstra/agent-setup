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

from . import frontmatter, index, links, schema, sections, store, style, writes

SKIP_DIRS: frozenset[str] = frozenset({"skills", ".worktrees"})

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

SKILL_LINKS = Path(".claude") / "skills"
SKILL_HOMES = Path(".agents") / "skills"

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

        if parts[0] in SKIP_DIRS and not (with_skills and parts[0] == "skills"):
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
    to delete. The chat style copies are written the same way outside
    the brain, so their folders are looked at for a write in flight,
    the one shape the tool leaves there.
    """
    found: list[Finding] = []
    candidates = [path for path in brain.root.rglob(".*") if path.relative_to(brain.root).parts[0] not in SKIP_DIRS]
    for folder in style.folders(brain):
        if store.quietly(folder.is_dir):
            candidates += list(folder.glob(".*"))

    for path in sorted(candidates):
        if store.quietly(path.is_symlink):
            continue

        in_flight = store.quietly(path.is_file) and frontmatter.TEMP_SHAPE.match(path.name) is not None
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
                    repair=set_field(path=entry.path, key="name", value=expected),
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
            found.append(
                Finding(path=entry.relative, check="sections", message=f"no {title} heading")
            )

        for message in sections.lifecycle_gaps(kind=entry.kind, fields=entry.document.fields(), body=body):
            found.append(Finding(path=entry.relative, check="lifecycle", message=message))

    return found


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
    """One build of the brain serves the check and every repair it hands out."""
    wanted = index.build(brain)

    return [
        Finding(
            path=relative(brain=brain, path=path),
            check="index",
            message="differs from what the tool builds for its folder",
            repair=write_index(path=path, text=wanted[path]),
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

    for name in skills_wanted(brain):
        trouble = skill_link_trouble(project=project, name=name)
        if trouble is None:
            continue

        missing = trouble == skill_missing(name)
        for_a_person = missing or trouble in (REAL_FOLDER_WITHOUT_SKILL, ANOTHER_SKILL)
        found.append(
            Finding(
                path=str((SKILL_HOMES if missing else SKILL_LINKS) / name),
                check="layout",
                message=trouble,
                repair=None if for_a_person else make_skill_link(project=project, name=name),
            )
        )

    found.extend(check_style_copies(brain))

    return found


CANNOT_SEE = ", so Claude Code cannot see the skill"
REAL_FOLDER_WITHOUT_SKILL = "a folder with no SKILL.md sits where the skill link belongs" + CANNOT_SEE
ANOTHER_SKILL = "a skill of its own sits where the skill link belongs, so Claude Code loads that one instead"


def skill_missing(
    name: str,
) -> str:
    return f"the skill itself is missing from .agents/skills/{name}, reinstall the kit"


def skills_wanted(
    brain: store.Brain,
) -> list[str]:
    """The skills Claude Code should find: every one the kit shipped by the brain's stamp, then every other folder under skills/ that carries a SKILL.md."""
    stamped = stamp_of(brain)
    names = [skill.name for skill in schema.KIT_SKILLS if stamped is None or schema.as_tuple(skill.since) <= stamped]

    try:
        others = sorted(
            path.name
            for path in (brain.root / "skills").iterdir()
            if path.name not in names and not schema.is_hidden(path.name) and store.readable_file(path / "SKILL.md")
        )
    except OSError:
        others = []

    return names + others


def stamp_of(
    brain: store.Brain,
) -> Optional[tuple[int, ...]]:
    """The kit release the brain is stamped with, as numbers, or None when the stamp is missing or not a version."""
    stamp = brain.root / schema.VERSION_FILE
    if not store.readable_file(stamp):
        return None

    try:
        return schema.as_tuple(stamp.read_text(encoding="utf-8").strip())
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def skill_link_trouble(
    project: Path,
    name: str,
) -> Optional[str]:
    """What is wrong with the named skill's link, or None when Claude Code loads this skill through it.

    What Claude Code needs is `.claude/skills/<name>/SKILL.md`, and it
    must be this skill: a link that resolves to the skill's own folder,
    or a real copy of its SKILL.md, the way a ZIP download or a checkout
    without symlinks leaves one. A link that lands elsewhere is dead or
    points at another skill and is remade. A real folder carrying a
    different SKILL.md is a skill of its own and is left for a person,
    and so is a real folder with no SKILL.md at all. A link can only be
    made when the skill itself is in the brain to point at, and a copy
    with nothing left to point at is all there is, so it passes.
    """
    link = project / SKILL_LINKS / name
    home = project / SKILL_HOMES / name

    if not store.readable_file(home / "SKILL.md"):
        return None if store.readable_file(link / "SKILL.md") else skill_missing(name)

    if store.quietly(link.is_symlink):
        return None if reaches(link=link, home=home) else "the skill link does not reach the skill" + CANNOT_SEE

    if store.quietly(link.is_dir):
        if not store.readable_file(link / "SKILL.md"):
            return REAL_FOLDER_WITHOUT_SKILL

        return None if same_bytes(one=link / "SKILL.md", other=home / "SKILL.md") else ANOTHER_SKILL

    if store.quietly(link.exists):
        return "something that is not a link sits where the skill link belongs" + CANNOT_SEE

    return "the skill link is missing" + CANNOT_SEE


def reaches(
    link: Path,
    home: Path,
) -> bool:
    """Whether the link resolves to the skill's own folder."""
    try:
        return link.resolve() == home.resolve()
    except OSError:
        return False


def same_bytes(
    one: Path,
    other: Path,
) -> bool:
    try:
        return one.read_bytes() == other.read_bytes()
    except OSError:
        return False


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
        os.symlink(skill_target(project=project, link=link, name=name), str(link))

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
    check_filenames,
    check_links,
    check_indexes,
    check_style,
    check_hygiene,
    check_layout,
)
