---
name: spec-reviews
kind: doc
description: format and lifecycle for .agents/reviews, the code review ledgers
updated: 2026-09-29
links: [spec/conventions.md, house-rules.md, spec/bugs.md]
---

# Spec: reviews/

One folder per code review, named `<yyyy-mm>-<branch-slug>`, born when
the review runs, permanent once born. The full protocol lives in
[house-rules.md](../house-rules.md), this spec covers the paper.

## The ledger

`ledger.md` inside the review's folder. Standard frontmatter,
`kind: review`, plus `branch:`, `status: open | closed` and
`level: low | medium | high | max`, the level the review ran at. The
body holds three sections.

1. **Summary**: the review's scope (what the branch did) and the final
   count when closed.
2. **Batches**: the batch table. Number, theme, status (pending,
   fixing, verified, done), the owner's ack that started it noted per
   batch, as a date, or as `auto` and the date when the batch ran on
   the owner's standing word. A review has five batches at most, since
   the batches are fixed together in one round and a batch is a theme
   of the report, wide enough for every finding of its kind. The batch
   the closing pass opens is not counted, and the
   [command reference](../skills/agent-brain/references/commands.md)
   says when the tool takes its theme.
3. **Findings**: one block per finding, ordered by batch then severity:

```
### F-07: <one line claim>
- severity: breaks | bug | debt | nit
- found-by: review | hunter
- batch: 2
- status: open | fixed | refuted | wontfix | deferred
- fix: <commit hash, date, when fixed>
- reason: <one line, when refuted, wontfix or deferred>
```

The severity is graded by what the defect does.

- `breaks`: a path a user takes fails or loses their work.
- `bug`: the code does the wrong thing for some input or state, or a
  step cannot be followed as written.
- `debt`: it works and costs later, such as a fact kept twice or a
  test that cannot fail.
- `nit`: wording and style.

The fix of a finding is the commit that holds its change, so the
findings a group fixed together carry the same hash, and a finding
another group's change settled carries that group's commit. A finding
that waited for the last pass carries the last pass's commit. A doc
that a code fix leaves stale is written again in the last pass's docs
commit, which the finding's hash does not name. A refuted finding is a
claim shown wrong, by a fixer with a verifier's agreement or, for a
claim about another product, by the page of that product's docs that
says so. A review run without sub agents refutes one on the agent's
own second read. A wontfix is a claim that holds, left as it is on
purpose. Each carries its reason on its own line, and the tool refuses
the status without one. A finding too big for its branch is `deferred`
with its reason the same way, on the owner's word alone, and it
graduates into bugs/ as its own file, linked both ways, which is the
only path a finding leaves its ledger by.

## Lifecycle

When the last batch closes, and the closing pass with it where one was
owed, the ledger flips to `status: closed` and the reviews INDEX
regroups it, and only then does the branch merge, on the owner's ask.
Nothing moves and nothing archives, since bug files and decisions link
into ledgers by name, and git is the archive.
