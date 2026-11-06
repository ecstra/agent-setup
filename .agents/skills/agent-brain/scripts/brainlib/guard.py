"""The guard on test assertions, which keeps an agent from weakening a test it was handed, in every language.

An assertion already written in a test file is the spec's word on what
the code must do, so the pre write hook refuses a write that changes or
removes one unless the owner's word for that file holds, given with an
end like the standing word and kept beside it, in a dotted file of the
brain that git ignores. An assertion added, moved or reindented passes,
and so does the code under test. A check is found by the way its
language writes one and held whole, over every line a formatter wraps
it onto, with the `if` line a Go test checks on. A value the check
reads from elsewhere, a variable or a table, is the code's, a named
limit.
"""

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Optional

from . import autoack, clock, frontmatter, store

FILE = ".ack-tests"
NONE = "no test file holds the owner's word"

# the code suffixes of each language's test files, and the folders a test of any of them sits in
CODE = {".rs", ".py", ".dart", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".java", ".kt", ".kts", ".swift", ".rb"}
# folder names compared in lower case, so Swift's Tests folder counts
TEST_FOLDERS = {"tests", "test", "__tests__", "spec", "specs"}
TEST_NAME = re.compile(
    r"(?:^test_.+\.py$|_test\.(?:py|go|dart|rb)$|^tests?\.(?:py|rs)$|_tests?\.rs$|\.(?:test|spec)\.(?:js|jsx|ts|tsx|mjs|cjs)$|(?:Test|Tests)\.(?:java|kt|kts|swift)$|_spec\.rb$)",
)

