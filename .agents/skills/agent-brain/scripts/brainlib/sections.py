"""The `## Heading` blocks a body carries, and the code a text holds.

Reading only. Nothing here rewrites prose, it reports what is there so a
command can refuse to file something the spec says is incomplete. The
reading of code here is the one every reader shares, section 0's cut,
the gates, the brain's own bodies and doctor alike.
"""

import re
from dataclasses import dataclass
from typing import Optional

from . import frontmatter, schema

HEADING = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)

# The two characters the house style bans outright, in prose and in a
# header value alike, since a value flows into an index's prose.
EM_DASH = "—"
EN_DASH = "–"

# Code in a text, fenced, indented or inline, read the way markdown
# reads it. It keeps its own punctuation and its own links, so the
# checks and the rewrites step over it. A fence is a run of three or
# more backticks or tildes that starts a line, up to three columns past
# the margin of the list item it sits in, and it runs to a run of the
# same character at least as long or to the text's end. A line four
# columns past its margin is code where no paragraph is open. A span is
# a pair of single backticks on one line, so three backticks in the
# middle of a sentence are just backticks.
LINE = re.compile(r"^.*$", re.MULTILINE)
FENCE_OPEN = re.compile(r"(`{3,}|~{3,})(.*)$")
FENCE_CLOSE = re.compile(r"(`{3,}|~{3,})\s*$")
LIST_MARKER = re.compile(r"([-*+]|\d{1,9}[.)])(?:([ \t]+)|$)")
ATX_OPEN = re.compile(r"(#{1,6})(?:[ \t]+|$)")
ATX_CLOSE = re.compile(r"(?:^|[ \t]+)#+$")
SETEXT_UNDERLINE = re.compile(r"(?:=+|-+)\s*$")
INLINE = re.compile(r"`[^`\n]*`")
NOT_A_LINE_END = re.compile(r"[^\n]")
CODE_INDENT = 4

# An HTML comment hides what it holds from a reader that asks, a gate
# or a heading an owner commented out for one. It is no code, so the
# kit's marker, itself a comment, is still found outside code.
COMMENT_OPEN = "<!--"
COMMENT_CLOSE = "-->"


@dataclass(frozen=True)
class Fence:
    """One fenced block: where it starts and ends, its info string, and its lines with the indent its fence carries taken off."""

    start: int
    end: int
    info: str
    text: str


@dataclass(frozen=True)
class Heading:
    """One heading outside code, of hashes or a setext line: where it starts and ends, its level, and its text without the closing hashes."""

    start: int
    end: int
    level: int
    text: str


@dataclass(frozen=True)
class Blocks:
    """What a reading of the blocks finds: where the code blocks sit, the fences among them, and the headings outside them."""

    code: list[tuple[int, int]]
    fences: list[Fence]
    headings: list[Heading]


@dataclass
class Opened:
    """A fence still open as the lines are read: where it starts, its run, the margin its closer keeps to, the columns its lines lose, its info string, and its lines so far."""

    start: int
    run: str
    margin: int
    indent: int
    info: str
    lines: list[str]


def prose_of(
    text: str,
) -> str:
    """The text with its code taken out."""
    kept: list[str] = []
    cursor = 0
    for start, end in code_spans(text):
        kept.append(text[cursor:start])
        cursor = end
    kept.append(text[cursor:])

    return "".join(kept)


def style_slips(
    text: str,
) -> list[str]:
    """What the house style bans in the text, each said the way doctor says it."""
    found: list[str] = []
    if EM_DASH in text or EN_DASH in text:
        found.append("carries a dash the house style bans")

    if ";" in text:
        found.append("carries a semicolon")

    return found


def code_spans(
    text: str,
) -> list[tuple[int, int]]:
    """Where the code sits in the text, as start and end offsets, the blocks first and then the spans in what the blocks leave."""
    blocks = blocks_of(text).code
    rest = blanked(
        text=text,
        spans=blocks,
    )
    spans = [(match.start(), match.end()) for match in INLINE.finditer(rest)]

    return sorted(blocks + spans)


def in_code(
    spans: list[tuple[int, int]],
    position: int,
) -> bool:
    """Whether an offset falls inside one of the spans, of code or of anything else a reader steps over."""
    return any(start <= position < end for start, end in spans)


