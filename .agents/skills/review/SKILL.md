---
name: review
description: The kit's code review, run on the owner's word over one branch. Finder sub agents in parallel by angle, one verifier per candidate, the ledger through the brain tool, then the batch loop of fixes, hunter and verifier until clean. Use it when the owner asks for a review, and never start one on your own.
argument-hint: [low|medium|high|max] [<base>...<head>]
---

# The review

The review protocol of [house-rules.md](../../house-rules.md), run by
the agent. The level names how wide the finding pass goes and never how
hard the model thinks. Thinking is the session's effort, which the owner
sets. Sub agents run wherever the agent has them, in parallel, and where
it has none the agent works through each angle itself, in sequence, and
says so in every report.

## What holds throughout

- The owner said "review". The agent never decides a branch is ready.
- Every sub agent gets the scope, one fetch command to run first, its
  angle or its finding, and the shape of the line it returns. It never
  gets the diff pasted in and never hears what the main session thinks.
- A sub agent returns lines. The main session files them with the brain
  tool and never re reads what a sub agent read.
- Parallel wherever two sub agents do not write the same file. Sub
  agents never write the ledger and never commit.
- One commit per fix, pushed after each, the hash in the ledger.
- The ledger is the record and never the answer. Every report opens
  with the lines `brain ledger report` prints, then says what changed,
  what is left and what the owner has to do, and nothing about the
  agent's own process. The shapes are in
  [references/report.md](references/report.md).
- In Claude Code the sub agents are the definitions under
  `.claude/agents/`, on Opus at xhigh. Another agent uses the strongest
  model it has.

## The gates

Before the pass: every suite, analyzer and build that AGENTS.md section
0 names is green, and `brain doctor` is clean. A red gate stops the
review, and the report says which one.

## The scope

```bash
git diff --stat main...HEAD
git log --oneline main..HEAD
git diff --stat HEAD
```

The range is `main...HEAD` unless the owner gave one. The files in the
stat and the range go into every sub agent prompt. Uncommitted changes
are in scope too, and the third command says whether there are any.

## The finding pass

1. Open the ledger before anything is found, so the review's folder
   exists the moment it starts, with the level recorded:

   ```bash
   brain ledger open feat/billing --summary "what the branch did, one line" --level high
   ```

2. Spawn the finders, one per angle the level lists in
   [references/angles.md](references/angles.md), all at once, each with
   the finder prompt from [references/prompts.md](references/prompts.md).
   A finder returns candidate lines and nothing else.
3. Pool the candidates, drop exact repeats, same file and line and
   defect, and number them C-1 onward.
4. Spawn the verifiers, one per candidate, all at once, with the
   verifier prompt. Low skips this step. A verdict is CONFIRMED,
   PLAUSIBLE or REFUTED. A refuted candidate is never filed, and the
   report gives the refuted count only.
5. Grade and batch what survived. Severity is breaks, bug, debt or nit
   per [spec/reviews.md](../../spec/reviews.md). Batches are by theme in
   severity order, correctness first, nits last, and a batch is sized so
   one round of fixes closes it. The claims go in on standard input
   inside a quoted heredoc, one per line, so the shell never touches a
   backtick or a dollar sign in them, and one call files every claim of
   a batch that shares a severity.

   ```bash
   brain ledger batch 2026-09-feat-billing --theme correctness
   brain ledger add 2026-09-feat-billing - --severity breaks --batch 1 <<'EOF'
   upgrade.py:412 the dirty guard skips ignored files
   upgrade.py:388 the migration rewrites a file git ignores
   EOF
   ```

6. Report with the findings shape, then stop. Batch 1 starts on the
   owner's word.

## The batch loop

One batch at a time, and inside it everything that can run at once does.

1. Mark the batch, fix each finding with one commit, push, and record
   the hash:

   ```bash
   brain ledger batch 2026-09-feat-billing 1 --status fixing
   brain ledger set 2026-09-feat-billing F-03 status=fixed fix=abc1234
   ```

2. Spawn at once, all fresh: a hunter over the batch's scope with the
   hunter prompt, and one verifier per finding of the batch with the
   batch verifier prompt.
3. What the hunter found goes through verifiers, all at once, and what
   survives is filed with `--found-by hunter --batch N` and fixed in this
   batch. No backlog.
4. After a follow up commit, the verifier of each finding it touched is
   resumed with the follow up prompt, which tells it the commits and to
   re read the changed lines before voting. Hunters are never resumed. A
   new hunter runs only when a follow up commit touched a file the batch
   had not touched before.
5. The batch closes on the first pass where every verifier says gone and
   the hunter has nothing new:

   ```bash
   brain ledger batch 2026-09-feat-billing 1 --status verified
   ```

   Then the report, with the batch shape. A finding that cannot be fixed
   in this branch is deferred into `.agents/bugs/` with `brain new bug`,
   linked both ways, and named in the report. A finding not worth fixing
   is set `wontfix` with the reason on its claim line.
6. The owner's ack closes the batch and opens the next:

   ```bash
   brain ledger batch 2026-09-feat-billing 1 --status done --ack 2026-09-23
   ```

## The closing pass

At high and max, once the last batch is done, the finders run once more
over the whole branch as it now stands, with the closing line added to
their prompt, looking only for what the fixes introduced or the review
missed. The pass opens a batch themed `closing pass`, so the ledger
knows it ran, and what survives verification is filed into it and run
like any batch. A pass that found nothing leaves the batch empty and
sets it done, which needs no ack. A sweep branch skips this pass. Then:

```bash
brain ledger batch 2026-09-feat-billing --theme "closing pass"
brain ledger close 2026-09-feat-billing
```

The closing report says the branch is ready to merge on the owner's
word, and the merge itself waits for that word.

## Without sub agents

An agent that cannot spawn sub agents works through the angles of its
level itself, one after another in the same context, checks each
candidate itself against the code before filing it, and opens every
report with one line saying the review ran without sub agents.
