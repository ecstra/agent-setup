---
name: spec-reviews
kind: doc
description: format and lifecycle for .agents/reviews, the code review ledgers
updated: 2026-09-23
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
2. **Batches**: the batch table. Number, theme, status
   (pending, fixing, verified, done), the owner's ack that started it
   noted per batch, as a date, or as `auto` and the date when the
   batch ran on the owner's standing word.
3. **Findings**: one block per finding, ordered by batch then severity:

```
### F-07: <one line claim>
- severity: breaks | bug | debt | nit
- found-by: review | hunter
- batch: 2
- status: open | fixed | wontfix | deferred
- fix: <commit hash, date, when fixed>
- reason: <one line, when wontfix or deferred>
```

A wontfix carries its reason on its own line, and the tool refuses the
status without one. A finding too big for its branch is `deferred`
with its reason the same way, and it graduates into bugs/ as its own
file, linked both ways, which is the only path a finding leaves its
ledger by.

## Lifecycle

When the last batch closes, and the closing pass with it where one was
owed, the ledger flips to `status: closed` and the reviews INDEX
regroups it, and only then does the branch merge, on the owner's word.
Nothing moves and nothing archives, since bug files and decisions link
into ledgers by name, and git is the archive.
