# Every command and flag

All of them run as `python3 .agents/skills/agent-brain/scripts/brain.py`,
shortened here to `brain`. Exit codes: 0 done, 1 refused with the reason
on standard error, 2 doctor still has findings.

## Reading

| Command | What it answers |
|---|---|
| `brain version` | The kit version this project carries, from `.agents/VERSION`. |
| `brain status [--json]` | The clock and the standing word first, then version, doctor health, counts per tracker, open reviews, the latest handover, unreadable files. The JSON form carries all of that but the clock and the word. |
| `brain ack` | The clock and where the owner's standing word to proceed stands, off, held, or on with what is left of it and what ends it. |
| `brain list <kind> [--status X] [--severity X] [--area X] [--by X] [--type X] [--branch X] [--date X] [--json]` | One line per entry of that kind, narrowed by any field. Kinds: bug, decision, doc, handover, memory, review, todo. |
| `brain show <key> [--meta]` | The whole file, or with `--meta` its frontmatter only. |
| `brain path <key>` | The absolute path behind an id, a name or a brain relative path. |
| `brain links <key> [--json]` | What the entry links to, and every entry that links to it. |

A `<key>` is an id such as `BUG-004`, a name such as
`stripe-retries-twice`, or a path inside `.agents/` such as
`docs/systems/login.md`.

## Writing

| Command | What it does |
|---|---|
| `brain new <kind> --title T --description D [fields] [--category C] [--link P]...` | Files a new entry. Prose on standard input. `--category` places a doc in a folder under `docs/`. `--link` repeats, takes a path, an id or a name, and is refused when it reaches nothing inside `.agents/`. |
| `brain set <key> field=value ...` | Changes fields, checks values and dates, applies the lifecycle rules, stamps `updated`. |
| `brain refile <key> --title T` | Renames for a new title. The id stays, every link follows. |
| `brain refile <key> --kind bug\|todo --description D [fields]` | Turns a todo into a bug or the reverse, new body on standard input. Both files stay, linked both ways, the old one marked `refiled`. |
| `brain index` | Rebuilds every `INDEX.md` and prints the ones that changed. |

Fields by kind, all passed as flags to `new` or as `field=value` to `set`:

- bug: `--severity breaks|bug|debt|nit` and `--area` required. `status`
  is open, branched, fixed, wontfix or refiled, `reported` defaults to
  today, `parent` optional.
- todo: `--by owner|agent` and `--area` required. `status` is open,
  done, dropped or refiled, `born` defaults to today, `done` is the
  closing date.
- decision: `--area` required. `status` is standing or superseded,
  `date` defaults to today, `superseded-by` names the successor.
- memory: `--type project|feedback|reference` required.
- review: `--branch` required. `status` is open or closed. Prefer
  `brain ledger open`, which writes the body shape too.
- doc and handover: no extra fields.

Required headings, which the body must carry: bug `Problem` and
`Evidence`, todo `What` and `Done when`, decision `Decision`, review
`Summary`, `Batches` and `Findings`. An empty standard input writes the
headings and nothing else, for filling in afterwards.

## The standing word

The owner's ack is the word to proceed with what the agent proposed
next. Said once as "auto ack" with an end, it stands until that end,
and the agent passes the review's gates that normally wait for it,
house rule 6 names them, saying in each report that it did. It never
starts a review, never opens a PR or merges, since those stay on the
owner's ask, and never passes a gate the rulebook or section 0 holds
for a person.

| Command | What it does |
|---|---|
| `brain ack on --for 8h` | Records the word for a duration, in minutes, hours or days, such as 90m, 8h or 2d. |
| `brain ack on --until "tomorrow 22:00"` | Records it until a moment, a time today, which means tomorrow when it has passed, `today HH:MM`, which never rolls over, `tomorrow HH:MM`, a date, which means that whole day through its last moment, or a date and time. |
| `brain ack on --until-done <key>` | Records it until a todo, a bug or a review is done, by id, name or path, a bug on a branch still counting as open. The word follows the entry's id, so a retitle leaves it standing, and it is taken back the moment the entry is done, gone from the brain, or doubled by a merge, where the brain's folder can be written, and the status line says when it could not be. An entry the brain cannot read right now, one a rebase stopped on, holds the word off until the entry reads again, and the status line says so. A review ledger that is missing holds it the same way rather than ending it, since the ledger lives on its branch and is back once that branch is checked out again. Refused for an entry of any other kind, for one already past open, and for a key that names more than one entry, which says to give the path where a path would tell them apart. Given with a time, the earlier end wins. |
| `brain ack off` | Takes the word back, and clears whatever sits where the word goes short of a folder. |

