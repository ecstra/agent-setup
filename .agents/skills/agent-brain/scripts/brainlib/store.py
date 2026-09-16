"""Finding the brain, reading what is in it, and naming what goes in next.

Every command starts here. Ids come from the files themselves, so the
next one is the highest that exists plus one. A gap left by a file that
moved or was deleted stays a gap, because the id it held is written into
commits, ledgers and links that nobody can rewrite.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import frontmatter, schema

SKIP_NAMES: frozenset[str] = frozenset(
    {
        "INDEX.md",
        "README.md",
        "SYSTEM.md",
        "house-rules.md",
    }
)

LEDGER = "ledger.md"


class StoreError(Exception):
    """The brain is missing, or something in it cannot be read."""


@dataclass
class Entry:
    """One file in the brain, with its frontmatter already parsed."""

    path: Path
    root: Path
    kind: schema.Kind
    document: frontmatter.Document

    @property
    def relative(self) -> str:
        return str(self.path.relative_to(self.root))

    @property
    def name(self) -> str:
        return self.document.get("name") or self.path.stem

    @property
    def identifier(self) -> Optional[str]:
        match = schema.FILENAME_WITH_ID.match(self.path.name)
        if match is None:
            return None

        return f"{match.group(1)}-{match.group(2)}"

    @property
    def slug(self) -> str:
        """The filename with its id taken off, which is what a title becomes."""
        match = schema.FILENAME_WITH_ID.match(self.path.name)
        if match is not None:
            return match.group(3)

        if self.kind.name == "review":
            return self.path.parent.name

        return self.path.stem

    @property
    def number(self) -> Optional[int]:
        match = schema.FILENAME_WITH_ID.match(self.path.name)
        if match is None:
            return None

        return int(match.group(2))

    def field(
        self,
        key: str,
    ) -> Optional[str]:
        return self.document.get(key)


@dataclass
class Brain:
    """The `.agents/` directory and everything filed inside it."""

    root: Path

    def folder(
        self,
        kind: schema.Kind,
    ) -> Path:
        return self.root / kind.folder

    def entries(
        self,
        kind: Optional[schema.Kind] = None,
    ) -> list[Entry]:
        kinds = [kind] if kind is not None else list(schema.KINDS.values())
        found: list[Entry] = []

        for one in kinds:
            found.extend(self.entries_of(one))

        return found

    def entries_of(
        self,
        kind: schema.Kind,
    ) -> list[Entry]:
        folder = self.folder(kind)
        if not folder.is_dir():
            return []

        found: list[Entry] = []

        for path in sorted(folder.rglob("*.md")):
            if path.name in SKIP_NAMES:
                continue

            if kind.name == "review" and path.name != LEDGER:
                continue

            found.append(self.read(path=path, kind=kind))

        return found

    def read(
        self,
        path: Path,
        kind: schema.Kind,
    ) -> Entry:
        try:
            document = frontmatter.read(str(path))
        except frontmatter.FrontmatterError as error:
            raise StoreError(f"{path}: {error}") from error

        return Entry(
            path=path,
            root=self.root,
            kind=kind,
            document=document,
        )

    def next_number(
        self,
        kind: schema.Kind,
    ) -> int:
        if not kind.has_ids:
            raise StoreError(f"{kind.name} files carry no id")

        numbers = [entry.number for entry in self.entries_of(kind)]
        taken = [number for number in numbers if number is not None]
        if not taken:
            return 1

        return max(taken) + 1

    def next_id(
        self,
        kind: schema.Kind,
    ) -> str:
        return schema.format_id(
            prefix=kind.id_prefix,
            number=self.next_number(kind),
        )

    def find(
        self,
        key: str,
    ) -> Optional[Entry]:
        """Resolve an id, a name, or a path inside the brain to one entry."""
        for entry in self.entries():
            if key in (entry.identifier, entry.name, entry.relative):
                return entry

            if entry.path.stem == key:
                return entry

        return None

    def with_slug(
        self,
        kind: schema.Kind,
        slug: str,
    ) -> Optional[Entry]:
        """The entry already filed under this title, whatever id it carries."""
        for entry in self.entries_of(kind):
            if entry.slug == slug:
                return entry

        return None

    def path_for(
        self,
        kind: schema.Kind,
        title: str,
        category: str = "",
    ) -> Path:
        slug = schema.slugify(title)
        if not slug:
            raise StoreError(f"'{title}' leaves nothing to name a file with")

        folder = self.folder(kind)
        if category:
            folder = folder / category

        if kind.name == "review":
            return folder / slug / LEDGER

        if kind.has_ids:
            return folder / f"{self.next_id(kind)}-{slug}.md"

        return folder / f"{slug}.md"


def find_brain(
    start: Optional[Path] = None,
) -> Brain:
    """Walk up from `start` until the `.agents/` directory turns up."""
    here = (start or Path.cwd()).resolve()

    for candidate in [here, *here.parents]:
        if candidate.name == ".agents" and (candidate / "INDEX.md").is_file():
            return Brain(root=candidate)

        inside = candidate / ".agents"
        if (inside / "INDEX.md").is_file():
            return Brain(root=inside)

    raise StoreError(
        "no .agents/ directory here or above, so there is no brain to work on"
    )
