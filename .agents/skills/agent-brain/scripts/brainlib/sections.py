"""The `## Heading` blocks a body carries, and the code a text holds.

Reading only. Nothing here rewrites prose, it reports what is there so a
command can refuse to file something the spec says is incomplete. The
reading of code here is the one every reader shares, section 0's cut,
the gates, the brain's own bodies and doctor alike.
"""

import bisect
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
# a run of backticks no backslash escapes, a backslash read with the
# character after it so an escaped backslash escapes nothing, closed by
# the next run as long inside its paragraph, heading or table row, so
# three backticks in the middle of a sentence with no three to close
# them are just backticks. A block quote's lines are read as a text of
# their own with their markers taken off, and a table's rows each alone.
LINE = re.compile(r"^.*$", re.MULTILINE)
FENCE_OPEN = re.compile(r"(`{3,}|~{3,})(.*)$")
FENCE_CLOSE = re.compile(r"(`{3,}|~{3,})\s*$")
LIST_MARKER = re.compile(r"([-*+]|\d{1,9}[.)])(?:([ \t]+)|$)")
THEMATIC_BREAK = re.compile(r"([-*_])(?:[ \t]*\1){2,}\s*$")
ATX_OPEN = re.compile(r"(#{1,6})(?:[ \t]+|$)")
ATX_CLOSE = re.compile(r"(?:^|[ \t]+)#+$")
SETEXT_UNDERLINE = re.compile(r"(?:=+|-+)\s*$")
DELIMITER_ROW = re.compile(r"[ \t]*(?:\|[ \t]*)?:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*(?:\|[ \t]*)?$")
INLINE_OPEN = re.compile(r"\\[\s\S]|<!--|`+")
NOT_A_LINE_END = re.compile(r"[^\n]")
QUOTE_MARK = ">"
CODE_INDENT = 4

# How deep the reader reads a quote inside a quote, each level a call of
# its own, so a line of hundreds of `>` stays well inside Python's
# recursion limit, and the markers past it are the innermost quote's text.
QUOTE_DEPTH = 32

# An HTML comment hides what it holds from a reader that asks, a gate
# or a heading an owner commented out for one. It is no code, so the
# kit's marker, itself a comment, is still found outside code. One that
# opens a line or a list item's text is a block of its own, as markdown
# reads it, one inside a list item ends with the item where no `-->`
# comes first, and one inside a sentence ends with its paragraph.
COMMENT_OPEN = "<!--"
COMMENT_CLOSE = "-->"
COMMENT_CLOSER = re.compile(re.escape(COMMENT_CLOSE))


@dataclass(frozen=True)
class Fence:
    """One fenced block: where it starts and ends, its info string, its lines with the indent its fence carries taken off, and whether a closer ends it or it runs to the end of the text."""

    start: int
    end: int
    info: str
    text: str
    closed: bool


@dataclass(frozen=True)
class Heading:
    """One heading outside code, of hashes or a setext line: where it starts and ends, its level, and its text without the closing hashes."""

    start: int
    end: int
    level: int
    text: str


