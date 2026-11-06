"""The line the tick adds when an agent did by hand what the brain tool does, so the habit is named where it shows.

The model, each rule with its reason.

- The tick runs after the calls, so nothing here refuses one, and a
  call the hook cannot read adds nothing and costs nothing else.
- A shell command is read line by line, a backslash at a line's end
  joining it to the next, a line break inside quotes, such as a commit
  message's, kept inside its line, and the body of a heredoc opened
  outside quotes dropped, since the shell runs each line as its own
  command and a heredoc's body is text, not shell. A line longer than
  LONGEST is passed over, so the nudge never costs the tick its moment.
- In PowerShell and cmd a backslash is the separator every path is
  spelled with, so there it escapes nothing, joins no lines and stays in
  the word it stands in. A call's shell is the one its command list
  names, else Claude Code's Bash tool, Git Bash on Windows, which keeps
  the POSIX reading, or a PowerShell tool, else the system's own,
  Codex's shell call among them, which Codex names Bash everywhere.
- A line splits into parts at the shell's separators, and a `cd` part
  moves the folder the later parts count from, on its line and after.
- A part's program is its first word past `sudo`, `env`, `command`,
  `exec`, `xargs`, the shell's own words and any assignment. A word is
  a path unless it is an option or its value, a number, a word with a
  space in it, a variable, or the pattern or script a reader or an edit
  in place takes first. A part fed by `xargs`, or whose path is a
  variable such as `$f` or find's `{}`, works on the paths the loops,
  the listings and the `grep -l` of the same command name, since a loop
  names the files in one part and works on each in another.
- A read is a field grep, a listing or a print. A field grep is grep,
  egrep, fgrep, rg, awk, or sed without -i, whose pattern names a
  header field the way the field opens its line, `^status`, any choice
  of a group opened there such as `^(title|status)`, or `status:`, and
  never as one word of an either-or search with no `^` in front, over
  paths that reach the brain,
  its folder or a tracker's, or over the folder it stands in when it
  searches that. A listing is ls, find, tree or wc over a tracker
  folder or a pattern of its files, or find or tree over the brain's
  folder. A print is cat, head or tail over a pattern of a tracker's
  files or over two entries or more. The search and list tools read the
  same way.
- A write is a redirect onto, or tee, mv, rm, touch, mkdir, sed -i,
  perl -i, git mv or git rm on, a path in a tracker folder, one of the
  brain's own files or the brain's folder itself, a cp whose last path
  is one, or find over one with -delete or with -exec running a writer.
- Words are placed as text, joined to the folder and normalized, and
  only the call's folder and the brain's are followed through their
  links, so no word of a command touches the disk.
"""

import fnmatch
import os
import re
import shlex
from dataclasses import dataclass, field
from typing import Iterator, Optional

from . import autoack, conclude, guard, schema, store, task

CALL = "python3 .agents/brain"
READ = f"The brain answers that itself, {CALL} list <kind> --open for what is still open, --status <status> for one status, status for its counts and show <key> for one entry, where a grep of its fields or a listing of its folders only guesses."
WRITE = f"That call wrote into the brain by hand, which the brain tool does through new, set, refile, steps, task, ledger, handover and index, so run {CALL} doctor to see what it left."
START = f"Read the brain through the tool too, {CALL} list <kind> --open, status or show <key>, never by a grep of its fields or a listing of its folders."

# The header fields an entry's state lives in, the ones a grep for the
# open entries reaches for, and not the words prose and code use too,
# such as name, type or description.
STATE_FIELDS = ("status", "severity", "area", "branch", "born", "done", "reported", "became", "parent", "superseded-by", "author", "editor")
NAMES = "|".join(re.escape(name) for name in STATE_FIELDS)
# A state field at the start of a line, alone or as any choice of a group
# opened there, or a state field and its colon anywhere.
FIELD = re.compile(rf"\^\s*(?:{NAMES})\b|\^\((?:[^()|]*\|)*\s*(?:{NAMES})\b|(?<![\w-])(?:{NAMES})\s*:")

