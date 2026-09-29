"""Slices of a range's diff, one for each finder of a code review.

A review reads a branch's diff with many finder agents at once, and each
finder gets one slice, small enough to read in one run. The slices are
cut from git's own line counts. A file weighs its added and deleted
lines, a test file rides with its code file, docs go apart from the code,
and a file too heavy for one slice is cut where its blocks open.
"""

import re
import subprocess
from bisect import bisect_right
from dataclasses import dataclass
from itertools import accumulate
from pathlib import Path, PurePosixPath
from typing import Callable, Optional, TypeVar

# A .txt file is as often a manifest, requirements.txt or CMakeLists.txt,
# as prose, so it goes with the code.
DOC_ENDINGS = (".md", ".mdx", ".rst", ".adoc")
DEFAULT_RANGE = "main...HEAD"
DEFAULT_SIZE = 300

TEST_PREFIX = "test_"
TEST_SUFFIXES = ("_test", ".test", ".spec", "Test", "Tests")

# The old start is not needed, only the old count, the new start and the
# new count. A count left out means 1.
HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", re.MULTILINE)

Item = TypeVar("Item")


class SliceError(Exception):
    """The cut was refused, with the reason in the message."""


@dataclass
class Part:
    """A changed file, or a run of its lines on the new side, with the changed lines it holds.

    `first` and `last` are 0 when the part is the whole file.
    """

    path: str
    weight: int
    first: int = 0
    last: int = 0


@dataclass
class Slice:
    """One finder's share of the diff, numbered from 1."""

    number: int
    parts: list[Part]

    @property
    def weight(self) -> int:
        return sum(part.weight for part in self.parts)


@dataclass
class Diff:
    """The diff of one range in one repository, read through git."""

    root: Path
    revisions: str

    @property
    def head(self) -> Optional[str]:
        """The revision on the new side, HEAD when nothing follows the dots, None for the working tree a lone revision is diffed against."""
        for dots in ("...", ".."):
            if dots in self.revisions:
                return self.revisions.split(sep=dots, maxsplit=1)[1] or "HEAD"

        return None

    def git(
        self,
        arguments: list[str],
    ) -> str:
        """Git's output, or a refusal carrying the first line of git's complaint.

        The output is read as bytes and decoded here, since text mode
        would turn a lone carriage return into a line break and throw the
        line numbers off. The paths are held to the top of the repository
        through the config, since the flag that does it, --no-relative,
        is refused by a git older than 2.28.
        """
        try:
            result = subprocess.run(
                ["git", "-C", str(self.root), "-c", "diff.relative=false", *arguments],
                capture_output=True,
                check=False,
            )
        except OSError as missing:
            raise SliceError("git is not on this machine") from missing

        if result.returncode != 0:
            complaint = result.stderr.decode(encoding="utf-8", errors="replace").strip().splitlines()
            said = complaint[0] if complaint else f"exit status {result.returncode}"
            raise SliceError(f"git could not diff {self.revisions} in {self.root}, {said}")

        return result.stdout.decode(encoding="utf-8", errors="replace")

    def weights(
        self,
        pathspecs: list[str],
    ) -> dict[str, int]:
        """Each changed path with its added and deleted lines, a binary file weighing 1."""
        # --no-textconv holds the counts to the file's own text, whatever
        # the user's config says, so they match what the cut reads later.
        output = self.git(
            arguments=[
                "diff",
                "--numstat",
                "-z",
                "--no-renames",
                "--no-textconv",
                self.revisions,
                "--",
                *pathspecs,
            ],
        )

        weights: dict[str, int] = {}
        for record in output.split("\0"):
            if not record:
                continue

            added, deleted, path = record.split(
                sep="\t",
                maxsplit=2,
            )
            weights[path] = 1 if added == "-" else int(added) + int(deleted)

        return weights

    def patch(
        self,
        path: str,
    ) -> str:
        """The file's diff with no context, only its own section when a folder of the same name changed too."""
        # No colour, no external or converting driver and no context
        # merged between hunks, whatever the user's config says, so every
        # hunk header counts exactly the changed lines.
        output = self.git(
            arguments=[
                "diff",
                "-U0",
                "--inter-hunk-context=0",
                "--no-color",
                "--no-ext-diff",
                "--no-textconv",
                "--no-renames",
                self.revisions,
                "--",
                f":(top,literal){path}",
            ],
        )

        # A path that is a file on one side and a folder on the other
        # brings the folder's files along, and git puts the path itself
        # first.
        return output.split(
            sep="\ndiff --git ",
            maxsplit=1,
        )[0]

    def text(
        self,
        path: str,
    ) -> str:
        """The file's text on the new side of the diff."""
        if self.head is not None:
            return self.git(arguments=["show", f"{self.head}:{path}"])

        top = self.git(arguments=["rev-parse", "--show-toplevel"]).rstrip("\n")

        return (Path(top) / path).read_bytes().decode(encoding="utf-8", errors="replace")


