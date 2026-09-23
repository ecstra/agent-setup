"""Auto ack, the owner's standing word to proceed, with an end it never runs past.

The owner says "auto ack" and the agent records it here through the
tool, with an end by time, by task or both, the earliest winning. There
is no default end. A word given without one is not recorded, and the
agent proposes an end to the owner and waits for the answer. While the
word stands the ledger takes an ack of "auto" and the review skill
passes its gates without waiting. The state is the tool's own, one
dotted file at the root of the brain, gitignored, never listed or
indexed, since it belongs to this machine and this stretch of work.
"""

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from . import clock, schema, store

FILE = ".ack"
OFF = "auto ack off"

# the last moment every zone can still show on its own clock
LATEST = datetime(9999, 12, 30, tzinfo=timezone.utc)

# the kinds a word can end with, and the statuses that keep each one open
OPEN_STATUSES = {
    "todo": ("open",),
    "bug": ("open", "branched"),
    "review": ("open",),
}

DURATION = re.compile(r"^(\d+(?:\.\d+)?)\s*([mhd])$")
CLOCK_TIME = re.compile(r"^(?:(today|tomorrow)\s+)?(\d{1,2}):(\d{2})$")
DAY_TIME = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:\s+(\d{1,2}):(\d{2}))?$")


class AckError(Exception):
    """The auto ack could not be set or read, with the reason in the message."""


@dataclass(frozen=True)
class Grant:
    """One standing word, when it was given, the moment it ends, and the task whose closing ends it, at least one of the two."""

    since: datetime
    until: Optional[datetime]
    task: Optional[str] = None


def path_of(
    brain: store.Brain,
) -> Path:
    return brain.root / FILE


def turn_on(
    brain: store.Brain,
    hours: Optional[float] = None,
    until_text: Optional[str] = None,
    task: Optional[str] = None,
    at: Optional[datetime] = None,
) -> Grant:
    """Record the word with its end, the earliest of the ends given, refused when none is given."""
    at = at or clock.now()
    ends: list[datetime] = []
    if hours is not None:
        if hours <= 0:
            raise AckError("auto ack lasts for a time above zero")

        ends.append(utc(at) + timedelta(hours=hours))

    if until_text:
        ends.append(parse_until(text=until_text, at=at))

    if task is not None:
        task = task_key(brain=brain, key=task)

    if not ends and task is None:
        raise AckError("auto ack needs an end, a time with --for or --until, a task with --until-done, or both")

    until = utc(min(ends)) if ends else None
    if until is not None and until <= utc(at):
        raise AckError("auto ack would end before it starts, give a time still to come")

    grant = Grant(
        since=at,
        until=until,
        task=task,
    )
    write(brain=brain, grant=grant)

    return grant


def turn_off(
    brain: store.Brain,
) -> bool:
    """Take the word back. True when there was one to take."""
    path = path_of(brain)
    if not store.quietly(path.is_file):
        return False

    path.unlink()

    return True


def current(
    brain: store.Brain,
    at: Optional[datetime] = None,
) -> Optional[Grant]:
    """The word as it stands, or None when none was given, its time ran out, its task is done or gone, or its task cannot be read or told apart right now.

    A word its task has ended, or whose task is gone from the brain, is
    taken back on the spot, so it never comes back when the task reads
    open again after a reopen, or when a new entry takes the same id on
    another branch. A task the brain cannot read or tell apart right
    now, one a rebase stopped on or a merge doubled, leaves the word
    off and the file in place, so the word is back once the entry is.
    """
    grant = read(brain)
    if grant is None:
        return None

    at = at or clock.now()
    if grant.until is not None and utc(at) >= grant.until:
        return None

    if grant.task is not None:
        state = task_state(brain=brain, key=grant.task)
        if state in ("done", "gone"):
            forget(brain=brain, grant=grant)

        if state != "open":
            return None

    return grant


def forget(
    brain: store.Brain,
    grant: Grant,
) -> None:
    """Drop the file of a word its task has ended, as long as it still holds that word.

    This runs on every read of the word, from hooks in parallel among
    them, so a file another read dropped first, one a newer word has
    since replaced, or a root that cannot be written right now, is no
    reason to fail the read. The word is off either way, and the next
    read tries again.
    """
    if read(brain) != grant:
        return

    try:
        path_of(brain).unlink()
    except OSError:
        pass


