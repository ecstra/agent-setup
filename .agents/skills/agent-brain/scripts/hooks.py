"""The hook every agent runs, so the brain is checked without anyone asking.

Claude Code, Codex and Gemini CLI each call this with their own event
JSON on standard input and the event name as the first argument. Five
events matter, the start of a session, each prompt the owner sends, a
tick after the agent's tool calls, a write, an edit or a patch about to
land anywhere in the project, refused where it does by hand what the
brain tool does, or, outside the kit's own checkout, writes the
project's AGENTS.md or the kit's Rust rule, makes a file among the
kit's own tests or loses an assertion a test file holds, and a write
that just landed anywhere in the project, after which the project's
linters and the check read the file written, and doctor reads the
whole brain where it landed inside .agents/, on a front
door or the root Cargo.toml, or where a patch deleted or moved a file. The session start,
the prompt and the tick carry the clock, since a model does not know
the time and forgets what it was told, where the owner's standing word
to proceed stands, on, held or off, and the work the agent is on, the
chain from the plan down to the step.

    python3 .agents/skills/agent-brain/scripts/hooks.py session-start --agent claude
    python3 .agents/skills/agent-brain/scripts/hooks.py prompt --agent claude
    python3 .agents/skills/agent-brain/scripts/hooks.py tick --agent claude
    python3 .agents/skills/agent-brain/scripts/hooks.py pre-write --agent codex
    python3 .agents/skills/agent-brain/scripts/hooks.py post-write --agent gemini

Exit 2 blocks the write, with the reason on standard error, which all
three agents honour.
"""

import argparse
import contextlib
import errno
import json
import os
import re
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import BinaryIO, NoReturn, Optional, TextIO, Union

from brainlib import autoack, check, clock, conclude, doctor, frontmatter, guard, handover, links, lint, nudge, reads, rust, schema, steps, store, task
from brainlib import rules as project_rules

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
    deleted: bool = False


class HookParser(argparse.ArgumentParser):
    """An argument parser whose refusal is the non blocking error, never the blocking exit.

    argparse exits 2 on an argument it does not know, and 2 is the exit
    every agent takes as a block, so a hook script older than the event
    its config names, one a checkout of an older branch put in place,
    would erase every prompt until the session restarts.
    """

    def error(
        self,
        message: str,
    ) -> NoReturn:
        say(line=f"the brain hook could not run: {message}")
        raise SystemExit(FAILED)


def main(
    argv: Optional[list[str]] = None,
) -> int:
    parser = HookParser(prog="hooks")
    parser.add_argument("event", choices=("session-start", "prompt", "tick", "pre-write", "post-write"))
    parser.add_argument("--agent", choices=("claude", "codex", "gemini"), default="claude")
    parser.add_argument("--with-rules", action="store_true", help="add SYSTEM.md to the context")
    args = parser.parse_args(argv)

    try:
        return run(args)
    except (store.StoreError, frontmatter.FrontmatterError, OSError, ValueError) as error:
        say(line=f"the brain hook could not run: {store.explain(error)}")
        return FAILED


def run(
    args: argparse.Namespace,
) -> int:
    """Dispatch one event. A brain the hook cannot read fails visibly, not silently.

    Exit 1 is the non blocking error every agent shows to the person,
    which is the right outcome for a broken brain: the write goes ahead
    and the reason is on screen, rather than every write being refused
    until someone finds a traceback. After a write the hook answers with
    exit 0 all the same, doctor's error in words in its context beside
    the check's slips, since an exit 1 would lose the slips.
    """
    event = read_event()
    brain = locate(event)
    if brain is None:
        return 0

    if args.event == "session-start":
        return session_start(
            brain=brain,
            agent=args.agent,
            with_rules=args.with_rules,
            source=str(event.get("source") or ""),
        )

    if args.event == "prompt":
        return prompt(brain=brain, agent=args.agent)

    if args.event == "tick":
        return tick(brain=brain, event=event, agent=args.agent)

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

    raw = stdin_bytes().decode("utf-8", errors="replace")
    if not raw.strip():
        return {}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    # an event is a JSON object, so an array, a string, a number or null is none
    return parsed if isinstance(parsed, dict) else {}


def cwd_of(
    event: dict,
) -> Path:
    """The folder the event names, or this process's own where it names none as text."""
    named = event.get("cwd")

    return Path(named) if isinstance(named, str) and named else Path.cwd()


def stdin_bytes() -> bytes:
    """Standard input as bytes, read under the text layer so the locale's encoding never gets a say.

    The event is JSON, which is UTF-8 whatever the locale, and on a
    prompt it carries the owner's own text. A byte layer that is not
    there, a text stream handed in by a test, is read as the text it
    holds.
    """
    buffer: Optional[BinaryIO] = getattr(sys.stdin, "buffer", None)
    if buffer is None:
        return sys.stdin.read().encode("utf-8")

    return buffer.read()


def locate(
    event: dict,
) -> Optional[store.Brain]:
    start = cwd_of(event)

    try:
        return store.find_brain(start)
    except store.StoreError:
        return None


# The one session start that leaves the last session's note where it is,
# since a fork carries the whole context it was forked from and the
# session that wrote the note still holds everything in it.
FORK = "fork"

# Claude Code shows up to this many characters of a hook's added context,
# and past it keeps the whole text in a file of the session's and shows
# its path with the first 2,000 characters without asking the model to
# read it, so a longer context asks for that itself, in its first line.
# It counts them as JavaScript counts a string, in UTF-16 units, where a
# character past the Basic Multilingual Plane, an emoji among them, is
# two, and a lone surrogate, which a file name that is not UTF-8 brings
# in, is one.
CLAUDE_SHOWS = 10_000
PAST_WHAT_CLAUDE_SHOWS = f"This context is longer than the {CLAUDE_SHOWS:,} characters Claude Code shows from a hook, so Claude Code keeps it whole in the file it names here. Read that file whole before you go on."