@dataclass
class Layout:
    """A file's new text as far as cutting it goes, the lines that can open a block and the changed lines up to each line."""

    openers: list[int]
    indents: list[int]
    running: list[int]

    @property
    def length(self) -> int:
        return len(self.running) - 1

    def weight(
        self,
        first: int,
        last: int,
    ) -> int:
        return self.running[last] - self.running[first - 1]

    def openers_within(
        self,
        first: int,
        last: int,
    ) -> list[tuple[int, int]]:
        """The lines after `first` up to `last` that can open a block, each with its indentation."""
        start = bisect_right(a=self.openers, x=first)
        end = bisect_right(a=self.openers, x=last)

        return list(zip(self.openers[start:end], self.indents[start:end]))


def cut(
    root: Path,
    revisions: str = DEFAULT_RANGE,
    size: int = DEFAULT_SIZE,
    pathspecs: Optional[list[str]] = None,
) -> list[Slice]:
    """The diff of `revisions` in slices of at most `size` changed lines, the code first and the docs after it."""
    if size < 1:
        raise SliceError(f"a slice holds at least 1 changed line, not {size}")

    if revisions.startswith("-"):
        raise SliceError(f"'{revisions}' reads as an option to git, not a revision range")

    diff = Diff(
        root=root,
        revisions=revisions,
    )
    # Outside a repository git diff falls back to comparing two paths and
    # answers with its usage, so the repository is asked for first.
    diff.git(arguments=["rev-parse", "--git-dir"])
    weights = diff.weights(pathspecs=pathspecs or [])

    paths = sorted(weights)
    code_units = units_of(paths=[path for path in paths if not is_doc(path=path)])
    doc_units = [[path] for path in paths if is_doc(path=path)]

    code_slices = packed(
        pieces=pieces_of(diff=diff, units=code_units, weights=weights, size=size),
        size=size,
        first_number=1,
    )
    doc_slices = packed(
        pieces=pieces_of(diff=diff, units=doc_units, weights=weights, size=size),
        size=size,
        first_number=len(code_slices) + 1,
    )

    return code_slices + doc_slices


def is_doc(
    path: str,
) -> bool:
    return path.lower().endswith(DOC_ENDINGS)


def stems_tested(
    path: str,
) -> list[str]:
    """The stems a test file's name points at, in the order of the naming patterns, empty for a file that is no test."""
    name = PurePosixPath(path).stem
    stems: list[str] = []
    if name.startswith(TEST_PREFIX):
        stems.append(name[len(TEST_PREFIX) :])

    for suffix in TEST_SUFFIXES:
        if name.endswith(suffix):
            stems.append(name[: -len(suffix)])

    return [stem for stem in stems if stem]


def units_of(
    paths: list[str],
) -> list[list[str]]:
    """The changed code files in units, each test file after its code file, in the path order of each unit's code file."""
    code_files = sorted(path for path in paths if not stems_tested(path=path))
    test_files = sorted(path for path in paths if stems_tested(path=path))

    by_stem: dict[str, list[str]] = {}
    for path in code_files:
        by_stem.setdefault(PurePosixPath(path).stem, []).append(path)

    units: dict[str, list[str]] = {path: [path] for path in code_files}
    for test in test_files:
        code = code_file_of(
            test=test,
            by_stem=by_stem,
        )
        if code is None:
            units[test] = [test]
            continue

        units[code].append(test)

    return [units[key] for key in sorted(units)]


