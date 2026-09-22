# Every command and flag

All of them run as `python3 .agents/skills/agent-brain/scripts/brain.py`,
shortened here to `brain`. Exit codes: 0 done, 1 refused with the reason
on standard error, 2 doctor still has findings.

## Reading

| Command | What it answers |
|---|---|
| `brain version` | The kit version this project carries, from `.agents/VERSION`. |
| `brain status [--json]` | Version, doctor health, counts per tracker, open reviews, the latest handover, unreadable files. |
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

## The review ledger

| Command | What it does |
|---|---|
| `brain ledger open <branch> --summary S` | Creates `reviews/<yyyy-mm>-<branch-slug>/ledger.md` with the three sections and an empty batch table. |
| `brain ledger batch <ledger> --theme T` | Adds the next batch, numbered past the highest one, status pending, and prints its number. The theme is one line with no pipe. |
| `brain ledger batch <ledger> <n> [--status pending\|fixing\|verified\|done] [--ack DATE] [--theme T]` | Sets a batch's status, the owner's ack, or its theme. Refuses when given none of them. The ack, like the theme, is one line with no pipe. |
| `brain ledger add <ledger> "claim" --severity S [--found-by review\|hunter] [--batch n]` | Records the next finding, numbered past the highest one, and prints its id. The claim is one line. |
| `brain ledger set <ledger> F-NN field=value ...` | Changes a finding, each value one line taken as written. The fields are severity, found-by, batch, status and fix, and a line a hand edit lost comes back. A fixed finding always names its commit, `fix=<hash>`. Statuses: open, fixed, wontfix, deferred. |
| `brain ledger close <ledger>` | Flips the ledger to closed and writes the count under Summary. Refuses while a finding is open or has no status. |

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
one where the project keeps those agents' folders, and the skill link
Claude Code needs, which must reach the skill rather than point at
nothing or be a plain file.

What `--fix` repairs: a missing or blank `updated` date, blank `links`
written as `[]`, a name that disagrees with its filename, a link written
as a name, a file linked more than once in one header, which keeps the
first, a stale index, a stale chat style copy, and the skill link
when it is missing, dead or a plain file. Each repaired file gets
today's date. The one thing `--fix` deletes is what an interrupted
write left behind, a temporary file or a scratch folder named the way
the tool names them. No other file is ever removed.

## Port and upgrade

Both run from a checkout of the kit, since a project without the tool
has nothing to run: `python3 <kit>/.agents/skills/agent-brain/scripts/brain.py port`
from the project's root. A project that already carries the tool can
run its own copy with `--kit` pointing at the newer checkout.

| Command | What it does |
|---|---|
| `brain port [--kit PATH] [--project PATH]` | Installs the kit into a project with no brain: the kit's files under `.agents/`, the front doors with the project's `## 0. Project Rules` kept from any old `AGENTS.md`, `CLAUDE.md` or `GEMINI.md`, or, with no such section anywhere, a front door's own words carried whole under that heading for the agent to read against the rulebook (a port does this, an upgrade never, since a front door without a section is then the kit's own earlier text), the hook configs merged beside the project's own hooks, the chat style, the ignore lines, the version stamp, then `doctor --fix`. Ends by listing what an unported project usually holds that belongs in the brain, for the agent to file through `brain new`. Refuses when a brain exists. |
| `brain upgrade [--kit PATH] [--project PATH]` | Brings a project that has a brain up to the kit. Runs the migrations the tree calls for first, then the same install. The one migration so far, to 1.0.0, runs while a `.agent/` folder is there: it moves it to `.agents/`, points every file at the new name, and carries section 0 out of the old `CLAUDE.md`. The stamp in `.agents/VERSION` says which release the project is on, and a kit older than it is refused. Refuses without a brain, and refuses while a file it would replace holds uncommitted work. |

What is the project's stays the project's: everything under `.agents/`
that is not the kit's, section 0, `README.md`, `CODEOWNERS`, and any
hook or setting of its own in the agent folders. Section 0 ends at the
comment line in `AGENTS.md` that says where the kit's words start, so
it is found the same way whatever a release says after that line. In a
file the first release wrote, before that line existed, it ends where
that release's opening paragraph stood, and that paragraph is history,
so it never moves. The kit's earlier hooks are replaced, told apart by
the tool's script in their command. A rename goes through git where git
tracks the file, so the move shows as one, and a root file the kit
replaces is named in the report along with where git keeps the old one.
The exit code is doctor's: 0 clean, 2 while findings remain, and those
are the project's own prose to put right.

## Hooks

`scripts/hooks.py` is what the agents call, with the event JSON on
standard input:

| Event | What happens |
|---|---|
| `session-start` | Prints `brain status` into the agent's context. `--with-rules` adds `SYSTEM.md` and the agent's own chat style copy, for an agent that does not expand imports. |
| `pre-write` | Blocks, exit 2, a write that would create a new brain file by hand, an `INDEX.md`, a file nested under `spec/`, a dotted path, which the brain never lists or checks, a rename of a brain file, which `brain refile` does, or a change to the header block of an existing brain file, its `updated` date aside. Edits to the prose of an existing file, the kit's own files, files directly under `spec/` and anything under `skills/` pass. The header check judges the file as the write would leave it: the whole new text, the text after the edit, or the file after the patch's hunks. A delete is not refused, and doctor runs after it. A file the hook cannot read is already broken, so the write is taken as its repair and doctor judges the result. The hunks of a patch are placed one after another as the patch applies them, and the result is judged. A hunk that fits nowhere is refused if any line it carries, kept, removed or added, is a fence or a field the file's header carries or its kind allows, since the hook cannot tell where it would land, and the refusal names the line. A loose hunk that carries only prose is left alone. |
| `post-write` | After a write inside `.agents/`, runs doctor and hands its findings back as context. |

The config files that wire them up ship with the kit: `.claude/settings.json`,
`.codex/hooks.json` and `.gemini/settings.json`.
