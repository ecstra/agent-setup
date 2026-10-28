"""The house rules a machine can hold a file to, over the project's own files.

Doctor reads the brain against its specs. This reads the project's own
markdown and Python, each file known by its suffix, against the rules
of SYSTEM.md a machine can judge without reading for meaning, types
left to a type checker: the prose by line as it renders, an em dash, a
semicolon, a colon anywhere but a list item's label or a table row,
with the code, the raw HTML and the literal text stepped over, and
Python by its syntax tree and its tokens, the parameters of a def, the
bases of a class broken across lines and the arguments of a call
already broken across lines each held to one per line with a trailing
comma, and in the kit's own checkout alone the future import of
annotations, which its code keeps out by its convention. The branch's
commit messages are read too, for a co-author line or an AI
attribution. It reports and never rewrites, since none of these has
one mechanical repair, and the post write hook runs it on the file
just written so the slip is fixed in the same round.
"""

import ast
import bisect
import html
import io
import os
import platform
import re
import stat
import sys
import tokenize
import warnings
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Optional

from . import doctor, frontmatter, handover, schema, sections, store, style, upgrade

MARKDOWN = ".md"
PYTHON = ".py"
MAIN = "main"
BRAIN_FOLDER = ".agents"

# How git is asked for the project's own files, those it tracks and the
# new ones it does not ignore, each name ended by a NUL byte no name holds.
LISTING: tuple[str, ...] = ("ls-files", "-z", "--cached", "--others", "--exclude-standard")

# The attributes a project marks the text it did not write with, as
# GitHub's linguist reads them, and the values that leave a file unmarked.
MARKS: tuple[str, ...] = ("linguist-generated", "linguist-vendored")
UNMARKED: tuple[str, ...] = ("unspecified", "unset", "false")

# The characters of the names one attribute call hands git, well under
# the 32767 Windows takes on a command line, the tightest of any system.
NAMES_PER_CALL = 8000

# The variables git takes the language of its words from, left out of
# each of the check's calls, so the warning for a folder git could not
# open reads in the words UNOPENED matches.
LOCALE: frozenset[str] = frozenset({"LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES"})
UNOPENED = re.compile(r"^warning: could not open directory '(.*)': (.*)$", re.MULTILINE)

# Why the check passes over a file, said of a file named on the command line.
NOT_PROSE_OR_CODE = "it is neither markdown nor Python"
TOOLS_OWN = "the brain tool writes it"
KITS_OWN = "the kit writes it whole and the next upgrade writes it back"

# What a line of prose may not carry, read as it renders: an em dash,
# the mark or two hyphens between words typed for it, a semicolon, and a
# colon outside a list item's label and a table row. The en dash is
# none, since SYSTEM.md bans the em dash alone.
EM_DASH = "\N{EM DASH}"
TYPED_EM_DASH = re.compile(r"\w[ \t]+--[ \t]+\w")

# The shapes a line is read by, none of them a slip, the marker that
# opens a list item however deep, whose label may end at a colon, the
# quote markers taken off a line before it is judged, and the delimiter
# row under a table's header row, whose rows take any colon.
LIST_ITEM = re.compile(r"^[ \t]*(?:[-*+]|\d{1,9}[.)])[ \t]+")
QUOTE = re.compile(r"^(?:[ \t]{0,3}>[ \t]?)+")
DELIMITER_ROW = re.compile(r"[ \t]*\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$")

# The header block a markdown file opens with, the front matter other
# tools read too: a `---` line, a key line straight after it, then lines
# each a key at the margin, an indented line, a list item, a comment or
# blank, up to the closing `---`. A file that opens with a thematic
# break and a blank line has none.
HEADER_KEY = re.compile(r"[^\s#-][^:\n]*:(?:[ \t]|$)")
HEADER_LINE = re.compile(r"[^\s#-][^:\n]*:(?:[ \t]|$)|[ \t]+\S|[ \t]*-(?:[ \t]|$)|[ \t]*#|[ \t]*$")

