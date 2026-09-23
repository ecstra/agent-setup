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
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from . import clock, store

FILE = ".ack"
OFF = "auto ack off"

DURATION = re.compile(r"^(\d+(?:\.\d+)?)\s*([mhd])$")
CLOCK_TIME = re.compile(r"^(?:(today|tomorrow)\s+)?(\d{1,2}):(\d{2})$")
DAY_TIME = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:\s+(\d{1,2}):(\d{2}))?$")


class AckError(Exception):
    """The auto ack could not be set or read, with the reason in the message."""


@dataclass(frozen=True)
class Grant:
    """One standing word: when it was given, when it ends, and the entry whose closing ends it sooner."""

    since: datetime
    until: datetime
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

        ends.append(at + timedelta(hours=hours))

    if until_text:
        ends.append(parse_until(text=until_text, at=at))

    if task is not None:
        task = entry_key(brain=brain, key=task)

    if not ends and task is None:
        raise AckError("auto ack needs an end, a time with --for or --until, a task with --until-done, or both")

    grant = Grant(
        since=at,
        until=min(ends) if ends else at + timedelta(days=365),
        task=task,
    )
    if grant.until <= at:
        raise AckError("auto ack would end before it starts, give a time still to come")

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
    """The word as it stands, or None when none was given, its time ran out, or its task is done."""
    grant = read(brain)
    if grant is None:
        return None

    at = at or clock.now()
    if at >= grant.until:
        return None

    if grant.task is not None and task_done(brain=brain, key=grant.task):
        return None

    return grant


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

    if grant.task is not None and (grant.until - at) > timedelta(days=300):
        return f"auto ack on until {grant.task} is done"

    text = f"auto ack on, {left(since=at, until=grant.until)} left, until {when(at=at, moment=grant.until)}"
    if grant.task is not None:
        text += f", or until {grant.task} is done"

    return text


def left(
    since: datetime,
    until: datetime,
) -> str:
    minutes = int((until - since).total_seconds() // 60)
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
    """A moment named the way a person says it: the time today, tomorrow, or the date and time."""
    days = (moment.date() - at.date()).days
    if days == 0:
        return f"{moment:%H:%M} today"

    if days == 1:
        return f"{moment:%H:%M} tomorrow"

    return f"{moment:%Y-%m-%d %H:%M}"


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
    """A moment from 22:00, tomorrow 22:00, 2026-09-24 22:00 or 2026-09-24, in the local zone.

    A bare time already past today means the same time tomorrow, since
    a word given in the evening is meant for the night, not for nothing.
    """
    text = text.strip().lower()
    try:
        match = CLOCK_TIME.match(text)
        if match is not None:
            moment = at.replace(hour=int(match.group(2)), minute=int(match.group(3)), second=0, microsecond=0)
            if match.group(1) == "tomorrow" or (match.group(1) is None and moment <= at):
                moment += timedelta(days=1)

            return moment

        match = DAY_TIME.match(text)
        if match is not None:
            day = datetime.strptime(match.group(1), "%Y-%m-%d")
            hour = int(match.group(2)) if match.group(2) else 23
            minute = int(match.group(3)) if match.group(3) else 59

            return at.replace(year=day.year, month=day.month, day=day.day, hour=hour, minute=minute, second=0, microsecond=0)
    except ValueError as bad:
        raise AckError(f"'{text}' is not a moment on the clock or the calendar, {bad}") from bad

    raise AckError(f"'{text}' is not a moment like 22:00, tomorrow 22:00 or 2026-09-24 22:00")


def entry_key(
    brain: store.Brain,
    key: str,
) -> str:
    """The name of the one entry the key answers to, refused when there is none or several."""
    try:
        entry = brain.find(key)
    except store.Ambiguous as clash:
        raise AckError(str(clash)) from clash

    if entry is None:
        raise AckError(f"nothing in the brain answers to '{key}', so auto ack cannot end with it")

    return entry.name


def task_done(
    brain: store.Brain,
    key: str,
) -> bool:
    """Whether the entry is past open, or gone, either of which ends the word."""
    try:
        entry = brain.find(key)
    except store.Ambiguous:
        return True

    return entry is None or (entry.field("status") or "open") != "open"


def write(
    brain: store.Brain,
    grant: Grant,
) -> None:
    data = {"since": grant.since.isoformat(), "until": grant.until.isoformat(), "task": grant.task}
    path_of(brain).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read(
    brain: store.Brain,
) -> Optional[Grant]:
    """The recorded word, or None when there is none or the file cannot be read as one."""
    path = path_of(brain)
    if not store.readable_file(path):
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Grant(
            since=datetime.fromisoformat(data["since"]),
            until=datetime.fromisoformat(data["until"]),
            task=data.get("task"),
        )
    except (OSError, ValueError, KeyError, TypeError):
        return None
