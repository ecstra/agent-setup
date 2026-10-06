"""The house rules a machine can hold a file to, over the project's own files.

Doctor reads the brain against its specs. This reads the code and the
prose of the whole project against the rules of SYSTEM.md a machine
can judge without reading for meaning: the prose by line, a dash the
house style bans, a semicolon, a colon anywhere but a list item's label,
with the code stepped over, and Python by its structure, the future
import of annotations the 3.9 floor does not take, a def whose
parameters do not sit one per line with a trailing comma, and a call
already broken across lines not held to the same. The branch's commit
messages are read too, for a co-author line or an AI attribution. It
reports and never rewrites, since none of these has one mechanical
repair, and the post write hook runs it on the file just written so
the slip is fixed in the same round.
"""

import ast
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import doctor, frontmatter, schema, store

MARKDOWN = ".md"
PYTHON = ".py"
MAIN = "main"
BRAIN_FOLDER = ".agents"

# What a line of prose may not carry: the dashes the house style bans,
# a semicolon, and a colon outside a list item's label.
DASHES = ("\u2014", "\u2013")
URL = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://\S+")
CLOCK = re.compile(r"\d:\d\d")
LIST_ITEM = re.compile(r"^[ \t]*(?:[-*+]|\d{1,9}[.)])[ \t]+")
HEADING = re.compile(r"^[ \t]{0,3}#{1,6}(?:[ \t]|$)")
TABLE_ROW = re.compile(r"^[ \t]*\|")
QUOTE = re.compile(r"^[ \t]{0,3}>[ \t]?")
FUTURE_ANNOTATIONS = "annotations"
TRAILING_COMMA = re.compile(r",[ \t]*(#.*)?$")

# What a commit message may not carry, per SYSTEM.md 10.1.
CO_AUTHOR = re.compile(r"(?im)^\s*co-authored-by\s*:")
ATTRIBUTION = re.compile(r"(?i)generated with .*claude|\U0001F916")

# The parameters a def may keep on its own line, since a method with
# nothing but its receiver has nothing to stack.
RECEIVERS = ("self", "cls")


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

        return f"{where}: {self.message}"


def run(
    project: Path,
    paths: Optional[list[Path]] = None,
    with_commits: bool = True,
) -> list[Slip]:
    """Every slip in the files given, or in the tracked tree, and in the branch's commits when asked."""
    files = chosen(project=project, paths=paths) if paths else tracked(project)
    found: list[Slip] = []

    for path in files:
        found += check_file(project=project, path=path)

    if with_commits and not paths:
        found += check_commits(project)

    return found


def chosen(
    project: Path,
    paths: list[Path],
) -> list[Path]:
    """The files the paths name, a folder standing for the markdown and Python under it, each once, in the order given."""
    found: list[Path] = []
    for given in paths:
        path = given if given.is_absolute() else Path.cwd() / given
        if store.quietly(path.is_dir):
            candidates = sorted(child for child in path.rglob("*") if child.suffix in (MARKDOWN, PYTHON) and not store.hidden(child.relative_to(path)))
        elif store.readable_file(path):
            candidates = [path]
        else:
            raise CheckError(f"no file at {store.near(str(given))}")

        found += [candidate for candidate in candidates if candidate not in found]

    return found


def tracked(
    project: Path,
) -> list[Path]:
    """Every markdown and Python file git tracks in the project, refused where git cannot list them."""
    listing = git(project=project, arguments=["ls-files", "-z"])
    if listing is None:
        raise CheckError("git cannot list the tracked files here, so give the paths to check")

    return [project / name for name in listing.split("\0") if name and name.endswith((MARKDOWN, PYTHON))]


def check_file(
    project: Path,
    path: Path,
) -> list[Slip]:
    """The slips of one file, by its suffix, nothing for a file that is not markdown or Python, that the kit wrote, or that the tool writes.

    An index is the tool's rendering of other files' header values, and
    a review ledger is the tool's record, whose claims name a file by
    its line with a colon, so neither is read.
    """
    relative = relative_of(project=project, path=path)
    if is_kits(project=project, relative=relative) or is_tools(relative):
        return []

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return [Slip(path=relative, message=f"cannot be read as UTF-8 text, {store.explain(error)}")]

    if path.suffix == MARKDOWN:
        return markdown_slips(relative=relative, text=text, own_words_only=relative == "AGENTS.md" and not is_kit_checkout(project))

    if path.suffix == PYTHON:
        return python_slips(relative=relative, text=text)

    return []


def relative_of(
    project: Path,
    path: Path,
) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except (OSError, ValueError, RuntimeError):
        return store.near(str(path))