# The brain's own files beside the tracker folders, which the tool alone writes.
OWN_FILES = (schema.INDEX, autoack.FILE, guard.FILE, task.FILE, conclude.FILE, schema.HANDOVER_FOLDER)
TRACKERS = schema.INDEXED_FOLDERS

LONGEST = 10_000

READERS = {"grep", "egrep", "fgrep", "rg", "awk", "sed"}
LISTERS = {"ls", "find", "tree", "wc"}
PRINTERS = {"cat", "head", "tail"}
WRITERS = {"tee", "mv", "rm", "touch", "mkdir"}
PRODUCERS = {"for", "ls", "find"}
WRAPPERS = {"sudo", "env", "command", "exec", "xargs", "do", "then", "else", "elif", "if", "while", "until", "time", "!", "{", "}"}
EXECS = {"-exec", "-execdir", "-ok", "-okdir"}
GIT_VALUED = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
SED_IN_PLACE = re.compile(r"^(?:-[nrEsuz]*i|--in-place)")
PERL_IN_PLACE = re.compile(r"^-[lnpaesw0-9]*i")
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
HEREDOC = re.compile(r"(?<!<)<<(?P<dash>-?)\s*(?P<quote>['\"]?)(?P<word>[A-Za-z_][A-Za-z0-9_]*)(?P=quote)")
PUNCTUATION = set("();<>|&")
GLOB = set("*?[{")
# the shells a command list may name, those that read a backslash as an escape and those that spell a path with one
POSIX_SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
WINDOWS_SHELLS = {"powershell", "pwsh", "cmd"}

# The options that take the word after them as their value, by program,
# so that word is never read as a path or a pattern.
GREP_VALUED = {"-e", "-f", "--regexp", "--file", "-m", "--max-count", "-A", "-B", "-C", "--after-context", "--before-context", "--context"}
VALUED = {
    "grep": GREP_VALUED,
    "egrep": GREP_VALUED,
    "fgrep": GREP_VALUED,
    "rg": GREP_VALUED | {"-g", "--glob", "--iglob", "-t", "--type", "-T", "--type-not", "-j", "--threads", "-M", "--max-columns", "--max-depth"},
    "awk": {"-F", "-f", "-v"},
    "sed": {"-e", "-f", "--expression", "--file"},
    "perl": {"-e", "-E"},
    "tree": {"-I", "-P"},
    "ls": {"-I", "--ignore"},
    "xargs": {"-I", "-d", "-E", "-a", "-s", "-n", "-P", "-L"},
}
GIVEN_PATTERN = {"-e", "-f", "--regexp", "--file", "--expression", "-E"}

SEARCHES = {"Grep", "grep_search", "search_file_content"}
GLOBS = {"Glob", "glob"}
LISTINGS = {"list_directory"}
BULK_READS = {"read_many_files"}

ROOT = "root"
ENTRIES = "entries"


@dataclass
class Part:
    """One command of a line, its program, its words past the program, where its output goes, whether xargs feeds it, and the folder it runs in."""

    program: str
    words: list[str]
    targets: list[str] = field(default_factory=list)
    fed: bool = False
    base: str = ""


def lines(
    brain: store.Brain,
    event: dict,
    agent: str = "claude",
) -> list[str]:
    """The lines a tick adds for the calls its event carries, each once, the read's before the write's, or none."""
    root = os.path.realpath(str(brain.root))
    base = os.path.realpath(str(event.get("cwd") or os.getcwd()))
    read = wrote = False

    for name, tool_input in calls_of(event):
        did_read, did_write = judged(name=name, tool_input=tool_input, base=base, root=root, agent=agent)
        read, wrote = read or did_read, wrote or did_write

    return [line for done, line in ((read, READ), (wrote, WRITE)) if done]


