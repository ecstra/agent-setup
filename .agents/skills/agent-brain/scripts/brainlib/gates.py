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
import string
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from . import check, doctor, sections, store, upgrade

# The word gates with no ASCII letter, ASCII digit or underscore beside
# it in either reading of the heading, so an identifier such as
# `ci_gates.yml` or `SKIP_GATES` holds no word gates, and any other
# character beside it parts it, a superscript digit or a letter of a
# script written without spaces among them.
GATES_WORD = re.compile(
    pattern=r"(?<![A-Za-z0-9_])gates(?![A-Za-z0-9_])",
    flags=re.IGNORECASE | re.ASCII,
)
SET_LINE = re.compile(r"^set(?:[ \t]|$)")

# What the text a link leaves is cut at in one pass, a run of `*` or `_`
# that may open or close emphasis and an HTML tag, past the backslash
# escapes that keep the character after them as written, so an escaped
# `*`, `_` or `<` opens nothing.
INLINE_MARK = re.compile(rf"(?P<escape>\\[\s\S])|(?P<run>\*+|_+)|(?P<tag>{check.TAG.pattern})")

# What an emphasis run is judged by beside it, an ASCII letter or digit,
# where any other character, a tag's bracket among them, leaves it free
# to open or close.
WORD_CHARACTERS = frozenset(string.ascii_letters + string.digits)

# The kinds of piece a heading's text is cut into, text it shows, a code
# span shown as written, markup that comes off, which is an HTML comment,
# a tag or an image, a run of `*` or `_` shown as written, and emphasis,
# a run paired with another, which comes off.
SHOWN = "shown"
CODE = "code"
MARKUP = "markup"
RUN = "run"
EMPHASIS = "emphasis"

# A link or an image, by an inline target or a reference label, a link
# shown by its text alone and an image taken off as markup is, past the
# backslash escapes that keep a bracket as it stands. An inline target holds no space outside
# angle brackets, its parentheses paired, and a title after it is
# quoted, and a reference label is a link only where the file defines
# it, on a line of its own that opens a paragraph, as CommonMark reads
# them. Anything else in brackets shows as it stands.
LINK = re.compile(
    pattern=(
        r"\\[\s\S]"
        r"|(?P<image>!?)\[(?P<text>(?:\\[\s\S]|[^\[\]\\])*)\]"
        r"(?:\([ \t]*(?:<(?:\\[\s\S]|[^<>\\\n])*>|(?!<)(?:\\\S|[^\s()\\]|\((?:\\\S|[^\s()\\])*\))*)"
        r"(?:[ \t]+(?:\"(?:\\[\s\S]|[^\"\\])*\"|'(?:\\[\s\S]|[^'\\])*'|\((?:\\[\s\S]|[^()\\])*\)))?[ \t]*\)"
        r"|\[(?P<label>(?:\\[\s\S]|[^\[\]\\])*)\])"
    ),
)
DEFINITION = re.compile(
    pattern=(
        r"[ \t]*\[(?P<label>(?:\\[\s\S]|[^\[\]\\])+)\]:[ \t]*\n?[ \t]*(?:<(?:\\[\s\S]|[^<>\\\n])*>|[^\s<]\S*)"
        r"(?:[ \t]+(?:\"[^\"\n]*\"|'[^'\n]*'|\([^()\n]*\)))?[ \t]*(?:\n|$)"
    ),
)

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
    """One gate, with its command, the folder it runs in, the one line that names it, and the shell its block runs under, or the argument list it runs as with no shell, which the kit's own gates are."""

    command: str
    cwd: Path
    name: str
    shell: str = "bash"
    argv: tuple[str, ...] = ()


@dataclass(frozen=True)
class Named:
    """What a project names, its gates in order, a line for each thing that does not run, and a line for each Gates heading that holds no gate."""

    gates: list[Gate] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    empty: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Answer:
    """What the floor's interpreter says of itself, the path it runs from, whether it is at the kit's floor, and its version."""

    path: str
    at_floor: bool
    version: str