def comment_spans(
    text: str,
    spans: Optional[list[tuple[int, int]]] = None,
) -> list[tuple[int, int]]:
    """Where the HTML comments sit outside code, each from its `<!--` to the first `-->` past it outside code.

    An opener with no such closer hides nothing, so a stray one never
    swallows the rest of the text. A caller that has the code spans
    passes them, so the text is scanned for code once.
    """
    if spans is None:
        spans = code_spans(text)

    found: list[tuple[int, int]] = []
    cursor = 0
    while True:
        opened = text.find(COMMENT_OPEN, cursor)
        if opened == -1:
            return found

        cursor = opened + 1
        if in_code(
            spans=spans,
            position=opened,
        ):
            continue

        closed = text.find(COMMENT_CLOSE, opened + len(COMMENT_OPEN))
        while closed != -1 and in_code(
            spans=spans,
            position=closed,
        ):
            closed = text.find(COMMENT_CLOSE, closed + 1)

        if closed == -1:
            continue

        found.append((opened, closed + len(COMMENT_CLOSE)))
        cursor = closed + len(COMMENT_CLOSE)


def blocks_of(
    text: str,
) -> Blocks:
    """The code blocks, the fences and the headings of the text, read line by line in the order they come.

    A fence opens on a list item's own line too, after its marker. The
    margin is where the text of the list item the line sits in starts,
    so a list item's paragraph indented four columns is read, and a
    heading or a fence left of that margin ends every list that is open.
    A paragraph is open from its first line to a blank line, a heading,
    a fence or a list item, and a line of `=` or `-` under it makes it a
    setext heading.
    """
    code: list[tuple[int, int]] = []
    fences: list[Fence] = []
    headings: list[Heading] = []
    items: list[int] = []
    fence: Optional[Opened] = None
    paragraph: Optional[int] = None
    after_break = True

    for match in LINE.finditer(text):
        line = match.group()
        start, end = match.span()

        if fence is not None:
            if not fence_closes(
                fence=fence,
                line=line,
            ):
                fence.lines.append(
                    dedented(
                        line=line,
                        columns=fence.indent,
                    ),
                )
                continue

            code.append((fence.start, end))
            fences.append(
                Fence(
                    start=fence.start,
                    end=end,
                    info=fence.info,
                    text="\n".join(fence.lines),
                ),
            )
            fence = None
            after_break = True
            continue

        if not line.strip():
            after_break = True
            paragraph = None
            continue

        indent = indent_of(line)
        bare = line.lstrip()
        marker = LIST_MARKER.match(bare)
        atx = ATX_OPEN.match(bare)
        underline = paragraph is not None and SETEXT_UNDERLINE.match(bare) is not None
        opener = fence_opener(bare)
        interrupts = marker is not None or atx is not None or underline or opener is not None
        if after_break or interrupts:
            while items and indent < items[-1]:
                items.pop()

        margin = items[-1] if items else 0
        if indent - margin >= CODE_INDENT:
            if after_break:
                code.append((start, end))
            continue

        if opener is not None:
            fence = Opened(
                start=start,
                run=opener.group(1),
                margin=margin,
                indent=indent,
                info=opener.group(2).strip(),
                lines=[],
            )
            paragraph = None
            continue

        if underline:
            headings.append(
                Heading(
                    start=paragraph,
                    end=end,
                    level=1 if bare.startswith("=") else 2,
                    text=" ".join(part.strip() for part in text[paragraph:start].split("\n") if part.strip()),
                ),
            )
            paragraph = None
            after_break = True
            continue

        if atx is not None:
            headings.append(
                Heading(
                    start=start,
                    end=end,
                    level=len(atx.group(1)),
                    text=ATX_CLOSE.sub(
                        repl="",
                        string=bare[atx.end() :].rstrip(),
                    ).strip(),
                ),
            )
            paragraph = None
            after_break = True
            continue

        if marker is not None:
            item_margin = indent + len(marker.group(1)) + item_gap(marker.group(2))
            items.append(item_margin)
            paragraph = None
            after_break = False

            item_fence = fence_opener(bare[marker.end() :])
            if item_fence is not None:
                fence = Opened(
                    start=start,
                    run=item_fence.group(1),
                    margin=item_margin,
                    indent=item_margin,
                    info=item_fence.group(2).strip(),
                    lines=[],
                )
            continue

        if paragraph is None:
            paragraph = start
        after_break = False

    # a fence with no closer runs to the end of the text, as markdown renders it
    if fence is not None:
        code.append((fence.start, len(text)))
        fences.append(
            Fence(
                start=fence.start,
                end=len(text),
                info=fence.info,
                text="\n".join(fence.lines),
            ),
        )

    return Blocks(
        code=code,
        fences=fences,
        headings=headings,
    )