# The raw HTML a page renders as no prose: a block opened by a tag whose
# text CommonMark leaves raw, to the line of its closing tag, an element
# of code, its tags and what it holds, and each other tag with its
# attributes.
RAW_BLOCK = re.compile(
    pattern=r"^(?:[ \t]{0,3}>[ \t]?)*[ \t]{0,3}<(pre|script|style|textarea)(?=[\s>]|$)",
    flags=re.IGNORECASE | re.MULTILINE,
)
CODE_ELEMENT = re.compile(
    pattern=r"<(code|kbd|samp)(?:\s[^<>]*)?>.*?</\1\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)
TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(?:\s+[^\s\"'=<>`/]+(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s\"'=<>`]+))?)*\s*/?>")

# The literal text a line keeps its punctuation in, as SYSTEM.md 6.3 says
# of paths and URLs, each turned to spaces in this order before the line
# is judged. A URL runs over the characters RFC 3986 lets one hold, up to
# the last that is not closing punctuation, so a semicolon, a colon, a
# comma, a period or a parenthesis right after it is the sentence's.
URL_TAIL = r"(?:[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]*[A-Za-z0-9\-_~/?#\[\]@!$&'(*+=%])"
LITERALS: tuple["re.Pattern[str]", ...] = (
    # a link reference definition whole, and a footnote definition's label and colon, whose text is judged
    re.compile(r"^[ \t]{0,3}\[(?!\^)(?:[^\[\]\\\n]|\\.)+\]:[ \t]*(?:<[^<>\n]*>|[^\s<]\S*)(?:[ \t]+(?:\"[^\"\n]*\"|'[^'\n]*'|\([^()\n]*\)))?[ \t]*$"),
    re.compile(r"^[ \t]{0,3}\[\^[^\[\]\s]+\]:"),
    # a URL, a word of a scheme written with no slashes, and git's user@host:path
    re.compile(rf"[A-Za-z][A-Za-z0-9+.-]*://{URL_TAIL}?"),
    re.compile(rf"(?<![A-Za-z0-9+.-])(?:mailto|tel|urn|data|file):{URL_TAIL}"),
    re.compile(rf"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+:{URL_TAIL}"),
    # a colon with a digit on each side, a time, a timestamp, a ratio or a line number, before the paths that end in one
    re.compile(r"(?<=\d):(?=\d)"),
    # a drive path with the line number after it, and a path with its line number or a host with its port, one word of letters, digits, dots, hyphens and slashes, a colon, then digits
    re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:\\(?:[^\s<>:\"|?*]*[^\s<>:\"|?*.,;)])?(?::\d+)?"),
    re.compile(r"(?<![^\W_])(?<![./-])(?:[^\W_]|[./-])+:\d+"),
    # an emoji shortcode
    re.compile(r":[A-Za-z0-9_+-]+:"),
)

FUTURE_ANNOTATIONS = "annotations"

# The lone argument or base that may open on its bracket's line and
# takes no trailing comma, a literal, a string or a generator, the shape
# Black keeps a call of one such argument in, and the one a generator
# must keep, since a comma after it does not parse.
HUGGED: tuple[type, ...] = (ast.Constant, ast.JoinedStr, ast.Dict, ast.List, ast.Set, ast.Tuple, ast.GeneratorExp)

# The tokens that carry no code, a comment, a line end, an indent and
# the stream's end, which no item is made of, so a comma in a comment
# is no comma of the code's.
UNSPOKEN: frozenset[int] = frozenset({tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER})

# Each opening bracket and the one that closes it.
BRACKETS: dict[str, str] = {"(": ")", "[": "]", "{": "}"}

# The bases a branch's commits are read against, the local main and
# each remote's, as git names them, and the note where they were not.
BASES: tuple[str, ...] = (f"refs/heads/{MAIN}", f"refs/remotes/*/{MAIN}")
UNREAD = "the commits were not read"

# What a commit message may not carry, per SYSTEM.md 10.1, each at the
# head of a line, its leading spaces and one emoji aside. A co-author
# trailer in any case, and an attribution, a trailer or the words of
# one, generated, written, created or made, then with or by, that name
# an agent as its product writes itself, a whole word that is no part
# of a file or folder name, so CLAUDE.md, .claude/ and a cursor name
# none, and the robot emoji elsewhere is no slip.
EMOJI = r"(?:[⌀-⏿☀-➿⬀-⯿\U0001f000-\U0001faff]️?[ \t]*)?"
AGENT = r"(?<![\w./\\-])(?:Claude|Codex|Gemini|Copilot|ChatGPT|Cursor|Aider)(?![\w/\\-]|\.\w)"
CO_AUTHOR = re.compile(rf"(?im)^[ \t]*{EMOJI}co-authored-by[ \t]*:")
ATTRIBUTION = re.compile(rf"(?m)^[ \t]*{EMOJI}(?i:assisted-by[ \t]*:|generated-by[ \t]*:|(?:generated|written|created|made)[ \t]+(?:with|by)\b).*?{AGENT}")

# The parameters a def may keep on its own line, since a method with
# nothing but its receiver has nothing to stack.
RECEIVERS = ("self", "cls")


class CheckError(Exception):
    """The check could not run as asked, with the reason in the message."""


class NotChecked(Exception):
    """A Python file the interpreter running the check cannot parse, so nothing in it is judged, with the file, the interpreter's version and why in the message, which is a note and no slip."""


@dataclass(frozen=True)
class Slip:
    """One thing a file or a commit falls short of, where, in the words the agent fixes it by."""

    path: str
    message: str
    line: int = 0

    def text(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path

        return f"{where}: {self.message}"


@dataclass(frozen=True)
class Target:
    """One file a run reads, where it is on disk and its name from the project as the disk spells it."""

    path: Path
    relative: str


@dataclass(frozen=True)
class Listing:
    """The files a run reads, in order, the slips the listing met, a name that cannot be read and a folder that cannot be opened, and the note on each file named that the check passes over."""

    files: list[Target]
    slips: list[Slip]
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Checked:
    """What a run of the check found, its slips, and the notes its caller says beside them, none of them a slip, on a file named and passed over, a file the interpreter cannot parse and the commits where they were not read."""

    slips: list[Slip]
    notes: list[str]


def run(
    project: Path,
    paths: Optional[list[Path]] = None,
) -> Checked:
    """Every slip in the files the paths name, or with no list of paths at all in the project's own files and the branch's commits, an empty list reading nothing, with the notes the caller says beside them, on each file named that the check passes over, each Python file the interpreter running the check cannot parse, and the commits where they were not read."""
    if paths is None:
        listing = tracked(project)
    else:
        listing = chosen(
            project=project,
            paths=paths,
        )

    found: list[Slip] = list(listing.slips)
    notes: list[str] = list(listing.notes)

    for target in listing.files:
        try:
            found += slips_of(
                project=project,
                target=target,
            )
        except NotChecked as unparsed:
            notes.append(str(unparsed))

    if paths is None:
        commits = check_commits(project)
        found += commits.slips
        notes += commits.notes

    return Checked(
        slips=found,
        notes=notes,
    )


def chosen(
    project: Path,
    paths: list[Path],
) -> Listing:
    """The files the paths name, each read against the shell's current folder, each file once by the file it resolves to, in the order given.

    A folder inside a git work tree stands for the files git lists under
    it, as the run with no paths reads them, and a folder outside one for
    the regular markdown and Python files under it that no dotted folder
    holds. A path that leads to nothing, or to a place outside the
    project, is refused. A file named that the check passes over is named
    once in a note with the reason, and one under a folder named is
    passed in silence, as the tree's are.
    """
    root = project.resolve()
    once: dict[str, Target] = {}
    slips: list[Slip] = []
    named: list[str] = []

    for given in paths:
        path = given if given.is_absolute() else Path.cwd() / given
        if store.quietly(path.is_dir):
            folder = within(
                root=root,
                path=path,
                given=given,
            )
            if handover.inside_repository(project=folder):
                listing = listed(
                    root=root,
                    folder=folder,
                )
            else:
                listing = walked(
                    root=root,
                    folder=folder,
                )

            for target in listing.files:
                once.setdefault(target.relative, target)

            slips += listing.slips
            continue

        if not store.readable_file(path):
            raise CheckError(f"no file at {store.near(str(given))}")

        resolved = within(
            root=root,
            path=path,
            given=given,
        )
        target = target_of(
            root=root,
            path=resolved,
        )
        once.setdefault(target.relative, target)
        named.append(target.relative)

    reasons = passed_over(
        project=project,
        relatives=list(once),
    )
    notes = [f"{relative} is passed over, {reasons[relative]}" for relative in dict.fromkeys(named) if reasons[relative] is not None]

    return Listing(
        files=[target for relative, target in once.items() if reasons[relative] is None],
        slips=slips,
        notes=notes,
    )


def tracked(
    project: Path,
) -> Listing:
    """The project's own markdown and Python files, those git tracks and the new ones it does not ignore, refused in git's words where git cannot list them, each the check passes over left out."""
    root = project.resolve()
    listing = listed(
        root=root,
        folder=root,
    )
    reasons = passed_over(
        project=project,
        relatives=[target.relative for target in listing.files],
    )

    return Listing(
        files=[target for target in listing.files if reasons[target.relative] is None],
        slips=listing.slips,
    )


def listed(
    root: Path,
    folder: Path,
) -> Listing:
    """The markdown and Python files git lists under the folder, those it tracks and the new ones it does not ignore, each name once in git's order, refused in git's words where git cannot list them.

    Each folder git says it could not open is a slip in words, since git
    lists none of the new files under it, and git names it from the top
    of its work tree.
    """
    where = named_from(
        root=root,
        path=folder,
    )
    reply = answered(
        folder=folder,
        arguments=list(LISTING),
        refusal="git cannot list the project's files" if folder == root else f"git cannot list the files under {where}",
    )
    names = [name for name in dict.fromkeys(reply.output.split("\0")) if name and prose_or_code(name)]
    spelled = [handover.on_disk(name=name) for name in names]
    listing = kept_on_disk(
        root=root,
        paths=[folder / name for name in spelled if name is not None],
    )
    warnings = UNOPENED.findall(reply.trouble)
    if not warnings:
        return listing

    top = answered(
        folder=folder,
        arguments=["rev-parse", "--show-toplevel"],
        refusal="git cannot say where its work tree starts",
    )
    unopened = [
        unopened_slip(
            root=root,
            folder=Path(top.output.strip()) / warned.rstrip("/"),
            reason=reason,
        )
        for warned, reason in warnings
    ]

    return Listing(
        files=listing.files,
        slips=listing.slips + unopened,
    )


def walked(
    root: Path,
    folder: Path,
) -> Listing:
    """The regular markdown and Python files under a folder outside git, those a dotted folder below it holds left out, in the order of their paths, each folder the walk cannot open a slip in words."""
    paths: list[Path] = []
    unopenable: list[OSError] = []
    walk = os.walk(
        top=folder,
        onerror=unopenable.append,
    )

    for place, folders, names in walk:
        folders[:] = sorted(name for name in folders if not name.startswith("."))
        paths += [Path(place) / name for name in names if prose_or_code(name)]

    listing = kept_on_disk(
        root=root,
        paths=sorted(
            paths,
            key=Path.as_posix,
        ),
    )
    unopened = [
        unopened_slip(
            root=root,
            folder=Path(error.filename),
            reason=error.strerror or store.explain(error),
        )
        for error in unopenable
    ]

    return Listing(
        files=listing.files,
        slips=unopened + listing.slips,
    )


def kept_on_disk(
    root: Path,
    paths: list[Path],
) -> Listing:
    """The paths that are regular files on disk by lstat, in their order, one that is gone or is a link, a folder or a pipe now left out, and one the disk will not say which of these it is, as in a folder no one may open, a slip in words."""
    found: list[Target] = []
    slips: list[Slip] = []

    for path in paths:
        try:
            regular = is_regular(path)
        except OSError as error:
            where = named_from(
                root=root,
                path=path,
            )
            slips.append(
                Slip(
                    path=where,
                    message=f"cannot be read, {store.explain(error)}",
                ),
            )
            continue

        if regular:
            found.append(
                target_of(
                    root=root,
                    path=path,
                ),
            )

    return Listing(
        files=found,
        slips=slips,
    )


def unopened_slip(
    root: Path,
    folder: Path,
    reason: str,
) -> Slip:
    """The slip of a folder that could not be opened, so none of the files under it were read."""
    where = named_from(
        root=root,
        path=folder,
    )

    return Slip(
        path=where,
        message=f"is a folder that could not be opened, {reason}, so the files under it were not read",
    )


def is_regular(
    path: Path,
) -> bool:
    """Whether the path is a regular file by lstat, so a link, a folder or a pipe of that name is none, False where nothing is there, and OSError where the disk will not say."""
    try:
        mode = os.lstat(path).st_mode
    except (FileNotFoundError, NotADirectoryError):
        return False

    return stat.S_ISREG(mode)


def check_file(
    project: Path,
    path: Path,
) -> list[Slip]:
    """The slips of one file, as the post write hook asks of each file written, nothing for one the check passes over or one outside the project.

    Where git cannot read the attributes, its words are the file's one
    slip, since a hook that raised would lose every slip it found. A
    Python file the interpreter running the check cannot parse has no
    slip, and the note on it goes to standard error.
    """
    root = project.resolve()
    resolved = within_project(
        root=root,
        path=path,
    )
    if resolved is None:
        return []

    target = target_of(
        root=root,
        path=resolved,
    )
    try:
        reasons = passed_over(
            project=project,
            relatives=[target.relative],
        )
    except CheckError as error:
        refused = Slip(
            path=target.relative,
            message=str(error),
        )

        return [refused]

    if reasons[target.relative] is not None:
        return []

    try:
        return slips_of(
            project=project,
            target=target,
        )
    except NotChecked as unparsed:
        say(str(unparsed))

        return []


def slips_of(
    project: Path,
    target: Target,
) -> list[Slip]:
    """The slips of a file the check judges, markdown read as UTF-8 with a leading byte order mark dropped and Python by the coding it declares, as Python reads it, each with a CRLF or a lone CR read as a line end, or the one slip that it cannot be read, or NotChecked for a Python file the interpreter running the check cannot parse."""
    relative = target.relative
    try:
        data = target.path.read_bytes()
    except OSError as error:
        unread = Slip(
            path=relative,
            message=f"cannot be read, {store.explain(error)}",
        )

        return [unread]

    if PurePosixPath(relative).suffix.lower() == PYTHON:
        try:
            text = python_text(data)
        except (SyntaxError, UnicodeDecodeError) as error:
            undecoded = Slip(
                path=relative,
                message=f"cannot be read as Python source, {store.explain(error)}",
            )

            return [undecoded]

        return python_slips(
            relative=relative,
            text=text,
            kit_checkout=is_kit_checkout(project),
        )

    try:
        text = as_text(
            data=data,
            encoding="utf-8-sig",
        )
    except UnicodeDecodeError as error:
        undecoded = Slip(
            path=relative,
            message=f"cannot be read as UTF-8 text, {store.explain(error)}",
        )

        return [undecoded]

    return markdown_slips(
        relative=relative,
        text=text,
        own_words_only=relative == "AGENTS.md" and not is_kit_checkout(project),
    )


def python_text(
    data: bytes,
) -> str:
    """A Python file's text by the coding it declares by PEP 263, UTF-8 where it declares none, a byte order mark dropped, or SyntaxError or UnicodeDecodeError where Python could not read it either.

    The lines are handed over split at a CRLF or a lone CR too, since
    a reader that splits at a line feed alone takes a file of lone CRs
    for one line and misses a coding on its second.
    """
    lines = iter(data.splitlines(keepends=True))
    coding, _ = tokenize.detect_encoding(lines.__next__)

    return as_text(
        data=data,
        encoding=coding,
    )


def as_text(
    data: bytes,
    encoding: str,
) -> str:
    """The bytes decoded, each CRLF and each lone CR read as a line end, as Python reads its source and the frontmatter module reads a header, so a file with Windows line ends reads as the same file."""
    reader = io.TextIOWrapper(
        buffer=io.BytesIO(data),
        encoding=encoding,
    )

    return reader.read()


def within(
    root: Path,
    path: Path,
    given: Path,
) -> Path:
    """The path given resolved, refused in words where it lies outside the project, whose own files are all the check reads."""
    resolved = within_project(
        root=root,
        path=path,
    )
    if resolved is None:
        raise CheckError(f"{given} is outside the project, and the check reads the project's own files")

    return resolved


def within_project(
    root: Path,
    path: Path,
) -> Optional[Path]:
    """The path resolved, or None where that lies outside the project or cannot be resolved."""
    try:
        resolved = path.resolve()
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return None

    return resolved


def target_of(
    root: Path,
    path: Path,
) -> Target:
    """A file inside the project with its name from the project, by the file it resolves to as the disk spells it, so one file goes by one name however it was given and the tests of which files are judged run on that name."""
    resolved = path.resolve()
    relative = named_from(
        root=root,
        path=resolved,
    )
    spelled = doctor.spelled_on_disk(
        base=root,
        path=relative,
    )

    return Target(
        path=resolved,
        relative=spelled or relative,
    )


def named_from(
    root: Path,
    path: Path,
) -> str:
    """The path named from the project, with forward slashes, or whole where it lies outside it."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def passed_over(
    project: Path,
    relatives: list[str],
) -> dict[str, Optional[str]]:
    """Why the check passes over each file, named from the project as the disk spells it, or None for each it judges, the one test the tree, the paths and the post write hook share.

    A file is judged where it is markdown or Python by its suffix in any
    case, the brain tool does not write it, the kit does not write it
    whole in a project, and git's attributes do not mark it generated or
    vendored, which outside git marks no file. Where git cannot read the
    attributes, the check is refused in git's words.
    """
    reasons: dict[str, Optional[str]] = {relative: None if prose_or_code(relative) else NOT_PROSE_OR_CODE for relative in relatives}
    left = [relative for relative, reason in reasons.items() if reason is None]
    if not left:
        return reasons

    kit_checkout = is_kit_checkout(project)
    stamp = store.stamp_of(project / BRAIN_FOLDER) or schema.as_tuple(schema.NO_VERSION)
    for relative in left:
        if is_tools(relative):
            reasons[relative] = TOOLS_OWN
            continue

        kits = is_kits(
            relative=relative,
            stamp=stamp,
        )
        if kits and not kit_checkout:
            reasons[relative] = KITS_OWN

    unmarked = [relative for relative in left if reasons[relative] is None]
    marks = marked(
        project=project,
        relatives=unmarked,
    )
    for relative, attribute in marks.items():
        reasons[relative] = f"git's attributes mark it {attribute}"

    return reasons


def prose_or_code(
    name: str,
) -> bool:
    """Whether the name ends in a suffix the check reads, markdown or Python, whatever its case."""
    return PurePosixPath(name).suffix.lower() in (MARKDOWN, PYTHON)


def marked(
    project: Path,
    relatives: list[str],
) -> dict[str, str]:
    """The files git's attributes mark generated or vendored, each with the attribute that marks it, none outside git, refused in git's words where git cannot read them.

    The names go to git as arguments, in calls short enough for any
    system's command line, and git waits for none on standard input.
    """
    if not relatives or not handover.inside_repository(project=project):
        return {}

    found: dict[str, str] = {}
    for names in batches(relatives):
        reply = answered(
            folder=project,
            arguments=["check-attr", "-z", *MARKS, "--", *names],
            refusal="git cannot read the attributes of the files",
        )
        fields = reply.output.split("\0")
        for name, attribute, value in zip(fields[0::3], fields[1::3], fields[2::3]):
            if value not in UNMARKED:
                found.setdefault(name, attribute)

    return found


def batches(
    names: list[str],
) -> list[list[str]]:
    """The names cut into runs of at most NAMES_PER_CALL characters, a longer name alone in its run."""
    found: list[list[str]] = [[]]
    size = 0
    for name in names:
        if found[-1] and size + len(name) + 1 > NAMES_PER_CALL:
            found.append([])
            size = 0

        found[-1].append(name)
        size += len(name) + 1

    return found


def is_kit_checkout(
    project: Path,
) -> bool:
    """Whether the project is the kit's own checkout, where a `test_*.py` file of the tool's tests lives, since they ship nowhere else, so a folder an upgrade left behind holding a dotfile alone is no checkout."""
    tests = project / BRAIN_FOLDER / schema.SKILLS / "agent-brain" / "scripts" / "tests"
    try:
        return any(store.readable_file(path) for path in tests.glob("test_*.py"))
    except OSError:
        return False


# The kind folder the review ledgers go in, one folder each.
REVIEWS = schema.KINDS["review"].folder


def is_tools(
    relative: str,
) -> bool:
    """Whether the file is one the brain tool writes whole where it writes it, in a project and in the kit's own checkout alike: the index at the brain's root and in each folder it indexes, a review ledger, and the handover note.

    An index is the tool's rendering of other files' header values, a
    ledger the tool's record, whose claims name a file by its line with
    a colon, and the note what `brain handover` writes, so no hand puts
    any of them right.
    """
    parts = relative.split("/")
    if parts[0] != BRAIN_FOLDER:
        return False

    inside = parts[1:]
    if inside == [schema.INDEX]:
        return True

    if len(inside) == 2 and inside[0] in schema.INDEXED_FOLDERS and inside[1] == schema.INDEX:
        return True

    if len(inside) == 3 and inside[0] == REVIEWS and inside[2] == schema.LEDGER:
        return True

    return "/".join(inside) == handover.RELATIVE


# The files at the project's top the kit writes whole, AGENTS.md aside,
# whose words above the kit's marker are the project's section 0, and
# the chat style in each agent folder, the source and doctor's copies.
KIT_ROOT_FILES: tuple[str, ...] = tuple(name for name in schema.ROOT_FILES if name != "AGENTS.md")
CHAT_STYLE: tuple[str, ...] = tuple(path.as_posix() for path in (style.SOURCE, *style.COPIES))


def is_kits(
    relative: str,
    stamp: tuple[int, ...],
) -> bool:
    """Whether a project stamped `stamp` holds the file from the kit, which the next upgrade writes back whole, so a slip there is the kit's and never the project's.

    The upgrade's own test decides, so a kit skill's folder and a sub
    agent definition are the kit's from the release that shipped each
    on, and one of that name in a project stamped older is the project's
    own and judged.
    """
    if relative in KIT_ROOT_FILES or relative in CHAT_STYLE:
        return True

    definition = next((definition for skill in schema.KIT_SKILLS for definition in skill.definitions if definition.path == relative), None)
    if definition is not None:
        return schema.carries(
            since=definition.since,
            stamp=stamp,
        )

    parts = relative.split("/")
    if parts[0] != BRAIN_FOLDER or len(parts) < 2:
        return False

    if schema.is_kit_path("/".join(parts[1:])):
        return True

    skill = upgrade.kit_skill_named(parts[2]) if len(parts) > 3 and parts[1] == schema.SKILLS else None

    return skill is not None and schema.ships(
        skill=skill,
        stamp=stamp,
    )


def markdown_slips(
    relative: str,
    text: str,
    own_words_only: bool = False,
) -> list[Slip]:
    """The prose slips of a markdown file, line by line as it renders, its header block, its code, its raw HTML and its literal text stepped over.

    The code is found by the one reader in sections, with the quote
    markers taken off first so code inside a quote is found too, and
    each region is blanked in place so the line numbers hold. A line is
    judged with its quote markers and its literal text taken off and its
    HTML entities read as the characters they render. In a project's
    AGENTS.md only the words above the kit's marker are the project's to
    put right.
    """
    reading = read_markdown(text)
    prose = reading.prose
    if own_words_only:
        # the marker is an HTML comment, blanked in the prose, so it is found in the text as the upgrade finds it, the first outside code, and the prose keeps the text's offsets
        mark = upgrade.first_outside_code(
            text=text,
            pattern=upgrade.MARK,
            start=0,
        )
        if mark != -1:
            prose = prose[:mark]

    found: list[Slip] = []
    bares = [
        QUOTE.sub(
            repl="",
            string=line,
        )
        for line in prose.split("\n")
    ]
    tables = table_rows(
        bares=bares,
        headings=reading.headings,
    )
    for number, bare in enumerate(
        bares,
        start=1,
    ):
        if not bare.strip():
            continue

        judged = literal_blanked(bare)
        rendered = html.unescape(judged)
        if EM_DASH in rendered or TYPED_EM_DASH.search(rendered):
            found.append(Slip(path=relative, line=number, message="carries a dash the house style bans, write a comma, a period or the word"))

        if ";" in rendered:
            found.append(Slip(path=relative, line=number, message="carries a semicolon, write two sentences"))

        colon = colon_slip(
            bare=bare,
            judged=judged,
            heading=number in reading.headings,
            table=number in tables,
        )
        if colon is not None:
            found.append(Slip(path=relative, line=number, message=colon))

    return found


@dataclass(frozen=True)
class Reading:
    """A markdown file as the prose check reads it, its text with what is stepped over turned to spaces and every line end kept, and the numbers of the lines a heading takes."""

    prose: str
    headings: frozenset[int]


@dataclass(frozen=True)
class Unquoted:
    """A text with the quote markers taken off each line outside code, where each line starts in it, and how far the start of each has moved from the text's by then."""

    text: str
    starts: list[int]
    moved: list[int]

    def origin(
        self,
        offset: int,
    ) -> int:
        """The offset in the text of an offset in the unquoted text."""
        after = bisect.bisect_right(
            a=self.starts,
            x=offset,
        )

        return offset + self.moved[after - 1]


def read_markdown(
    text: str,
) -> Reading:
    """The text with its header block, its code, its HTML comments and its raw HTML turned to spaces, each region once, and the lines its headings take.

    The header goes first, so no code or heading is read in it. The code
    is the one reader's in sections, over the text and over it again
    with the quote markers taken off, so code inside a quote is found.
    The raw HTML is read where the code and the comments leave text.
    """
    header = header_span(text)
    hidden: list[tuple[int, int]] = [] if header is None else [header]
    body = sections.blanked(
        text=text,
        spans=hidden,
    )

    outside = sections.code_spans(body)
    plain = unquoted(
        text=body,
        code=outside,
    )
    inside = [(plain.origin(start), plain.origin(end)) for start, end in sections.code_spans(plain.text)]
    code = merged(outside + inside)
    hidden += code + sections.comment_spans(
        text=body,
        spans=code,
    )

    rest = sections.blanked(
        text=text,
        spans=merged(hidden),
    )
    hidden += html_regions(rest)

    headings = frozenset(
        number
        for heading in sections.blocks_of(plain.text).headings
        for number in range(plain.text.count("\n", 0, heading.start) + 1, plain.text.count("\n", 0, heading.end) + 2)
    )
    prose = sections.blanked(
        text=text,
        spans=merged(hidden),
    )

    return Reading(
        prose=prose,
        headings=headings,
    )


def unquoted(
    text: str,
    code: list[tuple[int, int]],
) -> Unquoted:
    """The text with the quote markers taken off each line, however deep, but a line that starts inside code, which keeps what it holds."""
    kept: list[str] = []
    starts: list[int] = []
    moved: list[int] = []
    taken = 0
    offset = 0

    for line in text.split("\n"):
        marked = QUOTE.match(line)
        markers = 0
        if marked is not None and not sections.in_code(
            spans=code,
            position=offset,
        ):
            markers = marked.end()

        starts.append(offset - taken)
        taken += markers
        moved.append(taken)
        kept.append(line[markers:])
        offset += len(line) + 1

    return Unquoted(
        text="\n".join(kept),
        starts=starts,
        moved=moved,
    )


def html_regions(
    text: str,
) -> list[tuple[int, int]]:
    """Where the raw HTML sits in a text whose code and comments are blanked, a raw block first, then an element of code in what the blocks leave, then each other tag."""
    blocks: list[tuple[int, int]] = []
    for opened in RAW_BLOCK.finditer(text):
        if blocks and opened.start() < blocks[-1][1]:
            continue

        closing = re.compile(
            pattern=rf"</{opened.group(1)}\s*>",
            flags=re.IGNORECASE,
        )
        closer = closing.search(
            string=text,
            pos=opened.end(),
        )
        end = len(text)
        if closer is not None:
            end = line_end(
                text=text,
                offset=closer.end(),
            )

        blocks.append((opened.start(), end))

    rest = sections.blanked(
        text=text,
        spans=blocks,
    )
    elements = [element.span() for element in CODE_ELEMENT.finditer(rest)]
    rest = sections.blanked(
        text=rest,
        spans=elements,
    )
    tags = [tag.span() for tag in TAG.finditer(rest)]

    return blocks + elements + tags


def line_end(
    text: str,
    offset: int,
) -> int:
    """Where the line the offset sits on ends, before its line end, or the text's end."""
    end = text.find("\n", offset)

    return len(text) if end == -1 else end


def merged(
    spans: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """The spans in order, each that overlaps the one before joined to it, so a region is blanked once and no text is written twice."""
    found: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if found and start <= found[-1][1]:
            found[-1] = (found[-1][0], max(found[-1][1], end))
            continue

        found.append((start, end))

    return found


def header_span(
    text: str,
) -> Optional[tuple[int, int]]:
    """Where a header block opened on the first line runs, fences included, or None when the text opens with none, a key line straight after its `---` and each line to the closing one a line a header holds."""
    lines = text.split("\n")
    if len(lines) < 3 or lines[0] != frontmatter.FENCE or not HEADER_KEY.match(lines[1]):
        return None

    offset = len(lines[0]) + len(lines[1]) + 2
    for line in lines[2:]:
        if line == frontmatter.FENCE:
            return 0, offset + len(frontmatter.FENCE)

        if not HEADER_LINE.match(line):
            return None

        offset += len(line) + 1

    return None


def literal_blanked(
    line: str,
) -> str:
    """The line with its literal text turned to spaces, each of LITERALS in its order, so its offsets hold."""
    for literal in LITERALS:
        line = literal.sub(
            repl=lambda found: " " * len(found.group()),
            string=line,
        )

    return line


def table_rows(
    bares: list[str],
    headings: frozenset[int],
) -> frozenset[int]:
    """The numbers of the lines that are rows of a table as GitHub reads one, the header row straight above a delimiter row, a row of cells of hyphens and at least one pipe, that row, and the rows after it up to a blank line, a heading or a line with no pipe.

    A line above the header row, a heading among them, is no row, and a
    delimiter row with no header row above it, a blank line or a heading
    there, opens no table.
    """
    found: set[int] = set()
    for number, bare in enumerate(
        bares,
        start=1,
    ):
        if number in found or "|" not in bare or not DELIMITER_ROW.match(bare):
            continue

        header = number - 1
        if header < 1 or not bares[header - 1].strip() or header in headings:
            continue

        found.update((header, number))
        row = number + 1
        while row <= len(bares) and "|" in bares[row - 1] and row not in headings:
            found.add(row)
            row += 1

    return frozenset(found)


def colon_slip(
    bare: str,
    judged: str,
    heading: bool,
    table: bool,
) -> Optional[str]:
    """Why the line's colon is not a list item's label, or None when the line carries none that is not, its literal text blanked in what is judged and a table row taking any."""
    rendered = html.unescape(judged)
    if ":" not in rendered or table:
        return None

    if heading:
        return "carries a colon in a heading, which takes none"

    item = LIST_ITEM.match(bare)
    if item is None:
        return "carries a colon mid sentence, which the house style keeps for a list item's label"

    text = html.unescape(judged[item.end() :])
    if holds_a_sentence_end(text[: text.index(":")]):
        return "carries a colon mid sentence, past the sentence that opens the list item, which the house style keeps for the item's label"

    if text.count(":") > 1:
        return "carries a second colon in a list item, past the one that ends its label"

    return None


# A label ends at the item's first colon and holds no sentence, so a
# colon past a sentence's end sits mid sentence however the item opens,
# a bold label that ends in one too. A sentence ends at a period, a
# question mark or an exclamation mark, any closing emphasis after it,
# then a space and an upper case letter, the period of a known
# abbreviation aside.
SENTENCE_END = re.compile(r"[.!?][*_]*[ \t]+(?=\S)")
ABBREVIATION = re.compile(r"(?<![\w.])(?:e\.g|i\.e|etc|cf|vs|Dr|Mr|Mrs|Ms|St|No|Fig|Inc|Ltd|Co|Jr|Sr)\.$")


def holds_a_sentence_end(
    label: str,
) -> bool:
    """Whether the text before a list item's first colon holds the end of a sentence."""
    for end in SENTENCE_END.finditer(label):
        if not label[end.end()].isupper():
            continue

        if label[end.start()] == "." and ABBREVIATION.search(label[: end.start() + 1]):
            continue

        return True

    return False


def python_slips(
    relative: str,
    text: str,
    kit_checkout: bool = False,
) -> list[Slip]:
    """The structural slips of a Python file, read from its syntax tree and its tokens, or NotChecked where the interpreter running the check cannot parse it.

    The future import of annotations is a slip in the kit's own checkout
    alone, whose code keeps it out by its convention, since SYSTEM.md
    holds no such rule for a project.
    """
    code = read_python(
        relative=relative,
        text=text,
    )
    found: list[Slip] = []
    for node in walk_outside_strings(code.tree):
        if kit_checkout and isinstance(node, ast.ImportFrom) and node.module == "__future__" and any(alias.name == FUTURE_ANNOTATIONS for alias in node.names):
            found.append(
                Slip(
                    path=relative,
                    line=node.lineno,
                    message="imports annotations from __future__, which the kit's own code keeps out",
                ),
            )

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found += def_slips(
                relative=relative,
                node=node,
                code=code,
            )

        if isinstance(node, ast.ClassDef):
            found += class_slips(
                relative=relative,
                node=node,
                code=code,
            )

        if isinstance(node, ast.Call):
            found += call_slips(
                relative=relative,
                node=node,
                code=code,
            )

    return sorted(found, key=lambda slip: (slip.line, slip.message))


@dataclass(frozen=True)
class Code:
    """A Python file as its stacking is judged, its syntax tree, its lines, the tokens that carry code in order, the token each opening bracket closes at and each closing one opens at, the token that starts at each place, and the closing bracket that ends at each."""

    tree: ast.AST
    lines: list[str]
    tokens: list[tokenize.TokenInfo]
    closes: dict[int, int]
    opens: dict[int, int]
    starting: dict[tuple[int, int], int]
    ending: dict[tuple[int, int], int]

    def at(
        self,
        line: int,
        offset: int,
    ) -> tuple[int, int]:
        """A place the syntax tree gives, whose offset counts the line's bytes in UTF-8, as the line and the column in characters the tokens give."""
        before = self.lines[line - 1].encode("utf-8")[:offset]

        return line, len(before.decode("utf-8"))


def read_python(
    relative: str,
    text: str,
) -> Code:
    """The file's syntax tree and its tokens, or NotChecked where the interpreter running the check cannot parse it, or reaches its limits doing so.

    The tree is parsed with the file's name and the warnings of compiling
    it silenced, so a warning on an escape in a string neither lands on
    standard error with no file named nor turns to an error under
    `-W error`.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tree = ast.parse(
                source=text,
                filename=relative,
            )
            tokens = [token for token in tokenize.generate_tokens(io.StringIO(text).readline) if token.type not in UNSPOKEN]
    except (SyntaxError, ValueError, RecursionError, MemoryError, tokenize.TokenError) as error:
        raise NotChecked(f"{relative} is not checked, the Python {platform.python_version()} running the check cannot parse it, {unparsed(error)}") from error

    closes: dict[int, int] = {}
    waiting: list[int] = []
    for index, token in enumerate(tokens):
        if token.type == tokenize.OP and token.string in BRACKETS:
            waiting.append(index)

        if token.type == tokenize.OP and token.string in BRACKETS.values():
            closes[waiting.pop()] = index

    opens = {closing: opened for opened, closing in closes.items()}

    return Code(
        tree=tree,
        lines=text.split("\n"),
        tokens=tokens,
        closes=closes,
        opens=opens,
        starting={token.start: index for index, token in enumerate(tokens)},
        ending={tokens[closing].end: closing for closing in opens},
    )


def unparsed(
    error: BaseException,
) -> str:
    """Why the interpreter could not parse a file, in its words, with the line where it names one."""
    if isinstance(error, SyntaxError):
        return f"{error.msg} on line {error.lineno}" if error.lineno else str(error.msg)

    return str(error.args[0]) if error.args else type(error).__name__


def walk_outside_strings(
    tree: ast.AST,
) -> list[ast.AST]:
    """Every node of the tree but what sits inside a formatted string, whose positions the older interpreters place on the string itself."""
    found: list[ast.AST] = []
    ahead: list[ast.AST] = [tree]
    while ahead:
        node = ahead.pop()
        found.append(node)
        if isinstance(node, ast.JoinedStr):
            continue

        ahead.extend(ast.iter_child_nodes(node))

    return found


def def_slips(
    relative: str,
    node: ast.AST,
    code: Code,
) -> list[Slip]:
    """A def's parameters one per line below its bracket, with a trailing comma after the last, a def with none or a receiver alone aside."""
    arguments = node.args
    parameters = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]
    if arguments.vararg is not None:
        parameters.append(arguments.vararg)
    if arguments.kwarg is not None:
        parameters.append(arguments.kwarg)

    if not parameters or (len(parameters) == 1 and parameters[0].arg in RECEIVERS):
        return []

    opened = header_bracket(
        code=code,
        node=node,
    )

    return stacking_slips(
        relative=relative,
        code=code,
        opened=opened,
        unstacked=f"def {node.name} does not stack its parameters one per line with a trailing comma",
        uncommaed=f"def {node.name} has no trailing comma after its last parameter",
    )


def class_slips(
    relative: str,
    node: ast.ClassDef,
    code: Code,
) -> list[Slip]:
    """A class whose bases or keywords break across lines keeps them one per line with a trailing comma, a lone literal, string or generator aside."""
    bases: list[ast.AST] = [*node.bases, *node.keywords]
    if not bases:
        return []

    opened = header_bracket(
        code=code,
        node=node,
    )
    judged = held(
        code=code,
        opened=opened,
        items=bases,
    )
    if not judged:
        return []

    return stacking_slips(
        relative=relative,
        code=code,
        opened=opened,
        unstacked=f"class {node.name} breaks its bases across lines and does not stack them one per line",
        uncommaed=f"class {node.name} has no trailing comma after its last base",
    )


def call_slips(
    relative: str,
    node: ast.Call,
    code: Code,
) -> list[Slip]:
    """A call already broken across lines keeps its arguments one per line with a trailing comma, a lone literal, string or generator aside."""
    end = code.at(
        line=node.end_lineno,
        offset=node.end_col_offset,
    )
    opened = code.opens[code.ending[end]]
    judged = held(
        code=code,
        opened=opened,
        items=[*node.args, *node.keywords],
    )
    if not judged:
        return []

    return stacking_slips(
        relative=relative,
        code=code,
        opened=opened,
        unstacked=f"the call of {callee(node)} is broken across lines and does not stack its arguments one per line",
        uncommaed=f"the call of {callee(node)} has no trailing comma after its last argument",
    )


def header_bracket(
    code: Code,
    node: ast.AST,
) -> int:
    """The bracket a def's parameters or a class's bases open at, the first `(` after its keyword outside any other bracket, so a list of type parameters is stepped over."""
    start = code.at(
        line=node.lineno,
        offset=node.col_offset,
    )
    index = code.starting[start]
    while not is_mark(
        token=code.tokens[index],
        mark="(",
    ):
        index = code.closes.get(index, index) + 1

    return index


def held(
    code: Code,
    opened: int,
    items: list[ast.AST],
) -> bool:
    """Whether a call's arguments or a class's bases are held to the stacking, there being some, broken across lines, and other than one lone literal, string or generator, which may open on the bracket's line and takes no trailing comma."""
    broken = code.tokens[opened].start[0] != code.tokens[code.closes[opened]].start[0]
    lone = len(items) == 1 and isinstance(items[0], HUGGED)

    return bool(items) and broken and not lone


def stacking_slips(
    relative: str,
    code: Code,
    opened: int,
    unstacked: str,
    uncommaed: str,
) -> list[Slip]:
    """The slip of the items within a bracket where they do not stack one per line, named on the bracket's line, or where the last has no trailing comma, named on the line it ends on.

    Each item starts on a line after the line the one before it ends on,
    the first on a line after the bracket's, and the trailing comma is a
    comma token between the last item's end, its closing parenthesis
    included where it is parenthesized, and the closing bracket, so a
    comma in a comment or a string, after the bracket, or on the line
    below is read as it is.
    """
    bracket = code.tokens[opened].start[0]
    ended = bracket
    for first, last in items_within(
        code=code,
        opened=opened,
    ):
        if code.tokens[first].start[0] <= ended:
            sharing_a_line = Slip(
                path=relative,
                line=bracket,
                message=unstacked,
            )

            return [sharing_a_line]

        ended = code.tokens[last].end[0]

    trailing = is_mark(
        token=code.tokens[code.closes[opened] - 1],
        mark=",",
    )
    if trailing:
        return []

    missing_comma = Slip(
        path=relative,
        line=ended,
        message=uncommaed,
    )

    return [missing_comma]


def items_within(
    code: Code,
    opened: int,
) -> list[tuple[int, int]]:
    """The first and the last token of each item between a bracket and the one it closes at, parted by the bracket's own commas, a bracket inside an item taken whole, so a parenthesized item ends at its closing parenthesis, and a trailing comma parting off nothing.

    A lambda's parameters are the one list the grammar lets an item hold
    outside a bracket, a lone generator's targets aside, which are never
    parted, so a comma from a `lambda` to the colon that ends its
    parameters is the lambda's, each nested lambda waiting for a colon
    of its own.
    """
    parts: list[list[int]] = [[]]
    lambdas = 0
    index = opened + 1
    while index < code.closes[opened]:
        token = code.tokens[index]
        if token.type == tokenize.NAME and token.string == "lambda":
            lambdas += 1

        ending = is_mark(
            token=token,
            mark=":",
        )
        if ending and lambdas:
            lambdas -= 1

        parting = is_mark(
            token=token,
            mark=",",
        )
        if parting and not lambdas:
            parts.append([])
        else:
            parts[-1].append(index)

        index = code.closes.get(index, index) + 1

    return [(part[0], code.closes.get(part[-1], part[-1])) for part in parts if part]


def is_mark(
    token: tokenize.TokenInfo,
    mark: str,
) -> bool:
    """Whether the token is the operator or the bracket given, and no string or name that reads the same."""
    return token.type == tokenize.OP and token.string == mark


def callee(
    node: ast.Call,
) -> str:
    """The called thing's name as written, or what kind of expression it is."""
    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        return node.func.attr

    return "an expression"


def check_commits(
    project: Path,
) -> Checked:
    """The commits of HEAD that no main git knows reaches, the local one or a remote's, each read for a co-author line or an AI attribution, or no slip and the note that they were not read and why, where git cannot say or knows no main.

    Each record ends at a NUL byte, which no message can hold, and the
    signature the owner's config may show is left out, so neither a
    message nor a signature is read as a commit's hash.
    """
    try:
        known = answered(
            folder=project,
            arguments=["for-each-ref", "--format=%(refname)", *BASES],
            refusal=UNREAD,
            seconds=handover.GIT_SECONDS,
        )
        bases = known.output.split()
        if not bases:
            unknown = Checked(
                slips=[],
                notes=[f"{UNREAD}, git knows no {MAIN} branch here, local or a remote's, to read them against"],
            )

            return unknown

        log = answered(
            folder=project,
            arguments=["log", "--no-show-signature", "-z", "--format=%h%n%B", "HEAD", "--not", *bases, "--"],
            refusal=UNREAD,
            seconds=handover.GIT_SECONDS,
        )
    except CheckError as error:
        unread = Checked(
            slips=[],
            notes=[str(error)],
        )

        return unread

    found: list[Slip] = []
    for record in log.output.split("\0"):
        short, _, message = record.partition("\n")
        if short:
            found += commit_slips(
                short=short,
                message=message,
            )

    return Checked(
        slips=found,
        notes=[],
    )


def commit_slips(
    short: str,
    message: str,
) -> list[Slip]:
    """The slips of one commit's message, named by its short hash, a co-author line and an AI attribution."""
    where = f"commit {short}"
    found: list[Slip] = []
    if CO_AUTHOR.search(message):
        found.append(
            Slip(
                path=where,
                message="carries a co-author line, and a commit has one author",
            ),
        )

    if ATTRIBUTION.search(message):
        found.append(
            Slip(
                path=where,
                message="carries an AI attribution, which no commit carries",
            ),
        )

    return found


def answered(
    folder: Path,
    arguments: list[str],
    refusal: str,
    seconds: Optional[int] = None,
) -> handover.Reply:
    """Git's reply for the folder through the shared runner, waiting as long as git takes unless the seconds are given, as the upgrade's calls over the whole tree do, or the check refused in the words given and what git said."""
    try:
        reply = handover.git(
            project=folder,
            arguments=arguments,
            seconds=seconds,
            unset=LOCALE,
        )
    except handover.Unanswered as error:
        raise CheckError(f"{refusal}, {error}") from error

    if reply.code != 0:
        raise CheckError(f"{refusal}, {said_by(reply)}")

    return reply


def said_by(
    reply: handover.Reply,
) -> str:
    """The first line of what git said where it failed, or its exit code where it said nothing."""
    return handover.first_line(text=reply.trouble) or f"git exited {reply.code}"


def say(
    words: str,
) -> None:
    """A note of the check's on standard error, so standard output carries the slips alone, a JSON list of them among the rest."""
    print(
        words,
        file=sys.stderr,
    )