def session_start(
    brain: store.Brain,
    agent: str,
    with_rules: bool,
    source: str,
) -> int:
    """The clock, the word and the work, the note the last session left, read once, then the status and the rules where asked.

    The note goes in whole on a start, a resume, a clear and a compaction
    alike, since each is a session that has to pick up without the last
    one's head, and never on a fork. It is claimed before the status is
    counted, so the status says a note waits that the same context
    carries only where the next session reads it too, a note read in
    place since it could not be taken aside. It comes right after the
    clock, the word and the work, ahead of the status and the rules, so
    it sits at the head of whatever an agent shows of a long context. A
    context longer than Claude Code shows opens with a line that asks
    for the file Claude Code keeps it in to be read whole. The claimed
    file is removed only once the context is out, so a context that
    fails to go out leaves the file for the next start, which reads it
    again. A note for another branch, a file the tool never wrote and
    one it cannot open stay, each said in one line in the note's place.
    """
    # the note's lock is held from the first look to the removal, so a second start waits and finds none, and a fork takes no note and no lock
    with handover.taken(brain=brain) if source != FORK else contextlib.nullcontext(enter_result=None) as claim:
        text = the_moment(brain=brain) + handover_text(claim=claim)
        text += "\n\nThe brain, counted from the files right now:\n" + reads.render_status(data=reads.status(brain=brain)) + "\n" + nudge.START
        if with_rules:
            rulebook = brain.root / "SYSTEM.md"
            if store.readable_file(rulebook):
                text += "\n\nThe rules this project works by, from .agents/SYSTEM.md:\n\n" + text_of(rulebook)

            # Codex reads no imports, so the project's own rules, which AGENTS.md imports for the other agents, come in here
            for name in project_rules.names(brain.root):
                rule = brain.root / project_rules.FOLDER / name
                if store.readable_file(rule):
                    text += f"\n\nA rule of this project's own, from .agents/{project_rules.FOLDER}/{name}:\n\n" + text_of(rule)

            chat_style = brain.root.parent / f".{agent}" / "plain-and-short.md"
            if store.readable_file(chat_style):
                text += f"\n\nHow to talk in this project, from .{agent}/plain-and-short.md:\n\n" + text_of(chat_style)

        emit_context(agent=agent, text=text, event_name="SessionStart")

        # the context has gone out by now, so a file that stays can only be said on standard error
        if claim is not None and claim.taken:
            trouble: Optional[str] = handover.release(claim=claim)
            if trouble is not None:
                say(line=f"the brain hook put the handover in this session's context and could not remove its file, {trouble}")

    return 0


def handover_text(
    claim: Optional[handover.Claim],
) -> str:
    """The claimed note under the words for how it was taken, the one line that says why the file at its path stays, or nothing."""
    if claim is None:
        return ""

    if claim.note is None:
        return f"\n\n{claim.waiting}"

    if not claim.taken:
        heading = f"The handover the last session left here, read where it is, since it could not be taken aside, {claim.trouble}, and the next session reads it again."
    elif claim.again:
        heading = "The handover the last session left here, read before by a session that could not remove it, read again, its file to be removed when this context is out."
    else:
        heading = "The handover the last session left here, read once, its file to be removed when this context is out."

    return f"\n\n{heading}\n\n{claim.note.text.rstrip()}"


def prompt(
    brain: store.Brain,
    agent: str,
) -> int:
    """On each prompt the owner sends, the clock, the standing word and the current work, so all three are in front of the model when it reads the prompt."""
    emit_context(agent=agent, text=the_moment(brain=brain), event_name=PROMPT.get(agent, "UserPromptSubmit"))
    return 0


def tick(
    brain: store.Brain,
    event: dict,
    agent: str,
) -> int:
    """After the agent's tool calls, the clock, the standing word and the current work again, off and none included, so a long stretch of work never loses any of them and sees the word end, then a line naming the brain command for any of the calls that did by hand what the tool does."""
    text = "\n".join([the_moment(brain=brain)] + nudge.lines(brain=brain, event=event, agent=agent))
    emit_context(agent=agent, text=text, event_name=TICK.get(agent, "PostToolUse"))
    return 0


def the_moment(
    brain: store.Brain,
) -> str:
    """The clock, the standing word, the conclude word while one stands, and the current work, the lines the session start, the prompt hook and the tick carry.

    The owner's words for test files whose task has ended are taken back
    here too, as the standing word is in its own line, so neither comes
    back when the task reopens.
    """
    guard.sweep(brain)
    lines = [clock.line(), autoack.describe(brain=brain), conclude.describe(brain=brain), task.describe(brain=brain)]
    return "\n".join(line for line in lines if line is not None)


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
    touched = as_the_project_spells(brain=brain, touched=touches(event=event, agent=agent))
    for touch in touched:
        verdict = front_door_refusal(brain=brain, touch=touch) or kit_tests_refusal(brain=brain, touch=touch) or refusal(brain=brain, touch=touch) or assertion_refusal(brain=brain, touch=touch)
        if verdict is None:
            continue

        say(line=verdict)
        return BLOCK

    # a patch that reaches several brain files is judged across them too, since each alone reads as fine against the disk
    if len(touched) > 1:
        verdict = loop_across(brain=brain, writes=table_writes_of(brain=brain, touched=touched))
        if verdict is not None:
            say(line=verdict)
            return BLOCK

    emit_nothing(agent)
    return 0


RUST_BY_HAND = "rules/rust.md is the kit's Rust rule, which doctor writes whole from the tool's template, so nothing in it is edited by hand. The project's own Rust rules go in .agents/rules/project.md or a rule of their own through brain new rule, in addition to the kit's"
AGENTS_BY_HAND = "AGENTS.md is the kit's, written whole by the upgrade, so nothing in it is edited by hand. A project's own instruction is a rule, filed through brain new rule, which AGENTS.md then imports, and it loads once the session is reloaded. brain doctor --fix writes the import lines again, a merge's conflict in them among what it settles"


def front_door_refusal(
    brain: store.Brain,
    touch: Touch,
) -> Optional[str]:
    """Why a write to the project's AGENTS.md or to the kit's Rust rule is refused, or None, the kit's own checkout aside, where the files are the work."""
    project = brain.root.parent
    if touch.deleted or check.is_kit_checkout(project):
        return None

    try:
        folder = touch.path.parent.resolve()
        is_agents = folder == project.resolve() and touch.path.name.casefold() == project_rules.AGENTS.casefold()
        is_rust_rule = folder == (brain.root / project_rules.FOLDER).resolve() and touch.path.name.casefold() == rust.RULE
    except (OSError, RuntimeError):
        return None

    if is_rust_rule:
        return RUST_BY_HAND

    return AGENTS_BY_HAND if is_agents else None


# the folder of the kit's own tests below the brain, which ship nowhere, read in any case since a disk that folds case opens it in any
KIT_TESTS = (SKILLS, "agent-brain", "scripts", "tests")
KIT_TESTS_BY_HAND = "the kit's own tests live only in the kit's checkout, so no file is made in .agents/skills/agent-brain/scripts/tests/ by hand, since one there would mark the project as the kit's checkout and turn off the guards on AGENTS.md, the kit's Rust rule and test assertions"


def kit_tests_refusal(
    brain: store.Brain,
    touch: Touch,
) -> Optional[str]:
    """Why a write that would make a new file in the kit's tests folder is refused, or None, the kit's own checkout aside, where the tests are the work.

    A test file there is what marks the kit's checkout, so outside it a
    file is never made there, while one already there may be written.
    """
    if touch.deleted or check.is_kit_checkout(brain.root.parent):
        return None

    inside = links.within(brain=brain, path=touch.path)
    if inside is None:
        return None

    parts = tuple(part.casefold() for part in Path(inside).parts)
    if len(parts) <= len(KIT_TESTS) or parts[: len(KIT_TESTS)] != KIT_TESTS or os.path.lexists(touch.path):
        return None

    return KIT_TESTS_BY_HAND


