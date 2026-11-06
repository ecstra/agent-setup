"""The guard on test assertions, which keeps an agent from weakening a test it was handed, in every language.

An assertion already written in a test file is the spec's word on what
the code must do, so the pre write hook refuses a write that changes or
removes one unless the owner's word for that file holds, given with an
end like the standing word and kept beside it, in a dotted file of the
brain that git ignores. An assertion added, moved or reindented passes,
and so does the code under test. A line of a test is held by the way
its language writes a check, and a check that spans lines is held by
its first line, a named limit.
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
TEST_FOLDERS = {"tests", "test", "__tests__", "spec", "specs"}
TEST_NAME = re.compile(
    r"(?:^test_.+\.py$|_test\.(?:py|go|dart|rb)$|\.(?:test|spec)\.(?:js|jsx|ts|tsx|mjs|cjs)$|(?:Test|Tests)\.(?:java|kt|kts|swift)$|_spec\.rb$)",
)

# how each language writes a check, read off a line with its indent taken off
CHECKS = {
    ".rs": re.compile(r"\b(?:assert\w*|debug_assert\w*|insta::assert\w*)!|#\[should_panic"),
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


def is_test_file(
    relative: str,
) -> bool:
    """Whether the path is a test file by its name or by a folder of tests it sits in, or a snapshot."""
    path = PurePosixPath(relative)
    if path.suffix == ".snap":
        return True

    if path.suffix not in CODE:
        return False

    return TEST_NAME.search(path.name) is not None or any(part in TEST_FOLDERS for part in path.parts[:-1])


def assertions(
    relative: str,
    text: str,
) -> list[str]:
    """The lines of a test file the guard holds as its assertions, each with its indent taken off, in the order they stand.

    A Rust file outside a folder of tests holds its own tests below its
    `#[cfg(test)]` line, so only the lines from there on count, and a
    check above it is the code's. A snapshot is an assertion whole, every
    line of it below its header.
    """
    path = PurePosixPath(relative)
    lines = text.replace("\r\n", "\n").split("\n")
    if path.suffix == ".snap":
        return snapshot_lines(lines)

    if path.suffix == ".rs" and not is_test_file(relative):
        start = next((number for number, line in enumerate(lines) if RUST_TESTS.match(line)), None)
        if start is None:
            return []

        lines = lines[start:]
    elif not is_test_file(relative):
        return []

    check = CHECKS.get(path.suffix)
    if check is None:
        return []

    return [line.strip() for line in lines if line.strip() and check.search(line.strip())]


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
    """The owner's word for the file while it holds, by its time and its task, or None."""
    given = read(brain).get(relative)
    if given is None:
        return None

    return given if autoack.holds(brain=brain, grant=given, at=at or clock.now()) else None


def describe(
    brain: store.Brain,
    at: Optional[datetime] = None,
) -> list[str]:
    """One line per test file whose word holds, with what is left of it, or the one line that none does."""
    at = at or clock.now()
    lines = []
    for relative, given in sorted(read(brain).items()):
        if not autoack.holds(brain=brain, grant=given, at=at):
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
