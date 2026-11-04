"""The line the tick adds when an agent did by hand what the brain tool does, so the habit is named where it shows.

The tick runs after the calls, so nothing here refuses one. A read is a
grep of the brain's header fields over the brain, or a listing or a
count of a tracker folder. A write is a redirect, an edit in place or a
file command onto a path in a tracker folder or one of the brain's own
files. The kit's own files in the brain's folder are none of these, and
a call to the tool itself or to git's reading and committing says
nothing. A shell command is split as the shell splits it and read
segment by segment, a `cd` moving where its relative paths count from.
"""

import os
import re
import shlex
from typing import Iterator, Optional

from . import autoack, conclude, schema, store, task

CALL = "python3 .agents/skills/agent-brain/scripts/brain.py"
READ = f"The brain answers that itself, {CALL} list <kind> --status <status> for its entries, status for its counts and show <key> for one, where a grep of its fields or a listing of its folders only guesses."
WRITE = f"That call wrote into the brain by hand, which the brain tool does through new, set, refile, steps, task, ledger, handover and index, so run {CALL} doctor to see what it left."
START = f"Read the brain through the tool too, {CALL} list <kind> --status <status>, status or show <key>, never by a grep of its fields or a listing of its folders."

# A header field written as a grep pattern, `^status:` or `severity: bug`,
# for every field any kind of entry carries.
FIELD = re.compile(r"(?<![\w-])(?:" + "|".join(sorted({re.escape(field.name) for kind in schema.KINDS.values() for field in schema.fields_for(kind)})) + r"):")

# The brain's own files beside the tracker folders, which the tool alone writes.
OWN_FILES = (schema.INDEX, autoack.FILE, task.FILE, conclude.FILE, schema.HANDOVER_FOLDER)

READERS = {"grep", "egrep", "fgrep", "rg", "ag", "ack", "awk", "gawk", "sed", "perl"}
LISTERS = {"ls", "find", "fd", "tree", "wc", "du"}
WRITERS = {"mv", "rm", "rmdir", "touch", "mkdir", "tee"}
COPIERS = {"cp", "ln", "install"}
IN_PLACE = {"sed", "perl"}
TOOLS = {"brain"}
PYTHONS = {"python", "python3", "py"}
SHELL_WORDS = {"do", "then", "else", "elif", "if", "while", "until", "time", "!", "{", "}", "done", "fi", "esac", "exec", "command", "sudo", "env"}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
IN_PLACE_FLAG = re.compile(r"^(?:-[a-zA-Z]*i|--in-place)")
PUNCTUATION = set("();<>|&")

SEARCHES = {"Grep", "grep_search", "search_file_content"}
GLOBS = {"Glob", "glob"}
LISTINGS = {"list_directory", "LS"}
BULK_READS = {"read_many_files"}


def lines(
    brain: store.Brain,
    event: dict,
) -> list[str]:
    """The lines a tick adds for the calls its event carries, each once, the read's before the write's, or none."""
    root = os.path.realpath(str(brain.root))
    base = os.path.realpath(str(event.get("cwd") or os.getcwd()))
    read = wrote = False

    for name, tool_input in calls_of(event):
        did_read, did_write = judged(name=name, tool_input=tool_input, base=base, root=root)
        read, wrote = read or did_read, wrote or did_write

    return [line for done, line in ((read, READ), (wrote, WRITE)) if done]


def calls_of(
    event: dict,
) -> Iterator[tuple[str, dict]]:
    """Each call the event carries as its tool's name and input, Claude Code's batch of them or the one call Codex and Gemini CLI hand over, and nothing of a shape the hook cannot read."""
    if not isinstance(event, dict):
        return

    batch = event.get("tool_calls")
    calls = batch if isinstance(batch, list) else [event] if "tool_name" in event else []
    for call in calls:
        if isinstance(call, dict) and isinstance(call.get("tool_input"), dict):
            yield str(call.get("tool_name") or ""), call["tool_input"]


def judged(
    name: str,
    tool_input: dict,
    base: str,
    root: str,
) -> tuple[bool, bool]:
    """Whether one call read the brain's fields or listed its folders, and whether it wrote into the brain."""
    if "command" in tool_input:
        command = shell_text(tool_input["command"])
        if command is None:
            return False, False

        return shell(command=command, base=placed(token=str(tool_input.get("dir_path") or ""), base=base), root=root)

    if name in SEARCHES:
        where = placed(token=str(tool_input.get("path") or tool_input.get("dir_path") or ""), base=base)
        narrowed = tool_input.get("glob") or tool_input.get("include_pattern")
        spots = [where] + ([placed(token=str(narrowed), base=where)] if narrowed else [])
        return bool(FIELD.search(str(tool_input.get("pattern") or ""))) and any(reaches(path=spot, root=root) for spot in spots), False

    if name in GLOBS:
        where = placed(token=str(tool_input.get("path") or tool_input.get("dir_path") or ""), base=base)
        return in_tracker(path=placed(token=str(tool_input.get("pattern") or ""), base=where), root=root), False

    if name in LISTINGS:
        return in_tracker(path=placed(token=str(tool_input.get("dir_path") or tool_input.get("path") or ""), base=base), root=root), False

    if name in BULK_READS:
        included = tool_input.get("include") or tool_input.get("paths") or []
        items = [included] if isinstance(included, str) else included if isinstance(included, list) else []
        return any(in_tracker(path=placed(token=str(item), base=base), root=root) for item in items), False

    return False, False