def assertion_refusal(
    brain: store.Brain,
    touch: Touch,
) -> Optional[str]:
    """Why a write that loses an assertion a test file holds is refused, or None, the kit's own checkout aside, where its tests are the work, and a file the owner's word holds.

    A file deleted or moved away loses all it held, and so does a file a
    move lands on, which the move writes over. A patch's hunks that fit
    are applied, then each hunk that fits only by looser spacing is
    placed as apply_patch places it, so a check is read whole wherever
    the hunk lands. One that fits nowhere even so is judged by the
    assertions its lines before carry that its lines after do not. An
    edit whose old string the file does not hold word for word is placed
    as the agent's tool places it, and judged by its old and new strings
    alone where it fits nowhere. A new file holds none yet.
    """
    project = brain.root.parent
    if check.is_kit_checkout(project):
        return None

    source = touch.moved_from or touch.path
    read = project_text(project=project, path=source)
    losses: list[tuple[str, list[str]]] = []
    if read is not None:
        relative, before = read
        losses.append((relative, lost_from(touch=touch, relative=relative, before=before)))

    if touch.moved_from is not None:
        landed_on = project_text(project=project, path=touch.path)
        if landed_on is not None:
            losses.append((landed_on[0], guard.lost(relative=landed_on[0], before=landed_on[1], after="")))

    for relative, gone in losses:
        if gone and guard.granted(brain=brain, relative=relative) is None:
            return f"{relative} would lose the assertion `{gone[0]}`, and an assertion already written is the spec's word on what the code must do, so it changes or goes only on the owner's word, which the agent records once the owner gives it with brain ack tests {relative} --for 1h, else keep it and add the new check beside it"

    return None


def project_text(
    project: Path,
    path: Path,
) -> Optional[tuple[str, str]]:
    """The file's path from the project's root and its text, or None where it lies outside the project or cannot be read, a file not there yet among them."""
    try:
        return path.relative_to(project.resolve()).as_posix(), path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    except (OSError, ValueError):
        return None


def lost_from(
    touch: Touch,
    relative: str,
    before: str,
) -> list[str]:
    """The assertions the file at the touch's source loses, its text before given."""
    if touch.deleted or touch.moved_from is not None:
        return guard.lost(relative=relative, before=before, after="")

    after, loose = outcome_of(touch=touch, text=before)
    if loose:
        after, loose = placed_loosely(text=before if after is None else after, hunks=loose)

    gone = [] if after is None else guard.lost(relative=relative, before=before, after=after)
    for hunk in loose:
        old = "\n".join(before_lines(hunk))
        new = "\n".join(line[1:] for line in hunk if line[:1] in (" ", "+"))
        gone += guard.lost(relative=relative, before=old, after=new)

    # Claude Code's Edit takes a straight quote for a curly one and Gemini CLI's replace a line whatever its indent, so an edit the text does not hold word for word may land all the same
    if touch.content is None and touch.old_string is not None and unix(touch.old_string) not in before:
        old, new = unix(touch.old_string), unix(touch.new_string or "")
        placed = loosely_edited(text=before, old=old, new=new, every=touch.replace_all)
        gone += guard.lost(relative=relative, before=old, after=new) if placed is None else guard.lost(relative=relative, before=before, after=placed)

    return gone


# the curled quotes Claude Code's Edit reads as straight ones, each one character for one, so a place in the folded text is the same place in the file
STRAIGHT = str.maketrans({"\N{LEFT SINGLE QUOTATION MARK}": "'", "\N{RIGHT SINGLE QUOTATION MARK}": "'", "\N{LEFT DOUBLE QUOTATION MARK}": '"', "\N{RIGHT DOUBLE QUOTATION MARK}": '"'})


def loosely_edited(
    text: str,
    old: str,
    new: str,
    every: bool,
) -> Optional[str]:
    """The text after an edit whose old string it does not hold word for word, placed as the agent's tool places one, or None where it fits nowhere.

    Claude Code's Edit reads a curled quote as a straight one, so the old
    string is first looked for with the quotes of both folded. Gemini
    CLI's replace matches whole lines whatever their indent, so it is
    then looked for as a run of lines with their spacing taken off.
    """
    folded, wanted = text.translate(STRAIGHT), old.translate(STRAIGHT)
    start = folded.find(wanted) if wanted else -1
    if start != -1:
        pieces: list[str] = []
        last = 0
        while start != -1:
            pieces += [text[last:start], new]
            last = start + len(wanted)
            start = folded.find(wanted, last) if every else -1

        return "".join(pieces) + text[last:]

    lines = text.split("\n")
    block = [line.strip() for line in wanted.split("\n")]
    bare = [line.translate(STRAIGHT).strip() for line in lines]
    found = block_start(lines=bare, block=block)
    if found is None:
        return None

    placed: list[str] = []
    while found is not None:
        placed += lines[:found] + new.split("\n")
        lines, bare = lines[found + len(block) :], bare[found + len(block) :]
        found = block_start(lines=bare, block=block) if every else None

    return "\n".join(placed + lines)


def refusal(
    brain: store.Brain,
    touch: Touch,
) -> Optional[str]:
    """Why this write may not touch the brain by hand, or None if it may.

    A new brain file, an index, a dotted path, the standing word, the
    current work, anything in the handover folder, a rename, the header
    block of an existing file and the rows of its steps table are the
    tool's, a delete of the word, the work or a file in the handover
    folder aside. The prose below a header and around the table is the
    agent's to edit, and doctor reads it afterwards.
    """
    if touch.moved_from is not None:
        source = entry_path(brain=brain, path=touch.moved_from)
        if source is not None:
            return f"{source} is renamed with brain refile, not by hand"

        # a move onto an entry writes over its header and its steps, which only the tool writes
        target = entry_path(brain=brain, path=touch.path)
        if target is not None:
            return f"{target} is a brain file, and a move onto it would write over it by hand"

    path = touch.path
    inside = links.within(brain=brain, path=path)
    if inside is None:
        return None

    # a delete is never refused, the note a session read by hand and a stray index among them, and doctor runs after it
    if touch.deleted:
        return None

    # the word's name in any case, since a disk that ignores case would take
    # .ACK for the file itself, and the suffix as the store reads it
    if inside.casefold() == autoack.FILE:
        return f"{autoack.FILE} is the owner's standing word, set with brain ack on and never written by hand"

    if inside.casefold() == guard.FILE:
        return f"{guard.FILE} is the owner's word to change a test file's assertions, set with brain ack tests and never written by hand"

    if inside.casefold() == task.FILE:
        return f"{task.FILE} is the current work, set with brain task on and never written by hand"

    # the note's folder in any case too, for the same reason as the word's
    # name, where the brain's own folder, which within names ".", has no part
    parts_inside: tuple[str, ...] = Path(inside).parts
    top_folder: str = parts_inside[0] if parts_inside else ""
    if top_folder.casefold() == handover.FOLDER:
        return f"{inside}: {handover.BY_HAND}"

    if not markdown_named(path):
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
        return header_change(touch=touch, inside=inside) or table_change(brain=brain, touch=touch, inside=inside)

    return f"{inside} would be a new brain file written by hand. File it with brain new so it gets its id, its header block and its index line, with the prose on standard input, or rename an existing one with brain refile."