def is_kit_checkout(
    project: Path,
) -> bool:
    """Whether the project is the kit's own checkout, which is where the tool's tests live, since they ship nowhere else."""
    return store.quietly((project / BRAIN_FOLDER / schema.SKILLS / "agent-brain" / "scripts" / "tests").is_dir)


def is_tools(
    relative: str,
) -> bool:
    """Whether the file is one the brain tool writes whole inside the brain, an index or a review ledger."""
    parts = relative.split("/")
    if parts[0] != BRAIN_FOLDER or len(parts) < 2:
        return False

    if parts[-1] == schema.INDEX:
        return True

    return parts[1] == "reviews" and parts[-1] == schema.LEDGER


def is_kits(
    project: Path,
    relative: str,
) -> bool:
    """Whether the file is one the kit writes whole into a project, which the next upgrade writes back, so a slip there is the kit's and never the project's.

    In the kit's own checkout every file is the work and nothing is
    skipped.
    """
    if is_kit_checkout(project):
        return False

    parts = relative.split("/")
    if relative in ("CLAUDE.md", "GEMINI.md", "CONTRIBUTING.md"):
        return True

    if parts[0] == BRAIN_FOLDER and len(parts) > 1:
        inside = "/".join(parts[1:])
        if schema.is_kit_path(inside) and parts[1] != schema.INDEX:
            return True

        if parts[1] == schema.SKILLS and len(parts) > 2 and parts[2] in schema.KIT_SKILL_NAMES:
            return True

    return relative in KIT_AGENT_FILES


# The files the kit copies into the agent folders, which the upgrade
# writes back: the sub agent definitions and the chat style in each form.
KIT_AGENT_FILES: frozenset[str] = frozenset(
    {definition.path for skill in schema.KIT_SKILLS for definition in skill.definitions}
    | {".claude/output-styles/plain-and-short.md", ".codex/plain-and-short.md", ".gemini/plain-and-short.md"},
)


def markdown_slips(
    relative: str,
    text: str,
    own_words_only: bool = False,
) -> list[Slip]:
    """The prose slips of a markdown file, line by line, its header block and its code stepped over.

    The code is found the way doctor finds it in a front door, fences,
    indented blocks, spans and HTML comments, and blanked in place so
    the line numbers hold. In a project's AGENTS.md only the words above
    the kit's marker are the project's to put right.
    """
    prose = prose_of(text)
    if own_words_only:
        # the marker is an HTML comment, blanked in the prose, so it is found in the text, whose offsets the prose keeps
        mark = text.find(KIT_MARK)
        if mark != -1:
            prose = prose[:mark]

    found: list[Slip] = []
    for number, line in enumerate(prose.split("\n"), start=1):
        if not line.strip():
            continue

        bare = QUOTE.sub("", line)
        judged = CLOCK.sub("", URL.sub("", bare))
        if any(dash in judged for dash in DASHES):
            found.append(Slip(path=relative, line=number, message="carries a dash the house style bans, write a comma, a period or the word"))

        if ";" in judged:
            found.append(Slip(path=relative, line=number, message="carries a semicolon, write two sentences"))

        colon = colon_slip(bare=bare, judged=judged)
        if colon is not None:
            found.append(Slip(path=relative, line=number, message=colon))

    return found


KIT_MARK = "<!-- The kit's words start here. Section 0 goes above this line. -->"


def prose_of(
    text: str,
) -> str:
    """The text with its header block, its code and its HTML comments turned to spaces, every line end kept."""
    header = header_span(text)
    regions = list(doctor.hidden_regions(text).regions)
    if header is not None:
        regions.append((header[0], header[1], doctor.IN_CODE))

    return doctor.blanked(text=text, regions=regions, kinds=(doctor.IN_CODE, doctor.IN_COMMENT))


def header_span(
    text: str,
) -> Optional[tuple[int, int]]:
    """Where a header block opened on the first line runs, fences included, or None when the text opens with none."""
    if not text.startswith(frontmatter.FENCE + "\n"):
        return None

    rest = text[len(frontmatter.FENCE) + 1 :]
    closing = frontmatter.find_closing_fence(rest)
    if closing is None:
        return None

    return 0, len(frontmatter.FENCE) + 1 + closing + len(frontmatter.FENCE)


def colon_slip(
    bare: str,
    judged: str,
) -> Optional[str]:
    """Why the line's colon is not a list item's label, or None when the line carries none that is not."""
    if ":" not in judged or TABLE_ROW.match(bare):
        return None

    if HEADING.match(bare):
        return "carries a colon in a heading, which takes none"

    item = LIST_ITEM.match(bare)
    if item is None:
        return "carries a colon mid sentence, which the house style keeps for a list item's label"

    text = judged[item.end() :]
    if SENTENCE_END.search(text[: text.index(":")]):
        return "carries a colon mid sentence, past the sentence that opens the list item, which the house style keeps for the item's label"

    if text.count(":") > 1:
        return "carries a second colon in a list item, past the one that ends its label"

    return None


