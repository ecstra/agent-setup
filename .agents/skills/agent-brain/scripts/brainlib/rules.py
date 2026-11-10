"""The project's own rules, one markdown file each in .agents/rules/, every one a system instruction that AGENTS.md imports below its mark.

AGENTS.md is Agent Setup's, written whole by the port and the upgrade, and
everything after its mark is this module's to write, one import line
per rule, so each agent loads every rule at a session's start. A rule
added, renamed or deleted loads or stops loading once the session is
reloaded.
"""

from pathlib import Path
from typing import Optional

from . import frontmatter, schema, store

FOLDER = "rules"
PROJECT = "project.md"
PROJECT_NAME = "project"
AGENTS = "AGENTS.md"
# the line AGENTS.md carries above its imports of the rules, everything after it the tool's to write
MARK = "<!-- The project's rules, one import per line below, are the brain tool's to write. A new rule goes in through brain new rule. -->"
IMPORT = "@.agents/rules/{name}"
RELOAD = "a new rule loads only once the session is reloaded, so ask the owner to reload the session"
NOT_IMPORTED = "AGENTS.md does not import the rule, so it does not load, and brain doctor says why"
# the release the rules came in, from which AGENTS.md is Agent Setup's whole and holds no section 0
SINCE = "3.0.0"

PLACEHOLDER = """---
name: project
kind: rule
description: the project's own rules, which every agent loads as a system instruction
updated: {date}
links: []
---

# Project rules

<!-- This file is the project's own, and the upgrade never writes over it.
Every rule here loads as a system instruction in every session, so keep
it to durable instructions this project alone needs, written sparingly,
never a note, a todo or a doc. A Lint heading with fenced lines names
the linters the lint hook runs on each file written, and a Gates heading
with fenced blocks names the gates brain gates runs, as the brain tool's
commands.md says. A change here loads once the session is reloaded. -->
"""


class RuleUnreadable(Exception):
    """A rule file that cannot be read, with the reason in words."""


def names(
    brain_root: Path,
) -> list[str]:
    """The rule files in the rules folder, the project's own first and the others by name, the index, a dotted file and a name outside the slug left out, which doctor names."""
    try:
        found = [path.name for path in (brain_root / FOLDER).iterdir() if path.suffix == ".md" and path.name != schema.INDEX and schema.is_slug(path.stem) and path.is_file()]
    except OSError:
        return []

    return sorted(found, key=lambda name: (name != PROJECT, name))


def loaded(
    brain_root: Path,
) -> list[str]:
    """The rules AGENTS.md imports once the port or the upgrade has run, the project's own among them, since the run writes it where it is missing."""
    held = names(brain_root)

    return held if PROJECT in held else [PROJECT, *held]


def body_of(
    text: str,
) -> str:
    """A rule's text without its header block, or the whole text where it carries none."""
    try:
        return frontmatter.parse(text).body
    except frontmatter.FrontmatterError:
        return text


def texts(
    brain_root: Path,
) -> list[tuple[str, str]]:
    """Each rule's name and body, its header block left off, in the order the rules load, raising RuleUnreadable for one that cannot be read."""
    found: list[tuple[str, str]] = []
    for name in names(brain_root):
        try:
            text = (brain_root / FOLDER / name).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as error:
            raise RuleUnreadable(f"{FOLDER}/{name} cannot be read, {store.explain(error)}") from error
        found.append((name, body_of(text)))

    return found


def with_imports(
    text: str,
    names: list[str],
) -> str:
    """AGENTS.md's text with everything after its mark written again as one import line per rule, Agent Setup's words above it kept."""
    above = text.split(MARK, 1)[0].rstrip("\n")

    return f"{above}\n\n{MARK}\n" + "".join(IMPORT.format(name=name) + "\n" for name in names)


def imports_in(
    text: str,
) -> Optional[list[str]]:
    """The rule files AGENTS.md imports after its mark, or None where it carries no mark."""
    if MARK not in text:
        return None

    prefix = IMPORT.format(name="")

    return [line.strip()[len(prefix) :] for line in text.split(MARK, 1)[1].splitlines() if line.strip().startswith(prefix)]


def imports(
    brain_root: Path,
    name: str,
) -> bool:
    """Whether AGENTS.md imports the rule of that file name below its mark, false where it is missing, unreadable or carries no mark."""
    try:
        text = (brain_root.parent / AGENTS).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return False

    return name in (imports_in(text) or [])


def write_imports(
    brain_root: Path,
) -> bool:
    """Writes AGENTS.md's imports to match the rules on disk, and whether it changed it, nothing where AGENTS.md is missing or carries no mark."""
    agents = brain_root.parent / AGENTS
    try:
        text = agents.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return False

    if MARK not in text:
        return False

    written = with_imports(text=text, names=names(brain_root))
    if written == text:
        return False

    frontmatter.write_text(path=str(agents), text=written)
    return True
