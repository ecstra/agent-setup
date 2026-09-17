"""The hook every agent runs, so the brain is checked without anyone asking.

Claude Code, Codex and Gemini CLI each call this with their own event
JSON on standard input and the event name as the first argument. Three
events matter: the start of a session, a write that is about to create
a file inside .agents/, and a write that just landed there.

    python3 .agents/skills/agent-brain/scripts/hooks.py session-start --agent claude
    python3 .agents/skills/agent-brain/scripts/hooks.py pre-write --agent codex
    python3 .agents/skills/agent-brain/scripts/hooks.py post-write --agent gemini

Exit 2 blocks the write, with the reason on standard error, which all
three agents honour.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

from brainlib import doctor, frontmatter, links, reads, schema, store

BLOCK = 2
FAILED = 1

# The file markers of a Codex patch. A patch written with Windows line
# endings carries a carriage return before every newline, so the path
# is taken up to the last visible character rather than the line's end.
MARKER = re.compile(r"^\*\*\* (Add File|Update File|Delete File|Move to): (.+?)\s*$")
PATCH_OPENS = "*** Begin Patch"

# Where Codex puts the patch text: `command` per its hook reference, the
# others in case that name moves.
PATCH_KEYS = ("command", "patch", "input")

SKILLS = "skills"


@dataclass
class Touch:
    """One file a write event reaches, with what the write would do to it.

    `content` is the whole new text when the tool writes a file whole,
    `old_string` and `new_string` the edit a tool makes in place, and
    `hunks` the blocks a patch applies, each line still carrying its
    leading space, minus or plus. Whichever the agent's tool provides,
    the hook works out the file as the write would leave it.
    """

    path: Path
    content: Optional[str] = None
    old_string: Optional[str] = None
    new_string: Optional[str] = None
    replace_all: bool = False
    hunks: tuple[tuple[str, ...], ...] = ()
    moved_from: Optional[Path] = None


def main(
    argv: Optional[list[str]] = None,
) -> int:
    parser = argparse.ArgumentParser(prog="hooks")
    parser.add_argument("event", choices=("session-start", "pre-write", "post-write"))
    parser.add_argument("--agent", choices=("claude", "codex", "gemini"), default="claude")
    parser.add_argument("--with-rules", action="store_true", help="add SYSTEM.md to the context")
    args = parser.parse_args(argv)

    try:
        return run(args)
    except (store.StoreError, frontmatter.FrontmatterError, OSError, ValueError) as error:
        print(f"the brain hook could not run: {store.explain(error)}", file=sys.stderr)
        return FAILED


def run(
    args: argparse.Namespace,
) -> int:
    """Dispatch one event. A brain the hook cannot read fails visibly, not silently.

    Exit 1 is the non blocking error every agent shows to the person,
    which is the right outcome for a broken brain: the write goes ahead
    and the reason is on screen, rather than every write being refused
    until someone finds a traceback.
    """
    event = read_event()
    brain = locate(event)
    if brain is None:
        return 0

    if args.event == "session-start":
        return session_start(brain=brain, agent=args.agent, with_rules=args.with_rules)

    if args.event == "pre-write":
        return pre_write(brain=brain, event=event, agent=args.agent)

    return post_write(brain=brain, event=event, agent=args.agent)


def read_event() -> dict:
    """The event JSON the agent piped in, or nothing when it piped nothing.

    A closed standard input leaves `sys.stdin` as None, which is not an
    event either.
    """
    if sys.stdin is None or sys.stdin.isatty():
        return {}

    raw = sys.stdin.read()
    if not raw.strip():
        return {}

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def locate(
    event: dict,
) -> Optional[store.Brain]:
    start = Path(event.get("cwd") or Path.cwd())

    try:
        return store.find_brain(start)
    except store.StoreError:
        return None


def session_start(
    brain: store.Brain,
    agent: str,
    with_rules: bool,
) -> int:
    text = "The brain, counted from the files right now:\n" + reads.render_status(reads.status(brain))
    if with_rules:
        rules = brain.root / "SYSTEM.md"
        if store.readable_file(rules):
            text += "\n\nThe rules this project works by, from .agents/SYSTEM.md:\n\n" + text_of(rules)

        chat_style = brain.root.parent / f".{agent}" / "plain-and-short.md"
        if store.readable_file(chat_style):
            text += f"\n\nHow to talk in this project, from .{agent}/plain-and-short.md:\n\n" + text_of(chat_style)

    emit_context(agent=agent, text=text, event_name="SessionStart")
    return 0


def text_of(
    path: Path,
) -> str:
    """The file as text for the agent's context, or one line saying why there is none."""
    try:
        return path.read_bytes().decode("utf-8", errors="replace")
    except OSError as error:
        return f"({store.near(str(path))} cannot be read: {error.strerror or error})"


