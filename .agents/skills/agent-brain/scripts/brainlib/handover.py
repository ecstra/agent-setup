"""The handover, the one note a session leaves for the next.

A session that stops mid task, before a compaction or at its end,
writes the note through `brain handover`, and the session start hook
claims it, renaming it aside so a note written meanwhile is never the
one removed, puts it whole in front of the next session and removes the
claimed file once that context is out, so a note is read once. The
tool records what it can read off the machine, the branch and its head,
the uncommitted files, the standing word and the current work, and the
prose on standard input says the rest. The folder holds one note and
git ignores it, since the note belongs to one machine and one stretch
of work, like the standing word and the current work beside it. A file
at the note's path the tool never wrote is the project's own, and the
tool neither claims nor writes over it.
"""

import os
import re
import stat
import string
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from . import autoack, clock, frontmatter, schema, store, task

FOLDER = schema.HANDOVER_FOLDER
FILE = "handover.md"
RELATIVE = f"{FOLDER}/{FILE}"
# the name a claimed note goes by beside the note's own until the context that carries it is out
CLAIMED_NAME = f"{FILE}.reading"
NO_GIT = "no git"
NO_ANSWER = "git could not answer"
NO_COMMITS = "no commits yet"
DETACHED = "detached"
UNKNOWN_TIME = "an unknown time"
NO_WORDS = "a handover carries words, give them on standard input"
FOLDER_IN_THE_WAY = f"{RELATIVE} is a folder the tool never made, move it away by hand"
CLAIMED_FOLDER_IN_THE_WAY = f"{FOLDER}/{CLAIMED_NAME} is a folder the tool never made, move it away by hand"
FILE_IN_THE_WAY = f"{FOLDER} is a file the tool never made, where the note's folder goes, move it away by hand"
BY_HAND = f"{FOLDER}/ holds the one note brain handover writes for the next session, read and removed by the session start hook, and nothing there is written by hand"

# the files the record names, the rest counted, so a build folder git
# does not ignore never floods the next session's context
MOST_FILES_NAMED = 50

# how long one git call may take before the note says git could not
# answer, so a hung git never holds up a session start or a write
GIT_SECONDS = 10

# what git is asked for whether it takes two spellings that differ by case
# alone for one, by the record through the handover's runner and by the
# upgrade's git show line through the upgrade's, each reply read by
# `case_flag_of` so the two never read the flag apart
CASE_FLAG = ("config", "--type=bool", "--get", "core.ignorecase")

BYTE_ORDER_MARK = "\ufeff"
BRANCH_REF_PREFIX = "refs/heads/"

# a bisect started on a detached head keeps the commit's full name where
# a branch's name would be
OBJECT_NAME_SHAPE = re.compile(pattern=r"[0-9a-f]{40}|[0-9a-f]{64}")

# the one shape the tool writes a moment in, to the second, a fraction of
# one to six digits, then an offset or a Z, since the interpreters of the
# kit's floor and ceiling read different sets of ISO forms, the ceiling
# taking hour 24 for the next day's midnight and both taking an offset's
# minutes past 59 for more hours, so an hour runs to 23 and a minute to 59
MOMENT_SHAPE = re.compile(pattern=r"([0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9])(?:\.([0-9]{1,6}))?([+-](?:[01][0-9]|2[0-3]):[0-5][0-9]|Z)")

# git folds the case of ASCII letters alone where core.ignorecase is
# true, so to git's listing É and é stay two paths
ASCII_LOWER: dict[int, int] = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)

WORD_FOR_STATUS_LETTER: dict[str, str] = {
    "?": "untracked",
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
    "U": "unmerged",
    "T": "type changed",
}

# the word for a file renamed out of a project below the top, listed
# under the name it left, which is where the file was and no longer is
MOVED_OUT = "moved out of the project"

# the pairs git's status gives a file a merge left in conflict, whatever the letters say alone
UNMERGED = frozenset({"DD", "AU", "UD", "UA", "DU", "AA", "UU"})

# The claimed files this process took into a context and has not yet
# released, which `read` does not count as waiting. A claimed file no
# process holds, left by a session start that died or could not remove
# it, is the note still waiting.
HELD_PATHS: set[Path] = set()


class HandoverError(Exception):
    """The note could not be written as asked, with the reason in the message."""


class Unanswered(Exception):
    """Git gave no fact to stand on, with the words the note writes in the fact's place as the message."""


@dataclass(frozen=True)
class Note:
    """The note as it stands on disk, its whole text, and the branch and the moment its header names, None for each the header does not give.

    `again` says it waits under the name a claim gave it, read by a
    session start before that could not remove it.
    """

    text: str
    branch: Optional[str]
    written: Optional[datetime]
    again: bool = False


