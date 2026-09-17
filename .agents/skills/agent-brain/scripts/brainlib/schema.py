"""The rules in .agents/spec/, written so the tool can check them.

The prose specs stay the law a person reads. This module is the same law
in the form doctor and the write commands need, so a rule lives in one
place here rather than being rediscovered by every command.
"""

import re
from dataclasses import dataclass
from typing import Optional

DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FILENAME_WITH_ID = re.compile(r"^(BUG|TODO|DEC)-(\d{3})-(.+)\.md$")

# A review folder is <yyyy-mm>-<branch-slug>, per spec/reviews.md.
REVIEW_FOLDER = re.compile(r"^\d{4}-\d{2}-[a-z0-9]+(-[a-z0-9]+)*$")

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
class Kind:
    """A kind of brain file, its home, and what it must carry."""

    name: str
    folder: str
    fields: tuple[Field, ...] = ()
    sections: tuple[Section, ...] = ()
    id_prefix: str = ""
    frontmatter_kind: str = ""

    @property
    def kind_value(self) -> str:
        return self.frontmatter_kind or self.name

    @property
    def has_ids(self) -> bool:
        return bool(self.id_prefix)


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
    ),
    "bug": Kind(
        name="bug",
        folder="bugs",
        id_prefix="BUG",
        fields=(
            Field(
                name="status",
                values=("open", "branched", "fixed", "wontfix"),
            ),
            Field(
                name="severity",
                values=("breaks", "bug", "debt", "nit"),
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
    ),
    "todo": Kind(
        name="todo",
        folder="todos",
        id_prefix="TODO",
        fields=(
            Field(
                name="status",
                values=("open", "done", "dropped"),
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
    ),
    "decision": Kind(
        name="decision",
        folder="decisions",
        id_prefix="DEC",
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
    ),
    "review": Kind(
        name="review",
        folder="reviews",
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
# one markdown file in the directory with no frontmatter.
NO_FRONTMATTER: tuple[str, ...] = ("SYSTEM.md",)

# The folders that carry their own INDEX.md, per spec/conventions.md.
INDEXED_FOLDERS: tuple[str, ...] = (
    "docs",
    "memory",
    "todos",
    "bugs",
    "decisions",
    "reviews",
)

INDEX = "INDEX.md"
LEDGER = "ledger.md"


def is_kit_path(
    relative: str,
) -> bool:
    """Whether a path inside .agents/ names a file the kit owns.

    That is a root kit file, a spec, or the index of a folder that
    carries one. Everything else in the brain is an entry or a stray.
    """
    parts = relative.split("/")

    if len(parts) == 1:
        return parts[0] in KIT_FILES

    if len(parts) == 2 and parts[0] == "spec":
        return parts[1].endswith(".md") and parts[1] != INDEX

    return len(parts) == 2 and parts[0] in INDEXED_FOLDERS and parts[1] == INDEX


def kind_named(
    name: str,
) -> Kind:
    if name not in KINDS:
        known = ", ".join(sorted(KINDS))
        raise KeyError(f"unknown kind '{name}', expected one of {known}")

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