def calls_of(
    event: dict,
) -> Iterator[tuple[str, dict]]:
    """Each call the event carries as its tool's name and input, Claude Code's batch of them or the one call Codex and Gemini CLI hand over, and nothing of a shape the hook cannot read."""
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
    agent: str = "claude",
) -> tuple[bool, bool]:
    """Whether one call read the brain's fields, listed its folders or printed several entries, and whether it wrote into the brain."""
    if "command" in tool_input:
        command = shell_text(tool_input["command"])
        if command is None:
            return False, False

        return shell(command=command, base=placed(word=str(tool_input.get("dir_path") or ""), base=base), root=root, escapes=escapes_of(name=name, command=tool_input["command"], agent=agent))

    if name in SEARCHES:
        where_from = placed(word=str(tool_input.get("path") or tool_input.get("dir_path") or ""), base=base)
        narrowed = tool_input.get("glob") or tool_input.get("include_pattern")
        spots = [where_from] + ([placed(word=str(narrowed), base=where_from)] if narrowed else [])
        return bool(FIELD.search(str(tool_input.get("pattern") or ""))) and any(reaches(path=spot, root=root) for spot in spots), False

    if name in GLOBS:
        pattern = str(tool_input.get("pattern") or "")
        where_from = placed(word=str(tool_input.get("path") or tool_input.get("dir_path") or ""), base=base)
        return bool(GLOB & set(pattern)) and in_tracker(path=placed(word=pattern, base=where_from), root=root), False

    if name in LISTINGS:
        return in_tracker(path=placed(word=str(tool_input.get("dir_path") or ""), base=base), root=root), False

    if name in BULK_READS:
        included = tool_input.get("include") or []
        items = [str(item) for item in ([included] if isinstance(included, str) else included if isinstance(included, list) else [])]
        return several(words=items, base=base, root=root), False

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


def escapes_of(
    name: str,
    command: object,
    agent: str = "claude",
) -> str:
    """The character that escapes the next one in the shell a call runs, a backslash in a POSIX shell, Git Bash on Windows among them, and none in PowerShell or cmd, which spell a path with it.

    A command list names its shell and Claude Code's Bash and PowerShell
    tools name theirs, and any other call runs in the system's own, Codex's
    shell call among them, which it names Bash on every system.
    """
    if isinstance(command, list) and command:
        program: str = re.split(r"[\\/]", str(command[0]))[-1].casefold()
        program = program[: -len(".exe")] if program.endswith(".exe") else program
        if program in POSIX_SHELLS:
            return "\\"
        if program in WINDOWS_SHELLS:
            return ""

    if name == "Bash" and agent == "claude":
        return "\\"
    if name == "PowerShell":
        return ""

    return "" if os.name == "nt" else "\\"


def shell(
    command: str,
    base: str,
    root: str,
    escapes: str = "\\",
) -> tuple[bool, bool]:
    """Whether a command greps the brain's fields, lists a tracker folder or prints several entries, and whether it writes into the brain."""
    parts = list(parts_of(command=command, base=base, escapes=escapes))
    produced = [path for part in parts if part.program in PRODUCERS or names_files(part) for path in produced_by(part)]
    read = wrote = False

    for part in parts:
        did_read, did_write = part_judged(part=part, produced=produced, root=root)
        read, wrote = read or did_read, wrote or did_write

    return read, wrote


def parts_of(
    command: str,
    base: str,
    escapes: str = "\\",
) -> Iterator[Part]:
    """The parts of a command in the order the shell runs them, each line split at its separators, a `cd` moving the folder of the parts after it."""
    for line in shell_lines(command, escapes=escapes):
        if len(line) > LONGEST:
            continue

        try:
            tokens = shlex_tokens(line, escapes=escapes)
        except ValueError:
            continue

        for words in segments(tokens):
            part = part_of(words=words, base=base)
            if part is None:
                continue

            if part.program == "cd":
                base = placed(word=part.words[0], base=base) if part.words else base
                continue

            yield part


def shell_lines(
    command: str,
    escapes: str = "\\",
) -> list[str]:
    """The command's lines as the shell runs them, a backslash before a line break joining two lines where it escapes, a line break inside quotes kept inside its line, and the body of each heredoc opened outside quotes left out."""
    kept: list[str] = []
    pending: list[str] = []
    bodies: list[tuple[str, bool]] = []
    quote: Optional[str] = None

    for line in (command.replace("\\\n", " ") if escapes else command).split("\n"):
        if bodies:
            delimiter, tabs = bodies[0]
            if (line.lstrip("\t") if tabs else line) == delimiter:
                bodies.pop(0)
            continue

        pending.append(line)
        quote, opened = scanned(line=line, quote=quote, escapes=escapes)
        bodies += opened
        if quote is None:
            kept.append("\n".join(pending))
            pending = []

    return kept + (["\n".join(pending)] if pending else [])


