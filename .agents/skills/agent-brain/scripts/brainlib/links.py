"""What a file points at, what points back, and whether any of it holds.

A frontmatter link is a path relative to `.agents/`. Older brains wrote
names instead, so resolving still accepts an id or a name, and the
upgrade turns them into paths.
"""

import os
import re
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from . import frontmatter, store

MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

# The scratch folder a symlink is put back through, the prefix and the
# random tail TemporaryDirectory adds. Doctor knows the exact shape, so
# one left by an interrupted run is found and nothing else is touched.
SCRATCH_PREFIX = ".putback."
SCRATCH_SHAPE = re.compile(r"^\.putback\.[A-Za-z0-9_]+$")


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
    A dotted path is nobody's entry, so a link to one reaches nothing.
    """
    if not reference:
        return None

    candidate = brain.root / reference
    relative = within(brain=brain, path=candidate)
    if relative is None or store.hidden(Path(relative)):
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


@dataclass
class Planned:
    """One file about to have its links moved, with what it was before.

    `links` is the header list with the move made, or None when the
    header does not point there. `body` is the prose with its markdown
    links moved, or None when none of them point there.
    """

    entry: store.Entry
    links: Optional[list[str]]
    body: Optional[str]
    text: str
    link: Optional[str]


def rewrite_references(
    brain: store.Brain,
    old: str,
    new: str,
    stamp: str = "",
) -> list[Path]:
    """Point every frontmatter link at `old` to `new`, and say which files changed."""
    return [item.entry.path for item in move_links(brain=brain, old=old, new=new, stamp=stamp)]


def move_links(
    brain: store.Brain,
    old: str,
    new: str,
    stamp: str = "",
) -> list[Planned]:
    """Point every link at `old` to `new`, in headers and in prose, stamping each file touched.

    Paths are root relative. A header link is rewritten in path form, a
    markdown link in the prose keeps its relative form from the file it
    sits in. A file whose links change has changed, so it gets the date
    like any other edit, per the upkeep rule. The writes go all together
    or not at all: every file is read before any is written, and a file
    that cannot be written puts the ones before it back as they were,
    symlink included, so no link points at a path the rename then never
    made. What comes back is each file written with what it held before,
    so a caller that fails later can put them back too.
    """
    stamp = stamp or date.today().isoformat()
    planned: list[Planned] = []
    for entry in brain.entries():
        moved = moved_links(brain=brain, entry=entry, old=old, new=new)
        body = moved_body(brain=brain, entry=entry, old=old, new=new)
        if moved is None and body is None:
            continue

        planned.append(Planned(entry=entry, links=moved, body=body, text=frontmatter.load(str(entry.path)), link=link_target(entry.path)))

    written: list[Planned] = []

    try:
        for item in planned:
            if item.links is not None:
                item.entry.document.set_list(key="links", values=item.links)
            if item.body is not None:
                item.entry.document.body = item.body
            item.entry.document.set(key="updated", value=stamp)
            frontmatter.write(path=str(item.entry.path), document=item.entry.document)
            written.append(item)
    except OSError as error:
        stuck = put_back_all(written)
        if stuck:
            raise OSError(f"{store.explain(error)}, and {names_of(stuck)} could not be put back") from error
        raise
    finally:
        brain.refresh()

    return written


def put_back_all(
    written: list[Planned],
) -> list[Path]:
    """Restore every file it can, and hand back the ones it could not."""
    stuck: list[Path] = []

    for item in written:
        try:
            put_back(item)
        except OSError:
            stuck.append(item.entry.path)

    return stuck


def names_of(
    paths: list[Path],
) -> str:
    return ", ".join(store.near(str(path)) for path in paths)


def link_target(
    path: Path,
) -> Optional[str]:
    if not store.quietly(path.is_symlink):
        return None

    return os.readlink(str(path))


def put_back(
    item: Planned,
) -> None:
    """Restore a file the way it was, a symlink as the symlink it was.

    The symlink is made in a scratch folder beside the file and moved
    into place in one step, so there is no moment with nothing at the
    path, and no fixed name for a leftover to collide with.
    """
    path = item.entry.path
    if item.link is None:
        frontmatter.write_text(path=str(path), text=item.text)
        return

    with tempfile.TemporaryDirectory(dir=str(path.parent), prefix=SCRATCH_PREFIX) as scratch:
        beside = os.path.join(scratch, path.name)
        os.symlink(item.link, beside)
        os.replace(beside, str(path))


def moved_body(
    brain: store.Brain,
    entry: store.Entry,
    old: str,
    new: str,
) -> Optional[str]:
    """The entry's prose with every markdown link at `old` pointed at `new`, or None when none is.

    A body link is relative to the file it sits in, so the new target is
    written relative to that file too, anchor kept. Everything else in
    the prose is left character for character.
    """
    old_target = os.path.normpath(str(brain.root / old))
    folder = entry.path.parent

    def moved(match: "re.Match[str]") -> str:
        target = match.group(1)
        if "://" in target or target.startswith("#") or Path(target).is_absolute():
            return match.group(0)

        file_part, hash_sign, anchor = target.partition("#")
        if os.path.normpath(str(folder / file_part)) != old_target:
            return match.group(0)

        replacement = os.path.relpath(str(brain.root / new), str(folder)) + hash_sign + anchor
        head = match.group(0)[: match.start(1) - match.start(0)]
        tail = match.group(0)[match.end(1) - match.start(0) :]

        return head + replacement + tail

    body = MARKDOWN_LINK.sub(moved, entry.document.body)

    return body if body != entry.document.body else None


def moved_links(
    brain: store.Brain,
    entry: store.Entry,
    old: str,
    new: str,
) -> Optional[list[str]]:
    """The entry's links with `old` pointed at `new`, or None when none point there."""
    current = outgoing(entry)
    moved = [new if link == old or canonical(brain, link) == old else link for link in current]
    if moved == current:
        return None

    return moved


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
