"""The gates, run as one command before a review and before a merge.

Section 0 of the project's AGENTS.md names the gates under each heading
whose text holds the word gates, one fenced bash, sh or zsh block per
gate, and this runs them in order under the shell each block names,
with errexit and, where the shell has it, pipefail, the way a CI step
runs them. It stops at the first red one and says which, then runs the
check over the tree and the branch's commits, and doctor over the
brain. The kit's own checkout names no gates in a section 0, since its
front door ships to every project, so there the gates are the tool's
own tests under the interpreter running this and under the system's
`/usr/bin/python3` where that is another one at the kit's floor or
above, which is what every commit to the kit runs green first.
"""

import os
import platform
import re
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from . import check, doctor, sections, store, upgrade

GATES_WORD = re.compile(
    pattern=r"\bgates\b",
    flags=re.IGNORECASE,
)
SET_LINE = re.compile(r"^set(?:[ \t]|$)")

# A link or an image, by an inline target or a reference label, which a
# heading shows by its text alone.
LINK = re.compile(r"!?\[([^\]]*)\](?:\([^)]*\)|\[[^\]]*\])")

# The shell an info string's first word picks, and the flags each runs a
# block under, the ones GitHub Actions gives a `shell: bash` step, so a
# failing line or a failing stage of a pipeline turns the gate red as it
# would in CI. POSIX sh has no pipefail.
SHELLS: dict[str, str] = {
    "": "bash",
    "bash": "bash",
    "shell": "bash",
    "sh": "sh",
    "zsh": "zsh",
}
SHELL_FLAGS: dict[str, tuple[str, ...]] = {
    "bash": ("--noprofile", "--norc", "-eo", "pipefail", "-c"),
    "sh": ("-e", "-c"),
    "zsh": ("--no-rcs", "-e", "-o", "pipefail", "-c"),
}
POSIX = os.name == "posix"
WINDOWS = os.name == "nt"
GATE_SHAPE = "a gate is a fenced bash, sh or zsh block under it, one block per gate"
NO_GATES = "section 0 names no gates under a Gates heading, so the check and doctor are the gates here"

# The system interpreter on a Mac or a Linux box, the second one the
# kit's own tests run under where it answers at the floor the kit holds
# to and is not the one running this. On a Mac it is a shim that hands
# over to the developer tools' interpreter, so it is asked which one it
# is rather than judged by its own path.
FLOOR = Path("/usr/bin/python3")
FLOOR_VERSION = "3.9"
PROBE = "import platform, sys; print(sys.executable); print(sys.version_info >= (3, 9)); print(platform.python_version())"
SCRIPTS = Path(check.BRAIN_FOLDER) / "skills" / "agent-brain" / "scripts"
SUITE = ("-m", "unittest", "discover", "-s", "tests", "-t", ".")


class GatesError(Exception):
    """The gates could not be read or built, so no gate ran, with the reason in the message."""


@dataclass(frozen=True)
class Gate:
    """One gate: its command, the folder it runs in, the one line that names it, and the shell its block runs under, or the argument list it runs as with no shell, which the kit's own gates are."""

    command: str
    cwd: Path
    name: str
    shell: str = "bash"
    argv: tuple[str, ...] = ()


@dataclass(frozen=True)
class Named:
    """What a project names: its gates in order, a line for each thing that does not run, and a line for each Gates heading that holds no gate."""

    gates: list[Gate] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    empty: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Answer:
    """What the floor's interpreter says of itself: the path it runs from, whether it is at the kit's floor, and its version."""

    path: str
    at_floor: bool
    version: str


Runner = Callable[[Gate], int]


def run(
    project: Path,
    brain: store.Brain,
    runner: Optional[Runner] = None,
    out: Optional[Callable[[str], None]] = None,
) -> int:
    """Every gate in order, then the check, then doctor.

    0 when all are green, the store's REFUSED at the first red gate or
    where the gates cannot be read, its FINDINGS_REMAIN while a Gates
    heading holds no gate or the check or doctor has findings.
    """
    say = out or print
    runs = runner or run_gate
    try:
        named = gates_of(project)
    except GatesError as error:
        say(str(error))
        return store.REFUSED

    for line in named.notes + named.empty:
        say(line)

    total = len(named.gates)
    for number, gate in enumerate(
        named.gates,
        start=1,
    ):
        say(f"gate {number} of {total}, {gate.name}")
        code = runs(gate)
        if code != 0:
            say(f"gate {number} of {total} is red, {gate.name}, {ending(code)}, and the rest did not run")
            return store.REFUSED

    slips, notes = check_lines(project)
    for line in notes + slips:
        say(line)
    say("check clean" if not slips else f"check {len(slips)} findings")

    findings = doctor.run(brain=brain)
    for finding in findings:
        say(finding.line())
    say("doctor clean" if not findings else f"doctor {len(findings)} findings")

    return store.FINDINGS_REMAIN if named.empty or slips or findings else 0


