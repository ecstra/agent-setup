"""Who made a brain file and who last changed it, by git name.

An entry carries `author`, the git name of whoever filed it, and
`editor`, the git name of whoever last changed it through the tool,
beside `by`, which says whether a person asked for it or the agent
raised it. Where git names nobody, the login name stands in.
"""

import getpass
import subprocess
from pathlib import Path
from typing import Callable, Optional

from . import frontmatter

AUTHOR = "author"
EDITOR = "editor"
UNKNOWN = "unknown"
GIT_SECONDS = 10


def git_says(
    folder: Path,
    arguments: list[str],
) -> Optional[str]:
    """What git prints from the folder, or None where git is missing, slow, refuses or prints nothing."""
    try:
        done = subprocess.run(["git", "-C", str(folder), *arguments], capture_output=True, timeout=GIT_SECONDS, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None

    text = done.stdout.decode("utf-8", errors="replace").strip()

    return text if done.returncode == 0 and text else None


def current(
    project: Path,
) -> str:
    """The git user.name the project's git gives, else the login name, else unknown."""
    named = git_says(folder=project, arguments=["config", "user.name"])
    if named is not None:
        return named

    # the login name is a stand in, so a machine that cannot give one gets a plain word rather than a failed write
    try:
        return getpass.getuser() or UNKNOWN
    except (KeyError, OSError, ImportError):
        return UNKNOWN


def touch(
    document: frontmatter.Document,
    folder: Path,
) -> None:
    """Name whoever runs the tool as the editor of an entry the tool is changing, an index or a kit file, which carry no author, left alone."""
    if document.get(AUTHOR) is not None:
        document.set(key=EDITOR, value=current(folder))


def missing(
    document: frontmatter.Document,
) -> bool:
    return not document.get(AUTHOR) or not document.get(EDITOR)


def filler(
    path: Path,
) -> Callable[[], None]:
    """A repair that fills a missing author from the commit that added the file and a missing editor from the last commit that touched it, the current name for a file git has not seen."""

    def repair() -> None:
        document = frontmatter.read(str(path))
        if not document.get(AUTHOR):
            added = git_says(folder=path.parent, arguments=["log", "--follow", "--diff-filter=A", "--format=%an", "--", path.name])
            document.set(key=AUTHOR, value=added.splitlines()[-1] if added else current(path.parent))

        if not document.get(EDITOR):
            last = git_says(folder=path.parent, arguments=["log", "-1", "--format=%an", "--", path.name])
            document.set(key=EDITOR, value=last or current(path.parent))

        frontmatter.write(path=str(path), document=document)

    return repair
