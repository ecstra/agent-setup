"""Reading and writing a file's frontmatter without touching its body.

The body is what a person wrote. Every function here hands it back
exactly as it came in, which is why nothing reflows, strips or re-indents
it. Frontmatter lines are kept as raw text too, so a field nobody edited
is written back character for character.
"""

from dataclasses import dataclass
from typing import Optional

FENCE = "---"


class FrontmatterError(Exception):
    """A file that cannot be read as frontmatter plus body."""


@dataclass
class Document:
    """One brain file, split at the closing fence.

    `lines` holds the frontmatter as it was written, without the fences.
    `body` is everything after the closing fence line, including the
    newline that follows it.
    """

    lines: list[str]
    body: str

    def get(
        self,
        key: str,
    ) -> Optional[str]:
        for line in self.lines:
            name, value = split_field(line)
            if name == key:
                return value

        return None

    def set(
        self,
        key: str,
        value: str,
    ) -> None:
        for index, line in enumerate(self.lines):
            name, _ = split_field(line)
            if name == key:
                self.lines[index] = f"{key}: {value}"
                return

        self.lines.append(f"{key}: {value}")

    def fields(self) -> dict[str, str]:
        found: dict[str, str] = {}

        for line in self.lines:
            name, value = split_field(line)
            if name is not None:
                found[name] = value or ""

        return found

    def get_list(
        self,
        key: str,
    ) -> list[str]:
        value = self.get(key)
        if value is None:
            return []

        return parse_list(value)

    def set_list(
        self,
        key: str,
        values: list[str],
    ) -> None:
        self.set(
            key=key,
            value=render_list(values),
        )


def split_field(
    line: str,
) -> tuple[Optional[str], Optional[str]]:
    """Split one frontmatter line into its name and its raw value.

    A line with no colon is not a field, which is how a continuation line
    or a stray comment survives a round trip untouched.
    """
    if ":" not in line:
        return None, None

    if line.startswith(" ") or line.startswith("\t"):
        return None, None

    name, _, value = line.partition(":")

    return name.strip(), value.strip()


def parse_list(
    value: str,
) -> list[str]:
    inner = value.strip()
    if not inner.startswith("[") or not inner.endswith("]"):
        return [inner] if inner else []

    inner = inner[1:-1].strip()
    if not inner:
        return []

    return [item.strip() for item in inner.split(",") if item.strip()]


def render_list(
    values: list[str],
) -> str:
    return "[" + ", ".join(values) + "]"


def parse(
    text: str,
) -> Document:
    """Split `text` into frontmatter lines and the body after them."""
    if not text.startswith(FENCE + "\n"):
        raise FrontmatterError("the file does not open with a --- fence")

    rest = text[len(FENCE) + 1 :]
    closing = find_closing_fence(rest)
    if closing is None:
        raise FrontmatterError("the frontmatter fence is never closed")

    head, body = rest[:closing], rest[closing:]
    lines = head.split("\n")[:-1] if head else []

    return Document(
        lines=lines,
        body=body[len(FENCE) + 1 :],
    )


def find_closing_fence(
    rest: str,
) -> Optional[int]:
    """Offset of the closing fence line, or None when there is none.

    The body of a brain file often carries `---` as a rule between
    sections, so only a fence reached before any body content counts.
    """
    offset = 0

    for line in rest.split("\n"):
        if line == FENCE:
            return offset

        offset += len(line) + 1

    return None


def render(
    document: Document,
) -> str:
    head = "\n".join(document.lines)
    if head:
        head += "\n"

    return f"{FENCE}\n{head}{FENCE}\n{document.body}"


def load(
    path: str,
) -> str:
    """The file's text, refused as frontmatter when it cannot be read as such.

    A file that is not UTF-8, a dangling symlink, a folder named like a
    file or a file the process may not open all become one refusal, so
    a caller that notes bad files notes these too instead of dying.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except UnicodeDecodeError as error:
        raise FrontmatterError("the file is not UTF-8 text") from error
    except OSError as error:
        raise FrontmatterError(f"the file cannot be read: {error.strerror or error}") from error


def read(
    path: str,
) -> Document:
    return parse(load(path))


def write(
    path: str,
    document: Document,
) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render(document))