# how each language writes a check, read off a line with its indent taken off
CHECKS = {
    ".rs": re.compile(r"\b(?:prop_|debug_)?assert\w*!|#\[should_panic|\.assert\(\)"),
    ".py": re.compile(r"^assert\b|\.assert\w*\(|\bpytest\.raises\b|\bself\.fail\("),
    ".go": re.compile(r"\bt\.(?:Error|Errorf|Fatal|Fatalf|Fail|FailNow)\(|\b(?:assert|require)\.\w+\("),
    ".swift": re.compile(r"\bXCTAssert\w*\(|\bXCTFail\(|#expect\(|#require\("),
    ".java": re.compile(r"\bassert\w*\(|\bfail\("),
    ".rb": re.compile(r"\bexpect\b|\bassert\w*\b|\bmust_\w+|\bshould\b"),
}
SCRIPT_CHECK = re.compile(r"\bexpect(?:Later)?\s*\(|\bassert\w*[.(]|\.should\b")
for suffix in (".dart", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
    CHECKS[suffix] = SCRIPT_CHECK
CHECKS[".kt"] = CHECKS[".kts"] = CHECKS[".java"]

RUST_TESTS = re.compile(r"^\s*#\[cfg\(test\)\]")
GO_FAILS = re.compile(r"\bt\.(?:Error|Errorf|Fatal|Fatalf|Fail|FailNow)\(")
# a string or a character literal, taken out before brackets are counted, Rust's lifetimes left alone by its own pattern
QUOTED = re.compile(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'")
RUST_QUOTED = re.compile(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])'")
OPENS = "([{"
CLOSES = ")]}"
# the most lines one check is read over, so a bracket a string hides from the count never runs a check to the end of the file
LONGEST = 40


def is_test_file(
    relative: str,
) -> bool:
    """Whether the path is a test file by its name or by a folder of tests it sits in, or a snapshot."""
    path = PurePosixPath(relative)
    if path.suffix == ".snap":
        return True

    if path.suffix not in CODE:
        return False

    return TEST_NAME.search(path.name) is not None or any(part.lower() in TEST_FOLDERS for part in path.parts[:-1])


def assertions(
    relative: str,
    text: str,
) -> list[str]:
    """The checks a test file holds, each whole on one line, the lines it spans joined with their indent taken off, in the order they stand.

    A Rust file outside a folder of tests holds its tests in the items
    a `#[cfg(test)]` attribute stands on, so only the lines of those
    count, and a check elsewhere is the code's. A snapshot is an
    assertion whole, every line of it below its header.
    """
    path = PurePosixPath(relative)
    lines = text.replace("\r\n", "\n").split("\n")
    if path.suffix == ".snap":
        return snapshot_lines(lines)

    if path.suffix == ".rs" and not is_test_file(relative):
        counted = rust_test_lines(lines)
    elif is_test_file(relative):
        counted = set(range(len(lines)))
    else:
        return []

    check = CHECKS.get(path.suffix)
    if check is None:
        return []

    held: list[str] = []
    number = 0
    while number < len(lines):
        line = lines[number].strip()
        if number not in counted or not line or not check.search(line):
            number += 1
            continue

        start = go_check_line(lines=lines, number=number) if path.suffix == ".go" and GO_FAILS.search(line) else number
        end = statement_end(lines=lines, start=number, quoted=RUST_QUOTED if path.suffix == ".rs" else QUOTED)
        held.append(" ".join(part.strip() for part in lines[start : end + 1] if part.strip()))
        number = end + 1

    return held


def depth_of(
    line: str,
    quoted: "re.Pattern[str]",
) -> int:
    """How many brackets a line leaves open, its strings taken out first, negative where it closes more than it opens."""
    bare = quoted.sub("", line)

    return sum(bare.count(bracket) for bracket in OPENS) - sum(bare.count(bracket) for bracket in CLOSES)


def statement_end(
    lines: list[str],
    start: int,
    quoted: "re.Pattern[str]",
) -> int:
    """The last line of the check that opens at `start`, which runs on while a bracket stays open or the next line goes on with a method call."""
    depth = 0
    number = start
    while number < len(lines) and number - start < LONGEST:
        depth += depth_of(line=lines[number], quoted=quoted)
        following = next((line.strip() for line in lines[number + 1 :] if line.strip()), "")
        if depth <= 0 and not following.startswith("."):
            return number

        number += 1

    return min(number, len(lines) - 1)


def go_check_line(
    lines: list[str],
    number: int,
) -> int:
    """The `if` line a Go test's failure call sits under, which holds the check the call only reports, or the call's own line where it sits under none."""
    above = next((before for before in range(number - 1, -1, -1) if lines[before].strip()), None)
    if above is not None and lines[above].strip().startswith("if ") and lines[above].rstrip().endswith("{"):
        return above

    return number


def rust_test_lines(
    lines: list[str],
) -> set[int]:
    """The lines of the items a `#[cfg(test)]` attribute stands on, a module's body or a function's, and none for an item that ends at its first `;`, such as `mod tests;`."""
    counted: set[int] = set()
    for number, line in enumerate(lines):
        if not RUST_TESTS.match(line):
            continue

        depth = 0
        opened = False
        for item in range(number + 1, len(lines)):
            bare = RUST_QUOTED.sub("", lines[item])
            if not opened and ";" in bare and ("{" not in bare or bare.index(";") < bare.index("{")):
                break

            depth += bare.count("{") - bare.count("}")
            opened = opened or "{" in bare
            counted.add(item)
            if opened and depth <= 0:
                break

    return counted


def snapshot_lines(
    lines: list[str],
) -> list[str]:
    """A snapshot's lines below its header block of two `---` lines, or the whole of it where it carries none."""
    fences = [number for number, line in enumerate(lines) if line.strip() == "---"]
    body = lines[fences[1] + 1 :] if len(fences) >= 2 and fences[0] == 0 else lines

    return [line.strip() for line in body if line.strip()]


def lost(
    relative: str,
    before: str,
    after: str,
) -> list[str]:
    """The assertions the text before holds that the text after does not, each as often as it is lost, in the order they stood."""
    left = Counter(assertions(relative=relative, text=after))
    gone: list[str] = []
    for line in assertions(relative=relative, text=before):
        if left[line]:
            left[line] -= 1
        else:
            gone.append(line)

    return gone


def path_of(
    brain: store.Brain,
) -> Path:
    return brain.root / FILE


def grant(
    brain: store.Brain,
    relative: str,
    hours: Optional[float] = None,
    until_text: Optional[str] = None,
    task: Optional[str] = None,
    at: Optional[datetime] = None,
) -> autoack.Grant:
    """Record the owner's word for one test file with its end, refused with no end, as the standing word is."""
    at = at or clock.now()
    if hours is None and until_text is None and task is None:
        raise autoack.AckError("the owner's word for a test file needs an end, a time with --for or --until, or a task with --until-done")

    given = autoack.grant_for(brain=brain, hours=hours, until_text=until_text, task=task, at=at)
    words = read(brain)
    words[relative] = given
    write(brain=brain, words=words)

    return given


def revoke(
    brain: store.Brain,
    relative: str,
) -> bool:
    words = read(brain)
    if words.pop(relative, None) is None:
        return False

    write(brain=brain, words=words)

    return True


def granted(
    brain: store.Brain,
    relative: str,
    at: Optional[datetime] = None,
) -> Optional[autoack.Grant]:
    """The owner's word for the file while it holds, by its time and its task, or None.

    A word whose task is done or gone is taken back for good, as the
    standing word is, so it never comes back when the task reopens or a
    new entry takes its id.
    """
    given = read(brain).get(relative)
    if given is None:
        return None

    if given.task is not None and autoack.task_state(brain=brain, key=given.task) in ("done", "gone"):
        revoke(brain=brain, relative=relative)
        return None

    return given if autoack.holds(brain=brain, grant=given, at=at or clock.now()) else None


def describe(
    brain: store.Brain,
    at: Optional[datetime] = None,
) -> list[str]:
    """One line per test file whose word holds, with what is left of it, or the one line that none does."""
    at = at or clock.now()
    lines = []
    for relative in sorted(read(brain)):
        given = granted(brain=brain, relative=relative, at=at)
        if given is None:
            continue

        if given.until is None:
            lines.append(f"{relative}, until {given.task} is done")
        else:
            lines.append(f"{relative}, {autoack.left(since=at, until=given.until)} left, until {autoack.when(at=at, moment=given.until)}")

    return lines or [NONE]


def read(
    brain: store.Brain,
) -> dict[str, autoack.Grant]:
    """The words recorded, by the test file's path from the project's root, a file that does not read as them read as none."""
    path = path_of(brain)
    if not store.readable_file(path):
        return {}

    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
        return {
            relative: autoack.Grant(
                since=autoack.moment_of(word["since"]),
                until=None if word.get("until") is None else autoack.moment_of(word["until"]),
                task=word.get("task"),
            )
            for relative, word in data.items()
        }
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError, RecursionError):
        return {}


def write(
    brain: store.Brain,
    words: dict[str, autoack.Grant],
) -> None:
    path = path_of(brain)
    if not words:
        path.unlink(missing_ok=True)
        return

    data = {
        relative: {
            "since": given.since.isoformat(),
            "until": given.until.isoformat() if given.until is not None else None,
            "task": given.task,
        }
        for relative, given in sorted(words.items())
    }
    frontmatter.write_text(path=str(path), text=json.dumps(data, indent=2) + "\n")