def entry_path(
    brain: store.Brain,
    path: Path,
) -> Optional[str]:
    """The brain relative path of an existing entry file, or None for anything else."""
    inside = links.within(brain=brain, path=path)
    if inside is None or not markdown_named(path) or not store.quietly(path.exists):
        return None

    relative_path = Path(inside)
    if relative_path.parts[0] == SKILLS or store.hidden(relative_path) or schema.is_kit_path(inside):
        return None

    return inside


def markdown_named(
    path: Path,
) -> bool:
    """Whether the path carries the markdown suffix the way the store reads it, `.md` in lower case on every system."""
    return path.suffix == ".md"


HEADER_IS_THE_TOOLS = "the header block changes through brain set or brain refile, not by hand. The prose below it is yours to edit."


def header_change(
    touch: Touch,
    inside: str,
) -> Optional[str]:
    """Why this write to an existing brain file may not go ahead, or None if it may.

    The file is judged as the write would leave it: the whole new text,
    the text after the edit, or the file after the patch's hunks. Its
    header block, every line between the fences except the updated date
    the upkeep rule asks the agent to move, must come out as it went in.
    A file whose header does not read is already broken, so the write is
    taken as the repair and held to one thing, leaving a header that
    reads, then doctor judges the rest. A file the hook cannot open at
    all is not judged. A hunk that fits nowhere is judged by its shape
    either way: refused when it carries a fence or a header field, since
    the hook cannot tell where it would land.
    """
    try:
        text = frontmatter.load(str(touch.path))
    except frontmatter.FrontmatterError:
        return None

    current: Optional[frontmatter.Document] = None
    trouble = ""
    try:
        current = frontmatter.parse(text)
    except frontmatter.FrontmatterError as error:
        trouble = str(error)

    after, loose = outcome_of(touch=touch, text=text)
    names = field_names(inside=inside, lines=current.lines if current is not None else [])
    for hunk in loose:
        line = header_line_in(hunk=hunk, names=names)
        if line is not None:
            return f"{inside}: a hunk the hook cannot place touches the header block with '{line}', and {HEADER_IS_THE_TOOLS}"

    if after is None:
        return None

    try:
        wanted = frontmatter.parse(after)
    except frontmatter.FrontmatterError as error:
        if current is None:
            return still_broken(inside=inside, trouble=trouble, error=str(error))

        return f"{inside}: after that write the header would not read, {error}, and {HEADER_IS_THE_TOOLS}"

    if current is not None and header_lines(wanted) != header_lines(current):
        return f"{inside}: {HEADER_IS_THE_TOOLS}"

    return None


TABLE_IS_THE_TOOLS = "the steps table is the tool's"


def table_change(
    brain: store.Brain,
    touch: Touch,
    inside: str,
) -> Optional[str]:
    """Why this write may not touch the steps table of a plan, a todo or a bug, or None if it may.

    The rows the file holds are the tool's: a mark moves through the
    task or the steps command or follows the entry a step points at, a
    step is never reworded, repointed or deleted, the table is never
    taken away, and a table the write would leave unreadable is refused
    too. A row may follow the last one, held to what add holds a step
    to, pending, pointing at an entry the brain knows or at nothing,
    and on an open entry. A numbered list under Steps, new or written
    to, is the table in waiting, held to what filing holds it to, and a
    file whose table does not read now is doctor's, not the hook's. A
    hunk that fits nowhere and carries a row is refused, since the hook
    cannot tell where it would land.
    """
    write = table_write_of(brain=brain, touch=touch, inside=inside)
    if write is None:
        return None

    if isinstance(write, str):
        return write

    # a list's rows were held to what filing holds them to as they were turned, and only the loops a patch closes across files are left to judge
    if write.listed:
        return None

    why = changed_row(brain=brain, before=write.before, rows=write.rows, key=write.key, status=write.status, closed=write.closed) or added_row(
        brain=brain,
        before=write.before,
        rows=write.rows,
        key=write.key,
        status=write.status,
        closed=write.closed,
        own=write.own,
    )
    if why is None:
        return None

    return f"{inside}: {TABLE_IS_THE_TOOLS}, {why}, and the prose around it is yours to edit"


@dataclass(frozen=True)
class TableWrite:
    """A write to a stepped file as the hook reads it.

    The key is the name a command names the file by, own the keys a
    step would point at it with, its id and its name as the store reads
    them, or the header's name alone when the store holds no entry at
    the path, and node the file's own place in the pointer graph, its
    path folded in case, so two files that carry one id stay two
    nodes. The rows are the ones
    the file holds and the ones the write would leave, which a list
    under Steps gives as the rows the tool would turn it into.
    """

    inside: str
    key: str
    own: set[str]
    node: str
    status: str
    closed: bool
    before: list[steps.Step]
    rows: list[steps.Step]
    listed: bool

    @property
    def added(self) -> list[steps.Step]:
        return self.rows[len(self.before) :]


def table_write_of(
    brain: store.Brain,
    touch: Touch,
    inside: str,
) -> Union[TableWrite, str, None]:
    """The steps table a write reaches, as it is and as the write would leave it, a refusal when the write cannot be judged as a table, or None when there is no table to judge, a file the hook cannot read being taken as its repair the way the header check takes it."""
    try:
        text = frontmatter.load(str(touch.path))
        current = frontmatter.parse(text)
    except frontmatter.FrontmatterError:
        return None

    kind = str(current.get("kind") or "")
    if kind not in steps.STEPPED_KINDS:
        return None

    status = str(current.get("status") or "")
    closed = status not in steps.OPEN_STATUSES[kind]
    entry = entry_at(brain=brain, inside=inside)
    key = entry.name if entry is not None else Path(inside).stem

    # a table that does not read now is doctor's, and a list on disk is the table in waiting, judged whole as the write leaves it
    try:
        before = steps.stored_rows_of(kind=kind, body=current.body)
    except steps.StepsError:
        if steps.has_table(current.body):
            return None

        before = []

    after, loose = outcome_of(touch=touch, text=text)
    for hunk in loose:
        line = row_line_in(hunk)
        if line is not None:
            return f"{inside}: a hunk the hook cannot place touches the steps table with '{line}', and {TABLE_IS_THE_TOOLS}"

        line = step_line_in(hunk)
        if line is not None:
            return f"{inside}: a hunk the hook cannot place carries '{line}', which reads as a step or the Steps heading and could land in the list the tool turns into the table, and {TABLE_IS_THE_TOOLS}"

        # on a closed entry any numbered line could land under Steps as a step the record never had, and a table row would be refused there
        line = numbered_line_in(hunk) if closed else None
        if line is not None:
            return f"{inside}: a hunk the hook cannot place carries '{line}', which reads as a step, and {key} is {status}, a closed table being its record, so no step is added to it"

    if after is None:
        return None

    # the header check ran first on the same outcome and refused a write whose header would not read, so this parse holds
    body = frontmatter.parse(after).body

    own = steps.own_keys(entry) if entry is not None else {str(current.get("name") or key)}
    write = TableWrite(
        inside=inside,
        key=key,
        own=own,
        node=inside.casefold(),
        status=status,
        closed=closed,
        before=before,
        rows=[],
        listed=False,
    )

    if not steps.has_table(body):
        if before:
            return f"{inside}: {TABLE_IS_THE_TOOLS}, its rows are never taken away, and the prose around it is yours to edit"

        # a plan's table stands even empty, and its Steps section with it, since a plan with no table is doctor's finding
        if kind == "plan" and steps.has_table(current.body):
            return f"{inside}: {TABLE_IS_THE_TOOLS}, and a plan's table is never taken away, empty or not, and the prose around it is yours to edit"

        return listed_change(brain=brain, write=write, kind=kind, was=current.body, body=body)

    try:
        rows = steps.stored_rows_of(kind=kind, body=body)
    except steps.StepsError as error:
        return f"{inside}: after that write the steps table would not read, {error}"

    return replace(write, rows=rows)


