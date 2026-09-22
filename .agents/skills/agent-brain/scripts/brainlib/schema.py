"""The rules in .agents/spec/, written so the tool can check them.

The prose specs stay the law a person reads. This module is the same law
in the form doctor and the write commands need, so a rule lives in one
place here rather than being rediscovered by every command.
"""

import re
from dataclasses import dataclass
from typing import Optional

DATE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# A bug's severities, worst first, the one order every reader uses.
SEVERITIES: tuple[str, ...] = ("breaks", "bug", "debt", "nit")
FILENAME_WITH_ID = re.compile(r"^(BUG|TODO|DEC)-(\d{3})-(.+)\.md$")

# A review folder is <yyyy-mm>-<branch-slug>, per spec/reviews.md.
REVIEW_FOLDER = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-[a-z0-9]+(-[a-z0-9]+)*$")

ID_DIGITS = 3


@dataclass(frozen=True)
class Field:
    """One frontmatter field a kind carries."""

    name: str
    required: bool = True
    values: tuple[str, ...] = ()
    is_date: bool = False


@dataclass(frozen=True)
class Section:
    """One heading a kind's body carries."""

    title: str
    required: bool = True


@dataclass(frozen=True)
class Rule:
    """What a file in one status must carry, in the words used when it does not.

    One rule names one thing: a field that must be filled, a section
    that must be filled, or a link to a file of another kind. The writer
    refuses a status change that breaks a rule and doctor reports a file
    that sits in a status breaking one, with the same words.
    """

    status: str
    says: str
    field: str = ""
    section: str = ""
    link_kind: str = ""


@dataclass(frozen=True)
class Kind:
    """A kind of brain file, its home, what it must carry, and the rules its statuses hold to."""

    name: str
    folder: str
    fields: tuple[Field, ...] = ()
    sections: tuple[Section, ...] = ()
    id_prefix: str = ""
    frontmatter_kind: str = ""
    rules: tuple[Rule, ...] = ()
    # The fields `brain list` shows beside the id, and the description of
    # the folder's INDEX.md, empty for a folder that carries none.
    columns: tuple[str, ...] = ()
    index_description: str = ""

    @property
    def kind_value(self) -> str:
        return self.frontmatter_kind or self.name

    @property
    def has_ids(self) -> bool:
        return bool(self.id_prefix)

    @property
    def indexed(self) -> bool:
        return bool(self.index_description)


COMMON_FIELDS: tuple[Field, ...] = (
    Field(name="name"),
    Field(name="kind"),
    Field(name="description"),
    Field(name="updated", is_date=True),
    Field(name="links"),
)

KINDS: dict[str, Kind] = {
    "doc": Kind(
        name="doc",
        folder="docs",
        index_description="index of the knowledge library, one line per doc",
    ),
    "memory": Kind(
        name="memory",
        folder="memory",
        fields=(
            Field(
                name="type",
                values=("project", "feedback", "reference"),
            ),
        ),
        columns=("type",),
        index_description="index of project memory, one line per fact",
    ),
    "bug": Kind(
        name="bug",
        folder="bugs",
        id_prefix="BUG",
        columns=("status", "severity", "area"),
        index_description="the defect tracker's index, open bugs first",
        fields=(
            Field(
                name="status",
                values=("open", "branched", "fixed", "wontfix", "refiled"),
            ),
            Field(
                name="severity",
                values=SEVERITIES,
            ),
            Field(name="area"),
            Field(name="reported", is_date=True),
            Field(name="parent", required=False),
        ),
        sections=(
            Section(title="Problem"),
            Section(title="Evidence"),
            Section(title="Fix", required=False),
            Section(title="Verification", required=False),
        ),
        rules=(
            Rule(
                status="fixed",
                says="a bug goes fixed once its Fix section names the cause and the commit",
                section="Fix",
            ),
            Rule(
                status="wontfix",
                says="a wontfix needs its reason written under Problem",
                section="Problem",
            ),
            Rule(
                status="refiled",
                says="a refiled bug links to the todo it became",
                link_kind="todo",
            ),
        ),
    ),
    "todo": Kind(
        name="todo",
        folder="todos",
        id_prefix="TODO",
        columns=("status", "area"),
        index_description="the work tracker's index, open items first",
        fields=(
            Field(
                name="status",
                values=("open", "done", "dropped", "refiled"),
            ),
            Field(
                name="by",
                values=("owner", "agent"),
            ),
            Field(name="area"),
            Field(name="born", is_date=True),
            Field(name="done", required=False, is_date=True),
        ),
        sections=(
            Section(title="What"),
            Section(title="Why", required=False),
            Section(title="Done when"),
        ),
        rules=(
            Rule(
                status="done",
                says="a todo goes done with its closing date, done=YYYY-MM-DD",
                field="done",
            ),
            Rule(
                status="done",
                says="a todo goes done once Done when names what closed it",
                section="Done when",
            ),
            Rule(
                status="dropped",
                says="a todo goes dropped with its closing date, done=YYYY-MM-DD",
                field="done",
            ),
            Rule(
                status="refiled",
                says="a todo goes refiled with its closing date, done=YYYY-MM-DD",
                field="done",
            ),
            Rule(
                status="refiled",
                says="a refiled todo links to the bug it became",
                link_kind="bug",
            ),
        ),
    ),
    "decision": Kind(
        name="decision",
        folder="decisions",
        id_prefix="DEC",
        columns=("status", "date", "area"),
        index_description="index of every decision taken, newest first",
        fields=(
            Field(name="date", is_date=True),
            Field(name="area"),
            Field(
                name="status",
                values=("standing", "superseded"),
            ),
            Field(name="superseded-by", required=False),
        ),
        sections=(
            Section(title="Decision"),
            Section(title="Alternatives", required=False),
            Section(title="Consequences", required=False),
        ),
        rules=(
            Rule(
                status="superseded",
                says="a superseded decision names the one that replaced it",
                field="superseded-by",
            ),
        ),
    ),
    "review": Kind(
        name="review",
        folder="reviews",
        columns=("status", "branch"),
        index_description="index of code review ledgers, active first",
        fields=(
            Field(name="branch"),
            Field(
                name="status",
                values=("open", "closed"),
            ),
        ),
        sections=(
            Section(title="Summary"),
            Section(title="Batches"),
            Section(title="Findings"),
        ),
    ),
    "handover": Kind(
        name="handover",
        folder="handover",
        frontmatter_kind="doc",
    ),
}

