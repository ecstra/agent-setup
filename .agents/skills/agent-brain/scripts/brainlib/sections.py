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
# a run of backticks no backslash escapes, closed by the next run as
# long inside its paragraph or heading, so three backticks in the middle
# of a sentence with no three to close them are just backticks.
LINE = re.compile(r"^.*$", re.MULTILINE)
FENCE_OPEN = re.compile(r"(`{3,}|~{3,})(.*)$")
FENCE_CLOSE = re.compile(r"(`{3,}|~{3,})\s*$")
LIST_MARKER = re.compile(r"([-*+]|\d{1,9}[.)])(?:([ \t]+)|$)")
THEMATIC_BREAK = re.compile(r"([-*_])(?:[ \t]*\1){2,}\s*$")
ATX_OPEN = re.compile(r"(#{1,6})(?:[ \t]+|$)")
ATX_CLOSE = re.compile(r"(?:^|[ \t]+)#+$")
SETEXT_UNDERLINE = re.compile(r"(?:=+|-+)\s*$")
INLINE_OPEN = re.compile(r"<!--|(?<!\\)`+")
NOT_A_LINE_END = re.compile(r"[^\n]")
CODE_INDENT = 4

# An HTML comment hides what it holds from a reader that asks, a gate
# or a heading an owner commented out for one. It is no code, so the
# kit's marker, itself a comment, is still found outside code. One that
# opens a line is a block of its own, as markdown reads it, and one
# inside a sentence ends with its paragraph.
COMMENT_OPEN = "<!--"
COMMENT_CLOSE = "-->"
COMMENT_CLOSER = re.compile(re.escape(COMMENT_CLOSE))


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
    """What a reading of the blocks finds: where the code blocks sit, the fences among them, the headings outside them, the HTML comments that open a line, and the stretches of paragraph and heading text the spans are read in."""

    code: list[tuple[int, int]]
    fences: list[Fence]
    headings: list[Heading]
    comments: list[tuple[int, int]]
    inline: list[tuple[int, int]]


@dataclass
class Opened:
    """A fence still open as the lines are read: where it starts, its run, the margin its closer keeps to, the columns its lines lose, its info string, and its lines so far."""

    start: int
    run: str
    margin: int
    indent: int
    info: str
    lines: list[str]


@dataclass
class Paragraph:
    """A paragraph still open as the lines are read: where its text starts, where its last line ends, and the margin of the list item it opened in, which a line under it that is no lazy continuation keeps to."""

    start: int
    end: int
    margin: int


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
    """Where the code sits in the text, as start and end offsets, the blocks and the spans inside the paragraphs and headings they leave."""
    blocks = blocks_of(text)
    spans, _ = inline_of(
        text=text,
        stretches=blocks.inline,
    )

    return sorted(blocks.code + spans)


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
    """Where the HTML comments sit outside code, each from its `<!--` to the `-->` that closes it.

    A comment that opens a line runs to the first `-->` past it, through
    blank lines and through anything that looks like a fence, since no
    fence opens inside it. One inside a paragraph or a heading runs to
    the first `-->` before that paragraph or heading ends. An opener
    with no closer hides nothing, so a stray one never swallows the rest
    of the text. A caller that finds code the text's own reading does
    not, as the check does inside a quote, passes it, and a comment that
    opens inside it is none.
    """
    blocks = blocks_of(text)
    _, comments = inline_of(
        text=text,
        stretches=blocks.inline,
    )
    found = sorted(blocks.comments + comments)
    if not spans:
        return found

    return [
        comment
        for comment in found
        if not in_code(
            spans=spans,
            position=comment[0],
        )
    ]


def inline_of(
    text: str,
    stretches: list[tuple[int, int]],
) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """The code spans and the HTML comments inside the stretches of paragraph and heading text, read in the order they open.

    A run of backticks no backslash escapes is closed by the next run as
    long, and a comment by its first `-->`, each inside its stretch, and
    whichever opens first holds what follows, so a backtick inside a
    comment opens no span. An opener with nothing to close it inside its
    stretch is plain text.
    """
    spans: list[tuple[int, int]] = []
    comments: list[tuple[int, int]] = []
    for start, end in stretches:
        position = start
        while True:
            opener = INLINE_OPEN.search(
                string=text,
                pos=position,
                endpos=end,
            )
            if opener is None:
                break

            is_comment = opener.group() == COMMENT_OPEN
            closing = COMMENT_CLOSER if is_comment else re.compile(f"(?<!`){opener.group()}(?!`)")
            closer = closing.search(
                string=text,
                pos=opener.end(),
                endpos=end,
            )
            if closer is None:
                position = opener.end()
                continue

            found = comments if is_comment else spans
            found.append((opener.start(), closer.end()))
            position = closer.end()

    return spans, comments


