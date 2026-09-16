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
from pathlib import Path
from typing import Optional

from brainlib import doctor, reads, store

BLOCK = 2

ADD_FILE = re.compile(r"^\*\*\* Add File: (.+)$", re.MULTILINE)

HAND_WRITTEN_OK = ("skills", "spec")
KIT_FILES = ("SYSTEM.md", "README.md", "house-rules.md", "VERSION")


def main(
    argv: Optional[list[str]] = None,
) -> int:
    parser = argparse.ArgumentParser(prog="hooks")
    parser.add_argument("event", choices=("session-start", "pre-write", "post-write"))
    parser.add_argument("--agent", choices=("claude", "codex", "gemini"), default="claude")
    parser.add_argument("--with-rules", action="store_true", help="add SYSTEM.md to the context")
    args = parser.parse_args(argv)

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
    if sys.stdin.isatty():
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
        if rules.is_file():
            text += "\n\nThe rules this project works by, from .agents/SYSTEM.md:\n\n" + text_of(rules)

        chat_style = brain.root.parent / f".{agent}" / "plain-and-short.md"
        if chat_style.is_file():
            text += f"\n\nHow to talk in this project, from .{agent}/plain-and-short.md:\n\n" + text_of(chat_style)

    emit_context(agent, text, event_name="SessionStart")
    return 0


def text_of(
    path: Path,
) -> str:
    """The file as text for the agent's context, whatever bytes it holds."""
    return path.read_bytes().decode("utf-8", errors="replace")


def pre_write(
    brain: store.Brain,
    event: dict,
) -> int:
    for path in written_paths(event):
        verdict = refusal(brain, path)
        if verdict is None:
            continue

        print(verdict, file=sys.stderr)
        return BLOCK

    return 0


def refusal(
    brain: store.Brain,
    path: Path,
) -> Optional[str]:
    """Why this write may not create a brain file by hand, or None if it may."""
    try:
        relative = path.resolve().relative_to(brain.root)
    except ValueError:
        return None

    if path.suffix != ".md" or path.exists():
        return None

    if relative.parts[0] in HAND_WRITTEN_OK or relative.name in KIT_FILES:
        return None

    if relative.name == "INDEX.md":
        return f"{relative} is generated, run brain index instead of writing it"

    return (
        f"{relative} would be a new brain file written by hand. File it with "
        "brain new so it gets its id, its header block and its index line, "
        "with the prose on standard input."
    )


def post_write(
    brain: store.Brain,
    event: dict,
    agent: str,
) -> int:
    inside = [path for path in written_paths(event) if is_inside(brain, path)]
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
    try:
        path.resolve().relative_to(brain.root)
    except ValueError:
        return False

    return True


def written_paths(
    event: dict,
) -> list[Path]:
    """The files a write event touches, in the shape each agent sends."""
    tool_input = event.get("tool_input") or {}
    found: list[Path] = []

    for key in ("file_path", "path", "filePath"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            found.append(Path(value))

    for value in tool_input.values():
        if isinstance(value, str):
            found.extend(Path(match) for match in ADD_FILE.findall(value))

    return found


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
