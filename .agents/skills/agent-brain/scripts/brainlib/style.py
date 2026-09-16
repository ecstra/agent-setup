"""The chat style, written once for Claude Code and copied for the others.

`.claude/output-styles/plain-and-short.md` is the source, since Claude
Code reads it as an output style. Codex and Gemini CLI have no such
thing, so each gets the same text as a plain file inside its own config
folder, and doctor keeps the copies identical to the source.
"""

from pathlib import Path

from . import frontmatter, store

SOURCE = Path(".claude") / "output-styles" / "plain-and-short.md"

COPIES: tuple[Path, ...] = (
    Path(".codex") / "plain-and-short.md",
    Path(".gemini") / "plain-and-short.md",
)


class StyleError(Exception):
    """The source style file is missing or cannot be read."""


def project(
    brain: store.Brain,
) -> Path:
    return brain.root.parent


def source_body(
    brain: store.Brain,
) -> str:
    """The style text without the frontmatter only Claude Code reads."""
    source = project(brain) / SOURCE
    if not source.is_file():
        raise StyleError(f"{SOURCE} is missing, so there is no style to copy")

    try:
        document = frontmatter.read(str(source))
    except frontmatter.FrontmatterError as error:
        raise StyleError(f"{SOURCE}: {error}") from error

    return document.body.lstrip("\n")


def stale(
    brain: store.Brain,
) -> list[Path]:
    """The copies that are missing or differ from the source."""
    wanted = source_body(brain)
    found: list[Path] = []

    for relative in COPIES:
        target = project(brain) / relative
        if not target.is_file() or target.read_text(encoding="utf-8") != wanted:
            found.append(relative)

    return found


def write(
    brain: store.Brain,
) -> list[Path]:
    """Rewrite the stale copies from the source, and say which ones."""
    wanted = source_body(brain)
    changed: list[Path] = []

    for relative in stale(brain):
        target = project(brain) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(wanted, encoding="utf-8")
        changed.append(relative)

    return changed