@dataclass(frozen=True)
class Claim:
    """What the session start took of the note's folder.

    `note` is the note read and `path` the file to remove once the
    context that carries it is out, which only happens where the note
    was `taken` aside, and `again` says it is one a session claimed
    before and could not remove. `waiting` is the one line to say in its
    place where the file is left as it is, another branch's note, a file
    the tool never wrote, or one it cannot open, and then `note` is None.
    """

    note: Optional[Note]
    path: Path
    taken: bool
    again: bool
    waiting: Optional[str]


@dataclass(frozen=True)
class Reply:
    """What one git call gave back, its exit code, its output, and what it said went wrong, whole."""

    code: int
    out: str
    err: str


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
    """Write the note, the tool's record first and the prose under it, in place of the tool's note there.

    Refused with no prose, since a note with no words is nothing to
    resume from, with a folder in the file's place or in the place of
    the name a claim gives it, or a file in the folder's, and with
    whatever stands at the path that the tool never wrote or cannot read
    as a file, which `replace` never writes over. A note waiting there
    for another branch, or for a branch this one cannot be compared
    with, is refused too in words that name the branch this one reads,
    and `replace` writes over that on the owner's word. With nothing at
    the path, a claimed note a session could not remove is the note
    waiting, judged the same, and the note written takes its place.
    """
    words = trimmed(prose=prose)
    if not words:
        raise HandoverError(NO_WORDS)

    path = path_of(brain=brain)
    in_the_way: Optional[str] = obstacle(path=path)
    if in_the_way is not None:
        raise HandoverError(in_the_way)

    project = project_of(brain=brain)
    branch = current_branch(project=project)
    aside = path.with_name(name=CLAIMED_NAME)
    waiting_path = path if os.path.lexists(path) else aside
    waiting_note: Optional[Note] = note_in_the_way(path=waiting_path)
    if waiting_note is not None and not replace:
        ignore_case = ignore_case_for(
            note=waiting_note,
            branch=branch,
            project=project,
        )
        left_to_this_branch = names(
            note=waiting_note,
            branch=branch,
            ignore_case=ignore_case,
        )
        if not left_to_this_branch:
            raise HandoverError(
                f"a handover written on {waiting_note.branch} at {when(moment=waiting_note.written)} is waiting there "
                f"for a session on that branch while this one is on {branch}, and --replace writes over it",
            )

    # the moment in this machine's zone, so the note's lines name the zone the clock line names
    at = (at or clock.now()).astimezone()
    written = to_the_minute(moment=at)
    head = current_head(project=project)
    document = frontmatter.Document(
        lines=[
            f"branch: {branch}",
            f"head: {head}",
            f"written: {written.isoformat()}",
        ],
        body=body(
            brain=brain,
            branch=branch,
            head=head,
            at=at,
            words=words,
        ),
    )
    text = frontmatter.render(document=document)

    path.parent.mkdir(exist_ok=True)
    frontmatter.write_text(
        path=str(path),
        text=text,
    )

    # the note just written replaces a claimed one left on disk, which
    # would otherwise come back as the note waiting once this one goes
    if os.path.lexists(aside):
        try:
            aside.unlink()
        except OSError as error:
            raise HandoverError(
                f"{RELATIVE} is written, and {FOLDER}/{CLAIMED_NAME}, the note it replaces, could not be removed, "
                f"{store.explain(error=error)}, so delete it by hand",
            ) from error

    return Note(
        text=text,
        branch=branch,
        written=written,
    )


def to_the_minute(
    moment: datetime,
) -> datetime:
    """The same moment with its zone's offset cut to whole minutes, the most an ISO offset holds, and the zone's name kept, so a zone whose offset has seconds still writes the one shape `moment_of` reads."""
    offset: timedelta = moment.utcoffset() or timedelta(0)
    whole_minutes = timedelta(minutes=int(offset / timedelta(minutes=1)))
    if whole_minutes == offset:
        return moment

    return moment.astimezone(
        tz=timezone(
            offset=whole_minutes,
            name=moment.tzname(),
        ),
    )


def trimmed(
    prose: str,
) -> str:
    """The prose without the blank lines before and after it, every other character as it came, a first line's indentation included."""
    lines = prose.split(sep="\n")
    while lines and not lines[0].strip():
        lines.pop(0)

    while lines and not lines[-1].strip():
        lines.pop()

    return "\n".join(lines)