def pre_write(
    brain: store.Brain,
    event: dict,
    agent: str,
) -> int:
    for touch in touches(event=event, agent=agent):
        verdict = refusal(brain=brain, touch=touch)
        if verdict is None:
            continue

        print(verdict, file=sys.stderr)
        return BLOCK

    emit_nothing(agent)
    return 0


def refusal(
    brain: store.Brain,
    touch: Touch,
) -> Optional[str]:
    """Why this write may not touch the brain by hand, or None if it may.

    A new brain file, an index, a dotted path, a rename and the header
    block of an existing file are the tool's. The prose below a header
    is the agent's to edit, and doctor reads it afterwards.
    """
    if touch.moved_from is not None:
        source = entry_path(brain=brain, path=touch.moved_from)
        if source is not None:
            return f"{source} is renamed with brain refile, not by hand"

    path = touch.path
    inside = links.within(brain=brain, path=path)
    if inside is None or path.suffix != ".md":
        return None

    if Path(inside).parts[0] == SKILLS:
        return None

    if store.hidden(Path(inside)):
        return f"{inside} would be a dotted path, which the brain never lists or checks, so it holds none"

    if Path(inside).name == schema.INDEX:
        if schema.is_kit_path(inside):
            return f"{inside} is generated, run brain index instead of writing it"

        return f"{inside} would be an index where none belongs, the tool builds one per tracker, docs/ and memory/"

    if schema.is_kit_path(inside):
        return None

    if store.quietly(path.exists):
        return header_change(touch=touch, inside=inside)

    if Path(inside).parts[0] == "spec":
        return f"{inside} would nest inside spec/, which holds its files directly"

    return (
        f"{inside} would be a new brain file written by hand. File it with "
        "brain new so it gets its id, its header block and its index line, "
        "with the prose on standard input, or rename an existing one with "
        "brain refile."
    )


def entry_path(
    brain: store.Brain,
    path: Path,
) -> Optional[str]:
    """The brain relative path of an existing entry file, or None for anything else."""
    inside = links.within(brain=brain, path=path)
    if inside is None or path.suffix != ".md" or not store.quietly(path.exists):
        return None

    relative_path = Path(inside)
    if relative_path.parts[0] == SKILLS or store.hidden(relative_path) or schema.is_kit_path(inside):
        return None

    return inside


HEADER_IS_THE_TOOLS = (
    "the header block changes through brain set or brain refile, not by hand. "
    "The prose below it is yours to edit."
)


def header_change(
    touch: Touch,
    inside: str,
) -> Optional[str]:
    """Why this write to an existing brain file may not go ahead, or None if it may.

    The file is judged as the write would leave it: the whole new text,
    the text after the edit, or the file after the patch's hunks. Its
    header block, every line between the fences except the updated date
    the upkeep rule asks the agent to move, must come out as it went in.
    A file the hook cannot read is already broken, so the write is taken
    as the repair and doctor judges the result. A hunk that fits nowhere
    is judged by its shape: refused when it carries a fence or a header
    field, since the hook cannot tell where it would land.
    """
    try:
        text = frontmatter.load(str(touch.path))
        current = frontmatter.parse(text)
    except frontmatter.FrontmatterError:
        return None

    loose: tuple[tuple[str, ...], ...] = ()
    if touch.hunks:
        after, loose = patched(text=text, hunks=touch.hunks)
    else:
        after = outcome(touch=touch, text=text)

    names = field_names(current=current, inside=inside)
    for hunk in loose:
        line = header_line_in(hunk=hunk, names=names)
        if line is not None:
            return f"{inside}: a hunk the hook cannot place touches the header block with '{line}', and {HEADER_IS_THE_TOOLS}"

    if after is None:
        return None

    try:
        wanted = frontmatter.parse(after)
    except frontmatter.FrontmatterError as error:
        return f"{inside} would lose its header block, {error}, and {HEADER_IS_THE_TOOLS}"

    if header_lines(wanted) != header_lines(current):
        return f"{inside}: {HEADER_IS_THE_TOOLS}"

    return None


def field_names(
    current: frontmatter.Document,
    inside: str,
) -> set[str]:
    """The fields this file's header carries or could carry, the updated date aside.

    What the file holds now plus what its kind's spec allows, so a loose
    hunk that adds an optional field the file does not yet carry is
    still read as header work, while a prose line with a colon whose
    name is neither is not.
    """
    names = {name for name in (frontmatter.split_field(line)[0] for line in current.lines) if name is not None}
    kind = schema.kind_for_folder(Path(inside).parts[0])
    if kind is not None:
        names |= {field.name for field in schema.fields_for(kind)}

    return names - {"updated"}


