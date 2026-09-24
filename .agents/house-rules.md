---
name: house-rules-agent
kind: doc
description: the branch contract and code review protocol, the agent's operating version
updated: 2026-09-24
links: [spec/reviews.md, spec/bugs.md, spec/todos.md, README.md]
---

# House Rules

The development rules of every project that carries this directory. A
project may keep a short human cut at `docs/house-rules.md` and the hard
bans in a root CONTRIBUTING.md, both pointing here. The project's own
AGENTS.md section 0 names its exact gates, tooling, and PR rules.

## The branch contract

1. **One branch, one intent.** A feature, a fix, a restructure: one
   coherent intent per branch, named `feat/<slug>`, `fix/<slug>`, or
   `sweep/<slug>`. Size is measured by intent, never by commit count: a
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

## The gates

Before any review: every suite, analyzer, and build the project's
AGENTS.md section 0 names, green, and `brain doctor` clean. The review
judges code that already works, reviewers never burn effort on red
suites or a brain with broken links.

## The review protocol

1. **The timing is the owner's, the running is the agent's.** The owner
   says when a branch gets reviewed and the agent never decides that on
   its own. On the word, the agent runs the review itself with the
   kit's `branch-review` skill
   ([skills/branch-review/SKILL.md](skills/branch-review/SKILL.md))
   at the level the branch earns, low or medium for a small or
   mechanical branch and high or max where the surface is wide or the
   logic is subtle, and never low for a branch that breaks or changes
   an interface. The level sets how many angles the finding pass
   runs and never how hard the model thinks, which is the session's
   effort and the owner's to set. A tool's own review command, paid or
   cloud run ones included, is the owner's alone, so the agent neither
   reaches for one nor asks for it by name. Codex `/review --base main`
   (GPT) is a second pair of eyes the owner can add. All of it works on
   the local branch, whether or not a PR is open yet.
2. **Findings first, whole.** The finding pass runs one finder sub
   agent per angle, all at once, then verifiers over the candidates,
   a few at a time grouped by file, so what reaches the ledger has
   been checked against the code. The agent reports every finding ranked by severity before
   touching anything. No fixing during reporting, no silent triage.
3. **The ledger.** All findings land in
   `.agents/reviews/<yyyy-mm>-<branch-slug>/ledger.md` per
   [spec/reviews.md](spec/reviews.md): severity graded (breaks, bug,
   debt, nit), split into themed batches ordered by severity,
   correctness first, nits last. A finding not worth fixing gets a
   written reason, so no future review re litigates it.
4. **The batch loop.** One batch at a time, and inside it everything
   that can run at once does so.
   - Fix the batch, one commit per fix, the hash recorded beside the
     finding.
   - A hunter sub agent sweeps the batch's scope for related bugs the
     review missed, and beside it verifier sub agents, a few findings
     each grouped by file, check bug wise, not code wise, that each bug
     is actually gone and nothing new surfaced. Hunter finds enter the
     ledger as findings
     (`found-by: hunter`) and are fixed in the same batch. No backlog.
   - After a follow up commit, the verifier it concerns is resumed and
     told to re read the changed lines. The loop stops at the first
     pass where every verifier says gone and every hunter that ran has
     returned with its finds handled.
   - Sub agents run in parallel. They never edit, never commit, never
     write the ledger and never run the suite, which the gates run once
     per commit in the main session.
5. **Batch close.** Mark it in the ledger, report to the owner, and name
   anything unfixable in scope. Unfixables defer into `.agents/bugs/` as
   their own files, linked both ways, and earn a future branch sparingly,
   on the owner's call.
6. **The owner's ack gates each batch.** The next batch starts only when
   they say so. The ack is that word to start a batch, recorded on the
   batch it starts, and verification is what closes a batch. A standing
   word, `brain ack on` with an end by time or by task, is the ack for
   every gate of the review until that end, each batch and the closing
   pass, a batch the owner acked ahead starting on that ack instead,
   and each report says which of the two the step ran on. The close
   follows the last batch with no word. The PR and the merge are not
   the review's gates and stay on the owner's explicit ask, per the git
   rules below.
   A standing word with no end is not taken, the agent proposes one and
   waits. Nothing starts a review but the owner's own word.
7. **The closing pass.** Above low, the branch gets one more pass over
   itself as it stands after the last batch, to catch what the fixes
   introduced and what the review missed. Sweeps skip this.

## Git rules

- Commits are allowed and expected: one commit per change, so every
  change is undoable and addressable by hash.
- Single author, no co-author, no AI attribution anywhere: not in
  commits, not in PR titles or bodies, no generated-with footers.
- Commit messages in the owner's voice: added:/fixed:/improved:/updated:/
  removed:, one short sentence, two clauses at most.
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

Defects go to [bugs/](spec/bugs.md), work goes to [todos/](spec/todos.md),
long horizon work to [plans/](spec/plans.md), a goal with a steps table
the tool keeps, and the agent classifies on intake and uses todos
extensively (multi step work gets filed, not carried in a session's
head). Owner written todos get picked up, cleaned, and filed with their
wording preserved, and on completion the agent tells the owner which
of their own notes to tick. Work of more than one step starts with
`brain task on` and moves with `brain task done`, or of itself when
the entry a step points at closes, a refiled one handing the step on
to the entry filed in its place, per SYSTEM.md 8.3, so every hook line
says what the agent is on.