def code_file_of(
    test: str,
    by_stem: dict[str, list[str]],
) -> Optional[str]:
    """The code file a test file rides with, for the first stem its name points at that a changed code file carries.

    The candidates come in path order and `min` keeps the first of
    equals, so the first by path wins a tie.
    """
    for stem in stems_tested(path=test):
        candidates = by_stem.get(stem)
        if candidates:
            return min(
                candidates,
                key=lambda code: closeness(
                    test=test,
                    code=code,
                ),
            )

    return None


def closeness(
    test: str,
    code: str,
) -> tuple[bool, int]:
    """How near a code file sits to a test file, lowest when nearest, the test's own folder first and then the most leading folders shared."""
    test_folders = PurePosixPath(test).parent.parts
    code_folders = PurePosixPath(code).parent.parts

    shared = 0
    for test_folder, code_folder in zip(test_folders, code_folders):
        if test_folder != code_folder:
            break

        shared += 1

    return (code_folders != test_folders, -shared)


def pieces_of(
    diff: Diff,
    units: list[list[str]],
    weights: dict[str, int],
    size: int,
) -> list[list[Part]]:
    """What packing takes, a unit whole when it fits a slice, otherwise each of its files, and each part of a file cut apart."""
    pieces: list[list[Part]] = []
    for unit in units:
        if sum(weights[path] for path in unit) <= size:
            pieces.append([Part(path=path, weight=weights[path]) for path in unit])
            continue

        for path in unit:
            parts = parts_of(
                diff=diff,
                path=path,
                weight=weights[path],
                size=size,
            )
            pieces.extend([part] for part in parts)

    return pieces


def packed(
    pieces: list[list[Part]],
    size: int,
    first_number: int,
) -> list[Slice]:
    groups = greedy(
        items=pieces,
        weigh=lambda piece: sum(part.weight for part in piece),
        size=size,
    )

    return [
        Slice(
            number=first_number + index,
            parts=[part for piece in group for part in piece],
        )
        for index, group in enumerate(groups)
    ]


def greedy(
    items: list[Item],
    weigh: Callable[[Item], int],
    size: int,
) -> list[list[Item]]:
    """The items in groups, in order, each joining the group in hand while the group's weight and its own stay within `size`."""
    groups: list[list[Item]] = []
    in_hand = 0
    for item in items:
        weight = weigh(item)
        if groups and in_hand + weight <= size:
            groups[-1].append(item)
            in_hand += weight
            continue

        groups.append([item])
        in_hand = weight

    return groups


def parts_of(
    diff: Diff,
    path: str,
    weight: int,
    size: int,
) -> list[Part]:
    """A file whole, or in runs of its lines when it is heavier than a slice and can be cut.

    A binary file weighs 1, so it never comes past the first check. The
    cut starts from the whole file as one block, and since it is heavier
    than a slice its first cut falls at the lines that open with no
    indentation, which are the top level blocks.
    """
    whole = [Part(path=path, weight=weight)]
    if weight <= size or is_doc(path=path):
        return whole

    patch = diff.patch(path=path)
    if deleted_in(patch=patch):
        return whole

    lines = lines_of(text=diff.text(path=path))
    if not lines:
        return whole

    layout = layout_of(
        lines=lines,
        weights=line_weights(patch=patch),
    )
    blocks = refined(
        block=(1, layout.length),
        layout=layout,
        size=size,
    )

    return parts_from(
        path=path,
        blocks=blocks,
        layout=layout,
        size=size,
    )


def deleted_in(
    patch: str,
) -> bool:
    """Whether the file is gone on the new side, from the header above the first hunk."""
    header = patch.split(
        sep="\n@@",
        maxsplit=1,
    )[0]

    return any(line.startswith("deleted file mode") for line in header.split("\n"))


def lines_of(
    text: str,
) -> list[str]:
    """The text's lines as git counts them, split at line feeds only."""
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()

    return lines