def obstacle(
    path: Path,
) -> Optional[str]:
    """What stands where the note, the name a claim gives it or their folder goes that the tool never made, in the words that say what to move, or None.

    A folder at the claimed name would hold the note's rename aside and
    the write's removal of the claimed note it replaces, so it is
    refused before anything is written.
    """
    if os.path.lexists(path.parent) and not store.quietly(question=path.parent.is_dir):
        return FILE_IN_THE_WAY

    if store.quietly(question=path.is_dir):
        return FOLDER_IN_THE_WAY

    if store.quietly(question=path.with_name(name=CLAIMED_NAME).is_dir):
        return CLAIMED_FOLDER_IN_THE_WAY

    return None


def note_in_the_way(
    path: Path,
) -> Optional[Note]:
    """The tool's note at the path for a write to judge, or None when nothing stands there, refused when what stands there is not a file the tool can read as its own, a link that leads nowhere and a FIFO among them."""
    if not os.path.lexists(path):
        return None

    where = f"{FOLDER}/{path.name}"
    try:
        text = opened(path=path)
    except OSError as error:
        raise HandoverError(f"{where} could not be read, {store.explain(error=error)}, and a note that cannot be read is never written over") from error

    note: Optional[Note] = note_of(text=text)
    if note is None:
        raise HandoverError(f"{where} holds a file brain handover never wrote, move it into docs/ through brain new or delete it first")

    return note


def body(
    brain: store.Brain,
    branch: str,
    head: str,
    at: datetime,
    words: str,
) -> str:
    """The note's body, the record the tool reads off the machine, the standing word as it stood at the note's moment, then the session's own words."""
    project = project_of(brain=brain)
    note_path = path_of(brain=brain)
    record: list[str] = [f"- branch {branch} at {head}"]
    record += uncommitted_lines(
        project=project,
        notes={
            note_path.relative_to(project).as_posix(),
            note_path.with_name(name=CLAIMED_NAME).relative_to(project).as_posix(),
        },
    )
    standing_word = autoack.describe(
        brain=brain,
        at=at,
    )
    record.append(f"- {standing_word}")
    record += [f"- {line}" for line in task.describe(brain=brain).split(sep="\n")]

    when_written = clock.words(at=at)
    record_text = "\n".join(record)

    return (
        "\n# Handover\n\n"
        f"Written {when_written} on {branch}.\n\n"
        f"## As the tool found it\n\n{record_text}\n\n"
        f"## As the session left it\n\n{words}\n"
    )


