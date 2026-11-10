"""The project's own linters, run by the post write hook on each file the agent writes.

The project's rules in .agents/rules/ name them under a heading named
Lint, in fenced blocks, one line each, a file pattern and then one
command whose word `{file}` stands for the file. Each command runs with
no shell, the file handed over as one absolute path, so no path can be
read as code or as an option. The hook hands back what the linters could
not fix, with one line when they rewrote the file, and never blocks the
write.
"""

import contextlib
import fnmatch
import functools
import itertools
import os
import re
import shlex
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from . import check, rules, sections, store

HEADING = "lint"
FILE = "{file}"
PER_COMMAND = 20.0
BUDGET = 40.0
# a line beside the fence that is all one code span, in a list item or not, is a lint line written in the wrong place
CODE_LINE = re.compile(r"^\s*(?:[-*+]|\d+[.)])?\s*`([^`]+)`\s*$")
LEFT_LINES = 30
# a POSIX shell reads a backslash as an escape, while Windows spells every path with one
ESCAPES = "" if os.name == "nt" else "\\"
# what cmd, which runs a batch file such as an npm shim, reads as code in a path it is handed, quoted or not
CMD_CODE = frozenset('&|<>^%!"')


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
    try:
        found = rules.texts(project / check.BRAIN_FOLDER)
    except rules.RuleUnreadable as error:
        return [], [f"{error}, so no rule's lint line runs"]

    # every rule's Lint headings count, the project's own rule first and the others by name
    read: list[tuple[list[str], list[str]]] = [written for written in (written_lines(text) for _, text in found) if written is not None]
    if not read:
        return [], []

    fenced = [line for lines, _ in read for line in lines]
    strays = [line for _, lines in read for line in lines]
    if not fenced and not strays:
        return [], [f"the Lint heading holds no lint line, so nothing is linted, and each goes in a fenced block as a file pattern then one command with {FILE}"]

    lines: list[Line] = []
    refused: list[str] = [f"the lint line '{raw}' sits outside a fenced block, so it is not run" for raw in strays]
    for raw in fenced:
        try:
            words = words_of(raw)
        except ValueError:
            refused.append(f"the lint line '{raw}' does not read as words, so it is not run")
            continue

        reason: Optional[str] = refusal(raw=raw, words=words)
        if reason:
            refused.append(f"the lint line '{raw}' is not run, {reason}")
            continue

        lines.append(Line(pattern=words[0], words=words[1:]))

    return lines, refused


