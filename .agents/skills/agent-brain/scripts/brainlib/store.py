"""Finding the brain, reading what is in it, and naming what goes in next.

Every command starts here. Ids come from the files themselves, so the
next one is the highest that exists plus one. A gap left by a file that
moved or was deleted stays a gap, because the id it held is written into
commits, ledgers and links that nobody can rewrite.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import frontmatter, schema


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
    """The `.agents/` directory and everything filed inside it.

    Each folder is scanned once per command and the result kept, since a
    doctor run asks about the same files hundreds of times. Anything that
    writes calls `refresh` so the next question reads what is on disk.
    """

    root: Path

    def __post_init__(self) -> None:
        self.loaded: dict[str, list[Entry]] = {}
        self.unreadable: dict[Path, str] = {}

    def refresh(self) -> None:
        self.loaded = {}
        self.unreadable = {}

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
        if kind.name not in self.loaded:
            self.loaded[kind.name] = self.scan(kind)

        return list(self.loaded[kind.name])

    def scan(
        self,
        kind: schema.Kind,
    ) -> list[Entry]:
        """Read one folder. A file that cannot be read or parsed is noted, not fatal."""
        folder = self.folder(kind)
        if not folder.is_dir():
            return []

        found: list[Entry] = []

        for path in sorted(folder.rglob("*.md")):
            if path.name == schema.INDEX:
                continue

            if kind.name == "review" and path.name != schema.LEDGER:
                continue

            try:
                found.append(self.read(path=path, kind=kind))
            except StoreError as error:
                self.unreadable[path] = str(error)

        return found

    def read(
        self,
        path: Path,
        kind: schema.Kind,
    ) -> Entry:
        try:
            document = frontmatter.read(str(path))
        except frontmatter.FrontmatterError as error:
            raise StoreError(f"{near(str(path))}: {error}") from error

        return Entry(
            path=path,
            root=self.root,
            kind=kind,
            document=document,
        )

    def known(self) -> set[Path]:
        """Every path the store lists, the entries and the files it could not read."""
        listed = {entry.path for entry in self.entries()}

        return listed | set(self.unreadable)

    def kit_files(self) -> list[Path]:
        """The kit's own files that exist here, the rulebook excepted."""
        candidates = [self.root / name for name in schema.KIT_FILES if name not in schema.NO_FRONTMATTER]
        candidates += sorted((self.root / "spec").glob("*.md"))
        candidates += [self.root / folder / schema.INDEX for folder in schema.INDEXED_FOLDERS]

        return [path for path in candidates if readable_file(path)]

    def next_number(
        self,
        kind: schema.Kind,
    ) -> int:
        if not kind.has_ids:
            raise StoreError(f"{kind.name} files carry no id")

        numbers = [entry.number for entry in self.entries_of(kind)]
        numbers += [number_in(path.name, kind) for path in self.unreadable if self.folder(kind) in path.parents]
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
            folder = folder / category_folder(category)

        if kind.name == "review":
            return folder / slug / schema.LEDGER

        if kind.has_ids:
            return folder / f"{self.next_id(kind)}-{slug}.md"

        return folder / f"{slug}.md"


def number_in(
    filename: str,
    kind: schema.Kind,
) -> Optional[int]:
    """The id number a filename of this kind carries, readable or not.

    An id is taken the moment a file holds it in its name, so a file the
    store could not read still keeps its number out of circulation.
    """
    match = schema.FILENAME_WITH_ID.match(filename)
    if match is None or match.group(1) != kind.id_prefix:
        return None

    return int(match.group(2))


def quietly(
    question: Callable[[], bool],
) -> bool:
    """A path question such as `path.is_file`, answered False instead of raised.

    On the 3.9 floor `is_file`, `is_dir`, `is_symlink` and `exists` raise
    when the folder above cannot be searched, where newer interpreters
    answer False. Every gate above a read or a decision asks here, so
    both floors degrade the same way.
    """
    try:
        return question()
    except OSError:
        return False


def readable_file(
    path: Path,
) -> bool:
    """True when `path` is a file the process can see."""
    return quietly(path.is_file)


def category_folder(
    category: str,
) -> Path:
    """The folder a category names, one or more slugs deep, never outside the kind's folder."""
    parts = category.split("/")
    if not all(schema.is_slug(part) for part in parts):
        raise StoreError(f"'{category}' is not a category, which is one or more slugs such as systems/auth")

    return Path(*parts)


def explain(
    error: BaseException,
) -> str:
    """The error as one plain line, an OS error without the machine's path."""
    if isinstance(error, OSError) and error.filename:
        reason = error.strerror or type(error).__name__

        return f"{reason}: {near(os.fsdecode(error.filename))}"

    return str(error).strip("'")


def near(
    path: str,
) -> str:
    """A path from `.agents/` down, or just the filename when it lies elsewhere."""
    parts = Path(path).parts
    if ".agents" in parts:
        return str(Path(*parts[parts.index(".agents") :]))

    return Path(path).name


def find_brain(
    start: Optional[Path] = None,
) -> Brain:
    """Walk up from `start` until the `.agents/` directory turns up."""
    try:
        here = (start or Path.cwd()).resolve()
    except (OSError, RuntimeError, ValueError) as error:
        raise StoreError(f"the working directory cannot be resolved: {error}") from error

    for candidate in [here, *here.parents]:
        if candidate.name == ".agents" and readable_file(candidate / "INDEX.md"):
            return Brain(root=candidate)

        inside = candidate / ".agents"
        if readable_file(inside / "INDEX.md"):
            return Brain(root=inside)

    raise StoreError(
        "no .agents/ directory here or above, so there is no brain to work on"
    )
