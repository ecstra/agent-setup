---
name: branch-review
description: The kit's code review, run on the owner's word over one branch. Finder sub agents in parallel by angle, verifiers by findings grouped by file, the ledger through the brain tool, then the batch loop of fixes, hunter and verifiers until clean. Use it when the owner asks for a review, and never start one on your own.
argument-hint: [low|medium|high|max] [<base>...<head>]
---

# The review

The review protocol of [house-rules.md](../../house-rules.md), run by
the agent. The level names how wide the finding pass goes and never how
hard the model thinks, which is the session's effort and the owner's to
set. Sub agents do the reading and the judging wherever the agent has
them, and the last section says what to do without them.

## What holds throughout

- The owner said "review". The agent never decides a branch is ready,
  and no standing word starts one.
- Every gate of the review that waits for the owner's word, house rule
  6 names them, first asks `brain ack`. While the owner's standing word
  holds, the gate passes, the batch takes `--ack auto`, and the report
  says the step ran on the standing word and what is left of it. Off,
  the gate waits for the word in chat. The PR and the merge are not the
  review's gates and wait for the owner's ask either way. An owner who
  says "auto ack" with no end is asked for one, with a proposal such as
  this review's ledger as the task, `brain ack on --until-done <its
  key>` once the ledger is open, which ends when it closes, or a time
  tonight, and nothing is recorded until they answer.
- Every sub agent gets the scope, one fetch command to run first, its
  angle or its findings, and the block shape it returns. It never gets
  the diff pasted in and never hears what the main session thinks.
- A sub agent returns blocks, one per candidate or verdict, in the
  shapes [references/prompts.md](references/prompts.md) gives. The main
  session files them with the brain tool and never re reads what a sub
  agent read.
- Sub agents never edit, never commit, never run the test suite and
  never write the ledger. Verifiers judge from the code, and the gates
  run the suite once per commit in the main session.
- Parallel wherever it can be. Finders by angle, verifiers by findings,
  the hunter beside the verifiers. A verifier takes up to six
  candidates or findings, a file's stay together, and files with fewer
  share one verifier that gets the file list, so the count follows the
  findings and a branch of many files never means many verifiers. In
  Claude Code no more than twenty sub agents run at once, and a wider
  pass runs in waves. Ledger writes are the one exception and
  go one at a time, since the tool holds no lock and two at once would
  lose one.
- One commit per fix, pushed after each, the hash in the ledger.
- Every report follows [references/report.md](references/report.md),
  and the rule behind it is SYSTEM.md section 7.6.
- In Claude Code the sub agents are the definitions under
  `.claude/agents/`, on Opus at the session's effort, with Read and
  Bash. Claude Code reads them when a session starts, so after a port,
  an upgrade or an edit to a definition the running session keeps the
  old text, or has none, until it restarts. The prompt carries every
  rule and every shape on its own, so the review runs the same either
  way, and a session with no definition spawns a general purpose sub
  agent with the definition's text at the top of its prompt. Another
  agent uses the strongest model it has. Each definition caps the turns
  a sub agent may take, wide enough for a finder to read a large branch
  file by file. One that stops at its cap has read and not reported, so
  it is resumed once with the cap resume line of
  [references/prompts.md](references/prompts.md), a hunter included. A
  finder or a hunter whose report ends with (more remain) had more
  candidates than its cap, or files it never reached, and runs again,
  fresh, with every block reported so far by every run pasted under
  Already found, and, after a cap resume, with the files it named
  unread as its file list. A finder runs at most three times in a pass
  and a hunter three times in a batch, each hunter counted on its own,
  and a report names one cut short that way, with the files it never
  reached, or that candidates past its cap remained.

## The gates

Before the pass, every suite, analyzer and build that AGENTS.md section
0 names is green, and `brain doctor` is clean. A red gate stops the
review, and the report says which one.

## The scope

```bash
git diff --name-only main...HEAD
git log --oneline main..HEAD
git status --porcelain --untracked-files=all
```

The range is `main...HEAD` unless the owner gave one. The first command
lists every changed file whole, and the list and the range go into
every sub agent prompt. Uncommitted work is in scope too. The third
command lists it file by file, tracked and untracked alike, and a
prompt names an untracked file as one to read whole, since no diff
shows it.

## The finding pass

1. Open the ledger before anything is found, so the review's folder
   exists the moment it starts, with the level recorded. The summary
   comes in on standard input like every line the agent writes from the
   branch, so the shell never touches it.

   ```bash
   brain ledger open feat/billing --level high --summary - <<'EOF'
   what the branch did, one line
   EOF
   ```

2. Spawn the finders, one per angle the level lists in
   [references/angles.md](references/angles.md), all at once, each with
   the finder prompt. A finder returns candidate blocks and nothing
   else. At max the sweep finder waits for step 3.
3. Pool the candidates, merge those on the same file and line that name
   the same defect, and number them C-1 onward. At max, spawn the sweep
   finder now, with the pooled list as its already found list.
4. Spawn the verifiers, at most six candidates each, a file's together
   and small files sharing, all at once, with the verifier prompt. A
   verdict is CONFIRMED, PLAUSIBLE or REFUTED. A refuted candidate is
   never filed, and the report gives the refuted count only. The
   sweep's candidates go through a second, smaller round the same way.
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

6. Report with the findings shape. Batch 1 starts on the owner's word,
   so stop there, unless the standing word holds, in which case batch
   1 starts on it and the report's last line says so. When nothing
   survived, there is no batch and nothing
   was fixed, so no closing pass is owed. The report says so, the
   ledger closes, and the branch is ready to merge on the owner's word.

## The batch loop

One batch at a time.

1. Record the owner's ack on the batch, the word that starts it, then
   fix each finding with one commit, the gates green before every
   commit, push, and record the hash.

   ```bash
   brain ledger batch 2026-09-feat-billing 1 --status fixing --ack 2026-09-23
   brain ledger set 2026-09-feat-billing F-03 status=fixed fix=abc1234
   ```

2. Spawn at once, all fresh, a hunter over the batch's scope with the
   hunter prompt and verifiers over the batch's findings, grouped the
   same way as in the finding pass, with the batch verifier prompt.
3. What the hunter found goes through verifiers, all at once, and what
   survives is filed with `--found-by hunter --batch N` and fixed in this
   batch. No backlog. Those fixes then get fresh batch verifiers of
   their own, grouped the same way.
4. After a follow up commit, the verifier of each finding it touched is
   resumed with the follow up prompt, which tells it the commits and to
   re read the changed lines before voting. Hunters are never resumed
   for a follow up. A new hunter runs only when a follow up commit
   touched a file the batch had not touched before.
5. A finding that cannot be fixed in this branch is deferred into
   `.agents/bugs/` with `brain new bug`, linked both ways, and named in
   the report. A finding not worth fixing is set `wontfix`, and either
   way the tool wants the reason, before the batch can be verified.

   ```bash
   brain ledger set 2026-09-feat-billing F-09 status=wontfix reason="the guard is on purpose"
   ```

   The batch closes on the first pass where every finding has landed,
   every verifier says gone, the verifiers of the hunter's finds
   included, and every hunter that ran has returned with its finds
   filed and handled. Verification is what closes it, so both marks go
   in at once, and then the report, with the batch shape.

   ```bash
   brain ledger batch 2026-09-feat-billing 1 --status verified
   brain ledger batch 2026-09-feat-billing 1 --status done
   ```

6. The report's call is the ack of the next batch, which starts it as
   in step 1, or, after the last batch, the closing pass or the close.

## The closing pass

House rule 7 says which reviews owe a closing pass, the tool holds the
same rule, and the report's next line says when it is due. Once the
last batch is done, the finders run once more over the whole branch as
it now stands, with the closing line added to their prompt, looking
only for what the fixes introduced or the review missed. The pass
opens a batch themed `closing pass`, so the ledger knows it ran. What
survives verification is filed into it and reported with the finding
pass shape, findings first like any other, and the batch then runs on
the owner's word like any batch. When more survives than one round of
fixes closes, it is batched by theme in severity order like the
finding pass, the first batch themed `closing pass` and the rest
`closing pass, <theme>`, each on the owner's ack like any batch. A
pass that found nothing leaves the batch empty and sets it done, which
needs no ack. The empty pass is batch 2 here.

```bash
brain ledger batch 2026-09-feat-billing --theme "closing pass"
brain ledger batch 2026-09-feat-billing 2 --status done
```

## Closing the ledger

Once every batch is done, and the closing pass with it where one was
owed, the ledger closes and the report says the branch is ready to
merge on the owner's word. The close follows the last batch with no
word. The PR and the merge wait for the owner's ask whether or not a
standing word holds.

```bash
brain ledger close 2026-09-feat-billing
```

## Without sub agents

An agent that cannot spawn sub agents works through the angles of its
level itself, one after another in the same context, checks each
candidate itself against the code before filing it, and says so in
every report, right after the state lines.