def header_line_in(
    hunk: tuple[str, ...],
    names: set[str],
) -> Optional[str]:
    """The first line of a hunk, kept, removed or added, that is a fence or a header field."""
    for line in hunk:
        text = line[1:]
        if text == frontmatter.FENCE or frontmatter.split_field(text)[0] in names:
            return text

    return None


def outcome(
    touch: Touch,
    text: str,
) -> Optional[str]:
    """The file's text as the write would leave it, or None when nothing says.

    Line endings are folded to one kind first, since the file is read
    that way and an agent on Windows hands over the other kind.
    """
    if touch.content is not None:
        return unix(touch.content)

    if touch.old_string is not None:
        old, new = unix(touch.old_string), unix(touch.new_string or "")
        if touch.replace_all:
            return text.replace(old, new)

        return text.replace(old, new, 1)

    return None


def unix(
    text: str,
) -> str:
    return text.replace("\r\n", "\n")


def patched(
    text: str,
    hunks: tuple[tuple[str, ...], ...],
) -> tuple[Optional[str], tuple[tuple[str, ...], ...]]:
    """The text after the hunks that fit are applied, one after another, and the ones that did not.

    Each hunk is placed against the text as the hunks before it left it,
    the way the patch is applied. A hunk that fits nowhere is handed
    back loose, so the caller can judge it by its shape, and the rest
    are still applied. If none fits, the patch will not apply and there
    is no text to judge.
    """
    lines = text.split("\n")
    loose: list[tuple[str, ...]] = []

    for hunk in hunks:
        before = before_lines(hunk)
        start = block_start(lines=lines, block=before)
        if start is None:
            loose.append(hunk)
            continue

        lines[start : start + len(before)] = [line[1:] for line in hunk if line[:1] in (" ", "+")]

    if len(loose) == len(hunks):
        return None, tuple(loose)

    return "\n".join(lines), tuple(loose)


def before_lines(
    hunk: tuple[str, ...],
) -> list[str]:
    return [line[1:] for line in hunk if line[:1] in (" ", "-")]


def block_start(
    lines: list[str],
    block: list[str],
) -> Optional[int]:
    """Where a run of lines first occurs, or None when it does not, or is empty."""
    if not block:
        return None

    for start in range(len(lines) - len(block) + 1):
        if lines[start : start + len(block)] == block:
            return start

    return None


def header_lines(
    document: frontmatter.Document,
) -> list[str]:
    return [line for line in document.lines if frontmatter.split_field(line)[0] != "updated"]


def post_write(
    brain: store.Brain,
    event: dict,
    agent: str,
) -> int:
    inside = [touch for touch in touches(event=event, agent=agent) if is_inside(brain=brain, path=touch.path)]
    findings = doctor.run(brain) if inside else []
    if not findings:
        emit_nothing(agent)
        return 0

    lines = [finding.line() for finding in findings]
    text = "brain doctor after that write:\n" + "\n".join(lines) + "\nRun brain doctor --fix for the fixable ones."
    emit_context(agent=agent, text=text, event_name=AFTER_WRITE.get(agent, "PostToolUse"))
    return 0


def is_inside(
    brain: store.Brain,
    path: Path,
) -> bool:
    return links.within(brain=brain, path=path) is not None