def scanned(
    line: str,
    quote: Optional[str],
    escapes: str = "\\",
) -> tuple[Optional[str], list[tuple[str, bool]]]:
    """The quote a line leaves open, starting inside `quote`, and the heredocs it opens outside quotes, each as its closing word and whether tabs may come before it."""
    opened: list[tuple[str, bool]] = []
    at = 0
    while at < len(line):
        character = line[at]
        if quote == "'":
            quote = None if character == "'" else quote
        elif quote == '"':
            if character in escapes:
                at += 1
            elif character == '"':
                quote = None
        elif character in escapes:
            at += 1
        elif character in ("'", '"'):
            quote = character
        elif character == "#" and (at == 0 or line[at - 1].isspace()):
            break
        elif line.startswith("<<", at):
            heredoc = HEREDOC.match(line, at)
            if heredoc is not None:
                opened.append((heredoc.group("word"), heredoc.group("dash") == "-"))
                at = heredoc.end()
                continue

        at += 1

    return quote, opened


def shlex_tokens(
    line: str,
    escapes: str = "\\",
) -> list[str]:
    lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.escape = escapes

    return list(lexer)


def segments(
    tokens: list[str],
) -> Iterator[list[str]]:
    """The tokens between the shell's separators, a redirect's arrows kept with the part they belong to."""
    current: list[str] = []
    for token in tokens:
        if is_punctuation(token) and ">" not in token and "<" not in token:
            if current:
                yield current
            current = []
            continue

        current.append(token)

    if current:
        yield current


def is_punctuation(
    token: str,
) -> bool:
    return bool(token) and set(token) <= PUNCTUATION


def part_of(
    words: list[str],
    base: str,
) -> Optional[Part]:
    """The part a run of words makes, its program found past the wrappers, the options xargs takes and any assignment, its redirects taken out, or None when it runs nothing."""
    fed = False
    at = 0
    while at < len(words):
        word = words[at]
        if word == "xargs":
            fed = True

        if fed and word in VALUED["xargs"]:
            at += 2
            continue

        if word in WRAPPERS or ASSIGNMENT.match(word) or (fed and word.startswith("-")):
            at += 1
            continue

        targets, rest = redirected(words[at + 1 :])
        return Part(program=os.path.basename(word), words=rest, targets=targets, fed=fed, base=base)

    return None


def redirected(
    words: list[str],
) -> tuple[list[str], list[str]]:
    """The files a part's output goes to by `>`, `>>` or `&>`, and its words without the arrows, what they point at and the descriptor numbers before them."""
    targets: list[str] = []
    rest: list[str] = []
    skip = False
    for at, word in enumerate(words):
        if skip:
            skip = False
            continue

        following = words[at + 1] if at + 1 < len(words) else ""
        if word.isdigit() and is_punctuation(following):
            continue

        if is_punctuation(word):
            duplicated = "&" in word and (following.isdigit() or following == "-")
            if ">" in word and following and not duplicated:
                targets.append(following)
            skip = bool(following)
            continue

        rest.append(word)

    return targets, rest


