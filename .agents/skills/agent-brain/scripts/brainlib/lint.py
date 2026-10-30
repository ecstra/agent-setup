"""The project's own linters, run by the post write hook on each file the agent writes.

Section 0 of AGENTS.md names them under a heading named Lint, in fenced
blocks, one line each: a file pattern, then one command whose word
`{file}` stands for the file. Each command runs with no shell, the file
handed over as one absolute path, so no path can be read as code or as
an option. The hook hands back what the linters could not fix, with one
line when they rewrote the file, and never blocks the write.
"""

import contextlib
import fnmatch
import itertools
import os
import re
import shlex
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from . import check, sections, store, upgrade

HEADING = "lint"
FILE = "{file}"
PER_COMMAND = 20.0
BUDGET = 40.0
# a line beside the fence that is all one code span, in a list item or not, is a lint line written in the wrong place
CODE_LINE = re.compile(r"^\s*(?:[-*+]|\d+[.)])?\s*`([^`]+)`\s*$")
LEFT_LINES = 30

# the kit's own checkout lints the tool's Python with ruff, from the config beside the scripts
KIT_LINES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("*.py", ("ruff", "format", FILE)),
    ("*.py", ("ruff", "check", "--fix", FILE)),
)


@dataclass(frozen=True)
class Line:
    """One lint line: the file pattern and the command's words."""

    pattern: str
    words: tuple[str, ...]


@dataclass
class Linted:
    """What the linters left for the agent, what they could not run, and whether they rewrote the file."""

    left: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    rewrote: bool = False


def lines_of(
    project: Path,
) -> tuple[list[Line], list[str]]:
    """The lint lines the project names, and a reason for each line refused."""
    if check.is_kit_checkout(project):
        return [Line(pattern=pattern, words=words) for pattern, words in KIT_LINES], []

    door = project / "AGENTS.md"
    if not store.readable_file(door):
        return [], []

    try:
        text = door.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return [], []

    zero: Optional[str] = upgrade.section_zero_in(text)
    if zero is None:
        return [], []

    written: Optional[tuple[list[str], list[str]]] = written_lines(zero)
    if written is None:
        return [], []

    fenced, strays = written
    if not fenced and not strays:
        return [], [f"the Lint heading holds no lint line, so nothing is linted, and each goes in a fenced block as a file pattern then one command with {FILE}"]

    lines: list[Line] = []
    refused: list[str] = [f"the lint line '{raw}' sits outside a fenced block, so it is not run" for raw in strays]
    for raw in fenced:
        try:
            words = tuple(shlex.split(raw))
        except ValueError:
            refused.append(f"the lint line '{raw}' does not read as words, so it is not run")
            continue

        reason: Optional[str] = refusal(raw=raw, words=words)
        if reason:
            refused.append(f"the lint line '{raw}' is not run, {reason}")
            continue

        lines.append(Line(pattern=words[0], words=words[1:]))

    return lines, refused


def written_lines(
    zero: str,
) -> Optional[tuple[list[str], list[str]]]:
    """The lines of the fenced blocks under a Lint heading of section 0, comments and blank lines aside, and the lines beside them that name the file, or None with no such heading."""
    blocks: sections.Blocks = sections.blocks_of(zero)
    found: Optional[tuple[list[str], list[str]]] = None
    for heading in blocks.headings:
        if heading_name(heading.text) != HEADING:
            continue

        fenced, strays = found or ([], [])
        stretch_end: int = next(
            (later.start for later in blocks.headings if later.start > heading.start and later.level <= heading.level),
            len(zero),
        )
        beside: list[str] = []
        at = heading.end
        for fence in blocks.fences:
            if heading.end <= fence.start < stretch_end:
                fenced += [line.strip() for line in fence.text.split("\n") if line.strip() and not line.strip().startswith("#")]
                beside.append(zero[at : fence.start])
                at = fence.end

        beside.append(zero[at:stretch_end])
        spans = [CODE_LINE.match(line) for line in "".join(beside).split("\n")]
        strays += [span.group(1).strip() for span in spans if span and FILE in span.group(1)]
        found = (fenced, strays)

    return found