@dataclass(frozen=True)
class Piece:
    """A piece of a heading's text as it is read, what it holds as written and its kind, one of the kinds above."""

    text: str
    kind: str


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
    run_one: Runner = runner or run_gate
    try:
        named: Named = gates_of(project)
    except GatesError as error:
        say(str(error))
        return store.REFUSED

    for line in named.notes + named.empty:
        say(line)

    total = len(named.gates)
    for number, gate in enumerate(
        iterable=named.gates,
        start=1,
    ):
        say(f"gate {number} of {total}, {gate.name}")
        code = run_one(gate)
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
        checked: check.Checked = check.run(project=project)
    except check.CheckError as error:
        return [f"the check could not run, {error}"], []

    return [slip.text() for slip in checked.slips], checked.notes


def gates_of(
    project: Path,
) -> Named:
    """The gates the project names, the kit's own tests first in the kit's checkout, then section 0's, with the lines on what does not run."""
    in_section_zero: Named = section_gates(project)
    if check.is_kit_checkout(project):
        kits_own: Named = kit_gates(project)

        return Named(
            gates=kits_own.gates + in_section_zero.gates,
            notes=kits_own.notes + in_section_zero.notes,
            empty=in_section_zero.empty,
        )

    # every Gates heading gives a gate or a line that it holds none, so with neither section 0 has no such heading
    if not in_section_zero.gates and not in_section_zero.empty:
        return Named(notes=[NO_GATES])

    return in_section_zero