def touches(
    event: dict,
    agent: str,
) -> list[Touch]:
    """The files a write event touches, absolute, in the shape each agent sends.

    Claude Code and Gemini CLI name one file and hand over its new text
    or the edit they make in place. Codex hands over a patch that can
    add, update, delete or move several files, and only Codex is read
    that way, so a file whose text quotes a patch is not taken for one.
    A relative path is taken against the directory the event names, not
    the one this process happens to run in. The folder part is then
    spelled the way the disk spells it, so a project reached through a
    symlink still compares equal to the brain's real root.
    """
    base = Path(event.get("cwd") or Path.cwd())
    tool_input = event.get("tool_input") or {}
    found: list[Touch] = []

    if agent == "codex":
        for key in PATCH_KEYS:
            for text in texts_in(tool_input.get(key)):
                if PATCH_OPENS in text:
                    return patch_touches(base=base, patch=text)

        return found

    for key in ("file_path", "path", "filePath"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            found.append(
                Touch(
                    path=absolute(base=base, value=value.strip()),
                    content=text_field(tool_input=tool_input, key="content"),
                    old_string=text_field(tool_input=tool_input, key="old_string"),
                    new_string=text_field(tool_input=tool_input, key="new_string"),
                    replace_all=replaces_more_than_one(tool_input),
                )
            )

    return found


def replaces_more_than_one(
    tool_input: dict,
) -> bool:
    """Whether the edit means every occurrence, in the words each tool uses.

    Claude Code says replace_all, Gemini CLI says allow_multiple or
    counts them in expected_replacements.
    """
    if tool_input.get("replace_all") or tool_input.get("allow_multiple"):
        return True

    expected = tool_input.get("expected_replacements")

    return isinstance(expected, int) and expected > 1


def texts_in(
    value: object,
) -> list[str]:
    """The strings a field holds, whether it is one string or a list of them.

    A shell style call hands the patch over as one element of a list.
    """
    if isinstance(value, str):
        return [value]

    if isinstance(value, list):
        return [element for element in value if isinstance(element, str)]

    return []


def text_field(
    tool_input: dict,
    key: str,
) -> Optional[str]:
    value = tool_input.get(key)

    return value if isinstance(value, str) else None


def patch_touches(
    base: Path,
    patch: str,
) -> list[Touch]:
    """Every file a Codex patch names, an add carrying its text, an update its hunks.

    A hunk opens at `@@` and holds context, removed and added lines,
    each with its leading character. It closes at the next `@@`, the
    next file marker, or the end of file mark. A bare empty line inside
    a hunk is a blank context line, as apply_patch reads it, and blank
    lines trailing a hunk are the patch's spacing, not the file's. An
    added file reads a bare empty line as a blank line of its own.
    """
    found: list[Touch] = []
    hunk: list[str] = []
    updating: Optional[int] = None
    adding: Optional[int] = None

    def close_hunk() -> None:
        while hunk and hunk[-1] == " ":
            hunk.pop()
        if updating is not None and hunk:
            found[updating] = replace(found[updating], hunks=found[updating].hunks + (tuple(hunk),))
        hunk.clear()

    for raw in patch.splitlines():
        line = raw.rstrip("\r")
        marker = MARKER.match(line)
        if marker is not None:
            close_hunk()
            path = absolute(base=base, value=marker.group(2))
            if marker.group(1) == "Move to" and updating is not None:
                found.append(Touch(path=path, moved_from=found[updating].path))
                continue

            found.append(Touch(path=path, content="" if marker.group(1) == "Add File" else None))
            updating = len(found) - 1 if marker.group(1) == "Update File" else None
            adding = len(found) - 1 if marker.group(1) == "Add File" else None
            continue

        if adding is not None and (line[:1] == "+" or line == ""):
            found[adding] = replace(found[adding], content=(found[adding].content or "") + line[1:] + "\n")
            continue

        if line.startswith("@@") or line.startswith("*** End"):
            close_hunk()
            continue

        if updating is not None and line[:1] in (" ", "-", "+"):
            hunk.append(line)
        elif updating is not None and line == "":
            hunk.append(" ")

    close_hunk()

    return found


def absolute(
    base: Path,
    value: str,
) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = base / path

    return settled(path)


def settled(
    path: Path,
) -> Path:
    """The path with its folder resolved on disk and the file itself left alone.

    Only the folder is followed, so a symlinked file still counts where
    it sits. A folder that cannot be resolved, a loop on the 3.9 floor
    or a path with a stray null byte in it, keeps its lexical spelling
    and is judged as written.
    """
    try:
        return path.parent.resolve() / path.name
    except (OSError, RuntimeError, ValueError):
        return path


# What each agent calls the event after a write, which the reply names.
# Claude Code and Codex say PostToolUse, Gemini CLI says AfterTool.
AFTER_WRITE = {"claude": "PostToolUse", "codex": "PostToolUse", "gemini": "AfterTool"}


def emit_context(
    agent: str,
    text: str,
    event_name: str,
) -> None:
    """Hand text back the way this agent takes context from a hook.

    Codex takes plain text on standard output as developer context.
    Claude Code and Gemini CLI take one JSON object naming the event.
    """
    if agent == "codex":
        print(text)
        return

    payload = {"hookSpecificOutput": {"hookEventName": event_name, "additionalContext": text}}
    print(json.dumps(payload))


def emit_nothing(
    agent: str,
) -> None:
    """Say there is nothing to add, in the form the agent wants.

    On a pass, exit 0, Gemini CLI parses standard output as JSON, so it
    gets an empty object. On a refusal, exit 2, every agent takes the
    reason from standard error and reads nothing else. Claude Code takes
    silence on a pass, and for Codex anything printed would become
    context, so both get nothing.
    """
    if agent == "gemini":
        print("{}")


if __name__ == "__main__":
    sys.exit(main())
