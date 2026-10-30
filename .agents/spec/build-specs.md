---
name: spec-build-specs
kind: doc
description: format and lifecycle for .agents/build-specs, one branch's build spec
updated: 2026-10-30
links: [spec/conventions.md, spec/plans.md]
---

# Spec for build-specs/

One build spec per branch, written when the work starts, before the
code. It says what the branch builds and how it proves it, and lists
the todos, bugs and review it takes on in its steps table.

## Format

Standard frontmatter, `kind: build-spec`, plus these.

```
status: draft | acked | closed | dropped
branch: <the branch it builds>
born: <YYYY-MM-DD>
done: <YYYY-MM-DD, when closed or dropped>
```

Body sections, in order.

```
## Goal
## Behaviour
## Edge cases
## Out of scope
## Decisions
## Proof
## Changes
## Steps
```

Changes may stay empty. The Steps section is the table the tool keeps,
per spec/plans.md.

## Lifecycle

A spec is filed `draft`, goes `acked` on the owner's word, and goes
`closed` with its date once every step is settled, before the PR. One
given up goes `dropped` with its date. Where the work has to leave the
spec, the agent keeps going and adds a line to Changes, then brings the
other sections in line before the review.