def listed_change(
    brain: store.Brain,
    write: TableWrite,
    kind: str,
    was: str,
    body: str,
) -> Union[TableWrite, str, None]:
    """A numbered list under Steps, new or written to, as the rows the tool would turn it into, held to what filing holds a list to since the tool would refuse it then, a refusal when it does not pass or the entry is closed, or None when the section is empty or the write leaves it as it was."""
    if steps.blank(body) or steps_text(was) == steps_text(body):
        return None

    if write.closed:
        return f"{write.inside}: {TABLE_IS_THE_TOOLS}, {write.key} is {write.status}, and a closed table is its record, so no step is added to it, and the prose around it is yours to edit"

    try:
        turned = steps.converted(brain=brain, body=body, by="agent", kind=schema.kind_named(kind), own=write.own)
    except steps.StepsError as refused:
        return f"{write.inside}: {TABLE_IS_THE_TOOLS}, {refused}, and the prose around it is yours to edit"

    return replace(write, rows=steps.table(turned), listed=True)


def steps_text(
    body: str,
) -> str:
    """What the Steps section holds, as written, so a write elsewhere in the file leaves a list on disk unjudged."""
    where = steps.span(body)

    return body[where[0] : where[1]].strip() if where is not None else ""


def table_writes_of(
    brain: store.Brain,
    touched: list[Touch],
) -> list[TableWrite]:
    """The steps tables a patch reaches, one per brain file it touches that reads as a table, the refusals having been judged touch by touch already."""
    writes: list[TableWrite] = []
    for touch in touched:
        inside = entry_path(brain=brain, path=touch.path)
        if inside is None:
            continue

        write = table_write_of(brain=brain, touch=touch, inside=inside)
        if isinstance(write, TableWrite):
            writes.append(write)

    return writes


def loop_across(
    brain: store.Brain,
    writes: list[TableWrite],
) -> Optional[str]:
    """Why a row a patch adds may not close a loop, or None when none does.

    Each file alone reads as fine against the disk, since the other
    rows of the patch are not written yet, so the pointers of the brain
    as it stands and the rows the patch adds are walked together, and a
    row whose entry leads back to its own file is refused, whether the
    way back is another row of the patch or one already on disk.
    """
    edges = pointer_graph(brain)
    for write in writes:
        for step in write.added:
            target = resolved(brain=brain, key=step.points_at)
            if target is not None:
                edges.setdefault(write.node, set()).add(target)

    for write in writes:
        for step in write.added:
            target = resolved(brain=brain, key=step.points_at)
            if target is not None and leads_to(edges=edges, start=target, goal=write.node):
                return f"{write.inside}: {TABLE_IS_THE_TOOLS}, step {step.number} points at {step.points_at}, whose steps lead back here once the patch lands, and the entries would wait on each other for good, and the prose around it is yours to edit"

    return None


def pointer_graph(
    brain: store.Brain,
) -> dict[str, set[str]]:
    """Every pointer the open steps tables hold, a list not yet turned into one read by the keys its lines open with, as edges from the holder's file to the file pointed at, a closed entry's steps waiting on nothing.

    A file is its own node, the path folded in case, so two files that
    carry one id after a merge stay two nodes rather than one.
    """
    edges: dict[str, set[str]] = {}
    for kind_name in steps.STEPPED_KINDS:
        for entry in brain.entries_of(schema.kind_named(kind_name)):
            if not steps.is_open(entry):
                continue

            try:
                keys = steps.pointers_in(entry.document.body)
            except steps.StepsError:
                continue

            for key in keys:
                target = resolved(brain=brain, key=key)
                if target is not None:
                    edges.setdefault(entry.relative.casefold(), set()).add(target)

    return edges


def resolved(
    brain: store.Brain,
    key: str,
) -> Optional[str]:
    """The node of the entry a row's pointer reaches, its path folded in case, or None when it reaches nothing."""
    if not key:
        return None

    target = steps.pointed(brain=brain, key=key)

    return target.relative.casefold() if target is not None else None


def leads_to(
    edges: dict[str, set[str]],
    start: str,
    goal: str,
) -> bool:
    """Whether the pointers lead from one entry to another, at any remove."""
    seen: set[str] = set()
    ahead = [start]
    while ahead:
        node = ahead.pop()
        if node == goal:
            return True

        if node in seen:
            continue

        seen.add(node)
        ahead.extend(edges.get(node, ()))

    return False


def changed_row(
    brain: store.Brain,
    before: list[steps.Step],
    rows: list[steps.Step],
    key: str,
    status: str,
    closed: bool,
) -> Optional[str]:
    """Why the first row that no longer reads as filed may not change that way, or None when every row the file had stands.

    A closed table is its record before anything else, a step whose
    pointer reaches an entry takes its mark from there, and one whose
    pointer reaches nothing is marked by hand like a plain one.
    """
    for step in before:
        fresh = rows[step.number - 1] if step.number <= len(rows) else None
        if fresh is None:
            return f"step {step.number} is never deleted, a step that turned out wrong is skipped"

        if fresh.status != step.status:
            if closed:
                return f"{key} is {status}, and a closed table is its record"

            if step.points_at and steps.pointed(brain=brain, key=step.points_at) is not None:
                return f"step {step.number} points at {step.points_at} and takes its mark from that entry"

            return f"step {step.number} is marked {fresh.status} with {marking_command(key=key, number=step.number, status=fresh.status)}"

        # a cell left empty by a write from before the tool refused one is filled in by hand, since no command rewords a step, and held to what a new row's text is held to
        if fresh.text != step.text:
            if step.text.strip():
                return f"step {step.number} is worded as it was filed"

            why = opens_with_a_key(brain=brain, step=fresh) if not fresh.points_at else None
            if why is not None:
                return why

        if fresh.points_at != step.points_at:
            return f"step {step.number} points where it was filed to point"

        if fresh.by != step.by:
            return f"step {step.number} is set by whom it was filed by"

    return None


