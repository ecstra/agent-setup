"""Who made a brain file and who last changed it, by git name.

An entry carries `author`, the git name of whoever filed it, and
`editor`, the git name of whoever last changed it through the tool,
beside `by`, which says whether a person asked for it or the agent
raised it. Where git names nobody, the login name stands in. A name is
one line of plain text, whatever git or the machine hands over, its
letters as they came.
"""

import getpass
import os
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
UNREAD = "no author or editor, and git failed or took over a minute to read the brain's history, so brain doctor --fix fills it once git can"
# the line breaks and the control characters break a header line, while a joiner inside a word, as Persian and Hindi names carry, is the name's own
BREAKS = ("Cc", "Cs", "Zl", "Zp")


@dataclass
class History:
    """Who first added and who last changed each path git knows under the brain, from one walk of its history.

    `here` is the brain's path from the repository's top, and `old` the
    path of the folder it lived in before 1.0.0, or None where the brain
    is the top itself. `unread` says git could not finish the walk.
    """

    first: dict[str, tuple[str, str]] = field(default_factory=dict)
    last: dict[str, str] = field(default_factory=dict)
    shallow: set[str] = field(default_factory=set)
    top: Optional[Path] = None
    here: str = "."
    old: Optional[str] = None
    unread: bool = False


def clean(
    name: str,
) -> str:
    """A name on one line, its line breaks and control characters read as spaces and every run of space as one."""
    return " ".join("".join(" " if unicodedata.category(letter) in BREAKS else letter for letter in name).split())


def git_says(
    folder: Path,
    arguments: list[str],
) -> Optional[str]:
    """What git prints from the folder, empty where it prints nothing, or None where git is missing, slow or refuses."""
    try:
        done = subprocess.run(["git", "-C", str(folder), *arguments], capture_output=True, timeout=GIT_SECONDS, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None

    return done.stdout.decode("utf-8", errors="replace") if done.returncode == 0 else None


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


def missing(
    document: frontmatter.Document,
) -> bool:
    return not document.get(AUTHOR) or not document.get(EDITOR)


def parse_history(
    text: str,
) -> History:
    """The first adder and the last changer of each path, from `git log --reverse --name-status` with each commit opened by a NUL, its hash and its name.

    A rename hands the first adder on to the new path. A merge lists, one
    status letter per parent, only the paths it changed against all of
    them, the conflicts its author resolved. A line that is no status
    line, a signature check git printed among them, is passed by.
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
    if not (top or "").strip():
        # with a .git above the brain, git refused a repository it should have read, one another user owns for one
        return History(unread=any(os.path.lexists(folder / ".git") for folder in (brain.resolve(), *brain.resolve().parents)))

    root = Path(top.strip())
    try:
        here = brain.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return History()

    old = PurePosixPath(here).with_name(OLD_FOLDER).as_posix() if here != "." else None
    log = git_says(
        folder=root,
        arguments=["-c", "log.showSignature=false", "-c", "core.quotePath=false", "log", "--reverse", "-M", "-c", "--name-status", "--format=%x00%H %aN", "--", here, *([old] if old else [])],
    )
    # the flags that would ask git outright came in 2.15 and 2.31, and the shallow file has marked the clone's edge since git began
    common = git_says(folder=root, arguments=["rev-parse", "--git-common-dir"])
    if log is None and git_says(folder=root, arguments=["rev-parse", "--verify", "--quiet", "HEAD"]) is None:
        # git refuses to walk a branch with no commit yet, which is a history with nothing in it
        log = ""
    if log is None or common is None:
        return History(top=root, here=here, old=old, unread=True)

    known = parse_history(log)
    known.top, known.here, known.old = root, here, old
    try:
        known.shallow = set((root / common.strip() / "shallow").read_text(encoding="utf-8").split())
    except FileNotFoundError:
        known.shallow = set()
    except OSError:
        known.unread = True

    return known


def names_for(
    path: Path,
    known: History,
) -> tuple[Optional[str], str]:
    """The author and the editor git gives the file, the author None where a shallow clone hides the commit that added it.

    The current name stands in for a file git has not seen and for a
    commit whose name is blank.
    """
    keys: list[str] = []
    if known.top is not None:
        try:
            relative = PurePosixPath(path.resolve().relative_to(known.top.resolve()).as_posix())
            keys = [relative.as_posix()]
            if known.old is not None:
                keys.append(PurePosixPath(known.old, relative.relative_to(known.here)).as_posix())
        except ValueError:
            pass

    for key in keys:
        if key in known.last:
            name, commit = known.first.get(key, (known.last[key], ""))
            author = None if commit in known.shallow else name or current(path.parent)
            return author, known.last[key] or current(path.parent)

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
