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
from urllib.parse import unquote

from . import frontmatter, handover, people, schema, sections, store

# The two ways markdown writes a link: inline, `[text](target)`, and by
# reference, `[label]: target` on a line of its own. Group 1 is the
# target in both, so one rewrite serves both.
# the target, then the title markdown lets a link carry in double quotes, single quotes or brackets
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\((<[^>\n]*>|[^)\s]+)(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'|\([^)\n]*\)))?\s*\)")
REFERENCE_LINK = re.compile(r"^\[[^\]]+\]:[ \t]+(<[^>\n]*>|\S+)", re.MULTILINE)

# The scratch folder a symlink is put back through, the prefix and the
# random tail TemporaryDirectory adds. Doctor knows the exact shape, so
# one left by an interrupted run is found and nothing else is touched.
SCRATCH_PREFIX = ".putback."
SCRATCH_SHAPE = re.compile(r"^\.putback\.[A-Za-z0-9_]+$")

# What doctor says of a link that reaches nothing, and the reason doctor
# and a write give where the link goes into the handover folder, since a
# file may stand at that path and the folder's one note still never
# enters git.
REACHES_NOTHING: str = "reaches nothing"
HANDOVER_REASON: str = f"{REACHES_NOTHING}, since {schema.HANDOVER_FOLDER}/ holds the one note brain handover writes and no link goes into it"

# What git said of its case flag for each project this run asked about,
# kept for the run the way handover model R6 parses the flag once, so a
# doctor run over many links starts two git processes at most.
CASE_FLAGS: dict[Path, Optional[bool]] = {}


def resolve(
    brain: store.Brain,
    reference: str,
) -> Optional[Path]:
    """The file a link means, whether it was written as a path or a name.

    A path is read as a key is, so one written from the project's root,
    the repository's top or the disk's root reaches a file of Agent Setup's as it
    reaches an entry, and one into another project's brain reaches
    nothing.
    """
    keyed = brain.key_path(reference)
    if keyed is None:
        return None

    direct = inside(brain=brain, reference=keyed)
    if direct is not None and store.readable_file(direct):
        return direct

    try:
        entry = brain.find(reference)
    except store.Ambiguous:
        entry = None

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
    A dotted path is nobody's entry, so a link to one reaches nothing,
    and so is a path into the handover folder, whose one note never
    enters git.
    """
    if not reference:
        return None

    candidate = brain.root / reference
    relative = within(brain=brain, path=candidate)
    if relative is None or store.hidden(relative=Path(relative)):
        return None

    if in_handover(
        brain=brain,
        path=candidate,
    ):
        return None

    return candidate


def in_handover(
    brain: store.Brain,
    path: Path,
) -> bool:
    """Whether a path a link names lies in the brain's handover folder, the folder's name in any spelling `names_folder` takes for it."""
    relative: Optional[str] = within(
        brain=brain,
        path=path,
    )
    if relative is None:
        return False

    # the brain's own folder, which `within` names ".", has no first part
    parts: tuple[str, ...] = Path(relative).parts
    if not parts:
        return False

    return names_folder(
        brain=brain,
        top=parts[0],
        folder=schema.HANDOVER_FOLDER,
    )


def handover_reason(
    brain: store.Brain,
    reference: str,
) -> Optional[str]:
    """What a header link that reaches nothing says where it names something below the handover folder, or None where the folder is not why.

    The link is read the two ways `resolve` reads a path, from the
    brain's root and as `find` reads a key through `key_path`, from the
    project's folder, the repository's top, the disk's root or ~, with
    slashes or backslashes. A header link reaches a file alone, so one
    that names the folder itself reaches nothing as any folder does,
    and the folder's bare name is a key too, a name or a stem two files
    share or one a removed file carried, which the folder does not
    explain.
    """
    for spelled in (reference, brain.key_path(key=reference)):
        if spelled is None:
            continue

        named_path: Path = brain.root / spelled
        relative: Optional[str] = within(
            brain=brain,
            path=named_path,
        )
        if relative is None or len(Path(relative).parts) <= 1:
            continue

        if in_handover(
            brain=brain,
            path=named_path,
        ):
            return HANDOVER_REASON

    return None


def names_folder(
    brain: store.Brain,
    top: str,
    folder: str,
) -> bool:
    """Whether `top`, the first part of a path in the brain as it is spelled, names the brain's `folder`.

    Another casing of the folder's name names it where git takes two
    spellings that differ by case alone for one file here, and a second
    folder where git tells them apart, so the disk is never asked. Where
    git gives no answer for its flag, outside git, past its limit or in a
    repository it refuses, another casing names the handover folder and
    no other, the way the pre write hook folds that name, since a link
    refused there under another casing loses nothing and one let in
    would reach the note.
    """
    if top == folder:
        return True

    if top.casefold() != folder.casefold():
        return False

    git_folds_case: Optional[bool] = case_flag(brain=brain)
    if git_folds_case is None:
        return folder == schema.HANDOVER_FOLDER

    return git_folds_case


def case_flag(
    brain: store.Brain,
) -> Optional[bool]:
    """Whether git takes two spellings that differ by case alone for one file here, or None where git gives no answer, outside git, with no git installed, past its limit or in a repository it refuses, asked once per run for the project and the answer kept in CASE_FLAGS."""
    project: Path = handover.project_of(brain=brain)
    if project not in CASE_FLAGS:
        CASE_FLAGS[project] = asked_case_flag(project=project)

    return CASE_FLAGS[project]


def asked_case_flag(
    project: Path,
) -> Optional[bool]:
    """What git says of its case flag for the project, its reply read by `handover.case_flag_of`, or None where it gives no answer.

    Git is asked first whether it opens a repository here, since one it
    refuses, for its ownership among other reasons, or a `.git` it takes
    for none, still answers the flag's read from the global and system
    config, with an exit 0 where `~/.gitconfig` sets the flag. In a
    repository git opens, the read answers with an exit 0 and its word,
    or with an exit 1, which is its no. Every other exit is no answer,
    the fatal line of a config git cannot parse among them.
    """
    try:
        opened: handover.Reply = handover.readable_reply(
            project=project,
            arguments=["rev-parse", "--git-dir"],
        )
    except handover.Unanswered:
        return None

    if opened.code != 0:
        return None

    try:
        flag_reply: handover.Reply = handover.readable_reply(
            project=project,
            arguments=list(handover.CASE_FLAG_QUESTION),
        )
    except handover.Unanswered:
        return None

    if flag_reply.code not in (0, 1):
        return None

    return handover.case_flag_of(reply=flag_reply)


def within(
    brain: store.Brain,
    path: Path,
) -> Optional[str]:
    """The path relative to the brain, or None when it lies outside.

    Nothing is resolved and the disk is never asked, so a path read from
    a brain file's text is never looked up. A symlink filed inside the
    brain is inside it, and `..` is folded lexically, so a path cannot
    climb out unseen and a symlink loop on disk cannot raise here. The
    hooks spell a path they are handed as the brain spells it first.
    """
    root = Path(os.path.normpath(str(brain.root)))
    folded = Path(os.path.normpath(str(path)))

    try:
        return folded.relative_to(root).as_posix()
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


def broken_in_body(
    brain: store.Brain,
    path: Path,
    document: frontmatter.Document,
) -> list[tuple[str, str]]:
    """Markdown links in the prose that do not reach a file or a folder from where they stand, each with what doctor says of it.

    A body link is relative to its file, so an absolute one is broken
    however the machine it was written on is laid out, and one into the
    handover folder is broken however long the note waits, since it is
    read once and never enters git. A body link may name a folder, so
    one to the handover folder itself gives the folder as its reason,
    and `handover_reason` says why a header link to it reaches nothing
    as one to any folder does. A target is a URL, so it names the bytes
    its characters are in UTF-8 with each percent escape read as the
    byte it stands for, and the file it reaches is the one named with
    those bytes, spelled for the disk as `handover.on_disk` spells a name
    whatever codec this machine names files in, so a link reaches
    nothing where this machine has no name for its bytes, as Windows has
    none for a byte that is not UTF-8. A link that starts inside code is
    not a link, while one whose text holds a code span is.
    """
    found: list[tuple[str, str]] = []

    for target in body_targets(document.body):
        if "://" in target or target.startswith("#"):
            continue

        file_part: str = unquote(
            string=target.split("#")[0],
            errors="surrogateescape",
        )
        named_path: Path = path.parent / file_part
        into_the_folder: bool = in_handover(
            brain=brain,
            path=named_path,
        )
        spelled: Optional[str] = handover.on_disk(name=file_part)
        missing: bool = not file_part or Path(file_part).is_absolute() or spelled is None or not store.quietly(question=(path.parent / spelled).exists)
        if not missing and not into_the_folder:
            continue

        said: str = HANDOVER_REASON if into_the_folder else REACHES_NOTHING
        found.append((target, said))

    return found


def body_targets(
    body: str,
) -> list[str]:
    """Every link target in the prose, inline and reference style, code stepped over."""
    spans = sections.code_spans(body)

    return [bare(match.group(1)) for pattern in (MARKDOWN_LINK, REFERENCE_LINK) for match in pattern.finditer(body) if not sections.in_code(spans=spans, position=match.start())]


def bare(
    target: str,
) -> str:
    """The target without the angle brackets markdown allows around one."""
    if target.startswith("<") and target.endswith(">"):
        return target[1:-1]

    return target


def documents(
    brain: store.Brain,
) -> list[tuple[Path, frontmatter.Document]]:
    """Every file that carries links: the entries and Agent Setup's own files."""
    found = [(entry.path, entry.document) for entry in brain.entries()]

    return found + kit_documents(brain)


@dataclass
class Planned:
    """One file about to have its links moved, with what it was before.

    `links` is the header list with the move made, or None when the
    header does not point there. `body` is the prose with its markdown
    links moved, or None when none of them point there.
    """

    path: Path
    document: frontmatter.Document
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
    return [item.path for item in move_links(brain=brain, old=old, new=new, stamp=stamp)]


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
    for path, document in documents(brain):
        moved = moved_links(brain=brain, document=document, old=old, new=new)
        body = moved_body(brain=brain, path=path, document=document, old=old, new=new)
        if moved is None and body is None:
            continue

        planned.append(Planned(path=path, document=document, links=moved, body=body, text=frontmatter.load(str(path)), link=link_target(path)))

    written: list[Planned] = []

    try:
        for item in planned:
            if item.links is not None:
                item.document.set_list(key="links", values=item.links)
            if item.body is not None:
                item.document.body = item.body
            item.document.set(key="updated", value=stamp)
            if not schema.is_kit_path(item.path.relative_to(brain.root).as_posix()):
                people.stamp(document=item.document, folder=brain.root.parent)
            frontmatter.write(path=str(item.path), document=item.document)
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
            stuck.append(item.path)

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

    target: str = os.readlink(str(path))
    # Windows reads an absolute target back in its long spelling, \\?\C:\... or \\?\UNC\host\..., which a link put back would carry
    if os.name == "nt" and target.startswith("\\\\?\\"):
        return "\\\\" + target[8:] if target[4:8].upper() == "UNC\\" else target[4:]

    return target


def put_back(
    item: Planned,
) -> None:
    """Restore a file the way it was, a symlink as the symlink it was.

    The symlink is made in a scratch folder beside the file and moved
    into place in one step, so there is no moment with nothing at the
    path, and no fixed name for a leftover to collide with.
    """
    path = item.path
    if item.link is None:
        frontmatter.write_text(path=str(path), text=item.text)
        return

    with tempfile.TemporaryDirectory(dir=str(path.parent), prefix=SCRATCH_PREFIX) as scratch:
        beside = os.path.join(scratch, path.name)
        os.symlink(item.link, beside)
        os.replace(beside, str(path))


def moved_body(
    brain: store.Brain,
    path: Path,
    document: frontmatter.Document,
    old: str,
    new: str,
) -> Optional[str]:
    """The file's prose with every markdown link at `old` pointed at `new`, or None when none is.

    A body link is relative to the file it sits in, so the new target is
    written relative to that file too, anchor kept. Everything else in
    the prose is left character for character.
    """
    old_target = os.path.normpath(str(brain.root / old))
    folder = path.parent
    spans: list[tuple[int, int]] = []

    def moved(
        match: re.Match,
    ) -> str:
        target = bare(match.group(1))
        if sections.in_code(spans=spans, position=match.start()):
            return match.group(0)

        if not target or "://" in target or target.startswith("#") or Path(target).is_absolute():
            return match.group(0)

        file_part, hash_sign, anchor = target.partition("#")
        # read with its percent escapes decoded, as the check of a body link reads it, so my%20notes.md is my notes.md
        file_part = unquote(file_part, errors="surrogateescape")
        if os.path.normpath(str(folder / file_part)) != old_target:
            return match.group(0)

        # a markdown link takes forward slashes on every system
        replacement = Path(os.path.relpath(str(brain.root / new), str(folder))).as_posix() + hash_sign + anchor
        if target != match.group(1):
            replacement = f"<{replacement}>"
        head = match.group(0)[: match.start(1) - match.start(0)]
        tail = match.group(0)[match.end(1) - match.start(0) :]

        return head + replacement + tail

    body = document.body
    for pattern in (MARKDOWN_LINK, REFERENCE_LINK):
        spans = sections.code_spans(body)
        body = pattern.sub(moved, body)

    return body if body != document.body else None


def rebased(
    text: str,
    old_folder: Path,
    new_folder: Path,
) -> str:
    """The prose with every relative markdown link, written from `old_folder`, written again from `new_folder`, so words moved between files still reach what they named, anchors kept and code left alone."""
    spans: list[tuple[int, int]] = []

    def move(
        match: re.Match,
    ) -> str:
        target = bare(match.group(1))
        if sections.in_code(spans=spans, position=match.start()):
            return match.group(0)

        if not target or "://" in target or target.startswith(("#", "mailto:")) or Path(target).is_absolute():
            return match.group(0)

        file_part, hash_sign, anchor = target.partition("#")
        # a markdown link takes forward slashes on every system
        replacement = Path(os.path.relpath(os.path.normpath(old_folder / file_part), new_folder)).as_posix() + hash_sign + anchor
        if target != match.group(1):
            replacement = f"<{replacement}>"
        head = match.group(0)[: match.start(1) - match.start(0)]
        tail = match.group(0)[match.end(1) - match.start(0) :]

        return head + replacement + tail

    for pattern in (MARKDOWN_LINK, REFERENCE_LINK):
        spans = sections.code_spans(text)
        text = pattern.sub(move, text)

    return text


def moved_links(
    brain: store.Brain,
    document: frontmatter.Document,
    old: str,
    new: str,
) -> Optional[list[str]]:
    """The header's links with `old` pointed at `new`, or None when none point there."""
    current = document.get_list("links")
    moved = [new if link == old or canonical(brain=brain, reference=link) == old else link for link in current]
    if moved == current:
        return None

    return list(dict.fromkeys(moved))


def kit_documents(
    brain: store.Brain,
) -> list[tuple[Path, frontmatter.Document]]:
    """Agent Setup's own files that carry frontmatter, so names still resolve."""
    return brain.kit_documents()
