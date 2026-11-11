"""The session a command or a hook runs in, and the line of work it is on.

Two agents may work in one project folder, each on its own line of
work. What tells them apart is the session each runs in, which the
agent itself names in the environment of every command it starts. The
tool reads it there and nowhere else, and a hook whose agent names the
session to it another way puts it there first, so no command takes a
session's id and the agent never types one. Where no agent names a
session, as in a plain terminal, there is none, and the tool works on
the folder's own files as it did before 3.2.0.

Only a short hash of the id is ever kept or compared, so no file of
the brain holds the id itself.

The work in hand, the standing word and the stop time belong to a line
of work. The folder's own line keeps them at the root of the brain,
where they always were. A line started beside it is a folder under
`.lines/`, which holds the same three files under the same names and,
under `sessions/`, one empty file per session that is on it, named by
the session's hash. So no file is shared between two lines.
"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Optional

FOLDER = ".lines"
SESSIONS = "sessions"
NO_SESSION = "this agent names no session to its commands, so a line of work of its own cannot be told apart here"
BY_HAND = f"{FOLDER}/ holds the work in hand, the standing word and the stop time of each line of work started with brain task on --beside, and nothing there is written by hand"

# Codex names the session to the commands it runs under this name and to a hook in its event alone, so a Codex hook puts the event's id here
CODEX_SESSION = "CODEX_SESSION_ID"

# What an agent puts into the environment of the commands it runs, read
# in this order. Claude Code names the session to its commands and its
# hooks alike. Codex names the session and the thread, the session read
# first, since a sub agent's thread has an id of its own while its
# session is its parent's. Gemini CLI gives a command no id, only a
# hook, so its variable is not read and a Gemini session keeps the
# folder's one line and one unnamed note.
SESSION_VARS: tuple[str, ...] = ("CLAUDE_CODE_SESSION_ID", CODEX_SESSION, "CODEX_THREAD_ID")

# long enough that two sessions in one folder never share one, short enough for a file's name
HASH_LENGTH = 16


def session() -> Optional[str]:
    """The session this process runs in, as a short hash of the id its agent gives, or None where no agent names one."""
    for name in SESSION_VARS:
        given: str = os.environ.get(name, "").strip()
        if given:
            return hashlib.sha256(given.encode("utf-8")).hexdigest()[:HASH_LENGTH]

    return None


def home(
    root: Path,
) -> Path:
    """The folder that holds this session's work in hand, standing word and stop time, its line's or else the brain's own root.

    A session no agent names, one on no line, and one whose lines cannot
    be listed all stand on the folder's line, so nothing a line holds is
    ever read for a session that was not put on it.
    """
    named: Optional[str] = session()
    if named is None:
        return root

    for folder in folders(root):
        if os.path.isfile(folder / SESSIONS / named):
            return folder

    return root


def folders(
    root: Path,
) -> list[Path]:
    """Every line's folder, in the order the lines were started, or none where they cannot be listed."""
    try:
        found: list[Path] = [path for path in (root / FOLDER).iterdir() if path.is_dir()]
    except OSError:
        return []

    return sorted(found, key=lambda path: (not path.name.isdigit(), int(path.name) if path.name.isdigit() else 0, path.name))


def started(
    root: Path,
) -> Path:
    """A new line's folder, numbered one past the highest there is, so a line that ended never lends its number to the next."""
    taken: list[int] = [int(folder.name) for folder in folders(root) if folder.name.isdigit()]
    folder: Path = root / FOLDER / str(max(taken, default=0) + 1)
    folder.mkdir(parents=True)

    return folder


def put(
    root: Path,
    line: Optional[Path],
) -> None:
    """Put this session on the line, or with None back on the folder's own, its mark taken off every other line."""
    named: Optional[str] = session()
    if named is None:
        raise ValueError(NO_SESSION)

    for folder in folders(root):
        if folder != line:
            try:
                (folder / SESSIONS / named).unlink()
            except FileNotFoundError:
                pass

    if line is not None:
        (line / SESSIONS).mkdir(parents=True, exist_ok=True)
        (line / SESSIONS / named).touch()


def ended(
    folder: Path,
) -> None:
    """Take the line away with everything it held, so each session that was on it stands on the folder's line again."""
    shutil.rmtree(folder, ignore_errors=True)
    # the folder of all lines goes with its last one, and stays while another line is in it
    try:
        folder.parent.rmdir()
    except OSError:
        pass