# A label ends at the item's first colon and holds no sentence, so a
# colon after a period, a question mark or an exclamation mark sits mid
# sentence however the item opens, a bold label that ends in one too.
SENTENCE_END = re.compile(r"[.!?][*_]*[ \t]")


def python_slips(
    relative: str,
    text: str,
) -> list[Slip]:
    """The structural slips of a Python file, read from its syntax tree, or the one slip that it does not parse."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError) as error:
        return [Slip(path=relative, line=getattr(error, "lineno", 0) or 0, message=f"does not parse, {error.msg if isinstance(error, SyntaxError) else error}")]

    lines = text.split("\n")
    found: list[Slip] = []
    for node in walk_outside_strings(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "__future__" and any(alias.name == FUTURE_ANNOTATIONS for alias in node.names):
            found.append(Slip(path=relative, line=node.lineno, message="imports annotations from __future__, write the types the 3.9 floor reads"))

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found += def_slips(relative=relative, node=node, lines=lines)

        if isinstance(node, ast.Call):
            found += call_slips(relative=relative, node=node, lines=lines)

    return sorted(found, key=lambda slip: (slip.line, slip.message))


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
    lines: list[str],
) -> list[Slip]:
    """A def's parameters one per line below the def's own line, with a trailing comma after the last, a receiver alone aside."""
    arguments = node.args
    parameters = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]
    if arguments.vararg is not None:
        parameters.append(arguments.vararg)
    if arguments.kwarg is not None:
        parameters.append(arguments.kwarg)

    if not parameters or (len(parameters) == 1 and parameters[0].arg in RECEIVERS):
        return []

    starts = [parameter.lineno for parameter in parameters]
    if node.lineno in starts or len(set(starts)) != len(starts):
        return [Slip(path=relative, line=node.lineno, message=f"def {node.name} does not stack its parameters one per line with a trailing comma")]

    ends = [parameter.end_lineno or parameter.lineno for parameter in parameters]
    ends += [default.end_lineno or default.lineno for default in [*arguments.defaults, *arguments.kw_defaults] if default is not None]
    last = max(ends)
    if not TRAILING_COMMA.search(lines[last - 1]):
        return [Slip(path=relative, line=last, message=f"def {node.name} has no trailing comma after its last parameter")]

    return []


def call_slips(
    relative: str,
    node: ast.Call,
    lines: list[str],
) -> list[Slip]:
    """A call already broken across lines keeps its arguments one per line with a trailing comma, a lone generator aside, which takes none."""
    arguments: list[ast.AST] = [*node.args, *node.keywords]
    opened = node.func.end_lineno or node.func.lineno
    if not arguments or (node.end_lineno or node.lineno) == opened:
        return []

    if len(arguments) == 1 and isinstance(arguments[0], ast.GeneratorExp):
        return []

    starts = [argument.lineno for argument in arguments]
    if opened in starts or len(set(starts)) != len(starts):
        return [Slip(path=relative, line=node.lineno, message=f"the call of {callee(node)} is broken across lines and does not stack its arguments one per line")]

    last = max(argument.end_lineno or argument.lineno for argument in arguments)
    if not TRAILING_COMMA.search(lines[last - 1]):
        return [Slip(path=relative, line=last, message=f"the call of {callee(node)} has no trailing comma after its last argument")]

    return []


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
) -> list[Slip]:
    """The commits of the branch against main, each read for a co-author line or an AI attribution, nothing where git or main is not there."""
    listing = git(project=project, arguments=["log", f"{MAIN}..HEAD", "--format=%h%x1f%B%x1e"])
    if listing is None:
        return []

    found: list[Slip] = []
    for record in listing.split("\x1e"):
        if "\x1f" not in record:
            continue

        short, message = record.strip("\n").split("\x1f", 1)
        where = f"commit {short.strip()}"
        if CO_AUTHOR.search(message):
            found.append(Slip(path=where, message="carries a co-author line, and a commit has one author"))

        if ATTRIBUTION.search(message):
            found.append(Slip(path=where, message="carries an AI attribution, which no commit carries"))

    return found


def git(
    project: Path,
    arguments: list[str],
) -> Optional[str]:
    """What git prints for the project, or None when git is not there, fails, or the folder is not a repository."""
    try:
        result = subprocess.run(
            ["git", "-C", str(project), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None

    return result.stdout if result.returncode == 0 else None