def opens_with_a_key(
    brain: store.Brain,
    step: steps.Step,
) -> Optional[str]:
    """Why a row's text may not open with a key, since a row points through its Points at cell, or None when it does not."""
    try:
        word = steps.opening_key(brain=brain, number=step.number, text=step.text)
    except steps.StepsError as refused:
        return str(refused)

    if word:
        return f"step {step.number} opens with {word} in its Step cell, and a row points through its Points at cell"

    return None


def marking_command(
    key: str,
    number: int,
    status: str,
) -> str:
    """The commands that give a step the mark asked for: the task command when the work stands on the entry, the steps command in any case."""
    by_task = {"done": "brain task done", "skipped": "brain task skip", "pending": f"brain task step {number}"}[status]

    return f"{by_task} or brain steps {key} step {number} {status}"


def entry_at(
    brain: store.Brain,
    inside: str,
) -> Optional[store.Entry]:
    """The stepped entry the store holds at the path being written, matched in any case since a disk that ignores case takes the write however the path is spelled, so the keys a step would use to point at it and the key a command names it by are the store's, a plan's slug carrying no id however it starts, or None when the store holds no entry there."""
    wanted = inside.casefold()
    for kind_name in steps.STEPPED_KINDS:
        for entry in brain.entries_of(schema.kind_named(kind_name)):
            if entry.relative.casefold() == wanted:
                return entry

    return None


def added_row(
    brain: store.Brain,
    before: list[steps.Step],
    rows: list[steps.Step],
    key: str,
    status: str,
    closed: bool,
    own: set[str],
) -> Optional[str]:
    """Why the first row added after the last may not come in that way, held to what add holds a step to, or None when each may."""
    added = rows[len(before) :]
    if added and closed:
        return f"{key} is {status}, and a closed table is its record, so no step is added to it"

    for step in added:
        if not step.text.strip():
            return f"step {step.number} has no text"

        target = steps.pointed(brain=brain, key=step.points_at) if step.points_at else None
        if step.points_at and target is None:
            return str(steps.unreachable(brain=brain, number=step.number, key=step.points_at))

        if target is not None and steps.doubled(brain=brain, key=steps.pointer_of(target)):
            return str(steps.doubled_pointer(number=step.number, key=step.points_at, pointer=steps.pointer_of(target)))

        if target is not None and steps.pointer_of(target) in own:
            return f"step {step.number} points at {key} itself, and a step points at other work"

        if step.status != "pending" and step.points_at:
            return f"step {step.number} is added pending, and takes its mark from {step.points_at}"

        if step.status != "pending":
            return f"step {step.number} is added pending, and marked once it is {step.status} with {marking_command(key=key, number=step.number, status=step.status)}"

        if not step.points_at:
            why = opens_with_a_key(brain=brain, step=step)
            if why is not None:
                return why

    try:
        steps.refuse_cycles(brain=brain, rows=added, own=own)
    except steps.StepsError as loop:
        return str(loop)

    return None


def row_line_in(
    hunk: tuple[str, ...],
) -> Optional[str]:
    """The first line of a hunk, kept, removed or added, that is a line of the steps table, a row, its header or the five celled separator under it, blank space around it aside, since a patch tool may place it with that trimmed, a table of another shape in the prose being left alone."""
    for line in hunk:
        text = line[1:].strip()
        if steps.ROW.match(text) or TABLE_LINE.match(text):
            return line[1:]

    return None


TABLE_LINE = re.compile(r"^\|[ \t]*#[ \t]*\|[ \t]*Step[ \t]*\|[ \t]*Points at[ \t]*\|[ \t]*By[ \t]*\|[ \t]*Status[ \t]*\|$|^\|(?:[ \t]*:?-+:?[ \t]*\|){5}$")


def step_line_in(
    hunk: tuple[str, ...],
) -> Optional[str]:
    """The first line of a hunk, kept, removed or added, that is a numbered step opening with a key or a Steps heading, blank space around it aside, since a list the hook cannot place could be the one under Steps, which the tool turns into the table."""
    for line in hunk:
        text = line[1:].strip()
        if steps.opens_with_a_key(text) or STEPS_HEADING.match(text):
            return line[1:]

    return None


def numbered_line_in(
    hunk: tuple[str, ...],
) -> Optional[str]:
    """The first added line of a hunk that is a numbered line, blank space around it aside."""
    for line in hunk:
        if line.startswith("+") and steps.LISTED.match(line[1:].strip()):
            return line[1:]

    return None


STEPS_HEADING = re.compile(r"^#{1,6}[ \t]+steps[ \t]*$", re.IGNORECASE)


def outcome_of(
    touch: Touch,
    text: str,
) -> tuple[Optional[str], tuple[tuple[str, ...], ...]]:
    """The file as the write would leave it, and the hunks of a patch that fit nowhere."""
    if touch.hunks:
        return patched(text=text, hunks=touch.hunks)

    return outcome(touch=touch, text=text), ()


def still_broken(
    inside: str,
    trouble: str,
    error: str,
) -> str:
    """The refusal for a write that leaves a broken header broken, the reason said once when it is the same."""
    if trouble == error:
        return f"{inside} does not read as a header now, {trouble}, and that write would leave it so"

    return f"{inside} does not read as a header now, {trouble}, and that write would not make it one, {error}"


def field_names(
    inside: str,
    lines: list[str],
) -> set[str]:
    """The fields this file's header carries or could carry, the updated date aside.

    What the file holds now plus what its kind allows, so a loose
    hunk that adds an optional field the file does not yet carry is
    still read as header work, while a prose line with a colon whose
    name is neither is not. A file whose header does not read offers no
    lines, and its kind's fields still count.
    """
    names = {name for name in (frontmatter.split_field(line)[0] for line in lines) if name is not None}
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


def placed_loosely(
    text: str,
    hunks: tuple[tuple[str, ...], ...],
) -> tuple[str, tuple[tuple[str, ...], ...]]:
    """The text after each hunk is placed where its lines match the file's with their spacing taken off, as apply_patch places one that fits nowhere exactly, and the hunks that fit nowhere even so."""
    lines = text.split("\n")
    left: list[tuple[str, ...]] = []
    for hunk in hunks:
        before = [line.strip() for line in before_lines(hunk)]
        start = block_start(lines=[line.strip() for line in lines], block=before)
        if start is None:
            left.append(hunk)
            continue

        lines[start : start + len(before)] = [line[1:] for line in hunk if line[:1] in (" ", "+")]

    return "\n".join(lines), tuple(left)


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
    """After a write, the check over the file just written and, inside the brain, doctor over the whole of it, each handed back as context so the slip is fixed in the same round.

    A file the check did not judge, one whose attributes git cannot read,
    is named on standard error and never in the context, as the check
    says every note, since that is no slip of the file's and the agent
    fixes what the context holds, and a standard error that cannot take
    the notes loses them and nothing else. Where doctor cannot read the
    brain, its error goes in words in its place, and the hook still
    answers with exit 0, since the agent says the context to the person,
    and an exit 1 would show the person the error and lose the slips, so
    a broken brain never hides one.
    """
    touched = as_the_project_spells(brain=brain, touched=touches(event=event, agent=agent))
    parts: list[str] = []

    lint_part: Optional[str] = lint_after(
        brain=brain,
        paths=[touch.path for touch in touched if not touch.deleted],
    )
    if lint_part is not None:
        parts.append(lint_part)

    checks: list[check.Checked] = [
        check.check_file(
            project=brain.root.parent,
            path=touch.path,
        )
        for touch in touched
        if not touch.deleted
        and in_project(
            brain=brain,
            path=touch.path,
        )
    ]
    slips: list[check.Slip] = [slip for checked in checks for slip in checked.slips]
    if slips:
        parts.append("brain check after that write:\n" + "\n".join(slip.text() for slip in slips))

    say_notes(notes=[note for checked in checks for note in checked.notes])

    # a front door's imports are doctor's to judge, and so is the Rust rule a Cargo.toml at the root asks for, so a write to either runs doctor as a write inside the brain does,
    # and a file deleted or moved away may be one a brain entry links to, which only Codex's patch does through a write the hook sees
    inside = [touch for touch in touched if is_inside(brain=brain, path=touch.path) or is_front_door(brain=brain, path=touch.path) or is_root_manifest(brain=brain, path=touch.path) or touch.deleted or touch.moved_from is not None]
    doctor_part: Optional[str] = doctor_after(brain) if inside else None
    if doctor_part is not None:
        parts.append(doctor_part)

    if not parts:
        emit_nothing(agent)
        return 0

    emit_context(
        agent=agent,
        text="\n\n".join(parts),
        event_name=AFTER_WRITE.get(agent, "PostToolUse"),
    )
    return 0