def kit_gates(
    project: Path,
) -> Named:
    """The tool's tests as an argument list, under the interpreter running this, then under the floor's where it answers at the floor or above and is another one, with a line where it is below the floor."""
    if not sys.executable:
        raise GatesError("the interpreter running this gives no path of its own in sys.executable, so the tool's tests have nothing to run under, and no gate ran")

    interpreters: list[tuple[str, str]] = [(sys.executable, platform.python_version())]
    notes: list[str] = []
    answer: Optional[Answer] = floor_answer()
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
        answered: subprocess.CompletedProcess[str] = subprocess.run(
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
    heading holds the word gates where either reading of the text it
    shows does, a reference link's label shown or not by whether the
    file defines it, and each Gates heading runs to the next heading at
    its level or above, or to the end of section 0.
    """
    door = project / "AGENTS.md"
    if not store.readable_file(door):
        return Named()

    try:
        text = door.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        raise GatesError(f"AGENTS.md cannot be read, {store.explain(error)}, so no gate ran") from error

    section_zero: Optional[str] = upgrade.section_zero_in(text)
    if section_zero is None:
        return Named()

    blocks: sections.Blocks = sections.blocks_of(section_zero)
    labels: frozenset[str] = labels_of(text)

    taken: list[sections.Fence] = []
    empty: list[str] = []
    for heading in blocks.headings:
        readings: tuple[str, str] = shown(
            text=heading.text,
            labels=labels,
        )
        if not any(GATES_WORD.search(reading) for reading in readings):
            continue

        stretch_end: int = next(
            (later.start for later in blocks.headings if later.start > heading.start and later.level <= heading.level),
            len(section_zero),
        )
        fences_under = [fence for fence in blocks.fences if heading.end <= fence.start < stretch_end]
        if not any(shell_of(fence) is not None and commands_of(fence) for fence in fences_under):
            empty.append(f"the heading {heading.text} holds no gate, and {GATE_SHAPE}")

        taken += [fence for fence in fences_under if fence not in taken]

    gates: list[Gate] = []
    notes: list[str] = []
    for fence in sorted(
        taken,
        key=lambda fence: fence.start,
    ):
        shell: Optional[str] = shell_of(fence)
        commands: list[str] = commands_of(fence)
        first_line: str = next(
            (line.strip() for line in fence.text.split("\n") if line.strip()),
            "",
        )
        if shell is None:
            notes.append(
                not_run(
                    what=f"a {fence.info.split()[0]} block",
                    first=first_line,
                ),
            )
            continue

        if not commands:
            notes.append(
                not_run(
                    what="a block of nothing but comments" if first_line else "an empty block",
                    first=first_line,
                ),
            )
            continue

        gates.append(
            Gate(
                command=fence.text.strip(),
                cwd=project,
                name=next(
                    (line for line in commands if not SET_LINE.match(line)),
                    commands[0],
                ),
                shell=shell,
            ),
        )

    return Named(
        gates=gates,
        notes=notes,
        empty=empty,
    )


def labels_of(
    text: str,
) -> frozenset[str]:
    """The reference labels the file defines, each by its key, read where a paragraph opens outside code, a definition to a line."""
    blocks: sections.Blocks = sections.blocks_of(text)
    labels: set[str] = set()
    for start, end in blocks.inline:
        if any(heading.start <= start < heading.end for heading in blocks.headings):
            continue

        position = start
        while True:
            definition: Optional[re.Match[str]] = DEFINITION.match(
                string=text,
                pos=position,
                endpos=end,
            )
            if definition is None:
                break

            labels.add(label_key(definition.group("label")))
            position = definition.end()

    return frozenset(label for label in labels if label)


def label_key(
    label: str,
) -> str:
    """The label as CommonMark matches one, its white space run together and its case folded."""
    return " ".join(label.split()).casefold()


def shown(
    text: str,
    labels: frozenset[str],
) -> tuple[str, str]:
    """The heading's text as markdown shows it, read twice, once with each HTML comment, tag and image taken off flush and once with each taken off as a space, the text inside an element kept either way.

    Its code spans stand as written, each link shows its text alone, a
    reference link by a label the file defines among them, and a run of
    `*` or `_` outside the code spans comes off where it pairs as
    emphasis, so a word in a comment, an attribute, an image or a link's
    target never makes a Gates heading. Each step is one pass over the
    text, so the time grows with its length and no more.
    """
    pieces: list[Piece] = emphasized(
        pieces=pieces_of(
            text=text,
            labels=labels,
        ),
    )

    return (
        joined(
            pieces=pieces,
            markup="",
        ),
        joined(
            pieces=pieces,
            markup=" ",
        ),
    )


def pieces_of(
    text: str,
    labels: frozenset[str],
) -> list[Piece]:
    """The heading's text cut into pieces, its code spans and its HTML comments as the shared reader finds them in one line of inline text, and the text between them unlinked."""
    spans, comments = sections.inline_of(
        text=text,
        stretches=[(0, len(text))],
    )
    spans_and_comments: list[tuple[int, int, str]] = sorted(
        [(start, end, CODE) for start, end in spans] + [(start, end, MARKUP) for start, end in comments],
    )

    pieces: list[Piece] = []
    cursor = 0
    for start, end, kind in spans_and_comments:
        pieces += unlinked(
            text=text[cursor:start],
            labels=labels,
        )
        pieces.append(
            Piece(
                text=text[start:end],
                kind=kind,
            ),
        )
        cursor = end

    pieces += unlinked(
        text=text[cursor:],
        labels=labels,
    )

    return pieces


def unlinked(
    text: str,
    labels: frozenset[str],
) -> list[Piece]:
    """The pieces of text outside the code spans and the comments, each link by its text alone and each image as markup, the rest cut at its runs and its tags."""
    pieces: list[Piece] = []
    cursor = 0
    for found in LINK.finditer(text):
        pieces += marked(text[cursor : found.start()])
        link_text: Optional[str] = link_shown(
            found=found,
            labels=labels,
        )
        if link_text is None:
            pieces.append(
                Piece(
                    text=found.group(),
                    kind=MARKUP,
                ),
            )
        else:
            pieces += marked(link_text)
        cursor = found.end()

    pieces += marked(text[cursor:])

    return pieces


def marked(
    text: str,
) -> list[Piece]:
    """The text cut at each run of `*` or `_` and at each HTML tag, a tag as markup and the text between as text it shows, a backslash escape kept in it with the character after it, and no piece left empty."""
    pieces: list[Piece] = []
    cursor = 0
    for mark in INLINE_MARK.finditer(text):
        if mark.group("escape") is not None:
            continue

        if mark.start() > cursor:
            pieces.append(
                Piece(
                    text=text[cursor : mark.start()],
                    kind=SHOWN,
                ),
            )
        pieces.append(
            Piece(
                text=mark.group(),
                kind=MARKUP if mark.group("tag") is not None else RUN,
            ),
        )
        cursor = mark.end()

    if cursor < len(text):
        pieces.append(
            Piece(
                text=text[cursor:],
                kind=SHOWN,
            ),
        )

    return pieces


def emphasized(
    pieces: list[Piece],
) -> list[Piece]:
    """The pieces with each run of `*` or `_` that pairs with a later run of the same character and length taken as emphasis, found in one pass with a stack.

    A run opens where it is followed by no space and has no ASCII
    letter or digit before it, and closes where it is preceded by no
    space and has no ASCII letter or digit after it, each judged by the
    characters beside it as written. A closer pairs with the latest run
    of its kind still open, and each run opened after that one stays as
    written, as CommonMark reads it, so a lone run stays as written.
    """
    opened: list[int] = []
    still_open: set[int] = set()
    waiting: dict[str, list[int]] = {}
    paired: set[int] = set()
    for index, piece in enumerate(pieces):
        if piece.kind != RUN:
            continue

        before = pieces[index - 1].text[-1] if index else " "
        after = pieces[index + 1].text[0] if index + 1 < len(pieces) else " "
        openers_of_its_kind: list[int] = waiting.setdefault(piece.text, [])
        # a run a later pair closed over is open no more, and it is dropped from its kind's list here, once, so the pass stays linear
        while openers_of_its_kind and openers_of_its_kind[-1] not in still_open:
            openers_of_its_kind.pop()

        if openers_of_its_kind and not before.isspace() and after not in WORD_CHARACTERS:
            opener = openers_of_its_kind.pop()
            while opened[-1] != opener:
                still_open.discard(opened.pop())
            still_open.discard(opened.pop())
            paired.update((opener, index))
            continue

        if not after.isspace() and before not in WORD_CHARACTERS:
            opened.append(index)
            still_open.add(index)
            openers_of_its_kind.append(index)

    return [
        Piece(
            text=piece.text,
            kind=EMPHASIS,
        )
        if index in paired
        else piece
        for index, piece in enumerate(pieces)
    ]


def joined(
    pieces: list[Piece],
    markup: str,
) -> str:
    """The pieces as one text, each piece of markup as the given text, each run taken as emphasis taken off, and the rest as written."""
    shown_as: dict[str, str] = {MARKUP: markup, EMPHASIS: ""}

    return "".join(shown_as.get(piece.kind, piece.text) for piece in pieces)


def link_shown(
    found: re.Match,
    labels: frozenset[str],
) -> Optional[str]:
    """What a match of the link pattern shows, a link its text, an escape or a reference to a label the file does not define just as it stands, and None for an image, which comes off as markup does."""
    if found.group("text") is None:
        return found.group()

    label: Optional[str] = found.group("label")
    if label is not None and label_key(label or found.group("text")) not in labels:
        return found.group()

    if found.group("image"):
        return None

    return found.group("text")


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
    argv: list[str] = list(gate.argv) or shell_line(gate)

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
        completed: subprocess.CompletedProcess[bytes] = subprocess.run(
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
    shell: Optional[str] = shell_path(gate.shell)
    if shell is not None:
        return [shell, *SHELL_FLAGS[gate.shell], gate.command]

    fallback: Optional[str] = shell_path("sh") if gate.shell == "bash" and POSIX else None
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

    windows_folder = os.path.normcase(
        s=os.environ.get(
            key="SystemRoot",
            default="C:\\Windows",
        ),
    )
    for folder in os.environ.get(
        key="PATH",
        default="",
    ).split(os.pathsep):
        found: Optional[str] = (
            shutil.which(
                cmd=name,
                path=folder,
            )
            if folder
            else None
        )
        if found is not None and not os.path.normcase(os.path.abspath(found)).startswith(windows_folder + os.sep):
            return found

    return None
