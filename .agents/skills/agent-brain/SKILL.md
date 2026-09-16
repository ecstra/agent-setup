---
name: agent-brain
description: Files, changes, counts and checks everything in the project's .agents/ brain, which holds its todos, bugs, decisions, docs, memory, review ledgers and handovers. Use it whenever work needs filing or tracking, a bug turns up, a decision is taken, a session learns a durable fact, a review starts, a file needs a new title, or the brain needs checking. Never create or renumber a brain file by hand, the tool owns ids, header blocks and indexes.
---

# The brain tool

Everything under `.agents/` is filed, changed, counted and checked through
one command. It is plain Python with no dependencies, run from anywhere
inside the project:

```bash
python3 .agents/skills/agent-brain/scripts/brain.py status
```

Every example below shortens that to `brain`. The full flags for each
command are in [references/commands.md](references/commands.md).

## The rules the tool enforces

- A brain file is never written by hand. `brain new` picks the id, writes
  the header block, files it in the right folder and rebuilds the index.
  A hook blocks a hand written file in every agent that runs hooks.
- Ids only go up. A gap left by a moved or deleted file stays a gap.
- The indexes are generated. `brain index` rebuilds them, and doctor
  rebuilds them for you. Nobody edits an `INDEX.md`.
- Frontmatter links are paths relative to `.agents/`, so a file can be
  opened without searching. `brain refile` drags every link along.
- `brain doctor` is a gate. It exits 0 only when the brain is clean, so
  it runs green before any review.

## Start of a session

The hook prints `brain status` when a session opens. If it did not, run
it. Every number in it is counted from the files at that moment.

```bash
brain status
brain list bug --status open
brain list todo --status open --area auth
brain show BUG-004
brain path BUG-004
brain links DEC-012
```

`show --meta` prints the frontmatter only. `--json` on `status`, `list`
and `links` gives the same answer for a script.

## Filing something

The prose goes in on standard input inside a quoted heredoc, so the
shell passes it through untouched. The tool writes the structure around
it and refuses anything that breaks the spec, such as a missing
heading or a value outside the allowed set.

```bash
brain new bug --title "Token refresh loops after expiry" \
  --description "sign in loops once the refresh token expires" \
  --severity breaks --area auth <<'EOF'
## Problem

After the refresh token expires the sign in screen loops.

## Evidence

The auth log shows refresh, 401, refresh, 401.
EOF
```

The same shape files a todo (`--area`, `--by`), a decision (`--area`),
a memory (`--type project|feedback|reference`), a doc (`--category`), a
handover, or a review. Each kind's required headings are in its spec
under `.agents/spec/`, and the tool names the missing one if the body
lacks it.

## Changing something

```bash
brain set BUG-004 status=branched
brain set TODO-012 status=done done=2026-09-16
brain refile BUG-004 --title "Token refresh loops on expiry"
```

`set` applies the lifecycle rules: a bug goes `fixed` only once its Fix
section is written, a todo goes `done` only with a date and a filled
Done when, a decision goes `superseded` only naming its successor.

`refile --kind bug` turns a todo into a bug, or the reverse, with the
new body on standard input. Both files stay and link to each other, so
the id trail holds.

## A review

```bash
brain ledger open feat/billing --summary "The billing branch, six commits."
brain ledger batch 2026-09-feat-billing --theme correctness
brain ledger add 2026-09-feat-billing "the guard is inverted" --severity breaks --batch 1
brain ledger set 2026-09-feat-billing F-01 status=fixed fix=abc1234
brain ledger batch 2026-09-feat-billing 1 --status verified --ack 2026-09-16
brain ledger close 2026-09-feat-billing
```

Findings and batches number themselves. `close` refuses while any
finding is still open.

## Checking the brain

```bash
brain doctor
brain doctor --fix
```

Doctor reports every defect on one line each, marked `fixable` or
`flag`. `--fix` repairs the mechanical ones, such as a stale index, a
name that disagrees with its filename, a link written as a name, or a
missing skill link, and stamps every file it touches. What is left
needs a decision, so read it and act, never silence it.