def line_weights(
    patch: str,
) -> dict[int, int]:
    """The changed lines each line on the new side carries.

    An added line weighs at its own line. The deleted lines of a hunk
    weigh at the hunk's first line on the new side, line 1 when the hunk
    starts before the file does.
    """
    weights: dict[int, int] = {}
    for match in HUNK.finditer(patch):
        deleted = count_of(written=match.group(1))
        start = int(match.group(2))
        added = count_of(written=match.group(3))

        for line in range(start, start + added):
            weights[line] = weights.get(line, 0) + 1

        if deleted:
            at = start or 1
            weights[at] = weights.get(at, 0) + deleted

    return weights


def count_of(
    written: Optional[str],
) -> int:
    return 1 if written is None else int(written)


def layout_of(
    lines: list[str],
    weights: dict[int, int],
) -> Layout:
    """Where blocks can open, and the running weight from line 1."""
    per_line = [0] * (len(lines) + 1)
    for line, weight in weights.items():
        per_line[line] += weight

    openers: list[int] = []
    indents: list[int] = []
    for number, line in enumerate(lines, start=1):
        if is_blank(line=line):
            continue

        if number > 1 and not is_blank(line=lines[number - 2]):
            continue

        openers.append(number)
        indents.append(len(line) - len(line.lstrip(" \t")))

    return Layout(
        openers=openers,
        indents=indents,
        running=list(accumulate(per_line)),
    )


def is_blank(
    line: str,
) -> bool:
    return not line.strip()


def refined(
    block: tuple[int, int],
    layout: Layout,
    size: int,
) -> list[tuple[int, int]]:
    """The block, cut at the shallowest indentation it holds while it weighs more than `size` and holds a line that can open a block.

    Each cut takes every opening line at that indentation, so the blocks
    it leaves hold only deeper ones, and a block that holds none stays
    whole whatever it weighs.
    """
    first, last = block
    if layout.weight(first=first, last=last) <= size:
        return [block]

    inner = layout.openers_within(
        first=first,
        last=last,
    )
    if not inner:
        return [block]

    shallowest = min(indent for _, indent in inner)
    starts = [first] + [line for line, indent in inner if indent == shallowest]

    return [
        piece
        for span in spans(starts=starts, last=last)
        for piece in refined(
            block=span,
            layout=layout,
            size=size,
        )
    ]


def spans(
    starts: list[int],
    last: int,
) -> list[tuple[int, int]]:
    """Each start with the line before the next start, the final one running to `last`."""
    ends = [start - 1 for start in starts[1:]] + [last]

    return list(zip(starts, ends))


def parts_from(
    path: str,
    blocks: list[tuple[int, int]],
    layout: Layout,
    size: int,
) -> list[Part]:
    """Consecutive blocks packed into parts within `size`, each without the unchanged blocks at its ends."""
    groups = greedy(
        items=blocks,
        weigh=lambda block: layout.weight(
            first=block[0],
            last=block[1],
        ),
        size=size,
    )

    parts: list[Part] = []
    for group in groups:
        changed = [block for block in group if layout.weight(first=block[0], last=block[1]) > 0]
        if not changed:
            continue

        first = changed[0][0]
        last = changed[-1][1]
        parts.append(
            Part(
                path=path,
                weight=layout.weight(first=first, last=last),
                first=first,
                last=last,
            )
        )

    return parts


def render(
    slices: list[Slice],
    revisions: str,
    size: int,
) -> str:
    """The slices as plain text, one line per fact, for an agent to paste into a finder's prompt."""
    if not slices:
        return f"nothing changed in {revisions}"

    total = sum(slice_.weight for slice_ in slices)
    heading = f"{counted(number=len(slices), noun='slice')} of at most {counted(number=size, noun='changed line')}, {total} in all"
    lines = [heading]
    for slice_ in slices:
        lines.append(f"slice {slice_.number}, {counted(number=slice_.weight, noun='line')}")
        lines.extend(described(part=part) for part in slice_.parts)

    return "\n".join(lines)


def counted(
    number: int,
    noun: str,
) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def described(
    part: Part,
) -> str:
    if part.first == 0:
        return part.path

    return f"{part.path} lines {part.first} to {part.last}"
