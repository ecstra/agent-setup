"""The house rules a machine can hold a file to, over the project's own files.

Doctor reads the brain against its formats. This reads the project's own
markdown against the house prose rules of SYSTEM.md a machine can judge
without reading for meaning, and leaves code to the project's own
linters. It reads the prose by line as it renders for an em dash, a
semicolon or a colon anywhere but a list item's label or a table row,
with the code, the raw HTML and the literal text stepped over. The
branch's commit messages are read too, for a co-author line or an AI
attribution. It reports and never rewrites, since most of these need
new words that only the writer can choose, and the post write hook runs
it on the file just written so the slip is fixed in the same round.
"""

import bisect
import html
import html.entities
import io
import itertools
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Optional

from . import doctor, frontmatter, handover, schema, sections, store, style, upgrade

MARKDOWN = ".md"
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
# open reads in the words UNOPENED matches where git falls back to its
# own English. A git that falls back to the system's language words it
# otherwise, and its warning is passed on as a note as it stands.
LOCALE: frozenset[str] = frozenset({"LANG", "LANGUAGE", "LC_ALL", "LC_MESSAGES"})
UNOPENED = re.compile(
    pattern=r"^warning: could not open directory '(.*)': (.*)$",
    flags=re.MULTILINE,
)

# How the name of each variable git traces its own work by opens,
# GIT_TRACE, GIT_TRACE2 and the rest, each left out of the check's
# calls, since a trace git writes to standard error reads there as git's
# own words, a warning as it lists the files or the reason it refused.
TRACE = "GIT_TRACE"

# Why the check passes over a file, said of a file named on the command line.
NOT_MARKDOWN = "it is not markdown, and the project's own linters judge code"
TOOLS_OWN = "the brain tool writes it"
KITS_OWN = "the kit writes it whole and the next upgrade writes it back"

# What a line of prose may not carry, read as it renders, is an em dash,
# the mark or two hyphens between words typed for it, with a space on
# each side as the line is written, a semicolon, and a colon outside a
# list item's label and a table row. The en dash is none, since
# SYSTEM.md bans the em dash alone. A character the reading turned to a
# space, of code, a tag or literal text, is marked STEPPED_OVER where
# the hyphens are judged, so it stands beside them as the text it was
# and never as a space the line holds.
EM_DASH = "\N{EM DASH}"
STEPPED_OVER = "\0"
TYPED_EM_DASH = re.compile(r"\w[ \t\x00]*[ \t]--[ \t][ \t\x00]*\w")

# The character references CommonMark reads, each ended by its
# semicolon, a named one where HTML names it, and a backslash escape,
# which keeps the character after it as typed, so `\&mdash;` and `&#59`
# show as written.
REFERENCE = re.compile(r"\\[\s\S]|&(?:#[0-9]{1,7}|#[xX][0-9A-Fa-f]{1,6}|[A-Za-z][A-Za-z0-9]{0,31});")

# The shapes a line is read by, none of them a slip, the marker that
# opens a list item however deep, whose label may end at a colon, the
# quote markers taken off a line before it is judged, and the delimiter
# row under a table's header row, whose rows take any colon. Each run of
# spaces in the row is one only a pipe or a hyphen can end, so a line
# that fails to be one fails in time that grows with its length.
LIST_ITEM = re.compile(r"^[ \t]*(?:[-*+]|\d{1,9}[.)])[ \t]+")
QUOTE = re.compile(r"^(?:[ \t]{0,3}>[ \t]?)+")
DELIMITER_ROW = re.compile(r"[ \t]*(?:\|[ \t]*)?:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*(?:\|[ \t]*)?$")

# One of the quote markers QUOTE takes off, so a line's first few are taken alone.
QUOTE_MARKER = re.compile(r"[ \t]{0,3}>[ \t]?")

# The header block a markdown file opens with, the front matter other
# tools read too, is a `---` line, a key line straight after it, then
# lines each a key at the margin, an indented line, a list item, a
# comment or blank, up to the closing `---`. A file that opens with a
# thematic break and a blank line has none.
HEADER_KEY = re.compile(r"[^\s#-][^:\n]*:(?:[ \t]|$)")
HEADER_LINE = re.compile(r"[^\s#-][^:\n]*:(?:[ \t]|$)|[ \t]+\S|[ \t]*-(?:[ \t]|$)|[ \t]*#|[ \t]*$")

