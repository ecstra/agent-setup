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
SKILL_TARGET = Path("..") / ".." / ".agents" / "skills" / "agent-brain"


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


def run(
    brain: store.Brain,
    fix: bool = False,
) -> list[Finding]:
    """Every finding in the brain, after repairs when `fix` is set."""
    found = check_all(brain)
    if not fix:
        return found

    for finding in found:
        if finding.repair is not None:
            finding.repair()

    brain.refresh()

    return check_all(brain)


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
    """Every markdown file the checks look at, the rulebook excepted."""
    found: list[Path] = []

    for path in sorted(brain.root.rglob("*.md")):
        relative = path.relative_to(brain.root)
        if relative.parts[0] in SKIP_DIRS:
            continue

        if path.name in schema.NO_FRONTMATTER and len(relative.parts) == 1:
            continue

        found.append(path)

    return found


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
            if document.get(item.name) is not None:
                continue

            if item.name == "updated":
                found.append(
                    Finding(
                        path=where,
                        check="frontmatter",
                        message="no updated date",
                        repair=stamp_today(path),
                    )
                )
                continue

            found.append(
                Finding(path=where, check="frontmatter", message=f"no {item.name} field")
            )

        updated = document.get("updated")
        if updated and not schema.is_date(updated):
            found.append(
                Finding(path=where, check="frontmatter", message=f"updated reads '{updated}', not YYYY-MM-DD")
            )

    return found


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
        if actual == entry.kind.kind_value:
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
            writes.check(kind=entry.kind, fields=entry.document.fields())
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
        if entry.kind.name == "review":
            continue

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

    for path in markdown_files(brain):
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

    for path in markdown_files(brain):
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

    if not (brain.root / "VERSION").is_file():
        found.append(Finding(path="VERSION", check="layout", message="no kit version stamp, run the upgrade"))

    trouble = skill_link_trouble(project)
    if trouble is not None:
        found.append(
            Finding(
                path=str(SKILL_LINK),
                check="layout",
                message=f"{trouble}, so Claude Code cannot see the skill",
                repair=None if trouble == REAL_FOLDER_WITHOUT_SKILL else make_skill_link(project),
            )
        )

    found.extend(check_style_copies(brain))

    return found


REAL_FOLDER_WITHOUT_SKILL = "a folder with no SKILL.md sits where the skill link belongs"


def skill_link_trouble(
    project: Path,
) -> Optional[str]:
    """What is wrong with the skill link, or None when Claude Code can load the skill.

    What Claude Code needs is `.claude/skills/agent-brain/SKILL.md`. A
    dead link still counts as a symlink, a ZIP download or a checkout
    without symlinks leaves a plain file in the link's place, and a real
    folder is fine only while it carries the skill, so the check asks
    what is actually there.
    """
    link = project / SKILL_LINK

    if (link / "SKILL.md").is_file():
        return None

    if link.is_symlink():
        return "the skill link does not reach the skill"

    if link.is_dir():
        return REAL_FOLDER_WITHOUT_SKILL

    if link.exists():
        return "something that is not a link sits where the skill link belongs"

    return "the skill link is missing"


def check_style_copies(
    brain: store.Brain,
) -> list[Finding]:
    """Codex and Gemini CLI carry the chat style as copies of the Claude Code one."""
    try:
        stale = style.stale(brain)
    except style.StyleError as error:
        return [Finding(path=str(style.SOURCE), check="layout", message=str(error))]

    def repair() -> None:
        style.write(brain)

    return [
        Finding(
            path=str(relative),
            check="layout",
            message="the chat style copy does not match the Claude Code one",
            repair=repair,
        )
        for relative in stale
    ]


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
        os.symlink(str(SKILL_TARGET), str(link))

    return repair


CHECKS: tuple[Callable[[store.Brain], list[Finding]], ...] = (
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
