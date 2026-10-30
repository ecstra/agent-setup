---
name: house-rules-agent
kind: doc
description: the branch contract and code review protocol, the agent's operating version
updated: 2026-10-30
links: [README.md, skills/agent-brain/SKILL.md, skills/branch-review/SKILL.md]
---

# House Rules

The development rules of every project that carries this directory. A
project may keep a short human cut at `docs/house-rules.md` and the hard
bans in a root CONTRIBUTING.md, both pointing here. The project's own
AGENTS.md section 0 names its exact gates, tooling, and PR rules.

## The branch contract

1. **One branch, one intent.** A feature, a fix or a restructure is one
   coherent intent per branch, named `feat/<slug>`, `fix/<slug>`, or
   `sweep/<slug>`. Size is measured by intent, never by commit count. A
   long branch serving one intent is fine, a second intent born mid
   branch forks its own branch the day it appears, it never rides.
2. **Sweeps carry the small stuff.** Small bugs and small features group
   into a sweep branch by surface, one screen or one subsystem per sweep.
   A sweep never contains a breaking change.
3. **Branch from fresh main.** Merge whole, never cherry pick out of an
   unreviewed branch. A merged branch is deleted, its review ledger is
   the record.
4. **Main is reviewed code only.** Gates first, then review, then
   merge. No step skips, and nothing merges before the review has
   closed. When the PR opens and whether as a draft is the project's
   rule in AGENTS.md section 0, never a question the agent asks.
5. **A branch leaves no gap.** What the build spec promises is built
   and proven, and every doc, test and caller the change makes wrong is
   put right on the branch. A gap that waits on later work is filed as
   a bug or a todo naming what it waits on, per SYSTEM.md 8.3.

## The gates

The project's AGENTS.md section 0 names its linters under a Lint
heading and its gates under a Gates heading. The brain runs the Lint
lines on every file the agent writes, and `brain gates` runs the Gates
before a review and before a merge. It runs them in order and stops at
the first red one, and once all are green it runs `brain check` and
`brain doctor`, as
[commands.md](skills/agent-brain/references/commands.md#the-gates)
says. Before any review it is green. The review judges code that
already works, reviewers never burn effort on red suites or a brain
with broken links. When the review starts the working tree is clean
as well, since a review reads committed work only.

## The review protocol

1. **The timing is the owner's, the running is the agent's.** The owner
   says when a branch gets reviewed and the agent never decides that on
   its own. On the word, the agent runs the review itself with the
   kit's `branch-review` skill
   ([skills/branch-review/SKILL.md](skills/branch-review/SKILL.md)),
   which holds the steps, at the level the branch earns. Quick fits a
   small change, standard is the usual level, and deep fits a release
   or code that handles money, sign in or data. The level sets how many
   finders run and never how hard the model thinks, which is the
   session's effort and the owner's to set. A tool's own review
   command, paid or cloud run ones included, is the owner's alone, so
   the agent neither reaches for one nor asks for it by name. Codex
   `/review --base main` (GPT) is a second pair of eyes the owner can
   add. All of it works on the local branch, whether or not a PR is
   open yet.
2. **Harm only.** A finding is a defect with concrete harm, behaviour
   that breaks for a user or leaves the build spec, data lost or
   leaked, a security hole, an edge case a real input reaches, or code
   the spec never asked for. Style is the linters' and docs are the
   docs agent's, so neither is a finding. A defect older than the
   branch goes to `.agents/bugs/`.
3. **One pass and a short recheck.** Finders read the whole branch,
   verifiers vote on what they found, and the main agent fixes every
   confirmed finding itself in one go. A fresh verifier rechecks the
   diff of the fix, three rounds at most, then one docs agent brings
   the docs up to the code. The ledger under `.agents/reviews/`, which
   the brain tool keeps, holds each finding until it leaves as fixed,
   refuted, left as it is or deferred, and one that is not fixed
   carries its reason, so no future review re litigates it.
4. **The owner's ack gates each round.** Their word to review starts
   the first round, and each later round starts on their next word,
   recorded on that round's batch. A standing word, `brain ack on` with
   an end by time or by task, is the ack for every round until that
   end, and each report says which of the two the round ran on. The
   close follows the last round with no word. The PR and the merge are
   not the review's gates and stay on the owner's explicit ask, per the
   git rules below. A standing word with no end is not taken, the agent
   proposes one and waits. Nothing starts a review but the owner's own
   word.

## Git rules

- Commits are allowed and expected: one commit per change, so every
  change is undoable and addressable by hash.
- Single author, no co-author, no AI attribution anywhere: not in
  commits, not in PR titles or bodies, no generated-with footers.
- Commit messages in the owner's voice: `added:`, `fixed:`, `improved:`,
  `updated:` or `removed:`, one short sentence, two clauses at most.
- Push after each commit.
- PRs only on the owner's explicit ask in the current message, through
  the project's PR tooling, base main, plain unless section 0 says
  otherwise. Merges only on the owner's explicit ask, never before the
  review has closed.
- Never commit to main directly.
- Worktrees are disabled: never create one, and never use a worktree
  isolation mode for sub-agents. If the owner ever explicitly asks, the
  one sanctioned home is `.agents/.worktrees/` (gitignored), nowhere
  else, torn down when the task ends.

## The trackers

Defects go to `bugs/`, work goes to `todos/`,
long horizon work to `plans/`, a goal with a steps table
the tool keeps, and the agent classifies on intake and uses todos
extensively (multi step work gets filed, not carried in a session's
head). Owner written todos get picked up, cleaned, and filed with their
wording preserved, and on completion the agent tells the owner which
of their own notes to tick. Work of more than one step starts with
`brain task on` and moves with `brain task done`, or of itself when
the entry a step points at closes, a refiled one handing the step on
to the entry filed in its place, per SYSTEM.md 8.3, so every hook line
says what the agent is on.