def fence_opener(
    bare: str,
) -> Optional[re.Match]:
    """The fence the text opens with, or None, since a backtick fence's info string holds no backtick."""
    opener = FENCE_OPEN.match(bare)
    if opener is None:
        return None

    if opener.group(1).startswith("`") and "`" in opener.group(2):
        return None

    return opener


def fence_closes(
    fence: Opened,
    line: str,
) -> bool:
    """Whether the line closes the fence, a run of the same character at least as long, indented less than four columns past the fence's margin."""
    closer = FENCE_CLOSE.match(line.lstrip())
    if closer is None or indent_of(line) - fence.margin >= CODE_INDENT:
        return False

    return closer.group(1)[0] == fence.run[0] and len(closer.group(1)) >= len(fence.run)


def item_gap(
    spacing: Optional[str],
) -> int:
    """How far past its marker a list item's text starts, one column when the marker ends the line or the gap would make its text code."""
    if not spacing or len(spacing) > CODE_INDENT:
        return 1

    return len(spacing)


def indent_of(
    line: str,
) -> int:
    """How many columns the line's leading white space spans, a tab reaching the next multiple of four."""
    columns = 0
    for character in line:
        if character == " ":
            columns += 1
        elif character == "\t":
            columns += CODE_INDENT - columns % CODE_INDENT
        else:
            break

    return columns


def dedented(
    line: str,
    columns: int,
) -> str:
    """The line without the leading white space that reaches no further than the given column."""
    taken = 0
    position = 0
    while position < len(line) and line[position] in " \t":
        width = CODE_INDENT - taken % CODE_INDENT if line[position] == "\t" else 1
        if taken + width > columns:
            break

        taken += width
        position += 1

    return line[position:]


def blanked(
    text: str,
    spans: list[tuple[int, int]],
) -> str:
    """The text with the spans turned to spaces, its line ends and so its offsets kept."""
    kept: list[str] = []
    cursor = 0
    for start, end in sorted(spans):
        kept.append(text[cursor:start])
        kept.append(
            NOT_A_LINE_END.sub(
                repl=" ",
                string=text[start:end],
            ),
        )
        cursor = end
    kept.append(text[cursor:])

    return "".join(kept)


def heading_after(
    body: str,
    start: int,
    depth: int = 6,
    spans: Optional[list[tuple[int, int]]] = None,
) -> int:
    """The offset of the next heading outside code at or after `start`, else the body's end.

    `depth` is the deepest heading level that counts, so 2 finds the
    next `#` or `##` line and steps over the `###` lines under it. A
    caller that walks many headings of one body passes the code spans
    it already has, so the body is scanned for code once.
    """
    if spans is None:
        spans = code_spans(body)

    heading = re.compile(rf"^#{{1,{depth}}}[ \t]", re.MULTILINE)

    for match in heading.finditer(string=body, pos=start):
        if not in_code(spans=spans, position=match.start()):
            return match.start()

    return len(body)


def heading_matches(
    body: str,
) -> list[re.Match]:
    """Every `## Heading` line outside code, in order."""
    spans = code_spans(body)

    return [match for match in HEADING.finditer(body) if not in_code(spans=spans, position=match.start())]


def headings(
    body: str,
) -> list[str]:
    return [match.group(1) for match in heading_matches(body)]


def has(
    body: str,
    title: str,
) -> bool:
    return title.lower() in [found.lower() for found in headings(body)]


def span(
    body: str,
    title: str,
) -> Optional[tuple[int, int]]:
    """Where the text under one heading starts and ends, up to the next heading of any level.

    The title is matched without regard to case, the one rule for every
    reader of a section.
    """
    for match in heading_matches(body):
        if match.group(1).lower() != title.lower():
            continue

        return match.end(), heading_after(body=body, start=match.end())

    return None


def block(
    body: str,
    title: str,
) -> Optional[str]:
    """The text under one heading, up to the next heading of any level."""
    found = span(body=body, title=title)
    if found is None:
        return None

    return body[found[0] : found[1]]


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

    return [rule.says for rule in kind.rules if rule.status == status and rule_broken(rule=rule, fields=fields, body=body)]


def rule_broken(
    rule: schema.Rule,
    fields: dict[str, str],
    body: str,
) -> bool:
    """Whether the file falls short of the rule in any of the ways it names, said once."""
    if rule.field and not fields.get(rule.field, "").strip():
        return True

    if rule.section and not is_filled(body=body, title=rule.section):
        return True

    return bool(rule.link_kind) and not links_into(fields=fields, kind=schema.KINDS[rule.link_kind])


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
