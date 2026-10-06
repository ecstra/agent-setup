"""The gates, run as one command before a review and before a merge.

Section 0 of the project's AGENTS.md names the gates under a heading
that reads Gates, one fenced block per gate, and this runs them in
order, stops at the first red one and says which, then runs the check
over the tracked tree and doctor over the brain. The kit's own checkout
names no gates in a section 0, since its front door ships to every
project, so there the gates are the tool's own tests under each
interpreter the machine keeps, which is what every commit to the kit
runs green first.
"""

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import check, doctor, sections, store, upgrade

GATES_HEADING = re.compile(r"^(#{1,6})[ \t]+gates[ \t]*$", re.IGNORECASE | re.MULTILINE)
FENCE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})([^\n]*)\n(.*?)^[ \t]{0,3}\1[ \t]*$", re.DOTALL | re.MULTILINE)
SHELLS = ("bash", "sh", "shell", "zsh", "")

# The system interpreter on a Mac or a Linux box, which is the floor
# the kit holds to, and the second interpreter the kit's own tests run
# under when it is there and is not the one running this.
FLOOR = Path("/usr/bin/python3")
SCRIPTS = Path(check.BRAIN_FOLDER) / "skills" / "agent-brain" / "scripts"
SUITE = ("-m", "unittest", "discover", "-s", "tests", "-t", ".")


@dataclass(frozen=True)
class Gate:
    """One gate: the command as it runs, the folder it runs in, and the one line that names it."""

    command: str
    cwd: Path
    name: str


Runner = Callable[[Gate], int]


def run(
    project: Path,
    brain: store.Brain,
    runner: Optional[Runner] = None,
    out: Optional[Callable[[str], None]] = None,
) -> int:
    """Every gate in order, then the check, then doctor. 0 when all are green, 1 at the first red gate, 2 while the check or doctor has findings."""
    say = out or print
    runs = runner or run_gate
    gates = gates_of(project)
    if not gates:
        say("no gates named, so the check and doctor are the gates here")

    for number, gate in enumerate(gates, start=1):
        say(f"gate {number} of {len(gates)}, {gate.name}")
        code = runs(gate)
        if code != 0:
            say(f"gate {number} of {len(gates)} is red, exit {code}, and the rest did not run")
            return 1

    slips = check.run(project=project)
    for slip in slips:
        say(slip.text())
    say("check clean" if not slips else f"check {len(slips)} findings")

    findings = doctor.run(brain=brain)
    for finding in findings:
        say(finding.line())
    say("doctor clean" if not findings else f"doctor {len(findings)} findings")

    return 2 if slips or findings else 0


def gates_of(
    project: Path,
) -> list[Gate]:
    """The gates the project names, the kit's own tests first in the kit's checkout, then section 0's blocks under its Gates heading."""
    found = kit_gates(project) if check.is_kit_checkout(project) else []
    found += section_gates(project)

    return found


def kit_gates(
    project: Path,
) -> list[Gate]:
    """The tool's tests under the interpreter running this and under the floor's interpreter where that is another one."""
    scripts = project / SCRIPTS
    interpreters = [Path(sys.executable)]
    if store.quietly(FLOOR.is_file) and not same_interpreter(FLOOR, Path(sys.executable)):
        interpreters.append(FLOOR)

    return [
        Gate(
            command=" ".join([quoted(str(interpreter)), *SUITE]),
            cwd=scripts,
            name=f"the tool's tests under {interpreter}",
        )
        for interpreter in interpreters
    ]


def same_interpreter(
    one: Path,
    other: Path,
) -> bool:
    try:
        return one.resolve() == other.resolve()
    except (OSError, RuntimeError):
        return False


def quoted(
    text: str,
) -> str:
    """The text as one shell word, quoted when it holds a space."""
    return f'"{text}"' if " " in text else text


def section_gates(
    project: Path,
) -> list[Gate]:
    """One gate per fenced shell block under the Gates heading of section 0 in AGENTS.md, in order, or none."""
    door = project / "AGENTS.md"
    if not store.readable_file(door):
        return []

    try:
        text = door.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return []

    zero = upgrade.section_zero_in(text)
    if zero is None:
        return []

    heading = next((match for match in GATES_HEADING.finditer(zero) if not sections.in_code(spans=sections.code_spans(zero), position=match.start())), None)
    if heading is None:
        return []

    level = len(heading.group(1))
    end = next_heading(text=zero, start=heading.end(), level=level)
    blocks = [match for match in FENCE.finditer(zero, heading.end(), end) if match.group(2).strip().split(" ")[0].lower() in SHELLS]

    return [Gate(command=block.group(3).strip(), cwd=project, name=first_line(block.group(3))) for block in blocks if block.group(3).strip()]


def next_heading(
    text: str,
    start: int,
    level: int,
) -> int:
    """Where the next heading at the Gates heading's level or above begins, outside code, or the text's end."""
    spans = sections.code_spans(text)
    pattern = re.compile(rf"^#{{1,{level}}}[ \t]", re.MULTILINE)
    for match in pattern.finditer(text, start):
        if not sections.in_code(spans=spans, position=match.start()):
            return match.start()

    return len(text)


def first_line(
    block: str,
) -> str:
    return next((line.strip() for line in block.split("\n") if line.strip() and not line.strip().startswith("#")), block.strip().split("\n")[0])


def run_gate(
    gate: Gate,
) -> int:
    """Run one gate in its folder with its output passed straight through, under bash where the machine has it, and hand back its exit code."""
    shell = shutil.which("bash")
    try:
        if shell is not None:
            completed = subprocess.run([shell, "-c", gate.command], cwd=str(gate.cwd), check=False)
        else:
            completed = subprocess.run(gate.command, cwd=str(gate.cwd), shell=True, check=False)
    except OSError as error:
        print(store.explain(error), file=sys.stderr)
        return 1

    sys.stdout.flush()

    return completed.returncode


def is_tty() -> bool:
    """Whether the gates print to a person, for a caller that wants to say more then."""
    return os.isatty(sys.stdout.fileno()) if hasattr(sys.stdout, "fileno") else False
