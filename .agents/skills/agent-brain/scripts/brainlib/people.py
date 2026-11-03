"""Who made a brain file and who last changed it, by git name.

An entry carries `author`, the git name of whoever filed it, and
`editor`, the git name of whoever last changed it through the tool,
beside `by`, which says whether a person asked for it or the agent
raised it. Where git names nobody, the login name stands in. A name is
one line of plain text, whatever git or the machine hands over.
"""

import getpass
import subprocess
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Callable, Optional

from . import frontmatter

AUTHOR = "author"
EDITOR = "editor"
UNKNOWN = "unknown"
GIT_SECONDS = 60
# the folder the brain lived in before 1.0.0, whose history the upgrade's move leaves uncommitted
OLD_FOLDER = ".agent"
SHALLOW = "no author, since this shallow clone hides the commit that added the file, so git fetch --unshallow then brain doctor --fix fills it"


@dataclass
class History:
    """Who first added and who last changed each path git knows under the brain, from one walk of its history."""

    first: dict[str, tuple[str, str]] = field(default_factory=dict)
    last: dict[str, str] = field(default_factory=dict)
    shallow: set[str] = field(default_factory=set)
    top: Optional[Path] = None


def clean(
    name: str,
) -> str:
    """A name on one line, its control characters read as spaces and every run of space as one."""
    return " ".join("".join(" " if unicodedata.category(letter).startswith("C") else letter for letter in name).split())


def git_says(
    folder: Path,
    arguments: list[str],
) -> Optional[str]:
    """What git prints from the folder, or None where git is missing, slow, refuses or prints nothing."""
    try:
        done = subprocess.run(["git", "-C", str(folder), *arguments], capture_output=True, timeout=GIT_SECONDS, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None

    text = done.stdout.decode("utf-8", errors="replace")

    return text if done.returncode == 0 and text.strip() else None


def current(
    project: Path,
) -> str:
    """The git user.name the project's git gives, else the login name, else unknown."""
    named = clean(git_says(folder=project, arguments=["config", "user.name"]) or "")
    if named:
        return named

    # the login name is a stand in, so a machine that cannot give one gets a plain word rather than a failed write
    try:
        return clean(getpass.getuser()) or UNKNOWN
    except (KeyError, OSError, ImportError):
        return UNKNOWN


def stamp(
    document: frontmatter.Document,
    folder: Path,
) -> None:
    """Name whoever runs the tool as the editor of an entry the tool is changing."""
    document.set(key=EDITOR, value=current(folder))


def touch(
    document: frontmatter.Document,
    folder: Path,
) -> None:
    """Stamp the editor of a file a broad write passes through, where the file is an entry, an index or a kit file, which carry no author, left alone."""
    if document.get(AUTHOR) is not None:
        stamp(document=document, folder=folder)


def missing(
    document: frontmatter.Document,
) -> bool:
    return not document.get(AUTHOR) or not document.get(EDITOR)


def parse_history(
    text: str,
) -> History:
    """The first adder and the last changer of each path, from `git log --reverse --name-status` with each commit opened by a NUL, its hash and its name.

    A rename hands the first adder on to the new path. A line that is no
    status line, a signature check git printed among them, is passed by.
    """
    known = History()
    for block in text.split("\0")[1:]:
        head, _, rest = block.partition("\n")
        commit, _, raw = head.partition(" ")
        name = clean(raw)
        for line in rest.splitlines():
            parts = line.split("\t")
            if len(parts) < 2 or not parts[0] or parts[0][0] not in "ACMRT":
                continue

            if parts[0][0] == "R" and len(parts) == 3:
                known.first[parts[2]] = known.first.get(parts[1], (name, commit))
                known.last[parts[2]] = name
                continue

            known.first.setdefault(parts[1], (name, commit))
            known.last[parts[1]] = name

    return known


def history(
    brain: Path,
) -> History:
    """One walk of the history of the brain and of the folder it lived in before 1.0.0, names read through the project's mailmap."""
    top = git_says(folder=brain, arguments=["rev-parse", "--show-toplevel"])
    if top is None:
        return History()

    root = Path(top.strip())
    try:
        here = brain.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return History()

    old = PurePosixPath(here).with_name(OLD_FOLDER).as_posix()
    log = git_says(
        folder=root,
        arguments=["-c", "log.showSignature=false", "-c", "core.quotePath=false", "log", "--reverse", "-M", "--name-status", "--format=%x00%H %aN", "--", here, old],
    )
    known = parse_history(log or "")
    known.top = root

    if (git_says(folder=root, arguments=["rev-parse", "--is-shallow-repository"]) or "").strip() == "true":
        marks = git_says(folder=root, arguments=["rev-parse", "--path-format=absolute", "--git-path", "shallow"])
        try:
            known.shallow = set(Path(marks.strip()).read_text(encoding="utf-8").split()) if marks else set()
        except OSError:
            known.shallow = set()

    return known


def names_for(
    path: Path,
    known: History,
) -> tuple[Optional[str], str]:
    """The author and the editor git gives the file, the author None where a shallow clone hides the commit that added it, and the current name for a file git has not seen."""
    keys: list[str] = []
    if known.top is not None:
        try:
            relative = PurePosixPath(path.resolve().relative_to(known.top.resolve()).as_posix())
            keys = [relative.as_posix()]
            if relative.parts and relative.parts[0] == ".agents":
                keys.append(PurePosixPath(OLD_FOLDER, *relative.parts[1:]).as_posix())
        except ValueError:
            keys = []

    for key in keys:
        if key in known.last:
            name, commit = known.first.get(key, (known.last[key], ""))
            return (None if commit in known.shallow else name), known.last[key]

    who = current(path.parent)

    return who, who


def filler(
    path: Path,
    known: History,
) -> Callable[[], None]:
    """A repair that fills a missing author and editor from what git gives the file."""

    def repair() -> None:
        document = frontmatter.read(str(path))
        author, editor = names_for(path=path, known=known)
        if not document.get(AUTHOR) and author is not None:
            document.set(key=AUTHOR, value=author)

        if not document.get(EDITOR):
            document.set(key=EDITOR, value=editor)

        frontmatter.write(path=str(path), document=document)

    return repair