def lint_after(
    brain: store.Brain,
    paths: list[Path],
) -> Optional[str]:
    """The project's linters over each file written as one part of the context, the brain's own files aside outside the kit's checkout, or None when they leave nothing."""
    project = brain.root.parent
    in_kit = check.is_kit_checkout(project)
    lines: list[str] = []
    # one budget for the whole write, so a patch over many files still ends inside the agent's hook timeout
    deadline = time.monotonic() + lint.BUDGET
    for path in paths:
        if not in_project(brain=brain, path=path) or (is_inside(brain=brain, path=path) and not in_kit):
            continue

        result: lint.Linted = lint.run(
            project=project,
            path=path,
            per_command=lint.PER_COMMAND,
            budget=lint.BUDGET,
            deadline=deadline,
        )
        lines += result.left
        lines += result.notes
        if result.rewrote:
            lines.append(f"the linters rewrote {path.name}, so read it again before the next edit")

    if not lines:
        return None

    return "lint after that write:\n" + "\n".join(dict.fromkeys(lines))


def doctor_after(
    brain: store.Brain,
) -> Optional[str]:
    """Doctor's findings after a write as their part of the context, the error in words with the file and the reason where doctor cannot read the brain, or None when it finds nothing."""
    try:
        findings: list[doctor.Finding] = doctor.run(brain)
    except (store.StoreError, frontmatter.FrontmatterError, OSError, ValueError) as error:
        return f"brain doctor could not run after that write: {store.explain(error)}"

    if not findings:
        return None

    lines: list[str] = [finding.line() for finding in findings]

    return "brain doctor after that write:\n" + "\n".join(lines) + "\nRun brain doctor --fix for the fixable ones."


def in_project(
    brain: store.Brain,
    path: Path,
) -> bool:
    """Whether the file sits under the project and is there to read, the one kind of file the check reads after a write.

    The file is placed by its resolved path, the one the check names it
    by, so a link in the project that leads out of it is no file of the
    project's. A path that cannot be resolved, a loop on the 3.9 floor or
    a stray null byte, is placed nowhere.
    """
    try:
        path.resolve().relative_to(brain.root.parent.resolve())
    except (OSError, RuntimeError, ValueError):
        return False

    return store.readable_file(path)


def is_inside(
    brain: store.Brain,
    path: Path,
) -> bool:
    return links.within(brain=brain, path=path) is not None


def is_front_door(
    brain: store.Brain,
    path: Path,
) -> bool:
    """Whether the file is one of the project's front doors, AGENTS.md, CLAUDE.md or GEMINI.md at the top of the project, there or just deleted, in any case, since doctor names a door spelled in another case.

    A folder that cannot be resolved, one in a link loop or a path with
    a null byte, is no front door's, so the hook goes on with its other
    parts.
    """
    if path.name.casefold() not in {door.casefold() for door in schema.FRONT_DOORS}:
        return False

    try:
        return path.parent.resolve() == brain.root.parent.resolve()
    except (OSError, RuntimeError, ValueError):
        return False


def is_root_manifest(
    brain: store.Brain,
    path: Path,
) -> bool:
    """Whether the file is the Cargo.toml at the top of the project, whose coming or going doctor settles the Rust rule for."""
    if path.name != rust.MANIFEST:
        return False

    try:
        return path.parent.resolve() == brain.root.parent.resolve()
    except (OSError, RuntimeError, ValueError):
        return False


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
    base = cwd_of(event)
    named = event.get("tool_input")
    tool_input: dict = named if isinstance(named, dict) else {}
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
                ),
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
            action, target = marker.groups()
            path = absolute(base=base, value=target)
            if action == "Move to" and updating is not None:
                found.append(Touch(path=path, moved_from=found[updating].path))
                continue

            found.append(
                Touch(
                    path=path,
                    content="" if action == "Add File" else None,
                    deleted=action == "Delete File",
                ),
            )
            updating = len(found) - 1 if action == "Update File" else None
            adding = len(found) - 1 if action == "Add File" else None
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

    return settled(as_windows_opens(path) if store.WINDOWS else path)


# the name of a file's own data stream, which Windows opens as the file itself, read in any case
OWN_STREAM = "::$data"


def as_windows_opens(
    path: Path,
) -> Path:
    """The path as Windows opens it, each part with its own data stream's name and its trailing dots and spaces taken off, so `.ack.` and `.ack::$DATA` both write `.ack`, and a part of dots alone, `..` among them, kept."""
    parts: list[str] = []
    for part in path.parts[1 if path.anchor else 0 :]:
        if part.casefold().endswith(OWN_STREAM):
            part = part[: -len(OWN_STREAM)]
        parts.append(part.rstrip(". ") or part)

    return Path(path.anchor, *parts)


def settled(
    path: Path,
) -> Path:
    """The path with its folder resolved on disk and the file itself left alone, but for its name's case.

    Only the folder is followed, so a symlinked file still counts where
    it sits. A folder that cannot be resolved, a loop on the 3.9 floor
    or a path with a stray null byte in it, keeps its lexical spelling
    and is judged as written. Where a file stands at the path already
    under another case, its name is the one the folder lists, since a
    disk that ignores case, Windows' and macOS's by default, writes into
    that file, so `TODO-001-x.MD` is judged as the entry it lands on.
    """
    try:
        folder = path.parent.resolve()
    except (OSError, RuntimeError, ValueError):
        return path

    return folder / listed_name(folder=folder, name=path.name)


