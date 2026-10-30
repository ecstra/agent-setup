"""The project's own linters, run by the post write hook on each file the agent writes.

Section 0 of AGENTS.md names them under a heading named Lint, in fenced
blocks, one line each: a file pattern, then one command whose word
`{file}` stands for the file. Each command runs with no shell, the file
handed over as one absolute path, so no path can be read as code or as
an option. The hook hands back what the linters could not fix, with one
line when they rewrote the file, and never blocks the write.
"""

import fnmatch
import shlex
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
SHELL_WORDS = frozenset(("&&", "||", ";", "|", ">", ">>", "<", "&"))
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

    lines: list[Line] = []
    refused: list[str] = []
    for raw in written_lines(zero):
        try:
            words = tuple(shlex.split(raw))
        except ValueError:
            refused.append(f"the lint line '{raw}' does not read as words, so it is not run")
            continue

        reason: Optional[str] = refusal(words)
        if reason:
            refused.append(f"the lint line '{raw}' is not run, {reason}")
            continue

        lines.append(Line(pattern=words[0], words=words[1:]))

    return lines, refused


def written_lines(
    zero: str,
) -> list[str]:
    """Every line of the fenced blocks under a Lint heading of section 0, comments and blank lines aside."""
    blocks: sections.Blocks = sections.blocks_of(zero)
    found: list[str] = []
    for heading in blocks.headings:
        if heading_name(heading.text) != HEADING:
            continue

        stretch_end: int = next(
            (later.start for later in blocks.headings if later.start > heading.start and later.level <= heading.level),
            len(zero),
        )
        for fence in blocks.fences:
            if heading.end <= fence.start < stretch_end:
                found += [line.strip() for line in fence.text.split("\n") if line.strip() and not line.strip().startswith("#")]

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
    words: tuple[str, ...],
) -> Optional[str]:
    """Why a line cannot run as one command with the file as one argument, or None."""
    if len(words) < 2:
        return "a line is a file pattern then a command"

    command = words[1:]
    if any(word in SHELL_WORDS for word in command) or "=" in command[0]:
        return "one command per line, with no shell, so write each command on a line of its own"

    if FILE not in command:
        return f"the command needs the word {FILE} where the file goes"

    return None


def matches(
    pattern: str,
    relative: str,
) -> bool:
    """Whether the file's path from the project matches, a pattern with no slash matching the file's name."""
    if "/" in pattern:
        return fnmatch.fnmatchcase(relative, pattern)

    return fnmatch.fnmatchcase(relative.rsplit("/", 1)[-1], pattern)


def run(
    project: Path,
    path: Path,
    per_command: float = PER_COMMAND,
    budget: float = BUDGET,
) -> Linted:
    """Run every lint line that matches the file, in order, each stopped after its time, the whole stopped once the budget is spent."""
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
    started = time.monotonic()
    for line in matching:
        spent = time.monotonic() - started
        if spent >= budget:
            result.notes.append(f"the lint budget of {budget:g} seconds ran out, so '{' '.join(line.words)}' did not run")
            break

        command = [str(target) if word == FILE else word for word in line.words]
        try:
            done = subprocess.run(
                command,
                cwd=project,
                capture_output=True,
                timeout=min(per_command, budget - spent),
                check=False,
            )
        except FileNotFoundError:
            result.notes.append(f"{command[0]} is not installed, so {line.pattern} files are not linted with it")
            continue
        except subprocess.TimeoutExpired:
            result.notes.append(f"'{' '.join(line.words)}' was stopped after {min(per_command, budget - spent):g} seconds")
            continue
        except OSError as error:
            result.notes.append(f"'{' '.join(line.words)}' could not run, {store.explain(error)}")
            continue

        if done.returncode != 0:
            said = (done.stdout + done.stderr).decode("utf-8", errors="replace").strip().split("\n")
            result.left.append(f"{' '.join(line.words)}\n" + "\n".join(said[:LEFT_LINES]))

    result.rewrote = read_bytes(target) != before

    return result


def read_bytes(
    path: Path,
) -> bytes:
    try:
        return path.read_bytes()
    except OSError:
        return b""