def words_of(
    raw: str,
) -> tuple[str, ...]:
    """A lint line's words the way shlex.split reads them, quotes taken off, with a backslash kept as written where it spells the system's paths."""
    lexer = shlex.shlex(raw, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    lexer.escape = ESCAPES

    return tuple(lexer)


def written_lines(
    rule: str,
) -> Optional[tuple[list[str], list[str]]]:
    """The lines of the fenced blocks under a Lint heading of one rule, comments and blank lines aside, and the lines beside them that name the file, or None with no such heading."""
    blocks: sections.Blocks = sections.blocks_of(rule)
    found: Optional[tuple[list[str], list[str]]] = None
    for heading in blocks.headings:
        if heading_name(heading.text) != HEADING:
            continue

        fenced, strays = found or ([], [])
        stretch_end: int = next(
            (later.start for later in blocks.headings if later.start > heading.start and later.level <= heading.level),
            len(rule),
        )
        beside: list[str] = []
        at = heading.end
        for fence in blocks.fences:
            if heading.end <= fence.start < stretch_end:
                fenced += [line.strip() for line in fence.text.split("\n") if line.strip() and not line.strip().startswith("#")]
                beside.append(rule[at : fence.start])
                at = fence.end

        beside.append(rule[at:stretch_end])
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
    """Whether the line holds a shell operator outside quotes, which shlex's shell mode splits into a token of its own.

    The lexer keeps each quoted word's quotes, so a quoted operator is
    never a token of operators alone, and reads a # as text.
    """
    lexer = shlex.shlex(raw, posix=False, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
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
        if os.name == "nt":
            # Popen finds an .exe on the path alone, and npm installs a linter as a .cmd shim, which the path's extensions find
            command[0] = shutil.which(command[0]) or command[0]
            read_as_code: Optional[str] = next((character for character in str(target) if character in CMD_CODE), None)
            if read_as_code is not None and command[0].casefold().endswith((".cmd", ".bat")):
                result.notes.append(f"'{' '.join(line.words)}' was not run on this file, since {Path(command[0]).name} runs through cmd, which reads the {read_as_code} in its path as code")
                continue

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
    """Run one command in a process group of its own, so a timeout stops every process it started and none writes the file later.

    On Windows the group is a job object as well, which stops the whole
    tree at once, where taskkill takes a second and a half to start and
    a child the command started can write the file in that time.
    """
    options: dict = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    with subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **options) as process:
        job: Optional[int] = windows_job(process.pid) if os.name == "nt" else None
        try:
            out, err = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            stop_group(process, job=job)
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.communicate(timeout=1)
            raise
        finally:
            if job is not None:
                let_go(job)

    return subprocess.CompletedProcess(command, process.returncode, out, err)


EXTENDED_LIMITS = 9
KILL_ON_JOB_CLOSE = 0x2000
SET_QUOTA_AND_TERMINATE = 0x0100 | 0x0001


@functools.cache
def windows_api() -> tuple:
    """ctypes, Windows' kernel32 with the argument types a 64 bit handle needs, and the job's limits as Windows lays out JOBOBJECT_EXTENDED_LIMIT_INFORMATION.

    ctypes is imported here, on the Windows path alone, so a Python built
    without it, as one built without libffi is, still runs every hook.
    """
    import ctypes

    class BasicLimits(ctypes.Structure):
        _fields_ = [
            ("per_process_user_time", ctypes.c_int64),
            ("per_job_user_time", ctypes.c_int64),
            ("flags", ctypes.c_uint32),
            ("minimum_working_set", ctypes.c_size_t),
            ("maximum_working_set", ctypes.c_size_t),
            ("active_processes", ctypes.c_uint32),
            ("affinity", ctypes.c_size_t),
            ("priority_class", ctypes.c_uint32),
            ("scheduling_class", ctypes.c_uint32),
        ]

    class JobLimits(ctypes.Structure):
        _fields_ = [
            ("basic", BasicLimits),
            ("io", ctypes.c_uint64 * 6),
            ("process_memory", ctypes.c_size_t),
            ("job_memory", ctypes.c_size_t),
            ("peak_process_memory", ctypes.c_size_t),
            ("peak_job_memory", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = ctypes.c_void_p
    kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, ctypes.c_wchar_p)
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
    kernel32.SetInformationJobObject.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32)
    kernel32.AssignProcessToJobObject.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    kernel32.TerminateJobObject.argtypes = (ctypes.c_void_p, ctypes.c_uint)
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)

    return ctypes, kernel32, JobLimits


def windows_job(
    pid: int,
) -> Optional[int]:
    """A job object holding the process, and every process it starts from then on, that kills what is in it should the hook die first, or None where Windows makes or assigns none."""
    try:
        ctypes, kernel32, JobLimits = windows_api()
    except (AttributeError, ImportError, OSError):
        return None

    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return None

    limits = JobLimits()
    limits.basic.flags = KILL_ON_JOB_CLOSE
    process = kernel32.OpenProcess(SET_QUOTA_AND_TERMINATE, False, pid)
    held = bool(process) and bool(kernel32.SetInformationJobObject(job, EXTENDED_LIMITS, ctypes.byref(limits), ctypes.sizeof(limits))) and bool(kernel32.AssignProcessToJobObject(job, process))
    if process:
        kernel32.CloseHandle(process)
    if not held:
        kernel32.CloseHandle(job)
        return None

    return job


def let_go(
    job: int,
) -> None:
    """Close the job once the command is done, what it left running kept running as on POSIX, a daemon a linter starts among them."""
    ctypes, kernel32, JobLimits = windows_api()
    kernel32.SetInformationJobObject(job, EXTENDED_LIMITS, ctypes.byref(JobLimits()), ctypes.sizeof(JobLimits))
    kernel32.CloseHandle(job)


def stop_group(
    process: subprocess.Popen,
    job: Optional[int] = None,
) -> None:
    if os.name == "nt":
        if job is not None and windows_api()[1].TerminateJobObject(job, 1):
            return
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