def ending(
    code: int,
) -> str:
    """How a red gate ended, by its exit code, or by the signal that killed it, which a subprocess gives as the code's negative."""
    if code >= 0:
        return f"exit {code}"

    try:
        return f"killed by {signal.Signals(-code).name}"
    except ValueError:
        return f"killed by signal {-code}"


def check_lines(
    project: Path,
) -> tuple[list[str], list[str]]:
    """The check's slips over the tree and the branch's commits, a line each, each a finding, and its notes, none a finding, or the one line on why the check could not list the tree, which counts as a finding."""
    try:
        checked = check.run(project=project)
    except check.CheckError as error:
        return [f"the check could not run, {error}"], []

    return [slip.text() for slip in checked.slips], checked.notes


def gates_of(
    project: Path,
) -> Named:
    """The gates the project names, the kit's own tests first in the kit's checkout, then section 0's, with the lines on what does not run."""
    zero = section_gates(project)
    if check.is_kit_checkout(project):
        own = kit_gates(project)

        return Named(
            gates=own.gates + zero.gates,
            notes=own.notes + zero.notes,
            empty=zero.empty,
        )

    # every Gates heading gives a gate or a line that it holds none, so with neither section 0 has no such heading
    if not zero.gates and not zero.empty:
        return Named(notes=[NO_GATES])

    return zero


def kit_gates(
    project: Path,
) -> Named:
    """The tool's tests as an argument list, under the interpreter running this, then under the floor's where it answers at the floor or above and is another one, with a line where it is below the floor."""
    if not sys.executable:
        raise GatesError("the interpreter running this gives no path of its own in sys.executable, so the tool's tests have nothing to run under, and no gate ran")

    interpreters = [(sys.executable, platform.python_version())]
    notes: list[str] = []
    answer = floor_answer()
    if answer is not None and not same_interpreter(
        one=Path(answer.path),
        other=Path(sys.executable),
    ):
        if answer.at_floor:
            interpreters.append((str(FLOOR), answer.version))
        else:
            notes.append(f"{FLOOR} is Python {answer.version}, below the kit's floor of {FLOOR_VERSION}, so the tool's tests do not run under it")

    gates = [
        Gate(
            command=" ".join([interpreter, *SUITE]),
            cwd=project / SCRIPTS,
            name=f"the tool's tests under {interpreter}, Python {version}",
            argv=(interpreter, *SUITE),
        )
        for interpreter, version in interpreters
    ]

    return Named(
        gates=gates,
        notes=notes,
    )


