"""The conclude word, the time the owner names for the session to wrap itself up.

The owner says "stop at 17:15" and the agent records it here through the
tool. Every hook block that prints the clock adds a line with the time
left, a wind down line in the last minutes, and the steps to conclude
once the time has passed. It reads a time the way the standing word
does, and the state is one dotted file at the root of the brain, which
git ignores like the standing word.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from . import autoack, clock, frontmatter, lines, store

FILE = ".conclude"
OFF = "conclude off"
BROKEN = f"{FILE} does not read as a time and brain conclude off clears it"
FOLDER = f"{FILE} is a folder the tool never made, move it away by hand"
WIND_DOWN = timedelta(minutes=15)
# an hour past its time the word orders nothing, so a session that starts the next day, or another one beside it, is never told to stop, and nothing has to clear the file at a session start
STALE = timedelta(hours=1)


class ConcludeError(Exception):
    """The word could not be set as asked, with the reason in the message."""


def path_of(
    brain: store.Brain,
) -> Path:
    """The stop time's file on the line this session is on, the folder's own unless it was put on another."""
    return lines.home(brain.root) / FILE


def turn_on(
    brain: store.Brain,
    at_text: Optional[str] = None,
    in_text: Optional[str] = None,
    at: Optional[datetime] = None,
) -> datetime:
    """Record the moment to conclude, from a time or from a length of time, refused unless it is still to come."""
    if (at_text is None) == (in_text is None):
        raise ConcludeError("the conclude word takes a time with at or a length with in, one of the two")

    if autoack.a_folder(path=path_of(brain=brain)):
        raise ConcludeError(FOLDER)

    at = at or clock.now()
    try:
        if in_text is not None:
            moment = autoack.utc(at) + timedelta(hours=autoack.parse_duration(in_text))
        else:
            moment = autoack.utc(autoack.parse_until(text=at_text or "", at=at))
    except autoack.AckError as bad:
        raise ConcludeError(str(bad).replace("auto ack would end", "the conclude word would fall")) from bad
    except OverflowError as far:
        raise ConcludeError(f"the conclude word would fall past the year {autoack.LAST_YEAR}, give a nearer time") from far

    if moment <= autoack.utc(at):
        raise ConcludeError("the conclude word needs a time still to come")

    if moment > autoack.LATEST:
        raise ConcludeError(f"the conclude word would fall past the year {autoack.LAST_YEAR}, give a nearer time")

    frontmatter.write_text(
        path=str(path_of(brain=brain)),
        text=json.dumps({"at": moment.isoformat()}, indent=2) + "\n",
    )

    return moment


def turn_off(
    brain: store.Brain,
) -> bool:
    """Clear the word, whatever sits where it goes short of a folder. True when there was something to clear."""
    path = path_of(brain=brain)
    if autoack.a_folder(path=path):
        raise ConcludeError(FOLDER)

    if not store.quietly(path.exists) and not store.quietly(path.is_symlink):
        return False

    try:
        path.unlink()
    except FileNotFoundError:
        return False

    return True


def read(
    brain: store.Brain,
) -> Optional[datetime]:
    """The recorded moment, or None when the file is not there or does not read as one."""
    return moment_at(path=path_of(brain=brain))


def moment_at(
    path: Path,
) -> Optional[datetime]:
    """The moment the file at this path records, or None when it is not there or does not read as one."""
    if not store.readable_file(path):
        return None

    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
        return autoack.moment_of(data["at"])
    except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError):
        return None


def carried(
    here: Path,
    there: Path,
) -> None:
    """Carry the stop time of the line a session leaves, the folder `here`, to the line it goes to, the folder `there`.

    The owner named the time to the session and not to the work, so it
    goes where the session goes, to a line it starts, one it joins, and
    back to the folder's own when its line ends. It goes along only
    while it still orders something, and never over a time the other
    line still counts down to, which the sessions there were given. The
    line left keeps its own for whoever stays on it.
    """
    at = autoack.utc(clock.now())
    theirs = moment_at(path=here / FILE)
    if theirs is None or at >= theirs + STALE:
        return

    target = there / FILE
    standing = moment_at(path=target)
    if (standing is not None and at < standing + STALE) or autoack.a_folder(path=target):
        return

    frontmatter.write_text(
        path=str(target),
        text=json.dumps({"at": theirs.isoformat()}, indent=2) + "\n",
    )


def describe(
    brain: store.Brain,
    at: Optional[datetime] = None,
) -> Optional[str]:
    """The hook line for the word, the time left, the wind down or the steps to conclude, or None when no word stands."""
    path = path_of(brain=brain)
    if not store.quietly(path.exists) and not store.quietly(path.is_symlink):
        return None

    moment = read(brain=brain)
    if moment is None:
        return f"{OFF}, {BROKEN}"

    at = at or clock.now()
    when = autoack.when(at=at, moment=moment)
    if autoack.utc(at) >= moment + STALE:
        return f"the conclude word for {when} has passed, so it orders nothing now, and brain conclude off clears it"

    if autoack.utc(at) >= moment:
        return f"conclude now, its time {when} has passed, so stop the sub agents, commit only what passed the gates, save the working paper, write the handover with brain handover, and stop, whatever is left of the standing word"

    line = f"conclude at {when}, {autoack.left(since=at, until=moment)} left"
    if moment - autoack.utc(at) <= WIND_DOWN:
        line += ", so wind down, finish the step in hand and start no new work, sub agent or round of a review, the standing word included, and conclude once it is done and clear the word with brain conclude off after the handover that concludes the session, never after one written before a compaction"

    return line


def passed(
    brain: store.Brain,
    at: Optional[datetime] = None,
) -> bool:
    """Whether the word's time has passed, when a handover is the session concluding rather than one written mid work, a wind down's before a compaction included."""
    moment = read(brain=brain)

    return moment is not None and autoack.utc(at or clock.now()) >= moment