def stamp(
    brain: store.Brain,
    at: Optional[datetime] = None,
) -> str:
    """The ack a ledger records while the word stands, refused when it does not."""
    at = at or clock.now()
    if current(brain=brain, at=at) is None:
        raise AckError("auto ack is off, the owner's word starts a batch")

    return f"auto {at:%Y-%m-%d}"


def describe(
    brain: store.Brain,
    at: Optional[datetime] = None,
) -> str:
    """One line on the word, off or on with what is left of it, for the hooks and the status line."""
    at = at or clock.now()
    grant = current(brain=brain, at=at)
    if grant is None:
        return OFF

    if grant.until is None:
        return f"auto ack on until {grant.task} is done"

    text = f"auto ack on, {left(since=at, until=grant.until)} left, until {when(at=at, moment=grant.until)}"
    if grant.task is not None:
        text += f", or until {grant.task} is done"

    return text


def left(
    since: datetime,
    until: datetime,
) -> str:
    minutes = int((utc(until) - utc(since)).total_seconds() // 60)
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        return f"{hours} h {minutes} min"

    if hours:
        return f"{hours} h"

    return f"{minutes} min"


def when(
    at: datetime,
    moment: datetime,
) -> str:
    """A moment named the way a person says it, the time today, tomorrow, or the date and time, on the wall clock the word runs on."""
    moment = on_the_wall(at=at, moment=moment)
    days = (moment.date() - at.date()).days
    if days == 0:
        return f"{moment:%H:%M} today"

    if days == 1:
        return f"{moment:%H:%M} tomorrow"

    return f"{moment:%Y-%m-%d %H:%M}"


def utc(
    moment: datetime,
) -> datetime:
    """The same instant in UTC, so that arithmetic and comparison never run on a wall clock."""
    return moment.astimezone(timezone.utc)


def on_this_machine(
    at: datetime,
) -> bool:
    """Whether the moment is expressed in this machine's own zone, whose daylight saving rules then apply.

    The clock gives the moment with a fixed offset and no zone name, so
    the test is whether its wall clock, read as this machine's local
    time, is the same instant. A moment in some other zone is not.
    """
    if at.tzinfo is None:
        return True

    return at.replace(tzinfo=None).astimezone() == at


def on_the_wall(
    at: datetime,
    moment: datetime,
) -> datetime:
    """The moment on the wall clock the word runs on, this machine's when the word was given on it."""
    if on_this_machine(at):
        return moment.astimezone()

    return moment.astimezone(at.tzinfo)


def from_the_wall(
    at: datetime,
    naive: datetime,
) -> datetime:
    """A wall clock reading placed in the zone the word runs on, this machine's rules when the word was given on it."""
    if on_this_machine(at):
        return naive.astimezone()

    return naive.replace(tzinfo=at.tzinfo)


def parse_duration(
    text: str,
) -> float:
    """Hours from a duration such as 8h, 90m or 2d."""
    match = DURATION.match(text.strip().lower())
    if match is None:
        raise AckError(f"'{text}' is not a duration like 8h, 90m or 2d")

    amount = float(match.group(1))
    unit = match.group(2)
    if unit == "m":
        return amount / 60

    if unit == "d":
        return amount * 24

    return amount


def parse_until(
    text: str,
    at: datetime,
) -> datetime:
    """A moment from 22:00, tomorrow 22:00, 2026-09-24 22:00 or 2026-09-24, on the wall clock the word runs on.

    A bare time already past today means the same time tomorrow, since
    a word given in the evening is meant for the night, not for nothing.
    """
    text = text.strip().lower()
    wall = at.replace(tzinfo=None)
    try:
        match = CLOCK_TIME.match(text)
        if match is not None:
            moment = wall.replace(
                hour=int(match.group(2)),
                minute=int(match.group(3)),
                second=0,
                microsecond=0,
            )
            if match.group(1) == "tomorrow" or (match.group(1) is None and moment <= wall):
                moment += timedelta(days=1)

            return from_the_wall(at=at, naive=moment)

        match = DAY_TIME.match(text)
        if match is not None:
            day = datetime.strptime(match.group(1), "%Y-%m-%d")
            hour = int(match.group(2)) if match.group(2) else 23
            minute = int(match.group(3)) if match.group(3) else 59

            return from_the_wall(
                at=at,
                naive=day.replace(
                    hour=hour,
                    minute=minute,
                ),
            )
    except ValueError as bad:
        raise AckError(f"'{text}' is not a moment on the clock or the calendar, {bad}") from bad

    raise AckError(f"'{text}' is not a moment like 22:00, tomorrow 22:00 or 2026-09-24 22:00")


def task_key(
    brain: store.Brain,
    key: str,
) -> str:
    """The id, or the name of a review, of the one open todo, bug or review the key answers to, refused otherwise.

    The id is what stays through a retitle, so the word follows the
    entry and not its name.
    """
    try:
        entry = brain.find(key)
    except store.Ambiguous as clash:
        raise AckError(str(clash)) from clash

    if entry is None:
        raise AckError(f"nothing in the brain answers to '{key}', so auto ack cannot end with it")

    if entry.kind.name not in OPEN_STATUSES:
        raise AckError(f"auto ack ends with a todo, a bug or a review, and {entry.name} is a {entry.kind.name}")

    if not is_open(entry):
        raise AckError(f"{entry.name} is already {entry.field('status')}, so auto ack cannot end with it")

    stored = entry.identifier or entry.name
    try:
        brain.find(stored)
    except store.Ambiguous as clash:
        raise AckError(str(clash)) from clash

    return stored


def is_open(
    entry: store.Entry,
) -> bool:
    """Whether the entry still counts as open for its kind, a bug on a branch included."""
    return (entry.field("status") or "open") in OPEN_STATUSES.get(entry.kind.name, ("open",))


def task_state(
    brain: store.Brain,
    key: str,
) -> str:
    """Whether the task is open, done, gone from the brain, or unsure, when the brain cannot read it or tell it apart right now.

    Every state but open leaves the word off. Done and gone take it
    back for good. Unsure keeps the file, since an entry that is
    unreadable while a rebase stops on it, or doubled by a merge, may
    well read open again.
    """
    try:
        entry = brain.find(key)
    except store.Ambiguous:
        return "unsure"

    if entry is None:
        return "unsure" if unreadable_task(brain=brain, key=key) else "gone"

    return "open" if is_open(entry) else "done"


def unreadable_task(
    brain: store.Brain,
    key: str,
) -> bool:
    """Whether the task may still be there unread, in a file the brain could not read this time or a folder it could not list."""
    for path in brain.unreadable:
        if path.stem == key or path.stem.startswith(f"{key}-") or path.parent.name == key:
            return True

    folder = brain.folder(task_kind(key))

    return store.quietly(folder.is_dir) and not listable_throughout(folder)


def task_kind(
    key: str,
) -> schema.Kind:
    """The kind a stored task key names, by its id prefix, a review when it has none."""
    for name in OPEN_STATUSES:
        kind = schema.KINDS[name]
        if kind.id_prefix and key.startswith(f"{kind.id_prefix}-"):
            return kind

    return schema.KINDS["review"]


def listable_throughout(
    folder: Path,
) -> bool:
    """Whether the folder and every folder under it can be listed right now, which the scan needs to see what is in them.

    The scan walks the tree and skips a folder it cannot list without a
    word, so an entry in such a folder, a review's own folder say, goes
    missing rather than unread.
    """
    trouble: list[OSError] = []
    for _ in os.walk(folder, onerror=trouble.append):
        if trouble:
            return False

    return not trouble


def write(
    brain: store.Brain,
    grant: Grant,
) -> None:
    data = {
        "since": grant.since.isoformat(),
        "until": grant.until.isoformat() if grant.until is not None else None,
        "task": grant.task,
    }
    path_of(brain).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read(
    brain: store.Brain,
) -> Optional[Grant]:
    """The recorded word, or None when there is none or the file cannot be read as one.

    A word carries its zone on every moment and has an end by time, by
    task or both, and a file that says otherwise is no word.
    """
    path = path_of(brain)
    if not store.readable_file(path):
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        grant = Grant(
            since=moment_of(data["since"]),
            until=None if data.get("until") is None else moment_of(data["until"]),
            task=data.get("task"),
        )
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        return None

    if grant.until is None and grant.task is None:
        return None

    if grant.task is not None and not isinstance(grant.task, str):
        return None

    return grant


def moment_of(
    text: str,
) -> datetime:
    """A moment from the state file, refused when it carries no zone or lies past what any zone can show.

    The far end raises an OverflowError on its own, from the conversion
    the comparison needs, and the reader takes that as the refusal.
    """
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        raise ValueError(f"'{text}' carries no zone")

    if utc(moment) > LATEST:
        raise ValueError(f"'{text}' lies past what any zone can show")

    return moment