def floor_answer() -> Optional[Answer]:
    """What the floor's interpreter says of itself, or None where it is not there or does not answer, as a Mac's stub does with no developer tools."""
    if not store.quietly(FLOOR.is_file):
        return None

    try:
        answered = subprocess.run(
            args=[str(FLOOR), "-c", PROBE],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None

    lines = answered.stdout.splitlines()
    if answered.returncode != 0 or len(lines) != 3 or lines[1] not in ("True", "False"):
        return None

    return Answer(
        path=lines[0],
        at_floor=lines[1] == "True",
        version=lines[2],
    )


def same_interpreter(
    one: Path,
    other: Path,
) -> bool:
    try:
        return one.resolve() == other.resolve()
    except (OSError, RuntimeError):
        return False


def section_gates(
    project: Path,
) -> Named:
    """The gates under each Gates heading of section 0 in AGENTS.md, in order, with a line for each block no gate runs and one for each heading that holds no gate.

    A heading or a block inside code or an HTML comment is neither, a
    heading holds the word gates only in the text it shows, and each
    Gates heading runs to the next heading at its level or above, or to
    the end of section 0.
    """
    door = project / "AGENTS.md"
    if not store.readable_file(door):
        return Named()

    try:
        text = door.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        raise GatesError(f"AGENTS.md cannot be read, {store.explain(error)}, so no gate ran") from error

    zero = upgrade.section_zero_in(text)
    if zero is None:
        return Named()

    blocks = sections.blocks_of(zero)

    taken: list[sections.Fence] = []
    empty: list[str] = []
    for heading in blocks.headings:
        if not GATES_WORD.search(shown(heading.text)):
            continue

        end = next((later.start for later in blocks.headings if later.start > heading.start and later.level <= heading.level), len(zero))
        under = [fence for fence in blocks.fences if heading.end <= fence.start < end]
        if not any(shell_of(fence) is not None and commands_of(fence) for fence in under):
            empty.append(f"the heading {heading.text} holds no gate, and {GATE_SHAPE}")

        taken += [fence for fence in under if fence not in taken]

    gates: list[Gate] = []
    notes: list[str] = []
    for fence in sorted(
        taken,
        key=lambda fence: fence.start,
    ):
        shell = shell_of(fence)
        commands = commands_of(fence)
        first = next((line.strip() for line in fence.text.split("\n") if line.strip()), "")
        if shell is None:
            notes.append(
                not_run(
                    what=f"a {fence.info.split()[0]} block",
                    first=first,
                ),
            )
            continue

        if not commands:
            notes.append(
                not_run(
                    what="a block of nothing but comments" if first else "an empty block",
                    first=first,
                ),
            )
            continue

        gates.append(
            Gate(
                command=fence.text.strip(),
                cwd=project,
                name=next((line for line in commands if not SET_LINE.match(line)), commands[0]),
                shell=shell,
            ),
        )

    return Named(
        gates=gates,
        notes=notes,
        empty=empty,
    )


def shown(
    text: str,
) -> str:
    """The heading's text as markdown shows it, with no HTML comment and no tag, and a link or an image by its text alone, so a word in a comment, an attribute or a link's target never makes a Gates heading."""
    bare = sections.blanked(
        text=text,
        spans=sections.comment_spans(text),
    )
    kept: list[str] = []
    cursor = 0
    for start, end in sections.code_spans(bare):
        kept.append(unlinked(bare[cursor:start]))
        kept.append(bare[start:end])
        cursor = end
    kept.append(unlinked(bare[cursor:]))

    return "".join(kept)


def unlinked(
    text: str,
) -> str:
    """The text with each link and image by its text alone and no HTML tag."""
    return check.TAG.sub(
        repl="",
        string=LINK.sub(
            repl=r"\1",
            string=text,
        ),
    )


def shell_of(
    fence: sections.Fence,
) -> Optional[str]:
    """The shell the block's info string picks by its first word, without regard to case, or None for a block of another language."""
    words = fence.info.split()

    return SHELLS.get(words[0].lower() if words else "")


def commands_of(
    fence: sections.Fence,
) -> list[str]:
    """The block's lines that are neither blank nor a comment, each stripped."""
    return [line.strip() for line in fence.text.split("\n") if line.strip() and not line.strip().startswith("#")]


def not_run(
    what: str,
    first: str,
) -> str:
    """The one line that names a block no gate runs, with its first line where it has one."""
    said = f"{what} is not a gate and does not run"

    return f"{said}, {first}" if first else said


def run_gate(
    gate: Gate,
) -> int:
    """Run one gate in its folder with its output passed straight through, and hand back its exit code, negative where a signal killed it."""
    argv = list(gate.argv) or shell_line(gate)

    # the gate writes to this process's streams straight, and stderr writes the complaint's line at once, so the name line the caller printed leaves the buffer first
    sys.stdout.flush()
    sys.stderr.flush()
    if not argv:
        print(
            f"this gate is a {gate.shell} block and no {gate.shell} is on the path, so it needs one to run",
            file=sys.stderr,
        )
        return 1

    try:
        completed = subprocess.run(
            args=argv,
            cwd=str(gate.cwd),
            check=False,
        )
    except OSError as error:
        print(
            store.explain(error),
            file=sys.stderr,
        )
        return 1

    return completed.returncode


def shell_line(
    gate: Gate,
) -> list[str]:
    """The argument list that runs the gate's block under its shell, under sh where a bash gate on a POSIX machine finds no bash, said in one line, or nothing where its shell is not on the path."""
    found = shell_path(gate.shell)
    if found is not None:
        return [found, *SHELL_FLAGS[gate.shell], gate.command]

    fallback = shell_path("sh") if gate.shell == "bash" and POSIX else None
    if fallback is None:
        return []

    print("bash is not on the path, so this gate runs under sh -e")

    return [fallback, *SHELL_FLAGS["sh"], gate.command]


def shell_path(
    name: str,
) -> Optional[str]:
    """Where the shell is on the path, on Windows a bash under the Windows folder passed over, since that is the WSL launcher, which runs a gate inside a Linux distribution or fails where none is installed."""
    if not WINDOWS:
        return shutil.which(name)

    system = os.path.normcase(
        os.environ.get(
            key="SystemRoot",
            default="C:\\Windows",
        ),
    )
    for folder in os.environ.get(
        key="PATH",
        default="",
    ).split(os.pathsep):
        found = (
            shutil.which(
                cmd=name,
                path=folder,
            )
            if folder
            else None
        )
        if found is not None and not os.path.normcase(os.path.abspath(found)).startswith(system + os.sep):
            return found

    return None


def is_tty() -> bool:
    """Whether the gates print to a person, for a caller that wants to say more then."""
    return os.isatty(sys.stdout.fileno()) if hasattr(sys.stdout, "fileno") else False
