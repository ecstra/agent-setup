"""What a file points at, what points back, and whether any of it holds.

A frontmatter link is a path relative to `.agents/`. Older brains wrote
names instead, so resolving still accepts an id or a name, and the
upgrade turns them into paths.
"""

import os
import re
from datetime import date
from pathlib import Path
from typing import Optional

from . import frontmatter, store

MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def resolve(
    brain: store.Brain,
    reference: str,
) -> Optional[Path]:
    """The file a link means, whether it was written as a path or a name."""
    direct = inside(brain=brain, reference=reference)
    if direct is not None and store.readable_file(direct):
        return direct

    entry = brain.find(reference)
    if entry is not None:
        return entry.path

    for path, document in kit_documents(brain):
        if document.get("name") == reference:
            return path

    return None


def inside(
    brain: store.Brain,
    reference: str,
) -> Optional[Path]:
    """The file a path reference names, or None when it lies outside the brain.

    An absolute path replaces the root when joined, and `..` climbs out
    of it, so both are checked against the root before anything is read.
    """
    if not reference:
        return None

    candidate = brain.root / reference
    if within(brain=brain, path=candidate) is None:
        return None

    return candidate


def within(
    brain: store.Brain,
    path: Path,
) -> Optional[str]:
    """The path relative to the brain, or None when it lies outside.

    Nothing is resolved. A symlink filed inside the brain is inside it,
    and `..` is folded lexically, so a path cannot climb out unseen and
    a symlink loop on disk cannot raise here.
    """
    root = Path(os.path.normpath(str(brain.root)))
    folded = Path(os.path.normpath(str(path)))

    try:
        return str(folded.relative_to(root))
    except ValueError:
        return None


def canonical(
    brain: store.Brain,
    reference: str,
) -> Optional[str]:
    """The path form of a link, or None when it points at nothing."""
    path = resolve(brain=brain, reference=reference)
    if path is None:
        return None

    return within(brain=brain, path=path)


def outgoing(
    entry: store.Entry,
) -> list[str]:
    return entry.document.get_list("links")


def backlinks(
    brain: store.Brain,
    target: store.Entry,
) -> list[store.Entry]:
    """Every entry whose frontmatter links reach `target`."""
    found: list[store.Entry] = []

    for entry in brain.entries():
        if entry.path == target.path:
            continue

        resolved = [resolve(brain=brain, reference=link) for link in outgoing(entry)]
        if target.path in resolved:
            found.append(entry)

    return found


def broken(
    brain: store.Brain,
) -> list[tuple[store.Entry, str]]:
    """Every frontmatter link in the brain that reaches nothing."""
    found: list[tuple[store.Entry, str]] = []

    for entry in brain.entries():
        for link in outgoing(entry):
            if resolve(brain=brain, reference=link) is None:
                found.append((entry, link))

    return found


def broken_in_body(
    entry: store.Entry,
) -> list[str]:
    """Markdown links in the body that do not reach a file from where they stand.

    A body link is relative to its file, so an absolute one is broken
    however the machine it was written on is laid out.
    """
    found: list[str] = []

    for match in MARKDOWN_LINK.finditer(entry.document.body):
        target = match.group(1)
        if "://" in target or target.startswith("#"):
            continue

        file_part = target.split("#")[0]
        if Path(file_part).is_absolute() or not store.quietly((entry.path.parent / file_part).exists):
            found.append(target)

    return found


def rewrite_references(
    brain: store.Brain,
    old: str,
    new: str,
    stamp: str = "",
) -> list[Path]:
    """Point every frontmatter link at `old` to `new`, stamping each file touched.

    Paths are root relative. A file whose links change has changed, so
    it gets the date like any other edit, per the upkeep rule.
    """
    stamp = stamp or date.today().isoformat()
    changed: list[Path] = []

    for entry in brain.entries():
        current = outgoing(entry)
        updated = [
            new if link == old or canonical(brain, link) == old else link
            for link in current
        ]
        if updated == current:
            continue

        entry.document.set_list(key="links", values=updated)
        entry.document.set(key="updated", value=stamp)
        frontmatter.write(path=str(entry.path), document=entry.document)
        changed.append(entry.path)

    brain.refresh()

    return changed


def kit_documents(
    brain: store.Brain,
) -> list[tuple[Path, frontmatter.Document]]:
    """The kit's own files that carry frontmatter, so names still resolve."""
    found: list[tuple[Path, frontmatter.Document]] = []

    for path in brain.kit_files():
        try:
            found.append((path, frontmatter.read(str(path))))
        except frontmatter.FrontmatterError:
            continue

    return found
