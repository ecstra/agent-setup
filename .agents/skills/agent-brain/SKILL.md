---
name: agent-brain
description: The one way to file, change, count or check anything in the project's .agents/ brain. Use it to file a todo, a bug, a decision, a doc or a memory, to run a review ledger, to retitle a file, or to check the brain. Never write a brain file by hand.
---

# The brain tool

One command does everything under `.agents/`. It is plain Python with no
dependencies, and it runs from anywhere inside the project:

```bash
python3 .agents/skills/agent-brain/scripts/brain.py status
```

The examples below shorten that to `brain`. Every flag is listed in
[references/commands.md](references/commands.md).

## What the tool holds to

- No brain file is written by hand. `brain new` picks the id, writes the
  header block, puts the file in the right folder and rebuilds the index.
  A hook blocks a hand written file in every agent that runs hooks.
- Ids only go up. A gap left by a moved or deleted file stays a gap.
- The indexes are generated. `brain index` rebuilds them, doctor rebuilds
  them too, and nobody edits an `INDEX.md`.
- A link in frontmatter is a path relative to `.agents/`, so a file opens
  without a search. `brain refile` carries every link along.
- `brain doctor` is a gate. It exits 0 only when the brain is clean, so
  it runs green before any review.

## When a session starts

The hook prints `brain status` when a session opens. If it did not, run
it. Every number in it is counted from the files at that moment, so
trust it over anything remembered.

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

The prose goes in on standard input inside a quoted heredoc, which the
shell passes through untouched. The tool writes the structure around it
and refuses anything that breaks the spec, such as a missing heading or
a value outside the allowed set.

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
under `.agents/spec/`, and the tool names the one that is missing.

## Changing something

```bash
brain set BUG-004 status=branched
brain set TODO-012 status=done done=2026-09-16
brain refile BUG-004 --title "Token refresh loops on expiry"
```

`set` holds to the lifecycle rules. A bug goes `fixed` only once its Fix
section is written, a todo goes `done` only with a date and a filled
Done when, and a decision goes `superseded` only when it names what
replaced it.

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

Doctor reports each defect on its own line, marked `fixable` or `flag`.
`--fix` repairs the mechanical ones, a stale index, a name that
disagrees with its filename, a link written as a name, a missing skill
link, and stamps every file it touches. Whatever is left needs a
decision, so read it and act on it. Silencing a finding is never the
answer.