@dataclass(frozen=True)
class Blocks:
    """What a reading of the blocks finds: where the code blocks sit, the fences among them, the headings outside them, the HTML comments that open a line, the stretches of paragraph and heading text the spans are read in, and whether the text ends inside a paragraph, its last stretch, which a lazy line under a quote runs on."""

    code: list[tuple[int, int]]
    fences: list[Fence]
    headings: list[Heading]
    comments: list[tuple[int, int]]
    inline: list[tuple[int, int]]
    paragraph_open: bool


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
    """A paragraph still open as the lines are read: where its text starts, where its last line ends, the margin of the list item it opened in, which a line under it that is no lazy continuation keeps to, and whether it is a quote's paragraph run on past the quote, which no line under it underlines or makes a table."""

    start: int
    end: int
    margin: int
    lazy: bool


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

    A comment that opens a line, a list item's text or a line of a
    quote runs to the first `-->` past it, inside the quote for one in
    a quote, through blank lines and through anything that looks like a
    fence, since no fence opens inside it. One in a list item runs to
    the first `-->` before the item ends, at the first line that is not
    blank and sits left of the item's text, or to the item's end where
    none comes first. One inside a paragraph or a heading runs to the
    first `-->` before that paragraph or heading ends. Any other opener
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

    A backslash is read with the character after it, so an escaped
    backtick or `<` opens nothing and an escaped backslash escapes
    nothing. A run of backticks is closed by the next run as long, and a
    comment by its first `-->`, each inside its stretch, and whichever
    opens first holds what follows, so a backtick inside a comment opens
    no span and a backslash inside either is its own. An opener with
    nothing to close it inside its stretch is plain text.
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

            if opener.group().startswith("\\"):
                position = opener.end()
                continue

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
    depth: int = 0,
) -> Blocks:
    """The code blocks, the fences and the headings of the text, read line by line in the order they come.

    A list item's own line is read past its marker as a line of its
    own, so a fence, a heading, an HTML comment or another item opens
    there too. The margin is where the text of the list item the line
    sits in starts, the spacing after its marker counted in columns, so
    a list item's paragraph indented four columns is read, and a heading
    or a fence left of that margin ends every list that is open, as does
    any line left of it where no paragraph is open, and a blank line
    under an item whose marker ended its line. A line of three or more
    `-`, `*` or `_` and nothing else, spaced or not, is a thematic break
    and no list item. An HTML comment that opens a line runs to the line
    that holds its first `-->`, inside a list item to the item's end
    where no `-->` comes first, and nothing inside it opens. A paragraph
    is open from its first line, a list item's own line among them, to a
    blank line or another block, and a line of `=` or `-` under it makes
    it a setext heading, unless the line sits left of the list item the
    paragraph opened in, which makes it a lazy line of the paragraph, or
    for `-` a thematic break. A line of hyphens and pipes under one makes
    the paragraph's last line a table's header row, and each line after
    it that holds a pipe is a row. A block quote's lines are read as a
    text of their own, its code, comments and stretches put back where
    they stand in the text and its fences and headings left out, since
    no gate and no section stands in a quote, and a line under it that
    opens no block runs on the quote's last paragraph. `depth` is how
    many quotes the text already sits in, and at QUOTE_DEPTH a `>` opens
    no quote and is the innermost quote's text. The stretches of
    paragraph, heading and row text are where the spans and the comments
    inside a sentence are read.
    """
    code: list[tuple[int, int]] = []
    fences: list[Fence] = []
    headings: list[Heading] = []
    comments: list[tuple[int, int]] = []
    inline: list[tuple[int, int]] = []
    items: list[int] = []
    fence: Optional[Opened] = None
    paragraph: Optional[Paragraph] = None
    in_table = False
    empty_item = False
    read_to = 0

    for match in LINE.finditer(text):
        line = match.group()
        start, end = match.span()

        if start < read_to:
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
                    closed=True,
                ),
            )
            fence = None
            continue

        if not line.strip():
            if paragraph is not None:
                inline.append((paragraph.start, paragraph.end))
            paragraph = None
            in_table = False
            # an item whose marker ends its line takes no text past a blank line, as markdown reads it
            if empty_item:
                items.pop()
            empty_item = False
            continue

        empty_item = False
        position = start
        column = 0
        # a list item's text past its marker is read again as a line of its own, so the loop runs once per marker the line opens with
        while True:
            bare = text[position:end].lstrip()
            opened = end - len(bare)
            indent = indent_of(
                line=text[position:end],
                column=column,
            )
            runs_on = paragraph is not None and not paragraph.lazy
            underline = runs_on and indent >= paragraph.margin and SETEXT_UNDERLINE.match(bare) is not None
            header = runs_on and not underline and "|" in bare and DELIMITER_ROW.match(bare) is not None
            thematic = not underline and not header and THEMATIC_BREAK.match(bare) is not None
            marker = None if thematic or header else LIST_MARKER.match(bare)
            atx = ATX_OPEN.match(bare)
            opener = fence_opener(bare)
            comment: Optional[tuple[int, int]] = None
            if bare.startswith(COMMENT_OPEN):
                # a comment is a block, so it keeps to the innermost item the line does not sit left of, the margin the pop below leaves
                comment = comment_at(
                    text=text,
                    opened=opened,
                    margin=next((item for item in reversed(items) if item <= indent), 0),
                )

            quoted = depth < QUOTE_DEPTH and bare.startswith(QUOTE_MARK)
            interrupts = underline or thematic or marker is not None or atx is not None or opener is not None or comment is not None or quoted
            if paragraph is None or interrupts:
                while items and indent < items[-1]:
                    items.pop()

            margin = items[-1] if items else 0
            if indent - margin >= CODE_INDENT:
                if paragraph is None:
                    code.append((position, end))
                else:
                    paragraph.end = end
                break

            if in_table and not interrupts and "|" in bare:
                inline.append((opened, end))
                break

            in_table = False
            if header:
                head = max(paragraph.start, text.rfind("\n", 0, paragraph.end) + 1)
                if head > paragraph.start:
                    inline.append((paragraph.start, head - 1))
                inline.append((head, paragraph.end))
                paragraph = None
                in_table = True
                break

            if not interrupts:
                if paragraph is None:
                    paragraph = Paragraph(
                        start=opened,
                        end=end,
                        margin=margin,
                        lazy=False,
                    )
                paragraph.end = end
                break

            above = paragraph
            if paragraph is not None:
                inline.append((paragraph.start, paragraph.end))
            paragraph = None

            if opener is not None:
                fence = Opened(
                    start=start,
                    run=opener.group(1),
                    margin=margin,
                    indent=indent,
                    info=opener.group(2).strip(),
                    lines=[],
                )
                break

            if comment is not None:
                closed, read_to = comment
                comments.append((opened, closed))
                break

            if underline and above is not None:
                headings.append(
                    Heading(
                        start=above.start,
                        end=end,
                        level=1 if bare.startswith("=") else 2,
                        text=" ".join(part.strip() for part in text[above.start : start].split("\n") if part.strip()),
                    ),
                )
                break

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
                break

            if quoted:
                quote, read_to = quote_at(
                    text=text,
                    start=start,
                    mark=opened,
                    margin=margin,
                    depth=depth,
                )
                code += quote.code
                comments += quote.comments
                inline += quote.inline
                if quote.paragraph_open:
                    last_start, last_end = inline.pop()
                    paragraph = Paragraph(
                        start=last_start,
                        end=last_end,
                        margin=margin,
                        lazy=True,
                    )
                break

            if marker is None:
                break

            after = indent + len(marker.group(1))
            item_text = bare[marker.end() :]
            items.append(
                after
                + item_gap(
                    spacing=marker.group(2),
                    column=after,
                    rest=item_text,
                ),
            )
            if not item_text.strip():
                empty_item = True
                break

            position = opened + len(marker.group(1))
            column = after

    paragraph_open = paragraph is not None
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
                closed=False,
            ),
        )

    return Blocks(
        code=code,
        fences=fences,
        headings=headings,
        comments=comments,
        inline=inline,
        paragraph_open=paragraph_open,
    )


