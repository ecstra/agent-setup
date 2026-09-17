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
from dataclasses import dataclass
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

SKILLS = "skills"


@dataclass
class Touch:
    """One file a write event reaches, with what the write would do to it.

    `content` is the whole new text when the tool writes a file whole,
    `old_string` the text an edit replaces, `removed` the lines a patch
    takes out. Whichever the agent's tool provides, the hook reads.
    """

    path: Path
    content: Optional[str] = None
    old_string: Optional[str] = None
    removed: tuple[str, ...] = ()


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
        return session_start(brain, args.agent, args.with_rules)

    if args.event == "pre-write":
        return pre_write(brain, event)

    return post_write(brain, event, args.agent)


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

    emit_context(agent, text, event_name="SessionStart")
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
) -> int:
    for touch in touches(event):
        verdict = refusal(brain, touch)
        if verdict is None:
            continue

        print(verdict, file=sys.stderr)
        return BLOCK

    return 0


def refusal(
    brain: store.Brain,
    touch: Touch,
) -> Optional[str]:
    """Why this write may not touch the brain by hand, or None if it may.

    A new brain file, an index, a dotted path and the header block of
    an existing file are the tool's. The prose below a header is the
    agent's to edit, and doctor reads it afterwards.
    """
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


HEADER_IS_THE_TOOLS = (
    "the header block changes through brain set or brain refile, not by hand. "
    "The prose below it is yours to edit."
)


def header_change(
    touch: Touch,
    inside: str,
) -> Optional[str]:
    """Why this write to an existing brain file may not go ahead, or None if it may.

    The header block is every line between the fences except the
    updated date, which the upkeep rule asks the agent to move. A tool
    that writes the file whole shows its new text, one that edits shows
    the text it replaces, a patch shows the lines it takes out, and each
    is judged by whether it reaches the header.
    """
    try:
        text = frontmatter.load(str(touch.path))
        current = frontmatter.parse(text)
    except frontmatter.FrontmatterError:
        return None

    header = header_lines(current)

    if touch.content is not None:
        try:
            wanted = frontmatter.parse(touch.content)
        except frontmatter.FrontmatterError:
            return f"{inside} would lose its header block, and {HEADER_IS_THE_TOOLS}"

        if header_lines(wanted) != header:
            return f"{inside}: {HEADER_IS_THE_TOOLS}"

    if touch.old_string and edit_reaches_header(text=text, old_string=touch.old_string):
        return f"{inside}: {HEADER_IS_THE_TOOLS}"

    if any(line in header for line in touch.removed):
        return f"{inside}: {HEADER_IS_THE_TOOLS}"

    return None


def header_lines(
    document: frontmatter.Document,
) -> list[str]:
    return [line for line in document.lines if frontmatter.split_field(line)[0] != "updated"]


def edit_reaches_header(
    text: str,
    old_string: str,
) -> bool:
    """Whether the text an edit replaces lies in the header, the updated line aside."""
    end = frontmatter.header_end(text)
    if end is None:
        return False

    start = 0
    while True:
        found = text.find(old_string, start)
        if found < 0 or found >= end:
            return False

        if not within_updated_line(text=text, start=found, stop=found + len(old_string)):
            return True

        start = found + 1


def within_updated_line(
    text: str,
    start: int,
    stop: int,
) -> bool:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", line_start)
    if line_end < 0:
        line_end = len(text)

    return text[line_start:line_end].startswith("updated:") and stop <= line_end


def post_write(
    brain: store.Brain,
    event: dict,
    agent: str,
) -> int:
    inside = [touch for touch in touches(event) if is_inside(brain, touch.path)]
    if not inside:
        return 0

    findings = doctor.run(brain)
    if not findings:
        return 0

    lines = [finding.line() for finding in findings]
    text = "brain doctor after that write:\n" + "\n".join(lines) + "\nRun brain doctor --fix for the fixable ones."
    emit_context(agent, text, event_name="PostToolUse")
    return 0


def is_inside(
    brain: store.Brain,
    path: Path,
) -> bool:
    return links.within(brain=brain, path=path) is not None


def touches(
    event: dict,
) -> list[Touch]:
    """The files a write event touches, absolute, in the shape each agent sends.

    Claude Code and Gemini CLI name one file and hand over its new text
    or the text an edit replaces. Codex hands over a patch that can add,
    update, delete or move several files. A relative path is taken
    against the directory the event names, not the one this process
    happens to run in. The folder part is then spelled the way the disk
    spells it, so a project reached through a symlink still compares
    equal to the brain's real root.
    """
    base = Path(event.get("cwd") or Path.cwd())
    tool_input = event.get("tool_input") or {}
    found: list[Touch] = []

    for key in ("file_path", "path", "filePath"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            found.append(
                Touch(
                    path=absolute(base=base, value=value.strip()),
                    content=text_field(tool_input, "content"),
                    old_string=text_field(tool_input, "old_string"),
                )
            )

    for value in tool_input.values():
        if isinstance(value, str) and PATCH_OPENS in value:
            found.extend(patch_touches(base=base, patch=value))

    return found


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
    """Every file a Codex patch names, with the lines an update takes out."""
    found: list[Touch] = []
    removed: list[str] = []

    for line in patch.splitlines():
        marker = MARKER.match(line)
        if marker is not None:
            found.append(Touch(path=absolute(base=base, value=marker.group(2))))
            removed = []
            continue

        if found and line.startswith("-"):
            removed.append(line[1:].rstrip("\r"))
            found[-1] = Touch(path=found[-1].path, removed=tuple(removed))

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


def emit_context(
    agent: str,
    text: str,
    event_name: str,
) -> None:
    """Hand text back the way this agent takes context from a hook."""
    if agent == "codex":
        print(text)
        return

    payload = {"hookSpecificOutput": {"hookEventName": event_name, "additionalContext": text}}
    print(json.dumps(payload))


if __name__ == "__main__":
    sys.exit(main())