def shell_text(
    command: object,
) -> Optional[str]:
    """The command line a shell call runs, the script of a `bash -lc` list Codex hands over among them, or None for anything else."""
    if isinstance(command, str):
        return command

    if isinstance(command, list) and all(isinstance(part, str) for part in command):
        if len(command) >= 3 and command[-2] in ("-c", "-lc"):
            return command[-1]

        return shlex.join(command)

    return None


def shell(
    command: str,
    base: str,
    root: str,
) -> tuple[bool, bool]:
    """Whether a command line greps the brain's fields or lists a tracker folder, and whether it writes into the brain.

    A field grep counts once any segment of the line reaches the brain,
    since a loop names the folder in one segment and greps each file in
    another. A line the shell could not split says nothing.
    """
    try:
        tokens = shlex_tokens(command)
    except ValueError:
        return False, False

    field = reached = listed = wrote = False
    for words in segments(tokens):
        program, args = program_of(words)
        if program is None:
            continue

        if program == "cd":
            base = placed(token=args[0], base=base) if args else base
            continue

        if program in TOOLS or (program in PYTHONS and any(arg.endswith(("brain.py", "hooks.py")) for arg in args[:3])):
            continue

        if program == "git":
            sub = next((arg for arg in args if not arg.startswith("-")), "")
            if sub not in ("mv", "rm"):
                continue

        targets, rest = redirected(args)
        wrote = wrote or any(where(path=placed(token=target, base=base), root=root) == ENTRIES for target in targets)

        flags = [arg for arg in rest if arg.startswith("-")]
        paths = [placed(token=arg, base=base) for arg in rest if arg and not arg.startswith(("-", "$"))]
        in_place = program in IN_PLACE and any(IN_PLACE_FLAG.match(flag) for flag in flags)

        if program == "git" or program in WRITERS or in_place:
            wrote = wrote or any(where(path=path, root=root) == ENTRIES for path in paths)
        elif program in COPIERS:
            wrote = wrote or bool(paths) and where(path=paths[-1], root=root) == ENTRIES
        elif program in LISTERS:
            listed = listed or any(in_tracker(path=path, root=root) for path in paths or [base])
        elif program in READERS:
            field = field or any(FIELD.search(arg) for arg in rest)

        reached = reached or any(reaches(path=path, root=root) for path in paths)

    return (field and reached) or listed, wrote


def shlex_tokens(
    command: str,
) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True

    return list(lexer)


def segments(
    tokens: list[str],
) -> Iterator[list[str]]:
    """The tokens between the shell's separators, a redirect's arrows kept with the segment they belong to."""
    current: list[str] = []
    for token in tokens:
        if token and set(token) <= PUNCTUATION and ">" not in token and "<" not in token:
            if current:
                yield current
            current = []
            continue

        current.append(token)

    if current:
        yield current


def program_of(
    words: list[str],
) -> tuple[Optional[str], list[str]]:
    """The program a segment runs, by its bare name, past the shell's own words and any assignments in front, and the words after it."""
    for at, word in enumerate(words):
        if word in SHELL_WORDS or ASSIGNMENT.match(word):
            continue

        return os.path.basename(word), words[at + 1 :]

    return None, []


def redirected(
    args: list[str],
) -> tuple[list[str], list[str]]:
    """The paths a segment's output goes to by `>` or `>>`, and its words without the arrows and what they point at."""
    targets: list[str] = []
    rest: list[str] = []
    skip = False
    for at, arg in enumerate(args):
        if skip:
            skip = False
            continue

        if arg and set(arg) <= PUNCTUATION:
            if ">" in arg and at + 1 < len(args):
                targets.append(args[at + 1])
            skip = True
            continue

        rest.append(arg)

    return targets, rest


def placed(
    token: str,
    base: str,
) -> str:
    """The path a word names, counted from `base` when it is relative, with the links on its way followed as far as they go."""
    return os.path.realpath(os.path.join(base, os.path.expanduser(token)))


ROOT = "root"
ENTRIES = "entries"


def where(
    path: str,
    root: str,
) -> Optional[str]:
    """ROOT for the brain's folder itself, ENTRIES for a path in a tracker folder or one of the brain's own files, and None for anywhere else, the kit's own files in the brain's folder among them."""
    if path == root:
        return ROOT

    if not path.startswith(root + os.sep):
        return None

    first = path[len(root) + 1 :].split(os.sep)[0]

    return ENTRIES if first in schema.INDEXED_FOLDERS or first in OWN_FILES else None


def reaches(
    path: str,
    root: str,
) -> bool:
    """Whether a search from this path reaches the brain's entries, from the brain's folder or from inside it."""
    return where(path=path, root=root) is not None


def in_tracker(
    path: str,
    root: str,
) -> bool:
    """Whether the path is a tracker folder or inside one."""
    if not path.startswith(root + os.sep):
        return False

    return path[len(root) + 1 :].split(os.sep)[0] in schema.INDEXED_FOLDERS