# The raw HTML a page renders as no prose is a block opened by a tag whose
# text CommonMark leaves raw, to its closing tag or the end of the quote
# it opened in, an element of code, its tags and what it holds, and each
# other tag with its attributes, as CommonMark reads a tag, an attribute
# a name of letters, digits, `_`, `.`, `:` and `-` that opens with no
# digit, `.` or `-`, and a closing tag one with none. The quote markers
# before a raw block's tag are read as runs of up to four spaces after
# each `>`, so a quoted line that opens no block fails in time that
# grows with its depth.
RAW_BLOCK = re.compile(
    pattern=r"^[ \t]{0,3}(?:>[ \t]{0,4})*<(pre|script|style|textarea)(?=[\s>]|$)",
    flags=re.IGNORECASE | re.MULTILINE,
)
CODE_ELEMENT = re.compile(
    pattern=r"<(code|kbd|samp)(?:\s[^<>]*)?>.*?</\1\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)
TAG = re.compile(r"</[A-Za-z][A-Za-z0-9-]*\s*>|<[A-Za-z][A-Za-z0-9-]*(?:\s+[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s\"'=<>`]+))?)*\s*/?>")

# The literal text a line keeps its punctuation in, as SYSTEM.md 6.3 says
# of paths and URLs, each turned to spaces in this order before the line
# is judged. A URL runs over every character but a space, an angle
# bracket and the em dash, a letter of any script, a pipe, a brace or a
# quote among them, up to the last that is not closing punctuation, so a
# semicolon, a colon, a comma, a period or a parenthesis right after it
# is the sentence's, and so is a dash set flush against it. A scheme
# opens at a word's first letter, so a long word is read once and not
# from each letter, and the digits, dots, pluses and hyphens a word
# opens with before it, on none of which a scheme opens, go with the
# URL, so one glued to a number or a flag is literal text too.
URL_TAIL = r"(?:[^\s<>\N{EM DASH}]*[^\s<>\N{EM DASH}.,;:)])"
LITERALS: tuple["re.Pattern[str]", ...] = (
    # a link reference definition whole, and a footnote definition's label and colon, whose text is judged
    re.compile(r"^[ \t]{0,3}\[(?!\^)(?:[^\[\]\\\n]|\\.)+\]:[ \t]*(?:<[^<>\n]*>|[^\s<]\S*)(?:[ \t]+(?:\"[^\"\n]*\"|'[^'\n]*'|\([^()\n]*\)))?[ \t]*$"),
    re.compile(r"^[ \t]{0,3}\[\^[^\[\]\s]+\]:"),
    # a URL, a word of a scheme written with no slashes, and git's user@host:path
    re.compile(rf"(?<![A-Za-z0-9+.-])[0-9+.-]*[A-Za-z][A-Za-z0-9+.-]*://{URL_TAIL}?"),
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

# The bases a branch's commits are read against, the local main and
# each remote's, as `--remotes=*/main` takes them, a remote's name with
# a slash in it among them, and the note where they were not. Git is
# asked for the refs under the prefixes that hold them and each is kept
# by its whole name, since git matches a name with no wildcard against
# every ref below it too, a branch `main/fix` among them, and a `*` that
# stops at a slash.
BASE_PREFIXES: tuple[str, ...] = (f"refs/heads/{MAIN}", "refs/remotes")
BASE = re.compile(rf"refs/heads/{MAIN}|refs/remotes/.+/{MAIN}")
UNREAD = "the commits were not read"

# What a commit message may not carry, per SYSTEM.md 10.1, each at the
# head of a line, its leading spaces, a list marker, an opening
# parenthesis or bracket and any emoji aside, a sequence joined by zero
# width joiners or with a skin tone being one emoji. A co-author trailer
# in any case, and an attribution, a trailer or the words of one,
# generated, written, created or made, then with or by and the colon a
# trailer ends with where it is typed, whose object is an agent named
# as its product writes itself, right after it with no more than a
# link's opening bracket or its maker's name between, the maker's in
# the possessive too and before the bracket or after it, so an agent
# named later in the line is none. The name is a whole word, a
# version or a variant after a hyphen in it, that is no part of a file
# or folder name, a word that goes on to a slash or ends in a suffix, so
# CLAUDE.md, .claude/, Codex-guide.md and a cursor name none, while
# Claude-Code and Gemini-2.5-Pro name one, and the robot emoji elsewhere
# is no slip. The skin tones, U+1F3FB to U+1F3FF, are left out of the
# emoji an emoji opens with, so an emoji with its tone reads one way and
# a line of them that opens no trailer fails in time that grows with it.
EMOJI_POINT = r"[⌀-⏿☀-➿⬀-⯿\U0001f000-\U0001f3fa\U0001f400-\U0001faff]\ufe0f?[\U0001f3fb-\U0001f3ff]?"
EMOJI = rf"{EMOJI_POINT}(?:\u200d{EMOJI_POINT})*"
LINE_HEAD = rf"[ \t]*(?:(?:[-*+]|\d{{1,9}}[.)])[ \t]+|[(\[][ \t]*|{EMOJI}[ \t]*)*"
AGENT = r"(?<![\w./\\-])(?:Claude|Codex|Gemini|Copilot|ChatGPT|Cursor|Aider)(?!\w)(?![\w.-]*(?:[/\\]|\.[A-Za-z]\w*(?![\w.-])))"
NAMED = r"(?:\[[ \t]*)?(?:(?i:(?:GitHub|OpenAI|Google|Anthropic)(?:['’]s)?)[ \t]+(?:\[[ \t]*)?)?"
CO_AUTHOR = re.compile(rf"(?im)^{LINE_HEAD}co-authored-by[ \t]*:")
ATTRIBUTION = re.compile(rf"(?m)^{LINE_HEAD}(?:(?i:assisted-by|generated-by)[ \t]*:[ \t]*|(?i:generated|written|created|made)[ \t]+(?i:with|by)(?:[ \t]*:[ \t]*|[ \t]+)){NAMED}{AGENT}")


class CheckError(Exception):
    """The check could not run as asked, with the reason in the message."""


@dataclass(frozen=True)
class Slip:
    """One thing a file or a commit falls short of, where, in the words the agent fixes it by."""

    path: str
    message: str
    line: int = 0

    def text(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path

        return store.shown(f"{where}: {self.message}")


@dataclass(frozen=True)
class Target:
    """One file a run reads, where it is on disk and its name from the project as the disk spells it."""

    path: Path
    relative: str


@dataclass(frozen=True)
class Listing:
    """The files a run reads, in order, the slips the listing met, a name that cannot be read and a folder that cannot be opened, and the notes, each line git said as it listed the files that names no such folder and each file named that the check passes over."""

    files: list[Target]
    slips: list[Slip]
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Checked:
    """What a run of the check or its call over one file found, its slips, and the notes its caller says beside them, none of them a slip, on a line git said as it listed the files, a file named and passed over, a file not checked, one whose attributes git cannot read, and the commits where they were not read."""

    slips: list[Slip]
    notes: list[str]


def run(
    project: Path,
    paths: Optional[list[Path]] = None,
) -> Checked:
    """Every slip in the files the paths name, or with no list of paths at all in the project's own files and the branch's commits, an empty list reading nothing, with the notes the caller says beside them, on each line git said as it listed the files, each file named that the check passes over, and the commits where they were not read."""
    if paths is None:
        listing: Listing = tracked(project)
    else:
        listing = chosen(
            project=project,
            paths=paths,
        )

    found: list[Slip] = list(listing.slips)
    notes: list[str] = list(listing.notes)

    for target in listing.files:
        found += slips_of(
            target=target,
        )

    if paths is None:
        commits: Checked = check_commits(project)
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
    the regular markdown files under it that no dotted folder holds. A
    path that leads to nothing, or to a place outside the
    project, is refused. A file named that the check passes over is named
    once in a note with the reason, and one under a folder named is
    passed in silence, as the tree's are. A folder that cannot be opened,
    or a file that cannot be read, is one slip however many of the paths
    reach it, and a line git said as it listed one note, in the words of
    the first folder whose listing it came in.
    """
    root = project.resolve()
    targets: dict[str, Target] = {}
    slips: list[Slip] = []
    warned: dict[str, str] = {}
    named: list[str] = []
    listings: dict[Path, Optional[frozenset[str]]] = {}

    for given in paths:
        path = given if given.is_absolute() else Path.cwd() / given
        if store.quietly(path.is_dir):
            folder: Path = within(
                root=root,
                path=path,
                given=given,
            )
            if handover.inside_repository(project=folder):
                listing: Listing = listed(
                    root=root,
                    folder=folder,
                    listings=listings,
                    warned=warned,
                )
            else:
                listing = walked(
                    root=root,
                    folder=folder,
                    listings=listings,
                )

            for target in listing.files:
                targets.setdefault(target.relative, target)

            slips += listing.slips
            continue

        if not store.readable_file(path):
            raise CheckError(f"no file at {store.near(str(given))}")

        resolved: Path = within(
            root=root,
            path=path,
            given=given,
        )
        target = target_of(
            root=root,
            path=resolved,
            listings=listings,
        )
        targets.setdefault(target.relative, target)
        named.append(target.relative)

    reasons: dict[str, Optional[str]] = passed_over(
        project=project,
        relatives=list(targets),
    )
    notes = list(warned.values()) + [f"{relative} is passed over, {reasons[relative]}" for relative in dict.fromkeys(named) if reasons[relative] is not None]

    return Listing(
        files=[target for relative, target in targets.items() if reasons[relative] is None],
        slips=list(dict.fromkeys(slips)),
        notes=notes,
    )


def tracked(
    project: Path,
) -> Listing:
    """The project's own markdown files, those git tracks and the new ones it does not ignore, refused in git's words where git cannot list them, each the check passes over left out."""
    root = project.resolve()
    warned: dict[str, str] = {}
    listing: Listing = listed(
        root=root,
        folder=root,
        listings={},
        warned=warned,
    )
    reasons: dict[str, Optional[str]] = passed_over(
        project=project,
        relatives=[target.relative for target in listing.files],
    )

    return Listing(
        files=[target for target in listing.files if reasons[target.relative] is None],
        slips=listing.slips,
        notes=list(warned.values()),
    )


def listed(
    root: Path,
    folder: Path,
    listings: dict[Path, Optional[frozenset[str]]],
    warned: dict[str, str],
) -> Listing:
    """The markdown files git lists under the folder, those it tracks and the new ones it does not ignore, each name once in git's order, refused in git's words where git cannot list them, each folder on the way to one listed once into the run's `listings`.

    Each folder git says it could not open is a slip in words, since git
    lists none of the new files under it, and git names it from the top
    of its work tree. Every other line git says as it lists them is a
    note as it stands, since a git that speaks another language words
    its warning for such a folder where UNOPENED cannot read it, put once
    into the run's `warned` by the line git said, so a line the listings
    of two folders both say is one note.
    """
    where: str = named_from(
        root=root,
        path=folder,
    )
    which_files = "the project's files" if folder == root else f"the files under {where}"
    reply: handover.Reply = answered(
        folder=folder,
        arguments=list(LISTING),
        refusal=f"git cannot list {which_files}",
    )
    names = [name for name in dict.fromkeys(reply.output.split("\0")) if name and is_markdown(name)]
    spelled: list[Optional[str]] = [handover.on_disk(name=name) for name in names]
    listing: Listing = kept_on_disk(
        root=root,
        paths=[folder / name for name in spelled if name is not None],
        listings=listings,
    )

    for line in reply.trouble.split("\n"):
        said = line.strip()
        if said and not UNOPENED.match(line):
            warned.setdefault(said, f"git warned as it listed {which_files}, {said}")

    unopenable: list[tuple[str, str]] = UNOPENED.findall(reply.trouble)
    if not unopenable:
        return listing

    top: handover.Reply = answered(
        folder=folder,
        arguments=["rev-parse", "--show-toplevel"],
        refusal="git cannot say where its work tree starts",
    )
    unopened: list[Slip] = [
        unopened_slip(
            root=root,
            folder=Path(top.output.strip()) / place.rstrip("/"),
            reason=reason,
        )
        for place, reason in unopenable
    ]

    return Listing(
        files=listing.files,
        slips=listing.slips + unopened,
    )


def walked(
    root: Path,
    folder: Path,
    listings: dict[Path, Optional[frozenset[str]]],
) -> Listing:
    """The regular markdown files under a folder outside git, those a dotted folder below it holds left out, in the order of their paths, each folder the walk cannot open a slip in words, and each folder on the way to one listed once into the run's `listings`."""
    paths: list[Path] = []
    unopenable: list[OSError] = []
    walk = os.walk(
        top=folder,
        onerror=unopenable.append,
    )

    for place, folders, names in walk:
        folders[:] = sorted(name for name in folders if not name.startswith("."))
        paths += [Path(place) / name for name in names if is_markdown(name)]

    listing: Listing = kept_on_disk(
        root=root,
        paths=sorted(
            paths,
            key=Path.as_posix,
        ),
        listings=listings,
    )
    unopened: list[Slip] = [
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
    listings: dict[Path, Optional[frozenset[str]]],
) -> Listing:
    """The paths under the root that are regular files on disk by lstat, reached through folders none of which is a link, in their order, one that is gone or is a link, a folder or a pipe now left out, so is one under a folder now a link, and one the disk will not say which of these it is, as in a folder no one may open, a slip in words, each named as the disk spells it with each folder on its way listed once into the run's `listings`."""
    found: list[Target] = []
    slips: list[Slip] = []

    for path in paths:
        try:
            regular: bool = is_regular(
                root=root,
                path=path,
            )
        except OSError as error:
            where: str = named_from(
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
                    listings=listings,
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
    where: str = named_from(
        root=root,
        path=folder,
    )

    return Slip(
        path=where,
        message=f"is a folder that could not be opened, {reason}, so the files under it were not read",
    )


def is_regular(
    root: Path,
    path: Path,
) -> bool:
    """Whether the path under the root is a regular file by lstat, reached through folders that are each a folder by lstat, as git reads a name it lists, so a link, a folder or a pipe of that name is none, and nor is a name under a folder now a link, False where nothing is there, and OSError where the disk will not say."""
    parts = path.relative_to(root).parts
    try:
        for depth in range(1, len(parts)):
            if not stat.S_ISDIR(os.lstat(root.joinpath(*parts[:depth])).st_mode):
                return False

        mode = os.lstat(path).st_mode
    except (FileNotFoundError, NotADirectoryError):
        return False

    return stat.S_ISREG(mode)


def check_file(
    project: Path,
    path: Path,
) -> Checked:
    """The slips of one file, as the post write hook asks of each file written, and the notes its caller says beside them, none of them a slip, nothing for one the check passes over or one outside the project.

    Where git cannot read the attributes, the file is not checked, and
    the note says so in git's words apart from the slips, so the caller
    says the check did not run on it and never names a slip no edit of
    the file can put right, and a hook that raised would lose the rest.
    """
    nothing = Checked(
        slips=[],
        notes=[],
    )
    root = project.resolve()
    resolved: Optional[Path] = within_project(
        root=root,
        path=path,
    )
    if resolved is None:
        return nothing

    target: Target = target_of(
        root=root,
        path=resolved,
        listings={},
    )

    try:
        reasons: dict[str, Optional[str]] = passed_over(
            project=project,
            relatives=[target.relative],
        )
    except CheckError as error:
        refused = Checked(
            slips=[],
            notes=[f"{target.relative} is not checked, {error}"],
        )

        return refused

    if reasons[target.relative] is not None:
        return nothing

    return Checked(
        slips=slips_of(
            target=target,
        ),
        notes=[],
    )


def slips_of(
    target: Target,
) -> list[Slip]:
    """The slips of a markdown file the check judges, read as UTF-8 with a leading byte order mark dropped and a CRLF or a lone CR read as a line end, or the one slip that it cannot be read."""
    relative = target.relative
    try:
        data = target.path.read_bytes()
    except OSError as error:
        unread = Slip(
            path=relative,
            message=f"cannot be read, {store.explain(error)}",
        )

        return [unread]

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
    resolved: Optional[Path] = within_project(
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
    """The path resolved, or None where that lies outside the project or cannot be resolved.

    A path that reads outside only by its case is spelled as the disk
    spells it and asked again, so on a disk that folds case another case
    of the project is the project, and the folders are listed only then.
    """
    try:
        resolved = path.resolve()
    except (OSError, RuntimeError, ValueError):
        return None

    if is_under(path=resolved, root=root):
        return resolved

    spelled = store.as_on_disk(resolved)

    return spelled if is_under(path=spelled, root=root) else None


def is_under(
    path: Path,
    root: Path,
) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False

    return True


def target_of(
    root: Path,
    path: Path,
    listings: dict[Path, Optional[frozenset[str]]],
) -> Target:
    """A file inside the project with its name from the project, by the file it resolves to as the disk spells it, so one file goes by one name however it was given and the tests of which files are judged run on that name.

    Each folder on the way is listed once into `listings`, which the
    caller keeps for the files of one run, and a name each of whose
    parts its folder holds as given is the disk's spelling already, as
    doctor's spelling would answer, so that spelling, which lists every
    folder on the way again for each file, is asked of a name the disk
    spells otherwise alone.
    """
    resolved = path.resolve()
    relative: str = named_from(
        root=root,
        path=resolved,
    )
    as_given: bool = spelled_as_given(
        root=root,
        relative=relative,
        listings=listings,
    )
    if as_given:
        spelled: Optional[str] = relative
    else:
        spelled = doctor.spelled_on_disk(
            base=root,
            path=relative,
        )

    return Target(
        path=resolved,
        relative=spelled or relative,
    )


def spelled_as_given(
    root: Path,
    relative: str,
    listings: dict[Path, Optional[frozenset[str]]],
) -> bool:
    """Whether each part of the name is an entry of its folder exactly as given, or sits in a folder that cannot be listed, which doctor's spelling takes as given too, each folder listed once into `listings`, None for one that cannot be."""
    folder = root
    for part in relative.split("/"):
        if folder not in listings:
            try:
                listings[folder] = frozenset(os.listdir(folder))
            except OSError:
                listings[folder] = None

        entries = listings[folder]
        if entries is not None and part not in entries:
            return False

        folder = folder / part

    return True


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

    A file is judged where it is markdown by its suffix in any case,
    the brain tool does not write it, the kit does not write it
    whole in a project, and git's attributes do not mark it generated or
    vendored, which outside git marks no file. Where git cannot read the
    attributes, the check is refused in git's words.
    """
    reasons: dict[str, Optional[str]] = {relative: None if is_markdown(relative) else NOT_MARKDOWN for relative in relatives}
    to_judge = [relative for relative, reason in reasons.items() if reason is None]
    if not to_judge:
        return reasons

    kit_checkout: bool = is_kit_checkout(project)
    stamp: tuple[int, ...] = store.stamp_of(project / BRAIN_FOLDER) or schema.as_tuple(schema.NO_VERSION)
    for relative in to_judge:
        if is_tools(relative):
            reasons[relative] = TOOLS_OWN
            continue

        from_kit: bool = written_by_kit(
            relative=relative,
            stamp=stamp,
        )
        if from_kit and not kit_checkout:
            reasons[relative] = KITS_OWN

    unmarked = [relative for relative in to_judge if reasons[relative] is None]
    marks: dict[str, str] = marked(
        project=project,
        relatives=unmarked,
    )
    for relative, attribute in marks.items():
        reasons[relative] = f"git's attributes mark it {attribute}"

    return reasons


def is_markdown(
    name: str,
) -> bool:
    """Whether the name ends in the one suffix the check reads, markdown, whatever its case."""
    return PurePosixPath(name).suffix.lower() == MARKDOWN


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
        reply: handover.Reply = answered(
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
REVIEWS: str = schema.KINDS["review"].folder


def is_tools(
    relative: str,
) -> bool:
    """Whether the file is one the brain tool writes whole where it writes it, in a project and in the kit's own checkout alike, the index at the brain's root and in each folder it indexes, a review ledger, and the handover note.

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


# The files at the project's top the kit writes whole, AGENTS.md among
# them since the project's own words are its rules, and the chat style
# in each agent folder, the source and doctor's copies.
KIT_ROOT_FILES: tuple[str, ...] = schema.ROOT_FILES
CHAT_STYLE: tuple[str, ...] = tuple(path.as_posix() for path in (style.SOURCE, *style.COPIES))
# the kit's Rust rule, which doctor writes whole from the tool's template in a project with Rust
KIT_RULE = f"{BRAIN_FOLDER}/rules/rust.md"


def written_by_kit(
    relative: str,
    stamp: tuple[int, ...],
) -> bool:
    """Whether a project stamped `stamp` holds the file from the kit, which the next upgrade writes back whole, so a slip there is the kit's and never the project's.

    The upgrade's own test decides, so a kit skill's folder and a sub
    agent definition are the kit's from the release that shipped each
    on, and one of that name in a project stamped older is the project's
    own and judged.
    """
    if relative in KIT_ROOT_FILES or relative in CHAT_STYLE or relative == KIT_RULE:
        return True

    definition: Optional[schema.Definition] = next(
        (definition for skill in schema.KIT_SKILLS for definition in skill.definitions if definition.path == relative),
        None,
    )
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

    skill: Optional[schema.KitSkill] = upgrade.kit_skill_named(parts[2]) if len(parts) > 3 and parts[1] == schema.SKILLS else None

    return skill is not None and schema.ships(
        skill=skill,
        stamp=stamp,
    )


def markdown_slips(
    relative: str,
    text: str,
) -> list[Slip]:
    """The prose slips of a markdown file, line by line as it renders, its header block, its code, its raw HTML and its literal text stepped over.

    The code is found by the one reader in sections, with the quote
    markers taken off first so code inside a quote is found too, and
    each region is blanked in place so the line numbers hold. A line is
    judged with its quote markers and its literal text taken off and the
    character references CommonMark reads turned to the characters they
    render, beside the line as written, whose spaces alone stand beside
    two hyphens typed for a dash and whose marker alone, where the
    reading did not step over it, opens a list item, so code or a tag
    turned to spaces is never read as either, and beside the line with
    its code alone turned to spaces, so a sentence a code span opens is
    told from one that opens past a tag.
    """
    reading: Reading = read_markdown(text)
    prose = reading.prose

    found: list[Slip] = []
    for number, (line, typed, codeless) in enumerate(
        iterable=zip(prose.split("\n"), text.split("\n"), reading.codeless.split("\n")),
        start=1,
    ):
        bare = QUOTE.sub(
            repl="",
            string=line,
        )
        if not bare.strip():
            continue

        quote_width = len(line) - len(bare)
        written = typed[quote_width:]
        judged: str = literal_blanked(bare)
        rendered: str = as_rendered(
            text=as_judged(
                judged=judged,
                written=written,
            ),
        )
        if EM_DASH in rendered or TYPED_EM_DASH.search(rendered):
            found.append(
                Slip(
                    path=relative,
                    line=number,
                    message="carries a dash the house style bans, write a comma, a period or the word",
                ),
            )

        if ";" in rendered:
            found.append(
                Slip(
                    path=relative,
                    line=number,
                    message="carries a semicolon, write two sentences",
                ),
            )

        colon_message: Optional[str] = colon_slip(
            written=written,
            judged=judged,
            codeless=codeless[quote_width:],
            heading=number in reading.headings,
            table=number in reading.tables,
        )
        if colon_message is not None:
            found.append(
                Slip(
                    path=relative,
                    line=number,
                    message=colon_message,
                ),
            )

    return found


def as_judged(
    judged: str,
    written: str,
) -> str:
    """The judged line with each character the reading turned to a space, where the line as written holds another, marked STEPPED_OVER."""
    return "".join(STEPPED_OVER if kept != typed else kept for kept, typed in zip(judged, written))


def as_rendered(
    text: str,
) -> str:
    """The text with each character reference CommonMark reads turned to the character it renders, one with no closing semicolon, a name HTML does not know or an ampersand escaped with a backslash kept as typed."""
    return REFERENCE.sub(
        repl=rendered_reference,
        string=text,
    )


def rendered_reference(
    found: "re.Match[str]",
) -> str:
    """What a reference or a backslash escape the REFERENCE pattern found renders as, the escape as typed."""
    reference = found.group()
    if reference.startswith("\\"):
        return reference

    if reference.startswith("&#"):
        return html.unescape(reference)

    return html.entities.html5.get(reference[1:], reference)


def rendered_with_origins(
    text: str,
) -> tuple[str, list[int]]:
    """The text as as_rendered gives it, with where in the text each of its characters comes from, so a place in the rendered text finds its place in the line as written."""
    shown: list[str] = []
    origins: list[int] = []
    cursor = 0
    for found in REFERENCE.finditer(text):
        rendered: str = rendered_reference(found)
        shown += [text[cursor : found.start()], rendered]
        origins += [*range(cursor, found.start()), *[found.start()] * len(rendered)]
        cursor = found.end()

    shown.append(text[cursor:])
    origins += range(cursor, len(text))

    return "".join(shown), origins


@dataclass(frozen=True)
class Reading:
    """A markdown file as the prose check reads it, its text with what is stepped over turned to spaces and every line end kept, the text with its code alone turned to spaces, and the numbers of the lines a heading takes and of the lines of its tables."""

    prose: str
    codeless: str
    headings: frozenset[int]
    tables: frozenset[int]


@dataclass(frozen=True)
class Unquoted:
    """A text with the quote markers taken off each line outside a block of code, where each line starts in it, how far the start of each has moved from the text's by then, and where each run of quoted lines starts and ends in it."""

    text: str
    starts: list[int]
    moved: list[int]
    quotes: list[tuple[int, int]]

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
    """The text with its header block, its code, its HTML comments and its raw HTML turned to spaces, each region once, the text with its code alone turned to spaces, and the lines its headings and its tables take.

    The header goes first, so no code or heading is read in it. The code
    is the one reader's in sections, over the text and over each run of
    quoted lines alone with the quote markers taken off, but for a line
    that starts inside a block of code the reading over the text found,
    so code inside a quote is found and a fence left open in one ends
    where the quote does, as CommonMark closes it, and a span that
    reading pairs across a quote's lines never cuts the quote. The raw
    HTML is read where the code and the comments leave text, a raw block
    opened in a quote ending with the quote too. The tables are read
    from what is left, and the headings from the text as written, its
    header aside, so code or a tag keeps the shape of the line it opens,
    each over the lines of one depth of quote apart, by the markers a
    line is written with, and a lazy line read with the quote's
    paragraph it goes on with.
    """
    header: Optional[tuple[int, int]] = header_span(text)
    hidden: list[tuple[int, int]] = [] if header is None else [header]
    body: str = sections.blanked(
        text=text,
        spans=hidden,
    )

    outside: list[tuple[int, int]] = sections.code_spans(body)
    plain: Unquoted = unquoted(
        text=body,
        code=sections.blocks_of(body).code,
    )
    inside: list[tuple[int, int]] = [(plain.origin(quote_start + start), plain.origin(quote_start + end)) for quote_start, quote_end in plain.quotes for start, end in sections.code_spans(plain.text[quote_start:quote_end])]
    code: list[tuple[int, int]] = merged(outside + inside)
    hidden += code + sections.comment_spans(
        text=body,
        spans=code,
    )

    rest: str = sections.blanked(
        text=text,
        spans=merged(hidden),
    )
    hidden += html_regions(
        text=rest,
        quotes=[(plain.origin(quote_start), plain.origin(quote_end)) for quote_start, quote_end in plain.quotes],
    )

    regions: list[tuple[int, int]] = merged(hidden)
    prose: str = sections.blanked(
        text=text,
        spans=regions,
    )

    written = body.split("\n")
    depths, widths = quote_depths(
        lines=written,
        regions=regions,
    )
    unmarked = [line[width:] for line, width in zip(written, widths)]
    bares = [line[width:] for line, width in zip(prose.split("\n"), widths)]

    # the tables first, against the headings of hashes alone, each one line, since a line of hyphens under a table is a thematic break and makes no setext heading of it
    before_tables: list[tuple[int, int]] = headings_in(
        bares=unmarked,
        depths=depths,
        blank=frozenset(),
    )
    atx = frozenset(first for first, last in before_tables if first == last)
    tables: frozenset[int] = table_rows(
        bares=bares,
        headings=atx,
        depths=depths,
    )

    lazy_depths: list[int] = depths_with_lazy_lines(
        lines=unmarked,
        depths=depths,
        tables=tables,
    )
    headings = frozenset(
        number
        for first, last in headings_in(
            bares=unmarked,
            depths=lazy_depths,
            blank=tables,
        )
        for number in range(first, last + 1)
    )

    return Reading(
        prose=prose,
        codeless=sections.blanked(
            text=text,
            spans=code,
        ),
        headings=headings,
        tables=tables,
    )


def quote_depths(
    lines: list[str],
    regions: list[tuple[int, int]],
) -> tuple[list[int], list[int]]:
    """The depth of quote each line sits at, by the markers it is written with, and how many of its first characters the markers of that depth take.

    A line that starts inside a region the reading stepped over, opened
    on a line above, sits at the depth of the line the region opened on,
    since code, a comment or raw HTML never runs out of the quote it
    opens in, so the markers it is written with past that depth are the
    region's own text, and one it lacks makes it a lazy line of that
    quote. The regions are in order and none overlaps another.
    """
    opened = [start for start, _ in regions]
    starts: list[int] = []
    depths: list[int] = []
    widths: list[int] = []
    start = 0

    for line in lines:
        starts.append(start)
        before = bisect.bisect_left(
            a=opened,
            x=start,
        )
        if before > 0 and start < regions[before - 1][1]:
            opener = bisect.bisect_right(
                a=starts,
                x=regions[before - 1][0],
            )
            depth = depths[opener - 1]
        else:
            marked = QUOTE.match(line)
            depth = 0 if marked is None else marked.group().count(">")

        depths.append(depth)
        widths.append(
            markers_width(
                line=line,
                depth=depth,
            ),
        )
        start += len(line) + 1

    return depths, widths


def markers_width(
    line: str,
    depth: int,
) -> int:
    """How many of the line's first characters its first `depth` quote markers take, or all it has where it has fewer."""
    width = 0
    for _ in range(depth):
        marker = QUOTE_MARKER.match(
            string=line,
            pos=width,
        )
        if marker is None:
            break

        width = marker.end()

    return width


def unquoted(
    text: str,
    code: list[tuple[int, int]],
) -> Unquoted:
    """The text with the quote markers taken off each line, however deep, but a line that starts inside one of the blocks of code given, which keeps what it holds, and the runs of lines it took markers from."""
    kept: list[str] = []
    starts: list[int] = []
    moved: list[int] = []
    quotes: list[tuple[int, int]] = []
    taken = 0
    offset = 0
    quoted_above = False

    for line in text.split("\n"):
        marked = QUOTE.match(line)
        marker_width = 0
        if marked is not None and not sections.in_code(
            spans=code,
            position=offset,
        ):
            marker_width = marked.end()

        start = offset - taken
        starts.append(start)
        taken += marker_width
        moved.append(taken)
        kept.append(line[marker_width:])
        offset += len(line) + 1

        if marker_width and quoted_above:
            quotes[-1] = (quotes[-1][0], start + len(line) - marker_width)
        elif marker_width:
            quotes.append((start, start + len(line) - marker_width))

        quoted_above = marker_width > 0

    return Unquoted(
        text="\n".join(kept),
        starts=starts,
        moved=moved,
        quotes=quotes,
    )


def headings_in(
    bares: list[str],
    depths: list[int],
    blank: frozenset[int],
) -> list[tuple[int, int]]:
    """The numbers of the first and the last line of each heading, read by the one reader in sections over each run of lines at one depth of quote apart, so a line outside a quote or at another depth is never a setext underline to a quote's paragraph, and with the lines `blank` names read as blank."""
    found: list[tuple[int, int]] = []
    for _, run in itertools.groupby(
        iterable=range(len(bares)),
        key=depths.__getitem__,
    ):
        numbers = list(run)
        text = "\n".join("" if number + 1 in blank else bares[number] for number in numbers)
        first = numbers[0] + 1
        found += [(first + text.count("\n", 0, heading.start), first + text.count("\n", 0, heading.end)) for heading in sections.blocks_of(text).headings]

    return found


# A line of an open paragraph, which a line is read under to ask the one
# reader in sections whether that line goes on with a paragraph.
OPEN_PARAGRAPH = "text"


def depths_with_lazy_lines(
    lines: list[str],
    depths: list[int],
    tables: frozenset[int],
) -> list[int]:
    """The depth of quote each line belongs to, each lazy line, one with fewer quote markers than the line above that goes on with the quote's paragraph, at the depth of that paragraph.

    A line goes on with the paragraph the line above it ends where that
    line ends a run of its depth inside an open paragraph, or is itself
    lazy, neither line is a table's, and the one reader in sections
    reads the line under a paragraph's line as more of that paragraph,
    so a line that opens a block, or underlines a heading, which
    CommonMark never lets a lazy line do, keeps the depth it is written
    at.
    """
    open_at_end: frozenset[int] = paragraphs_open_at_end(
        lines=lines,
        depths=depths,
    )
    found = list(depths)
    for index in range(1, len(lines)):
        above = index - 1
        # the tables number their lines from one
        if depths[index] >= found[above] or index in tables or index + 1 in tables:
            continue

        continued = above in open_at_end or found[above] != depths[above]
        if continued and goes_on_with_a_paragraph(lines[index]):
            found[index] = found[above]

    return found


def paragraphs_open_at_end(
    lines: list[str],
    depths: list[int],
) -> frozenset[int]:
    """The index of each line that ends a run of lines at one depth of quote inside a paragraph still open there, as the one reader in sections reads the run, and so neither inside code or a comment nor a heading's."""
    found: set[int] = set()
    for _, run in itertools.groupby(
        iterable=range(len(lines)),
        key=depths.__getitem__,
    ):
        numbers = list(run)
        text = "\n".join(lines[number] for number in numbers)
        blocks: sections.Blocks = sections.blocks_of(text)
        still_open = any(end == len(text) for _, end in blocks.inline) and not any(heading.end == len(text) for heading in blocks.headings)
        if still_open:
            found.add(numbers[-1])

    return frozenset(found)


def goes_on_with_a_paragraph(
    line: str,
) -> bool:
    """Whether the one reader in sections reads the line, straight under a line of an open paragraph, as more of that paragraph, so a blank line, one that opens a block of its own and one that underlines the paragraph as a heading do not."""
    pair = f"{OPEN_PARAGRAPH}\n{line}"
    blocks: sections.Blocks = sections.blocks_of(pair)

    return not blocks.headings and blocks.inline == [(0, len(pair))]


def html_regions(
    text: str,
    quotes: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """Where the raw HTML sits in a text whose code and comments are blanked, a raw block first, to its closing tag or the end of the quote it opened in, then an element of code in what the blocks leave, then each other tag."""
    blocks: list[tuple[int, int]] = []
    for opened in RAW_BLOCK.finditer(text):
        if blocks and opened.start() < blocks[-1][1]:
            continue

        bound = next((last for first, last in quotes if first <= opened.end() <= last), len(text))
        closing = re.compile(
            pattern=rf"</{opened.group(1)}\s*>",
            flags=re.IGNORECASE,
        )
        closer = closing.search(
            string=text,
            pos=opened.end(),
            endpos=bound,
        )
        end = bound if closer is None else closer.end()

        blocks.append((opened.start(), end))

    rest: str = sections.blanked(
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
    depths: list[int],
) -> frozenset[int]:
    """The numbers of the lines that are rows of a table as GitHub reads one, the header row straight above a delimiter row, a row of cells of hyphens and at least one pipe, that row, and the rows after it up to a blank line, a heading, a line with no pipe or the end of the quote the table sits in.

    A line above the header row, a heading among them, is no row, and a
    delimiter row with no header row above it, a blank line, a heading
    or a line at another depth of quote there, opens no table.
    """
    found: set[int] = set()
    for number, bare in enumerate(
        iterable=bares,
        start=1,
    ):
        if number in found or "|" not in bare or not DELIMITER_ROW.match(bare):
            continue

        depth = depths[number - 1]
        header = number - 1
        if header < 1 or not bares[header - 1].strip() or header in headings or depths[header - 1] != depth:
            continue

        found.update((header, number))
        row = number + 1
        while row <= len(bares) and "|" in bares[row - 1] and row not in headings and depths[row - 1] == depth:
            found.add(row)
            row += 1

    return frozenset(found)


def colon_slip(
    written: str,
    judged: str,
    codeless: str,
    heading: bool,
    table: bool,
) -> Optional[str]:
    """Why the line's colon is not a list item's label, or None when the line carries none that is not, its literal text blanked in what is judged, a table row taking any, and a list item opened by a marker the line as written holds and the reading did not step over, so neither a tag or code turned to spaces before a hyphen nor a marker inside a comment opened on a line above opens one, with the line's code alone turned to spaces in `codeless`."""
    rendered: str = as_rendered(judged)
    if ":" not in rendered or table:
        return None

    if heading:
        return "carries a colon in a heading, which takes none"

    marked: str = as_judged(
        judged=judged,
        written=written,
    )
    list_marker = LIST_ITEM.match(written)
    if list_marker is None or STEPPED_OVER in marked[: list_marker.end()]:
        return "carries a colon mid sentence, which the house style keeps for a list item's label"

    item_text, origins = rendered_with_origins(marked[list_marker.end() :])
    past_a_sentence: bool = holds_a_sentence_end(
        label=item_text[: item_text.index(":")],
        origins=origins,
        written=written[list_marker.end() :],
        codeless=codeless[list_marker.end() :],
    )
    if past_a_sentence:
        return "carries a colon mid sentence, past the sentence that opens the list item, which the house style keeps for the item's label"

    if item_text.count(":") > 1:
        return "carries a second colon in a list item, past the one that ends its label"

    return None


# A label ends at the item's first colon and holds no sentence, so a
# colon past a sentence's end sits mid sentence however the item opens,
# a bold label that ends in one too. Both are read on the line as it
# renders. A sentence ends at a period, a question mark or an
# exclamation mark, any closing emphasis after it, then a space and an
# upper case letter, the period of a known abbreviation aside. The
# letter may follow what opens emphasis, a link, a parenthesis, a quote
# or a code span, and where the reading stepped over what follows the
# marks, a code span, the letter is read on the line as written. Each
# other thing it stepped over, a tag, a comment, a shortcode or literal
# text, reads as the spaces it was turned to before the line is judged,
# so a sentence opens at the letter past it.
SENTENCE_END = re.compile(r"[.!?][*_]*[ \t]+")
SENTENCE_OPENING = re.compile(r"[*_\[(\"'`\u201c\u2018]*")
ABBREVIATION = re.compile(r"(?<![\w.])(?:e\.g|i\.e|etc|cf|vs|Dr|Mr|Mrs|Ms|St|No|Fig|Inc|Ltd|Co|Jr|Sr)\.$")


def holds_a_sentence_end(
    label: str,
    origins: list[int],
    written: str,
    codeless: str,
) -> bool:
    """Whether a list item's label, read as it renders with what the reading stepped over marked STEPPED_OVER, holds the end of a sentence, the upper case letter after its opening marks read there, or on the line as written, from where `origins` places it, where the marks reach a code span, which `codeless` alone turns to spaces, and each other thing stepped over read as a space."""
    spaced = "".join(" " if character == STEPPED_OVER and codeless[origins[place]] == written[origins[place]] else character for place, character in enumerate(label))
    for sentence_end in SENTENCE_END.finditer(spaced):
        opened = SENTENCE_OPENING.match(
            string=spaced,
            pos=sentence_end.end(),
        ).end()
        if opened < len(spaced) and spaced[opened] == STEPPED_OVER:
            typed = SENTENCE_OPENING.match(
                string=written,
                pos=origins[opened],
            ).end()
            upper = typed < len(written) and written[typed].isupper()
        else:
            upper = opened < len(spaced) and spaced[opened].isupper()

        if not upper:
            continue

        if spaced[sentence_end.start()] == "." and ABBREVIATION.search(spaced[: sentence_end.start() + 1]):
            continue

        return True

    return False


def check_commits(
    project: Path,
) -> Checked:
    """The commits of HEAD that no main git knows reaches, the local one or a remote's, each read for a co-author line or an AI attribution, or no slip and the note that they were not read and why, where git cannot say or knows no main.

    Each record ends at a NUL byte, which no message can hold, and the
    signature the owner's config may show is left out, so neither a
    message nor a signature is read as a commit's hash.
    """
    try:
        known: handover.Reply = answered(
            folder=project,
            arguments=["for-each-ref", "--format=%(refname)", *BASE_PREFIXES],
            refusal=UNREAD,
            seconds=handover.GIT_SECONDS,
        )
        bases = [name for name in known.output.split() if BASE.fullmatch(name)]
        if not bases:
            unknown = Checked(
                slips=[],
                notes=[f"{UNREAD}, git knows no {MAIN} branch here, local or a remote's, to read them against"],
            )

            return unknown

        log: handover.Reply = answered(
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
    """Git's reply for the folder through the shared runner, waiting as long as git takes unless the seconds are given, as the upgrade's calls over the whole tree do, or the check refused in the words given and what git said, git run with neither the variables of its language nor those of a trace."""
    try:
        reply: handover.Reply = handover.git(
            project=folder,
            arguments=arguments,
            seconds=seconds,
            unset=LOCALE | frozenset(name for name in os.environ if name.startswith(TRACE)),
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