def quote_at(
    text: str,
    start: int,
    mark: int,
    margin: int,
    depth: int,
) -> tuple[Blocks, int]:
    """The blocks of the block quote whose first line starts at `start` with its `>` at `mark`, in a text that sits `depth` quotes deep, where they stand in the text, and where the quote's last line ends.

    The quote runs over the lines under it whose text opens with a `>`
    less than four columns past the margin. Each line loses its `>` and
    a space or a tab after it, so the quote is read as a text of its
    own, one quote deeper, and a quote inside it the same way in turn,
    down to QUOTE_DEPTH.
    """
    taken: list[int] = []
    origins: list[int] = []
    lines: list[str] = []
    length = 0
    end = start
    for match in LINE.finditer(text, start):
        line = match.group()
        marked = mark
        if match.start() != start:
            bare = line.lstrip()
            if not bare.startswith(QUOTE_MARK) or not margin <= indent_of(line) < margin + CODE_INDENT:
                break

            marked = match.end() - len(bare)

        content = marked + len(QUOTE_MARK)
        if text[content : content + 1] in (" ", "\t"):
            content += 1

        taken.append(length)
        origins.append(content)
        lines.append(text[content : match.end()])
        length += match.end() - content + 1
        end = match.end()

    inner = blocks_of(
        text="\n".join(lines),
        depth=depth + 1,
    )

    return (
        Blocks(
            code=placed(
                spans=inner.code,
                taken=taken,
                origins=origins,
            ),
            fences=[],
            headings=[],
            comments=placed(
                spans=inner.comments,
                taken=taken,
                origins=origins,
            ),
            inline=placed(
                spans=inner.inline,
                taken=taken,
                origins=origins,
            ),
            paragraph_open=inner.paragraph_open,
        ),
        end,
    )