def listed_name(
    folder: Path,
    name: str,
) -> str:
    """The name as the folder lists it, where a file under another case of it stands there, or the name as given."""
    try:
        if not os.path.lexists(folder / name):
            return name

        listed: list[str] = os.listdir(folder)
    except (OSError, ValueError):
        return name

    if name in listed:
        return name

    same: list[str] = [entry for entry in listed if entry.casefold() == name.casefold()]

    return same[0] if len(same) == 1 else name


def as_the_project_spells(
    brain: store.Brain,
    touched: list[Touch],
) -> list[Touch]:
    """The touches with each path inside the project spelled as the project and the disk spell it, so every rule that compares paths as text sees one spelling.

    On a disk that folds case `<PROJECT>/.AGENTS/.ack` is the brain's
    `.ack`, and `todos/index.md` is the index. The brain is asked first,
    since a `.agents` that is a link reaches the hook through the link's
    target, which lies outside the project. A path outside both keeps
    its spelling.
    """

    def spelled(path: Path) -> Path:
        for root in (brain.root, brain.root.parent):
            inside = store.below(path=path, root=root)
            if inside is not None:
                return store.as_on_disk(root / inside, root=root)

        return path

    return [replace(touch, path=spelled(touch.path), moved_from=None if touch.moved_from is None else spelled(touch.moved_from)) for touch in touched]


# What each agent calls the event after a write, which the reply names.
# Claude Code and Codex say PostToolUse, Gemini CLI says AfterTool.
AFTER_WRITE = {"claude": "PostToolUse", "codex": "PostToolUse", "gemini": "AfterTool"}

# What each agent calls the event on a prompt, and the one the tick rides
# on. Claude Code fires PostToolBatch once after each round of tool
# calls. Codex fires PostToolUse and Gemini CLI AfterTool after each
# tool, and the shipped configs match the shell tool alone, so there
# the tick comes after each shell call.
PROMPT = {"claude": "UserPromptSubmit", "codex": "UserPromptSubmit", "gemini": "BeforeAgent"}
TICK = {"claude": "PostToolBatch", "codex": "PostToolUse", "gemini": "AfterTool"}

# The events on which Codex takes plain text on standard output as
# developer context. On its tool events plain text is dropped and only
# the JSON object reaches the model.
CODEX_PLAIN = ("SessionStart", "UserPromptSubmit")


def emit_context(
    agent: str,
    text: str,
    event_name: str,
) -> None:
    """Hand text back the way this agent takes context from a hook.

    Codex takes plain text on standard output at the start of a session
    and on a prompt, and the JSON object after a tool. Claude Code and
    Gemini CLI take one JSON object naming the event. The text is flushed
    before this returns, so a pipe the agent closed fails here, while the
    session start still holds the note it claimed, and standard output
    is closed then, so the bytes it refused do not fail again at the exit.
    A hook started with its standard output closed has none, where print
    writes nothing without a word, so that fails here too, as a write to
    the closed descriptor would. A context longer than Claude Code shows
    of a hook opens, for Claude Code, with the line that asks for the
    file it keeps the context in to be read whole, whichever event hands
    it back, since the slips after a write run as long as the file
    written.
    """
    if sys.stdout is None:
        raise OSError(
            errno.EBADF,
            os.strerror(errno.EBADF),
        )

    length_in_utf16_units: int = (
        len(
            text.encode(
                encoding="utf-16-le",
                errors="surrogatepass",
            ),
        )
        // 2
    )
    if agent == "claude" and length_in_utf16_units > CLAUDE_SHOWS:
        text = f"{PAST_WHAT_CLAUDE_SHOWS}\n\n" + text

    try:
        if agent == "codex" and event_name in CODEX_PLAIN:
            write_utf8(
                stream=sys.stdout,
                text=text + "\n",
            )
            return

        payload = {"hookSpecificOutput": {"hookEventName": event_name, "additionalContext": text}}
        print(
            json.dumps(obj=payload),
            flush=True,
        )
    except OSError:
        let_go_of(stream=sys.stdout)
        raise


def say_notes(
    notes: list[str],
) -> None:
    """Put the check's notes on standard error, one line each, as UTF-8 bytes whatever the locale, as the context is.

    A note is the lesser part of the hook's answer and never costs the
    slips, so a standard error that is closed, absent or refuses the
    write loses the notes and nothing else, and the hook goes on to hand
    the context back and exit 0. A hook started with the descriptor
    closed has no standard error, where print would put the note on
    standard output ahead of the context, so nothing is written. One
    that refuses a note, its reader gone or its disk full, is let go,
    and the notes after it are lost with it.
    """
    if sys.stderr is None:
        return

    try:
        for note in notes:
            write_utf8(
                stream=sys.stderr,
                text=note + "\n",
            )
    except OSError:
        let_go_of(stream=sys.stderr)


def say(
    line: str,
) -> None:
    """Put one line for the agent on standard error as UTF-8 bytes whatever the locale, the way every agent reads it.

    A refusal names the file in whatever characters its name holds, and
    so does the error of a brain file the hook cannot read. It goes
    through the guard the notes go through, so a standard error that is
    closed or gone never puts the line on standard output nor turns a
    refusal into a crash that lets the write through.
    """
    say_notes(notes=[line])


def let_go_of(
    stream: TextIO,
) -> None:
    """Close a standard stream once its pipe has refused a write, dropping the bytes its buffer still holds.

    The interpreter flushes standard output and standard error again at
    the exit, and the refused bytes would fail a second time there, an
    exit of 120 in place of the hook's own, after an ignored error on
    standard error where standard output refused. A closed stream is
    never flushed again. The close fails on the same bytes, an error the
    one already on its way out reports or the lost notes stand for, so
    that second one is let go.
    """
    try:
        stream.close()
    except OSError:
        return


def write_utf8(
    stream: TextIO,
    text: str,
) -> None:
    """Put text on a standard stream as UTF-8 bytes, under the text layer, so the locale's encoding never gets a say.

    The rulebook carries characters a Windows code page cannot encode, a
    check note names a file in whatever characters its name holds, and
    the agent reads its pipes as UTF-8 whatever the locale. A lone
    surrogate, which a file name that is not UTF-8 brings into the
    status, has no UTF-8 bytes, so it goes out as its escape, the way
    brain.py writes such a name. A byte layer that is not there, a text
    stream handed in by a test, takes the text as it is.
    """
    buffer: Optional[BinaryIO] = getattr(stream, "buffer", None)
    if buffer is None:
        stream.write(text)
        stream.flush()
        return

    stream.flush()
    buffer.write(
        text.encode(
            encoding="utf-8",
            errors="backslashreplace",
        ),
    )
    buffer.flush()


def emit_nothing(
    agent: str,
) -> None:
    """Say there is nothing to add, in the form the agent wants.

    On a pass, exit 0, Gemini CLI parses standard output as JSON, so it
    gets an empty object. On a refusal, exit 2, every agent takes the
    reason from standard error and reads nothing else. Claude Code takes
    silence on a pass, and Codex drops plain text on a tool event, so
    both get nothing.
    """
    if agent == "gemini":
        print("{}")


if __name__ == "__main__":
    sys.exit(main())
