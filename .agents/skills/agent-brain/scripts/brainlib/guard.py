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
# a Rust test module of another name is known by its tests' attributes, and a lone test.py or test.rs is as often a test command's code
TEST_NAME = re.compile(
    r"(?:^test_.+\.py$|_test\.(?:py|go|dart|rb)$|^tests\.(?:py|rs)$|_tests\.rs$|\.(?:test|spec)\.(?:js|jsx|ts|tsx|mjs|cjs)$|(?:Test|Tests)\.(?:java|kt|kts|swift)$|_spec\.rb$)",
)

# how each language writes a check, read off a line with its indent taken off
CHECKS = {
    ".rs": re.compile(r"\b(?:prop_|debug_)?assert\w*!|#\[should_panic|\.assert\(\)"),
    ".py": re.compile(r"^assert\b|\.assert\w*\(|\bpytest\.raises\b|\bself\.fail\("),
    ".go": re.compile(r"\bt\.(?:Error|Errorf|Fatal|Fatalf|Fail|FailNow)\(|\b(?:assert|require)\.\w+\("),
    ".swift": re.compile(r"\bXCTAssert\w*\(|\bXCTFail\(|#expect\(|#require\("),
    ".java": re.compile(r"\bassert\w*\(|\bfail\("),
    # a bare should is a check where a matcher follows, never shoulda's `should "..." do`, which names an example
    ".rb": re.compile(r"\bexpect\b|\bassert\w*\b|\bmust_\w+|\.should(?:_not)?\b|\bshould(?:_not)?(?:\(|\s+(?!do\b)\w)"),
}
SCRIPT_CHECK = re.compile(r"\bexpect(?:Later)?\s*\(|\bassert\w*[.(]|\.should\b")
for suffix in (".dart", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
    CHECKS[suffix] = SCRIPT_CHECK
CHECKS[".kt"] = CHECKS[".kts"] = CHECKS[".java"]

# the attributes a Rust test item stands under, its module's and a test function's own, `#[tokio::test]` among them
RUST_TESTS = re.compile(r"^\s*#\[(?:cfg\(test\)|(?:[A-Za-z_]\w*::)*test(?:\([^\]]*\))?)\]")
GO_FAILS = re.compile(r"\bt\.(?:Error|Errorf|Fatal|Fatalf|Fail|FailNow)\(")
GO_IF = re.compile(r"^(?:\}\s*else\s+)?if\s.*\{$")
# a Ruby block or keyword opener, at a line's end or its start, and the end that closes one, read off a line with its indent taken off
RUBY_OPENS = re.compile(r"\bdo(?:\s*\|[^|]*\|)?$|^(?:if|unless|case|begin|while|until|for|def|class|module)\b")
RUBY_CLOSES = re.compile(r"^end\b")
# the one Ruby check whose expected value follows its block, RSpec's `expect do ... end.to`, where an assert_raises says it on its first line
RUBY_EXPECT_BLOCK = re.compile(r"\bexpect\s+do\b")
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

    A Rust file that is no test file by its name or folder holds its
    tests in the items a test attribute stands on, `#[cfg(test)]` or a
    test function's own, so only the lines of those count, and a check
    elsewhere is the code's. A snapshot is an assertion whole, every
    line of it below its header.
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

    quoted = RUST_QUOTED if path.suffix == ".rs" else QUOTED
    held: list[str] = []
    number = 0
    while number < len(lines):
        line = lines[number].strip()
        # a check's word inside a string, such as an example named "should add", is no check
        if number not in counted or not line or not check.search(quoted.sub("", line)):
            number += 1
            continue

        end = statement_end(lines=lines, start=number, suffix=path.suffix)
        parts = lines[number : end + 1]
        if path.suffix == ".go" and GO_FAILS.search(line):
            parts = go_check_lines(lines=lines, number=number) + parts
        held.append(" ".join(part.strip() for part in parts if part.strip()))
        number = end + 1

    return held


def depth_of(
    line: str,
    suffix: str,
    blocks: bool,
) -> int:
    """How many brackets a line leaves open, its strings taken out first, negative where it closes more than it opens, and Ruby's blocks too where they count."""
    bare = (RUST_QUOTED if suffix == ".rs" else QUOTED).sub("", line)
    depth = sum(bare.count(bracket) for bracket in OPENS) - sum(bare.count(bracket) for bracket in CLOSES)
    if blocks:
        stripped = bare.strip()
        depth += (RUBY_OPENS.search(stripped) is not None) - (RUBY_CLOSES.match(stripped) is not None)

    return depth


def statement_end(
    lines: list[str],
    start: int,
    suffix: str,
) -> int:
    """The last line of the check that opens at `start`, which runs on while a bracket or an `expect do` block stays open, the line ends in a `\\`, or the next line goes on with a method call."""
    blocks = suffix == ".rb" and RUBY_EXPECT_BLOCK.search(QUOTED.sub("", lines[start])) is not None
    depth = 0
    number = start
    while number < len(lines) and number - start < LONGEST:
        depth += depth_of(line=lines[number], suffix=suffix, blocks=blocks)
        following = next((line.strip() for line in lines[number + 1 :] if line.strip()), "")
        if depth <= 0 and not following.startswith(".") and not lines[number].rstrip().endswith("\\"):
            return number

        number += 1

    return min(number, len(lines) - 1)


def go_check_lines(
    lines: list[str],
    number: int,
) -> list[str]:
    """The `if` line of the block a Go test's failure call sits in, which holds the check the call only reports, or none where the block opens on another line.

    The block's line is the nearest above with less indent than the call,
    so a comment or a `t.Logf` between the two is no part of the check.
    """
    call = lines[number]
    indent = len(call) - len(call.lstrip())
    for above in range(number - 1, -1, -1):
        text = lines[above]
        if not text.strip() or len(text) - len(text.lstrip()) >= indent:
            continue

        return [text] if GO_IF.match(text.strip()) else []

    return []


def rust_test_lines(
    lines: list[str],
) -> set[int]:
    """The lines of the item each test attribute stands on, a module's body or a function's, from the attribute's own line.

    An item ends at its last brace, or at a `;` outside any bracket before
    its first brace, so `mod tests;` and `use` count for nothing while a
    header such as `fn check(bytes: [u8; 4])` runs on to its body.
    """
    counted: set[int] = set()
    for number, line in enumerate(lines):
        attribute = RUST_TESTS.match(line)
        if attribute is None:
            continue

        braces = 0
        brackets = 0
        opened = False
        ended = False
        spans: set[int] = set()
        for item in range(number, len(lines)):
            text = lines[item][attribute.end() :] if item == number else lines[item]
            spans.add(item)
            for character in RUST_QUOTED.sub("", text):
                if character in "([":
                    brackets += 1
                elif character in ")]":
                    brackets -= 1
                elif character == "{":
                    braces += 1
                    opened = True
                elif character == "}":
                    braces -= 1
                elif character == ";" and not opened and brackets <= 0:
                    ended = True

                if ended or (opened and braces <= 0):
                    break

            if ended or (opened and braces <= 0):
                break

        if not ended:
            counted |= spans

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
    new entry takes its id. A brain that cannot be written right now
    keeps the file, which the next read tries again, and the word is off
    either way.
    """
    given = read(brain).get(relative)
    if given is None:
        return None

    if given.task is not None and autoack.task_state(brain=brain, key=given.task) in ("done", "gone"):
        try:
            revoke(brain=brain, relative=relative)
        except OSError:
            pass
        return None

    return given if autoack.holds(brain=brain, grant=given, at=at or clock.now()) else None


def sweep(
    brain: store.Brain,
) -> None:
    """Take back each word whose task has ended, which every tick runs so a task done then reopened between two writes never gives a word back."""
    for relative in read(brain):
        granted(brain=brain, relative=relative)


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