A word with no end is refused, so the agent proposes one to the owner
and waits. A second `brain ack on` replaces the word outright, ends
and all. `brain ack on` also refuses an end that does not read as a
duration or a moment, one already past, a duration of zero or less, an
end past what the calendar can show, an empty end flag, a task the
brain does not know, one of any other kind than a todo, a bug or a
review, one already past open, a key several entries share, an id
doubled by a merge among them, a todo or a bug whose file carries no
id, and a review with no name. `brain ack` given an end with no `on`, and `brain ack off` given
any end, are refused too, each with a line that says so. A folder
where the word goes, which the tool never made and never removes, has
`brain ack on` and `brain ack off` refused and `brain ack` say so. The
state is one dotted file at the root of the brain,
`.agents/.ack`, the tool's own, gitignored and never listed or checked,
since it belongs to one machine and one stretch of work. A file that
does not read as a word, a moment with no zone in it included, counts
as no word, and the status line says so until `brain ack off` clears
it, as `brain ack on` does too where the file can be written. While it
stands, `brain ledger batch <ledger> <n> --status
fixing --ack auto` records the ack as `auto` with the day, so the
ledger says which batches ran on the standing word. Any ack that
starts with auto, in any case, is that call. It is refused on a batch
left pending, since the word is checked at the batch's start, refused
on a batch that already carries the owner's own ack, which it never
writes over, and off, held or run out it is refused anywhere. On a
batch that already started on the word, the stamp it carries stays. A
pending batch that still carries a stamp from an earlier word takes
the standing word again when it starts, so its start is refused while
the word is off, and the report says it waits for the owner's word.

## The review ledger

| Command | What it does |
|---|---|
| `brain ledger open <branch> --summary S [--level low\|medium\|high\|max]` | Creates `reviews/<yyyy-mm>-<branch-slug>/ledger.md` with the three sections and an empty batch table, the level recorded in its header, high unless given. The summary is one line, or `-` to read it from standard input inside a quoted heredoc, which keeps the shell off it, and it is refused when empty or when it runs to more than one line. Standard input is read as UTF-8 wherever the tool takes it, and a byte that is not is refused. |
| `brain ledger batch <ledger> --theme T` | Adds the next batch, numbered past the highest one, status pending, and prints its number. The theme is one line with no pipe. |
| `brain ledger batch <ledger> <n> [--status pending\|fixing\|verified\|done] [--ack DATE\|auto] [--theme T]` | Sets a batch's status, the owner's ack, or its theme. The ack is the owner's word that starts a batch, recorded on it, so `fixing`, `verified` and `done` on a batch that holds findings are refused until the batch carries one, and verification closes the batch with no further word. An ack of `auto` is the standing word's stamp, the section above says when it is taken, when it is refused, and that a stamp left on a pending batch is renewed at the start and refused while the word is off. Refuses when given none of them, and refuses `verified` or `done` while a finding in the batch is still open. A batch with no findings runs and closes without an ack, and a change to the theme alone never trips a guard. An open finding filed into a batch already verified or done, or reopened there, or a finding moved in already fixed, puts the batch back to `fixing` with its ack kept, since the word covered it, so the late fix is verified like the rest. A batch that had none, an empty one closed without an ack and then given a finding, asks for the ack before anything else. The ack, like the theme, is one line with no pipe. |
| `brain ledger add <ledger> "claim" --severity S [--found-by review\|hunter] [--batch n]` | Records the next finding, numbered past the highest one, and prints its id. The claim is one line. A batch number must name a row of the table, so no finding is filed where the report cannot see it. With `-` in place of the claim, the claims come in on standard input inside a quoted heredoc, one per line, all filed with the same severity, batch and found-by in one write, so they land whole or not at all, and the ids print one per line. That keeps the shell off a backtick or a dollar sign in a claim, and files a batch's worth in one call. Empty standard input is refused. |
| `brain ledger set <ledger> F-NN field=value ...` | Changes a finding, each value one line taken as written. The fields are severity, found-by, batch, status, fix and reason, and a line a hand edit lost comes back. A fixed finding always names its commit, `fix=<hash>`, a wontfix or a deferred one says why in the same call, `reason=<one line>`, and the reason leaves with the status, so a later status never borrows it. A batch must be one the table has. Statuses: open, fixed, wontfix, deferred. |
| `brain ledger report <ledger>` | The ledger's state in a few lines, counted from the file, with a blank status read as open the way close reads it. The first line gives the status and the counts, then one line per batch with its status, ack and counts, then a last line saying what comes next. That last line names an open or a fixed finding filed into no batch the table has before anything else, since a fix is verified by its batch, then walks the batches in order and says what the first unfinished one needs, the owner's word for a pending one, or its start when the ack is already on it or the standing word holds, a stamp from an earlier word counting only while the word holds, the ack on record for one that holds findings and has none, the standing word's while one holds, then its open findings, a late one included, its verification, and its marking done. Once every batch is done it says the closing pass is owed, per house rule 7, until a batch themed `closing pass` records that the pass ran, and then to close the ledger. |
| `brain ledger close <ledger>` | Flips the ledger to closed and writes the count under Summary. Refuses while a finding is open or has no status, and until the report's next line says to close the ledger, so a batch not yet done or a closing pass still owed holds it open. |