def blocks_of(
    text: str,
) -> Blocks:
    """The code blocks, the fences and the headings of the text, read line by line in the order they come.

    A fence opens on a list item's own line too, after its marker. The
    margin is where the text of the list item the line sits in starts,
    so a list item's paragraph indented four columns is read, and a
    heading or a fence left of that margin ends every list that is open.
    A line of three or more `-`, `*` or `_` and nothing else, spaced or
    not, is a thematic break and no list item. An HTML comment that
    opens a line runs to the line that holds its first `-->`, and
    nothing inside it opens. A paragraph is open from its first line, a
    list item's own line among them, to a blank line or another block,
    and a line of `=` or `-` under it makes it a setext heading, unless
    the line sits left of the list item the paragraph opened in, which
    makes it a lazy line of the paragraph, or for `-` a thematic break.
    The stretches of paragraph and heading text are where the spans and
    the comments inside a sentence are read.
    """
    code: list[tuple[int, int]] = []
    fences: list[Fence] = []
    headings: list[Heading] = []
    comments: list[tuple[int, int]] = []
    inline: list[tuple[int, int]] = []
    items: list[int] = []
    fence: Optional[Opened] = None
    paragraph: Optional[Paragraph] = None
    commented_to = 0
    after_break = True

    for match in LINE.finditer(text):
        line = match.group()
        start, end = match.span()

        if start < commented_to:
            continue

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
            if paragraph is not None:
                inline.append((paragraph.start, paragraph.end))
            after_break = True
            paragraph = None
            continue

        indent = indent_of(line)
        bare = line.lstrip()
        opened = end - len(bare)
        underline = paragraph is not None and indent >= paragraph.margin and SETEXT_UNDERLINE.match(bare) is not None
        thematic = not underline and THEMATIC_BREAK.match(bare) is not None
        marker = None if thematic else LIST_MARKER.match(bare)
        atx = ATX_OPEN.match(bare)
        opener = fence_opener(bare)
        closer = text.find(COMMENT_CLOSE, opened + len(COMMENT_OPEN)) if bare.startswith(COMMENT_OPEN) else -1
        interrupts = underline or thematic or marker is not None or atx is not None or opener is not None or closer != -1
        if after_break or interrupts:
            while items and indent < items[-1]:
                items.pop()

        margin = items[-1] if items else 0
        if indent - margin >= CODE_INDENT:
            if after_break:
                code.append((start, end))
            elif paragraph is not None:
                paragraph.end = end
            continue

        if not interrupts:
            if paragraph is None:
                paragraph = Paragraph(
                    start=start,
                    end=end,
                    margin=margin,
                )
            paragraph.end = end
            after_break = False
            continue

        above = paragraph
        if paragraph is not None:
            inline.append((paragraph.start, paragraph.end))
        paragraph = None
        after_break = True

        if opener is not None:
            fence = Opened(
                start=start,
                run=opener.group(1),
                margin=margin,
                indent=indent,
                info=opener.group(2).strip(),
                lines=[],
            )
            continue

        if closer != -1:
            commented_to = closer + len(COMMENT_CLOSE)
            comments.append((opened, commented_to))
            continue

        if underline and above is not None:
            headings.append(
                Heading(
                    start=above.start,
                    end=end,
                    level=1 if bare.startswith("=") else 2,
                    text=" ".join(part.strip() for part in text[above.start : start].split("\n") if part.strip()),
                ),
            )
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
            inline.append((opened + atx.end(), end))
            continue

        if marker is not None:
            item_margin = indent + len(marker.group(1)) + item_gap(marker.group(2))
            items.append(item_margin)
            after_break = False

            item_text = bare[marker.end() :]
            item_fence = fence_opener(item_text)
            if item_fence is not None:
                fence = Opened(
                    start=start,
                    run=item_fence.group(1),
                    margin=item_margin,
                    indent=item_margin,
                    info=item_fence.group(2).strip(),
                    lines=[],
                )
            elif item_text.strip():
                paragraph = Paragraph(
                    start=opened + marker.end(),
                    end=end,
                    margin=item_margin,
                )

    if paragraph is not None:
        inline.append((paragraph.start, paragraph.end))

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
        comments=comments,
        inline=inline,
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
