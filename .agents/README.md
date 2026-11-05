---
name: agent-readme
kind: doc
description: what the .agents directory is and how a cold agent boots from it
updated: 2026-11-05
links: [INDEX.md, house-rules.md, skills/agent-brain/SKILL.md]
---

# The Agent Directory

This directory is the project's brain, everything an agent needs to work
on this project, committed to the repo, all but what git ignores
there, so any agent on any machine resumes cold. Humans read docs/ at
the repo root when the project keeps one, agents read this.

## Booting

1. Read [INDEX.md](INDEX.md), the spine.
2. Read [house-rules.md](house-rules.md) before any branch, commit, or
   review work.
3. Read, list, count, file, change and check everything here through
   the brain tool, whose [skill sheet](skills/agent-brain/SKILL.md)
   says what each kind of file holds and how it moves. The tool writes every file's structure,
   and doctor names a file that breaks it.

## The map

- `SYSTEM.md`: the rules every agent works by. Claude Code and Gemini
  CLI pull it in through the root `AGENTS.md`. Codex gets it from its
  session start hook. An agent that has neither opens it first.
- `docs/`: the knowledge, categorized. What the product is and how it
  works.
- `memory/`: project facts learned along the way, one per file.
- `bugs/`: defects, one per file.
- `todos/`: work to do, one per file. The project's tracker.
- `plans/`: long horizon work, a goal with the steps that reach it, one
  per file, the steps a table the tool keeps.
- `build-specs/`: one per branch, what it builds and how it proves it,
  written before the code.
- `decisions/`: decisions taken and why, one per file.
- `reviews/`: one folder per code review, the ledger inside.
- `skills/`: the kit's skills. `agent-brain` is the brain tool, the one
  way anything here is read, listed, counted, filed, changed or checked,
  and `branch-review` is the code review the agent runs on the owner's
  word. A project may keep skills of its own here under other names,
  and doctor links them for Claude Code.
- `brain`: the launcher the brain tool is called through,
  `python3 .agents/brain`, the kit's own.
- `VERSION`: the kit release this brain is on, read by the tool.
- `.ack`: the owner's standing word to proceed and its end, the tool's
  own, which git ignores since it lives on one machine.
- `.task`: the current work, the chain from the plan down to the step
  the agent is on, which every hook prints, the tool's own and ignored
  the same way.
- `.handover/`: the note for the next session, which `brain handover`
  writes and the session start hook reads once, with the copy the hook
  reads, the lock the two take turns on and an ignore file of its own
  beside it, the tool's own and ignored the same way.

## Two absolutes

- Nothing secret ever enters this directory. All but what git ignores
  there is committed.
- Nothing here references any machine's local state. Machines point at
  this directory, never the reverse. What git ignores here is the one
  exception, since it never enters the repo.
