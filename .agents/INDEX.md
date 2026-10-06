---
name: agent-index
kind: doc
description: the spine of the agent directory, what exists and where
updated: 2026-10-06
links: [README.md, spec/conventions.md, house-rules.md]
---

# Index

The spine. Read this first, then follow into the folder indexes.
Built by the brain tool from the files it lists, so change those files
rather than this one.

## The directory itself

- [SYSTEM.md](SYSTEM.md), the rulebook every agent works by, reached through AGENTS.md
- [README.md](README.md), what the .agents directory is and how a cold agent boots from it
- [house-rules.md](house-rules.md), the branch contract and code review protocol, the agent's operating version
- [spec/conventions.md](spec/conventions.md), the shared rules every file in .agents obeys, frontmatter, naming, links, indexes
- [spec/docs.md](spec/docs.md), format and folder rules for .agents/docs, the knowledge library
- [spec/memory.md](spec/memory.md), format and rules for .agents/memory, project facts learned along the way
- [spec/bugs.md](spec/bugs.md), format and lifecycle for .agents/bugs, the defect tracker
- [spec/todos.md](spec/todos.md), format and lifecycle for .agents/todos, the work tracker
- [spec/decisions.md](spec/decisions.md), format for .agents/decisions, one decision per file
- [spec/plans.md](spec/plans.md), format and lifecycle for .agents/plans, a goal with the steps that reach it
- [spec/reviews.md](spec/reviews.md), format and lifecycle for .agents/reviews, the code review ledgers
- [spec/handover.md](spec/handover.md), the one note a session leaves for the next in .agents/handover, written by the tool, read once by the session start hook, never in git
- [skills/agent-brain/SKILL.md](skills/agent-brain/SKILL.md), the brain tool, the one way anything here is filed, changed or checked
- [skills/branch-review/SKILL.md](skills/branch-review/SKILL.md), the code review, run on the owner's word with sub agents in parallel
- [VERSION](VERSION), the kit release this brain is on

## The knowledge

- [docs/INDEX.md](docs/INDEX.md), the knowledge library: empty

## The trackers

- [plans/INDEX.md](plans/INDEX.md), the plans: empty
- [todos/INDEX.md](todos/INDEX.md), the work tracker: empty
- [bugs/INDEX.md](bugs/INDEX.md), the defect tracker: empty
- [decisions/INDEX.md](decisions/INDEX.md), the decision record: empty
- [reviews/INDEX.md](reviews/INDEX.md), code review ledgers: empty

## Memory and the handover

- [memory/INDEX.md](memory/INDEX.md), project facts: empty
- handover/, where brain handover writes the one note a session leaves for the next, which the session start hook reads once and removes, a note git ignores (spec/handover.md)
