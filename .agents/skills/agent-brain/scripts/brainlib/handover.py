"""The handover, the one note a session leaves for the next.

A session that stops mid task, before a compaction or at its end,
writes the note through `brain handover`, and the session start hook
puts it whole in front of the next session and removes it, so a note is
read once. The tool records what it can read off the machine, the
branch and its head, the uncommitted files, the standing word and the
current work, and the prose on standard input says the rest. The folder
holds one file and git ignores it, since the note belongs to one
machine and one stretch of work, like the standing word and the current
work beside it.
"""

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import autoack, clock, frontmatter, store, task

FOLDER = "handover"
FILE = "handover.md"
RELATIVE = f"{FOLDER}/{FILE}"
NO_GIT = "no git"
FOLDER_IN_THE_WAY = f"{RELATIVE} is a folder the tool never made, move it away by hand"
BY_HAND = f"{FOLDER}/ holds the one note brain handover writes for the next session, read and removed by the session start hook, and nothing there is written by hand"

# what git's two letter status says about a file, in a word
STATES: dict[str, str] = {
    "?": "untracked",
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
    "U": "unmerged",
    "T": "type changed",
}


class HandoverError(Exception):
    """The note could not be written as asked, with the reason in the message."""


@dataclass(frozen=True)
class Note:
    """The note as it stands on disk: its whole text, and the branch and the moment its header names, None for each the header does not give."""

    text: str
    branch: Optional[str]
    written: Optional[datetime]


def path_of(
    brain: store.Brain,
) -> Path:
    return brain.root / FOLDER / FILE


def project_of(
    brain: store.Brain,
) -> Path:
    return brain.root.parent


def write(
    brain: store.Brain,
    prose: str,
    replace: bool = False,
    at: Optional[datetime] = None,
) -> Note:
    """Write the note, the tool's record first and the prose under it, in place of the one there.

    Refused with no prose, since a note with no words is nothing to
    resume from, with a folder standing in the file's place, and while a
    note written on another branch waits there, which `replace` writes
    over on the owner's word.
    """
    words = prose.strip()
    if not words:
        raise HandoverError("a handover carries words, give them on standard input")

    path = path_of(brain)
    if store.quietly(path.is_dir):
        raise HandoverError(FOLDER_IN_THE_WAY)

    project = project_of(brain)
    branch = current_branch(project)
    standing = read(brain)
    if standing is not None and not replace and not is_for(note=standing, branch=branch):
        raise HandoverError(
            f"a handover written on {standing.branch} at {when(standing.written)} is waiting there "
            "for a session on that branch, and --replace writes over it"
        )

    # the moment in this machine's zone, so the note's lines name the zone the clock line names
    at = (at or clock.now()).astimezone()
    head = current_head(project)
    document = frontmatter.Document(
        lines=[
            f"branch: {branch}",
            f"head: {head}",
            f"written: {at.isoformat()}",
        ],
        body=body(
            brain=brain,
            branch=branch,
            head=head,
            at=at,
            words=words,
        ),
    )
    text = frontmatter.render(document)

    path.parent.mkdir(exist_ok=True)
    frontmatter.write_text(path=str(path), text=text)

    return Note(text=text, branch=branch, written=at)


def body(
    brain: store.Brain,
    branch: str,
    head: str,
    at: datetime,
    words: str,
) -> str:
    """The note's body: the record the tool reads off the machine, then the session's own words."""
    record = [f"- branch {branch} at {head}"]
    record += uncommitted_lines(project_of(brain))
    record.append(f"- {autoack.describe(brain=brain)}")
    record += [f"- {line}" for line in task.describe(brain=brain).split("\n")]

    return (
        "\n# Handover\n\n"
        f"Written {clock.words(at)} on {branch}.\n\n"
        "## As the tool found it\n\n" + "\n".join(record) + "\n\n"
        "## As the session left it\n\n" + words + "\n"
    )