def part_judged(
    part: Part,
    produced: list[str],
    root: str,
) -> tuple[bool, bool]:
    """Whether one part reads the brain by hand, and whether it writes into it."""
    wrote = any(where(path=placed(word=target, base=part.base), root=root) == ENTRIES for target in part.targets)
    program, words, base = part.program, part.words, part.base

    if program == "git":
        sub, base, words = git_subcommand(words=words, base=base)
        if sub not in ("mv", "rm"):
            return False, wrote
        program = sub

    if program == "find":
        return find_judged(part=part, root=root, wrote=wrote)

    in_place = (program == "sed" and any(SED_IN_PLACE.match(word) for word in words)) or (program == "perl" and any(PERL_IN_PLACE.match(word) for word in words))
    operands = operands_of(program=program, words=words, in_place=in_place)
    paths = [placed(word=word, base=base) for word in operands]
    indirect = part.fed or any(word.startswith("$") or word == "{}" for word in words)
    reach = paths + (produced if indirect else [])

    if program in WRITERS or in_place:
        return False, wrote or any(where(path=path, root=root) is not None for path in reach)

    if program == "cp":
        return False, wrote or bool(paths) and where(path=paths[-1], root=root) is not None

    if program in READERS:
        searched = reach or ([base] if recursive(program=program, words=words) else [])
        return bool(FIELD.search(pattern_of(program=program, words=words))) and any(reaches(path=path, root=root) for path in searched), wrote

    if program in LISTERS:
        folders = [path for word, path in zip(operands, paths) if folder_like(word)] or ([base] if program != "wc" and not operands else [])
        return any(in_tracker(path=path, root=root) or (program == "tree" and path == root) for path in folders), wrote

    if program in PRINTERS:
        patterned = indirect and any(GLOB & set(path) and in_tracker(path=path, root=root) for path in produced)
        return several(words=operands, base=base, root=root) or patterned, wrote

    return False, wrote


def find_judged(
    part: Part,
    root: str,
    wrote: bool,
) -> tuple[bool, bool]:
    """A find lists the folders it starts from, unless it deletes there or runs a writer on what it finds, which makes it a write, and a reader or a printer it runs judges what it finds as its own."""
    starts = find_starts(part)

    if "-delete" in part.words and any(where(path=path, root=root) is not None for path in starts):
        return False, True

    listed = any(in_tracker(path=path, root=root) or path == root for path in starts)
    for at, word in enumerate(part.words):
        if word in EXECS and at + 1 < len(part.words):
            inner = Part(program=os.path.basename(part.words[at + 1]), words=part.words[at + 2 :], fed=True, base=part.base)
            did_read, did_write = part_judged(part=inner, produced=starts, root=root)
            return (False, True) if did_write else (listed or did_read, wrote)

    return listed, wrote


def find_starts(
    part: Part,
) -> list[str]:
    """The folders a find starts from, its words before the first test, or the folder it stands in."""
    starts: list[str] = []
    for word in part.words:
        if word.startswith("-") or word in ("(", "!"):
            break
        starts.append(placed(word=word, base=part.base))

    return starts or [part.base]


def git_subcommand(
    words: list[str],
    base: str,
) -> tuple[str, str, list[str]]:
    """Git's subcommand past its own options, the folder its paths count from, which `-C` moves, and the words after it."""
    at = 0
    while at < len(words):
        word = words[at]
        if word in GIT_VALUED and at + 1 < len(words):
            if word == "-C":
                base = placed(word=words[at + 1], base=base)
            at += 2
            continue

        if word.startswith("-"):
            at += 1
            continue

        return word, base, words[at + 1 :]

    return "", base, []


def operands_of(
    program: str,
    words: list[str],
    in_place: bool,
) -> list[str]:
    """The words of a part that are paths, past its options and their values, its numbers, its words with a space, its variables and the pattern or script a reader or an edit in place takes first."""
    valued = VALUED.get(program, set())
    takes_pattern = program in READERS or in_place
    given = any(word in GIVEN_PATTERN and word in valued for word in words)
    found: list[str] = []
    skip = False

    for word in words:
        if skip:
            skip = False
            continue

        if word in valued:
            skip = True
            continue

        if not word or word.startswith("-"):
            continue

        # the pattern or the script goes first, whatever it holds, a space or a variable among them
        if takes_pattern and not given:
            given = True
            continue

        if word.startswith("$") or word == "{}" or word.isdigit() or any(character.isspace() for character in word):
            continue

        found.append(word)

    return found


