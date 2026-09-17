"""The `## Heading` blocks a body carries.

Reading only. Nothing here rewrites prose, it reports what is there so a
command can refuse to file something the spec says is incomplete.
"""

import re
from typing import Optional

from . import frontmatter, schema

HEADING = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)

# Code in a body, fenced or inline. It keeps its own punctuation and
# its own links, so the checks and the rewrites step over it.
CODE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)


def prose_of(
    text: str,
) -> str:
    """The text with its code taken out."""
    return CODE.sub("", text)


def code_spans(
    text: str,
) -> list[tuple[int, int]]:
    """Where the code sits in the text, as start and end offsets."""
    return [(match.start(), match.end()) for match in CODE.finditer(text)]


def in_code(
    spans: list[tuple[int, int]],
    position: int,
) -> bool:
    """Whether an offset falls inside one of the code spans."""
    return any(start <= position < end for start, end in spans)


def headings(
    body: str,
) -> list[str]:
    return [match.group(1) for match in HEADING.finditer(body)]


def has(
    body: str,
    title: str,
) -> bool:
    return title.lower() in [found.lower() for found in headings(body)]


def block(
    body: str,
    title: str,
) -> Optional[str]:
    """The text under one heading, up to the next heading of any level."""
    for match in HEADING.finditer(body):
        if match.group(1).lower() != title.lower():
            continue

        rest = body[match.end() :]
        end = re.search(r"^#{1,6}[ \t]", rest, re.MULTILINE)

        return rest[: end.start()] if end else rest

    return None


def is_filled(
    body: str,
    title: str,
) -> bool:
    text = block(body=body, title=title)
    if text is None:
        return False

    return bool(text.strip())


def missing(
    body: str,
    kind: schema.Kind,
) -> list[str]:
    """The required headings this body does not carry."""
    return [
        section.title
        for section in kind.sections
        if section.required and not has(body=body, title=section.title)
    ]


def lifecycle_gaps(
    kind: schema.Kind,
    fields: dict[str, str],
    body: str,
) -> list[str]:
    """What a file in its status is required to carry and does not, per the kind's rules.

    The writer asks this before a status change lands, doctor asks it of
    every file as it stands, so the two never disagree on a rule.
    """
    status = fields.get("status", "")
    gaps: list[str] = []

    for rule in kind.rules:
        if rule.status != status:
            continue

        if rule.field and not fields.get(rule.field, "").strip():
            gaps.append(rule.says)

        if rule.section and not is_filled(body=body, title=rule.section):
            gaps.append(rule.says)

        if rule.link_kind and not links_into(fields=fields, kind=schema.KINDS[rule.link_kind]):
            gaps.append(rule.says)

    return gaps


def links_into(
    fields: dict[str, str],
    kind: schema.Kind,
) -> bool:
    """Whether the header links to an entry of the kind, judged by the shape of the path.

    A path in the kind's folder that is not its index and, for a kind
    with ids, carries the kind's own id in its name. Whether the file is
    there is the link check's business.
    """
    for link in frontmatter.parse_list(fields.get("links", "")):
        parts = link.split("/")
        if len(parts) < 2 or parts[0] != kind.folder or parts[-1] == schema.INDEX:
            continue

        match = schema.FILENAME_WITH_ID.match(parts[-1])
        if kind.has_ids and (match is None or match.group(1) != kind.id_prefix):
            continue

        return True

    return False


def skeleton(
    kind: schema.Kind,
    title: str,
) -> str:
    """The empty body a new file starts with, headings and nothing else."""
    if not kind.sections:
        return f"\n# {title}\n"

    blocks = [
        f"## {section.title}\n" for section in kind.sections if section.required
    ]

    return "\n" + "\n".join(blocks)