## Doctor

| Command | What it does |
|---|---|
| `brain doctor [--json]` | Every finding, one per line, `[fixable]` or `[flag]`. Exit 2 while any remain. |
| `brain doctor --fix` | Applies every fixable repair, in passes until a pass changes nothing, then reports what is left. A repair that fails is reported as a flag with the reason. |

What doctor checks: nothing left behind by an interrupted write, no
stray files, meaning every markdown file under `.agents/` is either an
entry the store lists or a file the kit owns, frontmatter present and
complete, `updated` a real date, names matching filenames and unique,
kind matching folder, fields and values against the spec, required
headings, the lifecycle rules, filename patterns and duplicate ids,
links that resolve, links written as paths with each file once, body
links that resolve, indexes current, no dashes or semicolons in prose,
no machine paths, nothing shaped like a secret, the version stamp, the
chat style copies for Codex and Gemini CLI matching the Claude Code
one where the project keeps those agents' folders, the skill links
Claude Code needs, one per skill the kit ships and one per skill folder
the project keeps, each of which must reach its skill rather than point
at nothing or be a plain file, a real folder copy of a kit skill that
fell behind the brain's, a dangling link doctor once made for a project
skill since gone from the brain, a skills folder it cannot list, and a
version stamp that is not a version.

What `--fix` repairs: a missing or blank `updated` date, blank `links`
written as `[]`, a name that disagrees with its filename, a link written
as a name, a file linked more than once in one header, which keeps the
first, a stale index, a stale chat style copy, a skill link when it is
missing, dead, pointing elsewhere or a plain file, which the link
replaces, and a real folder copy of a kit skill that fell behind the
brain's, which is refreshed from it. Each repaired file gets today's
date. The only things `--fix` removes are what an interrupted write
left behind, a temporary file or a scratch folder named the way the
tool names them, the plain file or the wrong link sitting where a skill
link belongs, and a link under `.claude/skills` into the brain's skills
folder that dangles, leading to nothing at all, the way a link doctor
made for a project skill does once that skill is gone. The stray pass
never removes a link or a folder that still leads somewhere, whatever
it holds. A link sitting where a skill link belongs and leading
elsewhere is replaced by the right one, and a repair that rewrites a
file, a stale index or chat style copy, writes a real file in place of
any link standing there. No other file is removed.

## Port and upgrade

Both run from a checkout of the kit, since a project without the tool
has nothing to run: `python3 <kit>/.agents/skills/agent-brain/scripts/brain.py port`
from the project's root. A project that already carries the tool can
run its own copy with `--kit` pointing at the newer checkout. Without
`--project`, a port works on the top of the git repository around the
current folder and an upgrade on the nearest folder at or above the
current one that carries a brain, and neither ever works on your home
folder. The report's first line names the folder either one works on,
and `--project` has to name a folder that is there.

| Command | What it does |
|---|---|
| `brain port [--kit PATH] [--project PATH]` | Installs the kit into a project with no brain: the kit's files under `.agents/`, the front doors with the project's `## 0. Project Rules` kept from any old `AGENTS.md`, `CLAUDE.md` or `GEMINI.md`, or, with no such section anywhere, a front door's own words carried whole under that heading for the agent to read against the rulebook (a port does this, an upgrade never, since a front door without a section is then the kit's own earlier text), the hook configs merged beside the project's own hooks, the review's sub agent definitions, the chat style, the ignore lines, the version stamp, then `doctor --fix`. Ends by listing what is left to file through `brain new`: the markdown git sees outside the dot folders, root files one by one and deeper ones counted by folder, with `docs/` marked as the one the rules let a project keep (outside git, the root markdown and the usual folder names, a dot named file left out either way since the brain never files one). Refuses when a brain exists. |
| `brain upgrade [--kit PATH] [--project PATH]` | Brings a project that has a brain up to the kit. Runs the migrations the tree calls for first, then the same install. The one migration so far, to 1.0.0, runs while a `.agent/` folder is there. It moves it to `.agents/`, points every file git tracks or sees that names the old folder at the new name, the kit's own skill folders aside since the install replaces those (outside git, the root markdown, the ignore file and the brain's own markdown), refuses by name while a file git ignores names it, since such a file can neither be saved first nor be left behind, and carries section 0 out of the old `CLAUDE.md`. The stamp in `.agents/VERSION` says which release the project is on, and a kit older than it is refused. Refuses without a brain, refuses while a file it would replace holds uncommitted work, and refuses, before its first write, a project stamped before a kit skill shipped that keeps its own folder under that skill's name, in `.agents/skills`, in `.claude/skills` where the link goes, or a sub agent definition of its own under a name the skill brings, until the folder or file is moved aside. A folder the kit itself wrote is known by its bytes and passes. |

