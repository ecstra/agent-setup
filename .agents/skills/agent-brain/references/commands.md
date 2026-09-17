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
| `brain refile <key> --kind bug\|todo --description D [fields]` | Turns a todo into a bug or the reverse, new body on standard input. Both files stay, linked both ways, the old one closed. |
| `brain index` | Rebuilds every `INDEX.md` and prints the ones that changed. |

Fields by kind, all passed as flags to `new` or as `field=value` to `set`:

- bug: `--severity breaks|bug|debt|nit` and `--area` required. `status`
  is open, branched, fixed or wontfix, `reported` defaults to today,
  `parent` optional.
- todo: `--by owner|agent` and `--area` required. `status` is open,
  done or dropped, `born` defaults to today, `done` is the closing date.
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
| `brain ledger batch <ledger> --theme T` | Adds the next batch, status pending, and prints its number. |
| `brain ledger batch <ledger> <n> [--status pending\|fixing\|verified\|done] [--ack DATE]` | Sets a batch's status and the owner's ack. |
| `brain ledger add <ledger> "claim" --severity S [--found-by review\|hunter] [--batch n]` | Records the next finding and prints its id. |
| `brain ledger set <ledger> F-NN field=value ...` | Changes a finding. `status=fixed` needs `fix=<hash>`. Statuses: open, fixed, wontfix, deferred. |
| `brain ledger close <ledger>` | Flips the ledger to closed and writes the count under Summary. Refuses while a finding is open. |

## Doctor

| Command | What it does |
|---|---|
| `brain doctor [--json]` | Every finding, one per line, `[fixable]` or `[flag]`. Exit 2 while any remain. |
| `brain doctor --fix` | Applies every fixable repair, in passes until a pass changes nothing, then reports what is left. A repair that fails is reported as a flag with the reason. |

What doctor checks: no stray files, meaning every markdown file under
`.agents/` is either an entry the store lists or a file the kit owns,
frontmatter present and complete, `updated` a real
date, names matching filenames and unique, kind matching folder, fields
and values against the spec, required headings, the lifecycle rules,
filename patterns and duplicate ids, links that resolve, links written
as paths, body links that resolve, indexes current, no dashes or
semicolons in prose, no machine paths, nothing shaped like a secret, the
version stamp, and the skill link Claude Code needs, which must reach
the skill rather than point at nothing or be a plain file.

What `--fix` repairs: a missing or blank `updated` date, blank `links`
written as `[]`, a name that disagrees with its filename, a link written
as a name, a stale index, a stale chat style copy, and the skill link
when it is missing, dead or a plain file. Each repaired file gets
today's date.

## Hooks

`scripts/hooks.py` is what the agents call, with the event JSON on
standard input:

| Event | What happens |
|---|---|
| `session-start` | Prints `brain status` into the agent's context. `--with-rules` adds `SYSTEM.md` and the agent's own chat style copy, for an agent that does not expand imports. |
| `pre-write` | Blocks, exit 2, a write that would create a new brain file by hand, an `INDEX.md`, or a file nested under `spec/`. Edits to existing files, the kit's own files, files directly under `spec/` and anything under `skills/` pass. |
| `post-write` | After a write inside `.agents/`, runs doctor and hands its findings back as context. |

The config files that wire them up ship with the kit: `.claude/settings.json`,
`.codex/hooks.json` and `.gemini/settings.json`.