def uncommitted_lines(
    project: Path,
    notes: set[str],
) -> list[str]:
    """The project's uncommitted files as list lines, the first MOST_FILES_NAMED with their state and the rest counted, or the one line for none or git's silence.

    Git names every file from the repository's top and covers the whole
    repository, so a project below the top keeps its own files, named
    from its own folder, and a file renamed out of it counts as its own
    under the name it left, moved out of the project where git calls it
    renamed, beside any file that stands at that name now. The note
    itself, under its own name or the name a claim gives it, `notes`
    from the project, is left out, and a file that left one of those
    names is not the note. Where git ignores case, a path that spells the
    project's folder or one of the note's names with an ASCII letter in
    another case is theirs, as it is to git, and one that differs in any
    other letter is another path. The paths and the prefix are compared
    as git printed them, a byte that is not UTF-8 kept as the shared
    runner's escape, so two folders git names apart by such a byte stay
    apart, and the escape is replaced only in the line written. With none
    of the project's own, the line says whether the working tree is clean
    or has changes outside the project.
    """
    try:
        prefix = printed(
            project=project,
            arguments=["rev-parse", "--show-prefix"],
        ).rstrip("\n")
        listing = printed(
            project=project,
            arguments=["--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "-z"],
        )
    except Unanswered as unanswered:
        return [f"- uncommitted files, {unanswered}"]

    ignore_case = ignores_case(project=project)
    changed: list[tuple[str, str, Optional[str]]] = changed_files(porcelain=listing)
    owned: list[Optional[tuple[str, str]]] = [
        own_file(
            state=state,
            path=path,
            left=left,
            prefix=prefix,
            notes=notes,
            ignore_case=ignore_case,
        )
        for state, path, left in changed
    ]
    files: list[tuple[str, str]] = [file for file in owned if file is not None]

    changed_outside_only = not files and any(
        from_project(
            path=path,
            prefix=prefix,
            ignore_case=ignore_case,
        )
        is None
        for _, path, _ in changed
    )
    if changed_outside_only:
        return ["- uncommitted files, none in this project, the working tree has changes outside it"]

    if not files:
        return ["- uncommitted files, none, the working tree is clean"]

    noun = "file" if len(files) == 1 else "files"
    lines: list[str] = [f"- uncommitted, {len(files)} {noun}"]
    lines += [f"  - {one_line(text=replaced(text=path))}, {state}" for state, path in files[:MOST_FILES_NAMED]]
    if len(files) > MOST_FILES_NAMED:
        lines.append(f"  - and {len(files) - MOST_FILES_NAMED} more")

    return lines


def own_file(
    state: str,
    path: str,
    left: Optional[str],
    prefix: str,
    notes: set[str],
    ignore_case: bool,
) -> Optional[tuple[str, str]]:
    """One entry of git's listing as the project's own file, its state and its name from the project's folder, or None for the note and for a file that never stood in the project.

    The note is judged by the name a file stands at, and a file renamed
    out of the project by the name it left, so a file that left the
    note's names is never taken for the note. Each path is matched to
    the project's folder and the note's names as git matches them,
    without regard to an ASCII letter's case where `ignore_case` says git
    ignores it.
    """
    name: Optional[str] = from_project(
        path=path,
        prefix=prefix,
        ignore_case=ignore_case,
    )
    if name is not None:
        is_note = any(
            same_path(
                one=name,
                other=note,
                ignore_case=ignore_case,
            )
            for note in notes
        )
        if is_note:
            return None

        return (state, name)

    if left is None:
        return None

    former: Optional[str] = from_project(
        path=left,
        prefix=prefix,
        ignore_case=ignore_case,
    )
    if former is None:
        return None

    state_where_it_left = MOVED_OUT if state == WORD_FOR_STATUS_LETTER["R"] else state

    return (state_where_it_left, former)


def from_project(
    path: str,
    prefix: str,
    ignore_case: bool,
) -> Optional[str]:
    """A path git names from the repository's top, named from the project's folder instead, the folder being `prefix` from the top, or None for a path outside it."""
    in_the_folder = same_path(
        one=path[: len(prefix)],
        other=prefix,
        ignore_case=ignore_case,
    )
    if not in_the_folder:
        return None

    return path[len(prefix) :]


def same_path(
    one: str,
    other: str,
    ignore_case: bool,
) -> bool:
    """Whether git takes the two paths for one, folding only the case git folds where it ignores case, an ASCII letter's."""
    return one == other or (ignore_case and one.translate(ASCII_LOWER) == other.translate(ASCII_LOWER))


def changed_files(
    porcelain: str,
) -> list[tuple[str, str, Optional[str]]]:
    """The state and the path of each entry in a NUL separated porcelain listing, and the name a renamed file left, None for every other entry.

    The old name of a rename or a copy follows its entry and is never an
    entry of its own. A renamed file is gone from its old name, while a
    copy's source stays where it was, with an entry of its own where it
    changed, so a copy carries None.
    """
    found: list[tuple[str, str, Optional[str]]] = []
    tokens = porcelain.split(sep="\0")
    index = 0

    while index < len(tokens):
        entry = tokens[index]
        index += 1
        if len(entry) < 4:
            continue

        code = entry[:2]
        left = tokens[index] if "R" in code else None
        found.append((state_of(code=code), entry[3:], left))
        if code[0] in "RC" or code[1] in "RC":
            index += 1

    return found


def state_of(
    code: str,
) -> str:
    """The word for a porcelain status pair, the one state of the two letters that tells the next session most about the file."""
    if code in UNMERGED:
        return WORD_FOR_STATUS_LETTER["U"]

    if code[1] == "D":
        return WORD_FOR_STATUS_LETTER["D"]

    if code[0] in "ARC":
        return WORD_FOR_STATUS_LETTER[code[0]]

    letter = code[1] if code[1] != " " else code[0]

    return WORD_FOR_STATUS_LETTER.get(
        letter,
        letter,
    )


def current_branch(
    project: Path,
) -> str:
    """The branch the project is on, else the one a rebase or a bisect in progress works on, detached where there is none, or the words for what git could not tell.

    A head on a branch names it, whatever a rebase or a bisect left on
    disk, and only a detached head asks what one in progress works on.
    The branch is named from its full ref without `refs/heads/`, the way
    a rebase's file is read and the name a bisect's file already holds,
    so a branch that shares its name with a tag, or whose own name starts
    with `refs/heads/`, reads one way in all three.
    """
    try:
        has_commits(project=project)
        reply: Reply = asked(
            project=project,
            arguments=["symbolic-ref", "-q", "HEAD"],
        )
        if reply.code == 1 and not reply.err:
            return branch_in_progress(project=project) or DETACHED
    except Unanswered as unanswered:
        return str(unanswered)

    full_ref = reply.out.strip()
    if reply.code == 0 and full_ref:
        return branch_name_of(ref=full_ref)

    return no_answer(reply=reply)


def branch_in_progress(
    project: Path,
) -> Optional[str]:
    """The branch a rebase or a bisect in progress works on, from the files git keeps for it, or None, a detached start included.

    The files are looked for in the folder `rev-parse --git-dir` names,
    spelled for the disk by `on_disk` from the bytes git printed, so a
    git dir named with a byte that is not UTF-8, or with a name this
    machine's file name codec spells apart from UTF-8, is the folder git
    meant, and one this machine cannot spell is not reached. A rebase
    keeps the branch's full ref, and a bisect the name without
    `refs/heads/`, or the commit's full name for a detached start.
    """
    git_dir: Optional[str] = on_disk(
        name=printed(
            project=project,
            arguments=["rev-parse", "--git-dir"],
        ).rstrip("\n"),
    )
    if git_dir is None:
        return None

    folder = project / git_dir
    for name in ("rebase-merge/head-name", "rebase-apply/head-name"):
        head_name = file_text(path=folder / name)
        if head_name.startswith(BRANCH_REF_PREFIX):
            return head_name[len(BRANCH_REF_PREFIX) :]

    started_on = file_text(path=folder / "BISECT_START")
    if started_on and OBJECT_NAME_SHAPE.fullmatch(string=started_on) is None:
        return started_on

    return None


def branch_name_of(
    ref: str,
) -> str:
    return ref[len(BRANCH_REF_PREFIX) :] if ref.startswith(BRANCH_REF_PREFIX) else ref


def file_text(
    path: Path,
) -> str:
    """A small file git keeps, as text without the whitespace around it, or nothing where git keeps none, and Unanswered with the reason where one stands that this process cannot read, since then what git keeps there is not known."""
    try:
        kept = path.read_bytes()
    except FileNotFoundError:
        return ""
    except OSError as error:
        raise Unanswered(f"{NO_ANSWER}, {store.explain(error=error)}") from error

    return kept.decode(
        encoding="utf-8",
        errors="replace",
    ).strip()


def current_head(
    project: Path,
) -> str:
    """The head's short hash and subject on one line, or the words for what stands in for them."""
    try:
        has_commits(project=project)
        log = answer(
            project=project,
            arguments=["log", "-1", "--no-show-signature", "--encoding=UTF-8", "--format=%h %s"],
        )
    except Unanswered as unanswered:
        return str(unanswered)

    return one_line(text=log.split(sep="\n")[0])


def has_commits(
    project: Path,
) -> None:
    """Go on where the head names a commit, else stop with the words for a repository with no commits yet, or for what git said."""
    reply: Reply = asked(
        project=project,
        arguments=["rev-parse", "-q", "--verify", "HEAD"],
    )
    if reply.code == 0:
        return

    if reply.code == 1 and not reply.err:
        raise Unanswered(NO_COMMITS)

    raise Unanswered(no_answer(reply=reply))


def ignores_case(
    project: Path,
) -> bool:
    """Whether git takes two spellings that differ by case alone for one here, a branch's two for one ref and a path's two for one file, as it does where it set core.ignorecase for a disk that ignores case, asked through the handover's own runner, so no `.git` at the project's root or above it, or a git that gives no answer in GIT_SECONDS, reads as no."""
    try:
        reply: Reply = asked(
            project=project,
            arguments=list(CASE_FLAG),
        )
    except Unanswered:
        return False

    return case_flag_of(reply=reply)


def case_flag_of(
    reply: Reply,
) -> bool:
    """Whether git's reply to CASE_FLAG says it takes two spellings that differ by case alone for one, the one reading of the flag, which a caller that asks through a runner of its own hands its reply to."""
    return reply.code == 0 and reply.out.strip() == "true"


def answer(
    project: Path,
    arguments: list[str],
) -> str:
    """What git prints for the project, a byte that is not UTF-8 read as the replacement character, or Unanswered with the words for why it printed nothing to stand on."""
    return replaced(
        text=printed(
            project=project,
            arguments=arguments,
        ),
    )


def printed(
    project: Path,
    arguments: list[str],
) -> str:
    """What git prints for the project as the shared runner gives it, a byte that is not UTF-8 kept as a surrogate escape, or Unanswered with the words for why it printed nothing to stand on."""
    reply: Reply = git_here(
        project=project,
        arguments=arguments,
    )
    if reply.code != 0:
        raise Unanswered(no_answer(reply=reply))

    return reply.out


def asked(
    project: Path,
    arguments: list[str],
) -> Reply:
    """One of the handover's own git calls, Unanswered with no git where no `.git` sits at the project's root or above it, which is answered without git as the upgrade answers it.

    A byte of the output that is not UTF-8 reads as the replacement
    character, so the note, the status and the context never hold the
    surrogate escape the shared runner keeps it as.
    """
    reply: Reply = git_here(
        project=project,
        arguments=arguments,
    )

    return Reply(
        code=reply.code,
        out=replaced(text=reply.out),
        err=reply.err,
    )


def git_here(
    project: Path,
    arguments: list[str],
) -> Reply:
    """One of the handover's own git calls as the shared runner gives it, Unanswered with no git where no `.git` sits at the project's root or above it, which is answered without git as the upgrade answers it."""
    if not inside_repository(project=project):
        raise Unanswered(NO_GIT)

    return git(
        project=project,
        arguments=arguments,
    )


def replaced(
    text: str,
) -> str:
    """The text with each surrogate escape the shared runner keeps for a byte that is not UTF-8 read as the replacement character."""
    return text.encode(
        encoding="utf-8",
        errors="surrogateescape",
    ).decode(
        encoding="utf-8",
        errors="replace",
    )


def on_disk(
    name: str,
) -> Optional[str]:
    """A name from the shared runner's text spelled the way the file system spells it, so it reaches the file whose bytes git printed whatever codec this machine names files in, or None where this machine cannot spell it.

    The text's UTF-8 bytes with the runner's escapes restored are the
    bytes git printed. Windows names files in UTF-16 and has no name for
    a byte that is not UTF-8, so there such a name reaches nothing, and
    the UnicodeError, a ValueError brain.py does not catch, ends here.
    """
    try:
        return os.fsdecode(
            name.encode(
                encoding="utf-8",
                errors="surrogateescape",
            ),
        )
    except UnicodeError:
        return None


def git(
    project: Path,
    arguments: list[str],
    seconds: Optional[int] = GIT_SECONDS,
) -> Reply:
    """One git call from the folder, its output read as UTF-8 with a byte that is not UTF-8 kept as a surrogate escape, its trouble with such a byte replaced, and no line ending changed.

    Git itself finds the repository that holds the folder, a bare one
    included, so the upgrade reads through this what git reads, and the
    bytes of a path git printed come back from the output's text. It is
    Unanswered with no git where git is not installed, and with git
    could not answer where git takes longer than `seconds`, GIT_SECONDS
    unless the caller says, and None waits as long as git takes.
    """
    try:
        result: subprocess.CompletedProcess[bytes] = subprocess.run(
            ["git", "-C", str(project), *arguments],
            capture_output=True,
            timeout=seconds,
            check=False,
        )
    except OSError as error:
        raise Unanswered(NO_GIT) from error
    except subprocess.TimeoutExpired as error:
        raise Unanswered(f"{NO_ANSWER}, it gave no answer in {seconds} seconds") from error

    return Reply(
        code=result.returncode,
        out=result.stdout.decode(
            encoding="utf-8",
            errors="surrogateescape",
        ),
        err=result.stderr.decode(
            encoding="utf-8",
            errors="replace",
        ).strip(),
    )


def inside_repository(
    project: Path,
) -> bool:
    """Whether a `.git` sits at the project's root or above it, answered without git so no locale and no refusal of git's is in the way."""
    root = project.resolve()

    return any(store.quietly(question=(folder / ".git").exists) for folder in [root, *root.parents])


def no_answer(
    reply: Reply,
) -> str:
    said = first_line(text=reply.err)

    return f"{NO_ANSWER}, {said}" if said else NO_ANSWER


def first_line(
    text: str,
) -> str:
    """The first line of what git said, cut at the line feed git ends each line with and nowhere else, a carriage return in it written as its escape so the note's line stays one."""
    return one_line(text=text.strip().split(sep="\n")[0].strip())


def one_line(
    text: str,
) -> str:
    """The text with each line break and carriage return written as its escape, so it stays one line of the note."""
    return text.replace(
        "\r",
        "\\r",
    ).replace(
        "\n",
        "\\n",
    )


def read(
    brain: store.Brain,
) -> Optional[Note]:
    """The tool's note waiting on disk, unclaimed, or None when there is none, it cannot be opened, or the file there is not the tool's.

    With no file at the note's path, a claimed note left on disk is the
    note waiting, as `claim` and `write` judge it, read as one read
    before, unless a claim of this process holds it, since the session
    start counts the status after its claim and that note is in the
    very context the status goes into.
    """
    path = path_of(brain=brain)
    if os.path.lexists(path):
        return note_at(
            path=path,
            again=False,
        )

    aside = path.with_name(name=CLAIMED_NAME)
    if aside in HELD_PATHS:
        return None

    return note_at(
        path=aside,
        again=True,
    )


def note_at(
    path: Path,
    again: bool,
) -> Optional[Note]:
    if not store.readable_file(path=path):
        return None

    try:
        return note_of(
            text=opened(path=path),
            again=again,
        )
    except OSError:
        return None


def opened(
    path: Path,
) -> str:
    """The file's text as a note is read, UTF-8 with a stray byte replaced, a leading byte order mark dropped, and each line ending read as a line break as a text file's is, so none of them hides the header, the CRLF Windows writes the note with among them.

    What stands at the path that is not a file, a folder, a FIFO or a
    device, is refused with an OSError before it is opened, since a FIFO
    or a device would hold the read up, and a link that leads nowhere
    raises as the system names it.
    """
    if not stat.S_ISREG(os.stat(path).st_mode):
        raise OSError(None, "Not a file", str(path))

    decoded = path.read_bytes().decode(
        encoding="utf-8",
        errors="replace",
    )
    text = decoded.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    return text[len(BYTE_ORDER_MARK) :] if text.startswith(BYTE_ORDER_MARK) else text


def note_of(
    text: str,
    again: bool = False,
) -> Optional[Note]:
    """The tool's note in the text, or None for a file the tool never wrote, one whose header does not read, carries a kind, or lacks the branch or the moment."""
    try:
        fields: dict[str, str] = frontmatter.parse(text=text).fields()
    except frontmatter.FrontmatterError:
        return None

    if "kind" in fields or "branch" not in fields or "written" not in fields:
        return None

    return Note(
        text=text,
        branch=fields["branch"] or None,
        written=moment_of(value=fields["written"]),
        again=again,
    )


def moment_of(
    value: Optional[str],
) -> Optional[datetime]:
    """The moment a header names in the one shape the tool writes, or None for anything else, so every interpreter the kit runs on reads and refuses the same headers.

    The fraction is filled out to six digits and a Z read as +00:00
    before `datetime.fromisoformat` sees it, the two forms of that shape
    the interpreters of the kit's floor read otherwise.
    """
    shape: Optional[re.Match[str]] = MOMENT_SHAPE.fullmatch(string=value or "")
    if shape is None:
        return None

    to_the_second, digits, offset = shape.groups()
    fraction = ""
    if digits:
        six_digits = digits.ljust(
            6,
            "0",
        )
        fraction = f".{six_digits}"

    offset = "+00:00" if offset == "Z" else offset

    try:
        return datetime.fromisoformat(to_the_second + fraction + offset)
    except ValueError:
        return None


def claim(
    brain: store.Brain,
) -> Optional[Claim]:
    """Take the note for the session starting, or say in one line why it stays, None when nothing waits.

    The note is renamed aside in one step, then read and judged again
    there, so a file written at the note's path between the first read
    and the rename is taken only where it is this session's note too,
    and a note written between the read and the removal is never the one
    removed. A note at the note's path is the latest, written after
    anything a session claimed, and its rename replaces a claimed one
    left on disk. With none there, one a session claimed before and
    could not remove is the note still waiting, read again. Where the
    rename fails the note is read where it is, and stays for the next
    session.
    """
    path = path_of(brain=brain)
    if os.path.lexists(path):
        return judged(
            brain=brain,
            path=path,
            again=False,
        )

    aside = path.with_name(name=CLAIMED_NAME)
    if os.path.lexists(aside):
        return judged(
            brain=brain,
            path=aside,
            again=True,
        )

    return None


def judged(
    brain: store.Brain,
    path: Path,
    again: bool,
    branch: Optional[str] = None,
) -> Claim:
    """The claim on the file at the path, taken where it is this session's note, else left as it is with the line that says why.

    `branch` is the session's, asked of git here unless the caller has
    asked it already. A note at the note's path goes aside to be taken,
    and one under the claimed name is taken where it is.
    """
    project = project_of(brain=brain)
    where = path.relative_to(project).as_posix()
    try:
        text = opened(path=path)
    except OSError as error:
        return left(
            path=path,
            again=again,
            waiting=f"The handover in {where} could not be read, {store.explain(error=error)}, so it is left where it is.",
        )

    note: Optional[Note] = note_of(
        text=text,
        again=again,
    )
    if note is None:
        return left(
            path=path,
            again=again,
            waiting=f"{where} holds a file brain handover never wrote, left where it is, move it into docs/ through brain new or delete it.",
        )

    session_branch = current_branch(project=project) if branch is None else branch
    ignore_case = ignore_case_for(
        note=note,
        branch=session_branch,
        project=project,
    )
    for_this_session = is_for(
        note=note,
        branch=session_branch,
        ignore_case=ignore_case,
    )
    if not for_this_session:
        return left(
            path=path,
            again=again,
            waiting=f"A handover written on {note.branch} at {when(moment=note.written)} waits in {where} for a session on that branch, and this one is on {session_branch}.",
        )

    if path.name != CLAIMED_NAME:
        return taken_aside(
            brain=brain,
            path=path,
            note=note,
            branch=session_branch,
        )

    HELD_PATHS.add(path)

    return Claim(
        note=note,
        path=path,
        taken=True,
        again=again,
        waiting=None,
    )


def taken_aside(
    brain: store.Brain,
    path: Path,
    note: Note,
    branch: str,
) -> Claim:
    """The note renamed aside, then judged again there as the file the rename moved, or read where it is when the rename fails, so the next session reads it again.

    A file written at the note's path after the first read is the one
    the rename moves, so where it is not this session's note, or cannot
    be read, it is left under the claimed name with the line that says
    why, and the next start reads it as the note still waiting.
    """
    aside = path.with_name(name=CLAIMED_NAME)
    try:
        os.replace(
            src=path,
            dst=aside,
        )
    except OSError:
        return Claim(
            note=note,
            path=path,
            taken=False,
            again=False,
            waiting=None,
        )

    return judged(
        brain=brain,
        path=aside,
        again=False,
        branch=branch,
    )


def left(
    path: Path,
    again: bool,
    waiting: str,
) -> Claim:
    return Claim(
        note=None,
        path=path,
        taken=False,
        again=again,
        waiting=waiting,
    )


def release(
    claim: Claim,
) -> Optional[str]:
    """Remove the claimed file once the context that carries it is out, and say why when it cannot be. A file not taken aside stays.

    This process lets go of the file either way, so one it could not
    remove is the note still waiting for the status and the next start.
    """
    if not claim.taken:
        return None

    HELD_PATHS.discard(claim.path)
    try:
        claim.path.unlink()
    except FileNotFoundError:
        return None
    except OSError as error:
        return store.explain(error=error)

    return None


def is_for(
    note: Note,
    branch: str,
    ignore_case: bool = False,
) -> bool:
    """Whether the note is for a session on this branch.

    A note that names no branch, or one where git did not answer, is for
    any session, and any note is for a session whose own git did not
    answer, so a git hiccup never strands a note. Two branch names
    compare as text, without regard to case where git takes the two
    spellings for one ref, and a note of a detached head or of a
    repository with no commits yet is for a session that reads the same.
    """
    if silent(branch=branch):
        return True

    return names(
        note=note,
        branch=branch,
        ignore_case=ignore_case,
    )


def names(
    note: Note,
    branch: str,
    ignore_case: bool,
) -> bool:
    """Whether the note's header leaves it to this branch, naming no branch, one where git did not answer, or this one."""
    if note.branch is None or silent(branch=note.branch):
        return True

    if ignore_case and real(branch=note.branch) and real(branch=branch):
        return note.branch.casefold() == branch.casefold()

    return note.branch == branch


def ignore_case_for(
    note: Note,
    branch: str,
    project: Path,
) -> bool:
    """Whether the note's branch and this one, differing by case alone, are one ref to git here, which git is asked only then."""
    if note.branch is None or note.branch == branch or note.branch.casefold() != branch.casefold():
        return False

    return ignores_case(project=project)


def silent(
    branch: str,
) -> bool:
    """Whether the branch reads as git's silence rather than a branch, no git or git could not answer."""
    return branch == NO_GIT or branch.startswith(NO_ANSWER)


def real(
    branch: str,
) -> bool:
    """Whether the branch is a branch's name, not the words for a detached head, a repository with no commits, or git's silence."""
    return branch not in (DETACHED, NO_COMMITS) and not silent(branch=branch)


def when(
    moment: Optional[datetime],
) -> str:
    """The moment in the clock's words and this machine's zone, or the words for one the note does not name or this machine's clock cannot place."""
    if moment is None:
        return UNKNOWN_TIME

    try:
        return clock.words(at=moment.astimezone())
    except (OverflowError, ValueError, OSError):
        # a moment at the calendar's ends, or before 1970 on Windows, has no place on this machine's clock
        return UNKNOWN_TIME