What is the project's stays the project's: everything under `.agents/`
that is not the kit's, section 0, `README.md`, `CODEOWNERS`, and any
hook or setting of its own in the agent folders. Section 0 ends at the
comment line in `AGENTS.md` that says where the kit's words start, so
it is found the same way whatever a release says after that line. In a
file the first release wrote, before that line existed, it ends where
that release's opening paragraph stood, and that paragraph is history,
so it never moves. The kit's earlier hook groups are replaced under
every event, told apart by a command that is nothing but a call of the
tool's own script, so a group of the project's own that calls the
script bare counts as the kit's and goes with them, while a group that
wraps that call, or calls a copy kept elsewhere, is the project's and
stays, and an event left with no group stays as an empty list. A rename
goes through git where git tracks the file, so the move shows as one,
and a root file the kit replaces is named in the report along with
where git keeps the old one.
The exit code is doctor's: 0 clean, 2 while findings remain, and those
are the project's own prose to put right. A finding in the kit's own
files, under `skills/agent-brain/` or `skills/branch-review/`, is the
kit's to fix, printed apart and never counted, since the install
replaces those files every time.
The tool ships without its own tests, and the chat style copies in
`.codex/` and `.gemini/` are the doctor's to make from the source in
`.claude/output-styles/`.

## Hooks

`scripts/hooks.py` is what the agents call, with the event JSON on
standard input:

| Event | What happens |
|---|---|
| `session-start` | Prints the clock, the standing word and `brain status` into the agent's context. `--with-rules` adds `SYSTEM.md` and the agent's own chat style copy, for an agent that does not expand imports. |
| `prompt` | On each prompt the owner sends, puts the clock and the standing word in front of the model, since a model does not know the time and forgets what it was told. |
| `tick` | After the agent's tool calls, the clock and the standing word again, off included, so a long stretch of work never loses either and sees the word end. Claude Code fires it once after each round of tool calls, Codex and Gemini CLI after each shell call. |
| `pre-write` | Blocks, exit 2, a write that would create a new brain file by hand, an `INDEX.md`, a file nested under `spec/`, a dotted path, which the brain never lists or checks, the `.ack` file, which `brain ack on` writes, a rename of a brain file, which `brain refile` does, or a change to the header block of an existing brain file, its `updated` date aside. Edits to the prose of an existing file, the kit's own files, files directly under `spec/` and anything under `skills/` pass. The header check judges the file as the write would leave it: the whole new text, the text after the edit, or the file after the patch's hunks. A delete is not refused, and doctor runs after it. A file the hook cannot read is already broken, so the write is taken as its repair and doctor judges the result. The hunks of a patch are placed one after another as the patch applies them, and the result is judged. A hunk that fits nowhere is refused if any line it carries, kept, removed or added, is a fence or a field the file's header carries or its kind allows, since the hook cannot tell where it would land, and the refusal names the line. A loose hunk that carries only prose is left alone. |
| `post-write` | After a write inside `.agents/`, runs doctor and hands its findings back as context. |

Context goes back as one JSON object naming the event, which all three
agents read on every event. Codex also takes plain text at the start of
a session and on a prompt, and gets it there. On its tool events plain
text is dropped, so those get the JSON object too.

The config files that wire them up ship with the kit: `.claude/settings.json`,
`.codex/hooks.json` and `.gemini/settings.json`. Codex runs its hooks
in the session's own folder with no variable for the project's, so the
Codex commands walk up to the script from there through a POSIX shell,
and each carries a Windows form beside it that runs the script by its
path from the project root. The Claude Code one also
carries the kit's two settings, `CLAUDE_CODE_SUBAGENT_MODEL` for the sub
agents' model and `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` for how many
tool calls may run at once. The port and the upgrade add each to a
project's `env` when it lacks the key and leave a value the project set.