# Files the kit owns at the root of .agents/. They carry no project
# content, so doctor judges them against the kit rather than a kind.
KIT_FILES: tuple[str, ...] = (
    "SYSTEM.md",
    "INDEX.md",
    "README.md",
    "house-rules.md",
)

# SYSTEM.md is the rulebook. An agent takes it as it stands, so it is the
# one markdown file at the root of the directory with no frontmatter. The
# tool's own docs under skills/ follow the Agent Skills standard instead.
NO_FRONTMATTER: tuple[str, ...] = ("SYSTEM.md",)

# The folders that carry their own INDEX.md, per spec/conventions.md,
# read off the kinds so the table lives in one place.
INDEXED_FOLDERS: tuple[str, ...] = tuple(kind.folder for kind in KINDS.values() if kind.indexed)

INDEX = "INDEX.md"
LEDGER = "ledger.md"

# The one word for a status a file does not carry, wherever it is counted.
UNKNOWN = "unknown"


def is_hidden(
    relative: str,
) -> bool:
    """Whether any part of a path inside .agents/ starts with a dot.

    A dotfile or anything inside a dot folder is nobody's: an editor's
    swap file, a scratch folder a write left behind, a tool's cache. It
    is never an entry, never the kit's, never linked, listed or checked.
    """
    return any(part.startswith(".") for part in relative.split("/"))


def is_kit_path(
    relative: str,
) -> bool:
    """Whether a path inside .agents/ names a file the kit owns.

    That is a root kit file, a spec, or the index of a folder that
    carries one. Everything else in the brain is an entry or a stray,
    and a dotted path is neither.
    """
    if is_hidden(relative):
        return False

    parts = relative.split("/")

    if len(parts) == 1:
        return parts[0] in KIT_FILES

    if len(parts) == 2 and parts[0] == "spec":
        return parts[1].endswith(".md") and parts[1] != INDEX

    return len(parts) == 2 and parts[0] in INDEXED_FOLDERS and parts[1] == INDEX


class UnknownKind(Exception):
    """A kind name the spec does not know, with the known ones in the message."""


def kind_named(
    name: str,
) -> Kind:
    if name not in KINDS:
        known = ", ".join(sorted(KINDS))
        raise UnknownKind(f"unknown kind '{name}', expected one of {known}")

    return KINDS[name]


def kind_for_folder(
    folder: str,
) -> Optional[Kind]:
    for kind in KINDS.values():
        if kind.folder == folder:
            return kind

    return None


def fields_for(
    kind: Kind,
) -> tuple[Field, ...]:
    return COMMON_FIELDS + kind.fields


def is_slug(
    value: str,
) -> bool:
    return bool(SLUG.match(value))


def is_date(
    value: str,
) -> bool:
    return bool(DATE.match(value))


def is_review_folder(
    value: str,
) -> bool:
    return bool(REVIEW_FOLDER.match(value))


def format_id(
    prefix: str,
    number: int,
) -> str:
    return f"{prefix}-{number:0{ID_DIGITS}d}"


def slugify(
    title: str,
) -> str:
    """Turn a title into the filename slug the conventions ask for."""
    lowered = title.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered)

    return cleaned.strip("-")