def heading_name(
    text: str,
) -> str:
    """A heading's text without a leading number such as 0.2 and a closing colon, in lower case."""
    words = text.strip().rstrip(":").split()
    if words and all(part.isdigit() for part in words[0].rstrip(".").split(".")):
        words = words[1:]

    return " ".join(words).lower()


def refusal(
    raw: str,
    words: tuple[str, ...],
) -> Optional[str]:
    """Why a line cannot run as one command with the file as one argument, or None."""
    if len(words) < 2:
        return "a line is a file pattern then a command"

    command = words[1:]
    if unquoted_shell(raw) or "=" in command[0]:
        return "one command per line, with no shell, so write each command on a line of its own"

    if FILE not in command:
        return f"the command needs the word {FILE} where the file goes"

    return None


def unquoted_shell(
    raw: str,
) -> bool:
    """Whether the line holds a shell operator outside quotes, which shlex's shell mode splits into a token of its own."""
    lexer = shlex.shlex(raw, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return any(token and set(token) <= set(lexer.punctuation_chars) for token in lexer)
    except ValueError:
        return False


def matches(
    pattern: str,
    relative: str,
) -> bool:
    """Whether the file's path from the project matches, a pattern with no slash matching the file's name and `**/` matching no folder too."""
    if "/" in pattern:
        parts = pattern.split("**/")
        forms = {"".join(part + kept for part, kept in zip(parts, choice + ("",))) for choice in itertools.product(("**/", ""), repeat=len(parts) - 1)}
        return any(fnmatch.fnmatchcase(relative, form) for form in forms)

    return fnmatch.fnmatchcase(relative.rsplit("/", 1)[-1], pattern)


def run(
    project: Path,
    path: Path,
    per_command: float = PER_COMMAND,
    budget: float = BUDGET,
    deadline: Optional[float] = None,
) -> Linted:
    """Run every lint line that matches the file, in order, each stopped after its time, the whole stopped once the budget is spent.

    A hook that lints several files passes one `deadline` on the
    monotonic clock, so the budget covers the whole write.
    """
    result = Linted()
    lines, refused = lines_of(project)
    result.notes += refused

    try:
        target = path.resolve()
        relative = target.relative_to(project.resolve()).as_posix()
    except (OSError, RuntimeError, ValueError):
        return result

    matching = [line for line in lines if matches(pattern=line.pattern, relative=relative)]
    if not matching:
        return result

    before: bytes = read_bytes(target)
    ends = deadline if deadline is not None else time.monotonic() + budget
    for line in matching:
        left = ends - time.monotonic()
        if left <= 0:
            result.notes.append(f"the lint budget of {budget:g} seconds ran out, so '{' '.join(line.words)}' did not run")
            break

        command = [str(target) if word == FILE else word for word in line.words]
        try:
            done = run_alone(
                command=command,
                cwd=project,
                timeout=min(per_command, left),
            )
        except FileNotFoundError:
            result.notes.append(f"{command[0]} is not installed, so {line.pattern} files are not linted with it")
            continue
        except subprocess.TimeoutExpired:
            result.notes.append(f"'{' '.join(line.words)}' was stopped after {min(per_command, left):g} seconds")
            continue
        except OSError as error:
            result.notes.append(f"'{' '.join(line.words)}' could not run, {store.explain(error)}")
            continue

        if done.returncode != 0:
            said = (done.stdout + done.stderr).decode("utf-8", errors="replace").strip().split("\n")
            result.left.append(f"{' '.join(line.words)}\n" + "\n".join(said[:LEFT_LINES]))

    result.rewrote = read_bytes(target) != before

    return result


def run_alone(
    command: list[str],
    cwd: Path,
    timeout: float,
) -> subprocess.CompletedProcess:
    """Run one command in a process group of its own, so a timeout stops every process it started and none writes the file later."""
    options: dict = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    with subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **options) as process:
        try:
            out, err = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            stop_group(process)
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.communicate(timeout=1)
            raise

    return subprocess.CompletedProcess(command, process.returncode, out, err)


def stop_group(
    process: subprocess.Popen,
) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True, check=False)
        return

    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(process.pid, signal.SIGKILL)


def read_bytes(
    path: Path,
) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        return b""