def placed(
    spans: list[tuple[int, int]],
    taken: list[int],
    origins: list[int],
) -> list[tuple[int, int]]:
    """The spans of a text whose lines start at the `taken` offsets, where they stand in the text those lines were taken from, each line starting there at its offset in `origins`."""
    return [
        (
            origin_of(
                offset=start,
                taken=taken,
                origins=origins,
            ),
            origin_of(
                offset=end,
                taken=taken,
                origins=origins,
            ),
        )
        for start, end in spans
    ]


def origin_of(
    offset: int,
    taken: list[int],
    origins: list[int],
) -> int:
    """Where an offset of a text whose lines start at the `taken` offsets stands in the text its lines were taken from."""
    line = bisect.bisect_right(taken, offset) - 1

    return origins[line] + offset - taken[line]


def comment_at(
    text: str,
    opened: int,
    margin: int,
) -> Optional[tuple[int, int]]:
    """Where the HTML comment whose `<!--` opens a line at `opened` ends and where the reading of the lines goes on, or None where it is no comment.

    It ends at its first `-->`. Inside a list item whose text starts at
    column `margin` it ends where the item ends if no `-->` comes first,
    at the first line under it that is not blank and sits left of the
    item's text, as CommonMark ends an HTML block with its container,
    and the reading goes on at that line. At the margin of the text an
    opener with no closer is no comment, so a stray one never hides the
    rest of the text.
    """
    bound = len(text)
    if margin:
        bound = item_end(
            text=text,
            position=opened,
            margin=margin,
        )

    closer = text.find(COMMENT_CLOSE, opened + len(COMMENT_OPEN), bound)
    if closer != -1:
        closed = closer + len(COMMENT_CLOSE)
        return closed, closed

    if not margin:
        return None

    return len(text[:bound].rstrip()), bound


def item_end(
    text: str,
    position: int,
    margin: int,
) -> int:
    """Where the list item whose text starts at column `margin` ends below the line that holds `position`, at the first line that is not blank and sits left of that column, else at the end of the text."""
    below = text.find("\n", position) + 1
    if not below:
        return len(text)

    for line in LINE.finditer(
        string=text,
        pos=below,
    ):
        if line.group().strip() and indent_of(line.group()) < margin:
            return line.start()

    return len(text)


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
    column: int,
    rest: str,
) -> int:
    """How many columns past its marker a list item's text starts, the spacing counted from the column the marker ends at, one where no text follows the marker or the gap would make its text code."""
    gap = (
        indent_of(
            line=spacing or "",
            column=column,
        )
        - column
    )
    if not rest.strip() or gap > CODE_INDENT:
        return 1

    return gap


def indent_of(
    line: str,
    column: int = 0,
) -> int:
    """The column the line's leading white space reaches from the given column, a tab reaching the next multiple of four, so from the line's start how many columns it spans."""
    for character in line:
        if character == " ":
            column += 1
        elif character == "\t":
            column += CODE_INDENT - column % CODE_INDENT
        else:
            break

    return column


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