def pattern_of(
    program: str,
    words: list[str],
) -> str:
    """The pattern a reader searches for, the value of its -e or else its first word that is no option."""
    valued = VALUED.get(program, set())
    skip = False
    for at, word in enumerate(words):
        if word in ("-e", "--regexp", "--expression") and at + 1 < len(words):
            return words[at + 1]

        if skip:
            skip = False
            continue

        if word in valued:
            skip = True
            continue

        if not word.startswith("-"):
            return word

    return ""


def recursive(
    program: str,
    words: list[str],
) -> bool:
    """Whether a reader with no path searches the folder it stands in, as rg always does and grep does with -r."""
    if program == "rg":
        return True

    return program in ("grep", "egrep", "fgrep") and any(word == "--recursive" or (word.startswith("-") and not word.startswith("--") and ("r" in word or "R" in word)) for word in words)


def folder_like(
    word: str,
) -> bool:
    """Whether a word names a folder or a pattern of files, and not one named file, a folder named with a dot in front, `.agents`, among the folders."""
    last = os.path.basename(word.rstrip("/"))

    return bool(GLOB & set(word)) or last in ("", ".", "..") or "." not in last.lstrip(".")


def several(
    words: list[str],
    base: str,
    root: str,
) -> bool:
    """Whether the words name a pattern of a tracker's files, or two entries or more."""
    paths = [(word, placed(word=word, base=base)) for word in words]
    hits = [path for _, path in paths if in_tracker(path=path, root=root)]

    return any(GLOB & set(word) and in_tracker(path=path, root=root) for word, path in paths) or len(hits) > 1


def produced_by(
    part: Part,
) -> list[str]:
    """The paths a loop or a listing hands on to the parts after it, a loop's words past `in`, a find's folders and a listing's operands."""
    if part.program == "find":
        return find_starts(part)

    if part.program == "for":
        words = part.words[part.words.index("in") + 1 :] if "in" in part.words else []
    else:
        words = operands_of(program=part.program, words=part.words, in_place=False)

    paths = [placed(word=word, base=part.base) for word in words if word and not word.startswith(("-", "$"))]

    return paths or ([part.base] if names_files(part) and recursive(program=part.program, words=part.words) else [])


def names_files(
    part: Part,
) -> bool:
    """Whether a reader prints the names of the files it searched rather than their lines, as grep -l and rg -l do, which makes it a source of paths for the parts after it."""
    return part.program in READERS and any(word in ("--files-with-matches", "--files-without-match") or (word.startswith("-") and not word.startswith("--") and ("l" in word or "L" in word)) for word in part.words)


def placed(
    word: str,
    base: str,
) -> str:
    """The path a word names, joined to `base` when it is relative and normalized as text, a home folder at its front spelled out."""
    if word == "~" or word.startswith("~/"):
        word = os.path.expanduser(word)

    return os.path.normpath(os.path.join(base, word))


def where(
    path: str,
    root: str,
) -> Optional[str]:
    """ROOT for the brain's folder itself, ENTRIES for a path in a tracker folder or one of the brain's own files, a pattern that reaches one among them, and None for anywhere else, the kit's own files in the brain's folder among them."""
    if path == root:
        return ROOT

    first = first_under(path=path, root=root)
    if first is None:
        return None

    return ENTRIES if matches(component=first, names=TRACKERS + OWN_FILES) else None


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
    """Whether the path is a tracker folder, inside one, or a pattern that reaches one."""
    first = first_under(path=path, root=root)

    return first is not None and matches(component=first, names=TRACKERS)


def first_under(
    path: str,
    root: str,
) -> Optional[str]:
    """The first folder or file name of a path inside the brain's folder, or None for a path outside it."""
    if not path.startswith(root + os.sep):
        return None

    return path[len(root) + 1 :].split(os.sep)[0]


def matches(
    component: str,
    names: tuple[str, ...],
) -> bool:
    """Whether a name, or a pattern of them such as `*` or `{bugs,todos}`, names one of the given names."""
    if component in names:
        return True

    if component.startswith("{") and component.endswith("}"):
        return any(choice in names for choice in component[1:-1].split(","))

    return bool(GLOB & set(component)) and any(fnmatch.fnmatchcase(name, component) for name in names)