def uncommitted_lines(
    project: Path,
) -> list[str]:
    """The uncommitted files as list lines, one per file with its state, or the one line that says the tree is clean or git is not there."""
    listing = git(project=project, arguments=["status", "--porcelain", "--untracked-files=all", "-z"])
    if listing is None:
        return [f"- uncommitted files, {NO_GIT}"]

    files = changed_files(listing)
    if not files:
        return ["- uncommitted files, none, the working tree is clean"]

    noun = "file" if len(files) == 1 else "files"
    lines = [f"- uncommitted, {len(files)} {noun}"]
    lines += [f"  - {path}, {state}" for state, path in files]

    return lines


def changed_files(
    porcelain: str,
) -> list[tuple[str, str]]:
    """The state and the path of each entry in a NUL separated porcelain listing, a rename's old name left out."""
    found: list[tuple[str, str]] = []
    tokens = porcelain.split("\0")
    index = 0

    while index < len(tokens):
        entry = tokens[index]
        index += 1
        if len(entry) < 4:
            continue

        code = entry[0] if entry[0] not in " ?" else entry[1]
        found.append((STATES.get(code, code), entry[3:]))
        if entry[0] in "RC":
            index += 1

    return found


def current_branch(
    project: Path,
) -> str:
    """The branch the project is on, before its first commit too, HEAD when detached, or the word for a folder git does not answer for."""
    name = git(project=project, arguments=["symbolic-ref", "--short", "-q", "HEAD"])
    if name is None:
        name = git(project=project, arguments=["rev-parse", "--abbrev-ref", "HEAD"])

    return name.strip() if name and name.strip() else NO_GIT


def current_head(
    project: Path,
) -> str:
    """The head's short hash and subject, or what stands in for them where git has none."""
    head = git(project=project, arguments=["log", "-1", "--format=%h %s"])
    if head is None:
        return NO_GIT if git(project=project, arguments=["rev-parse", "--is-inside-work-tree"]) is None else "no commits yet"

    return head.strip().split("\n")[0]


def git(
    project: Path,
    arguments: list[str],
) -> Optional[str]:
    """What git prints for the project, or None when git is not there, fails, or the folder is not a repository."""
    try:
        result = subprocess.run(
            ["git", "-C", str(project), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None

    return result.stdout if result.returncode == 0 else None


def read(
    brain: store.Brain,
) -> Optional[Note]:
    """The note on disk, or None when there is none.

    A file whose header the tool cannot read is still the note, since
    the file goes by the tool's own name in the tool's own folder, and
    it names no branch and no moment.
    """
    path = path_of(brain)
    if not store.readable_file(path):
        return None

    try:
        text = frontmatter.load(str(path))
    except frontmatter.FrontmatterError:
        return None

    try:
        document = frontmatter.parse(text)
    except frontmatter.FrontmatterError:
        return Note(text=text, branch=None, written=None)

    return Note(
        text=text,
        branch=document.get("branch") or None,
        written=moment_of(document.get("written")),
    )


def moment_of(
    value: Optional[str],
) -> Optional[datetime]:
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def is_for(
    note: Note,
    branch: str,
) -> bool:
    """Whether the note is for a session on this branch, which it is when either side has no branch to compare."""
    return note.branch is None or note.branch == NO_GIT or branch == NO_GIT or note.branch == branch


def remove(
    brain: store.Brain,
) -> Optional[str]:
    """Take the note away once it is read, and say why when it cannot be."""
    try:
        path_of(brain).unlink()
    except FileNotFoundError:
        return None
    except OSError as error:
        return store.explain(error)

    return None


def when(
    moment: Optional[datetime],
) -> str:
    """The moment in the clock's words and this machine's zone, or the words for a note that names none."""
    return clock.words(moment.astimezone()) if moment is not None else "an unknown time"


def describe(
    brain: store.Brain,
) -> Optional[str]:
    """One line for the status, or None when no note waits."""
    note = read(brain)
    if note is None:
        return None

    return f"waiting, written {when(note.written)} on {note.branch or 'an unknown branch'}"


def as_data(
    brain: store.Brain,
) -> Optional[dict]:
    """The note's header for the JSON form of the status, or None when no note waits."""
    note = read(brain)
    if note is None:
        return None

    return {
        "branch": note.branch,
        "written": note.written.isoformat() if note.written is not None else None,
    }
