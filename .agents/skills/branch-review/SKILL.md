---
name: branch-review
description: The kit's code review, run on the owner's word over one branch. Finder sub agents in parallel by slice and angle, the ledger through the brain tool, then rounds of fixes by fixer sub agents in parallel by file group, each checked by a verifier and swept by a hunter until clean. Use it when the owner asks for a review, and never start one on your own.
argument-hint: [low|medium|high|max] [<base>...<head>]
---

# The review

The review protocol of [house-rules.md](../../house-rules.md), run by
the agent. The level names how wide the finding pass goes and never how
hard the model thinks, which is the session's effort and the owner's to
set. Sub agents do the reading, the fixing and the judging wherever the
agent has them, and the last section says what to do without them. The
main session coordinates. It cuts the work, briefs the sub agents, files
what they return, runs the gates and commits.

## What holds throughout

- The owner said "review". The agent never decides a branch is ready,
  and no standing word starts one.
- Every finding gets fixed. None is dropped for being rare or small,
  and none is left for later on the agent's own call. A finding leaves
  the open list as fixed, as refuted once a verifier agrees the claim
  is wrong, or as wontfix with a reason the report names. One that
  cannot be fixed inside the branch is named in the report with the
  reason, and it leaves for `.agents/bugs/` on the owner's word alone.
- Every gate of the review that waits for the owner's word, house rule
  6 names them, first asks `brain ack`. While the owner's standing word
  holds, the gate passes, the batch takes `--ack auto`, or starts on
  the owner's dated ack where it already carries one, and the report
  says which of the two the step ran on and, for the standing word,
  what is left of it. Off, the gate waits for the word in chat, unless
  the batch already carries the owner's ack, which starts it. The PR
  and the merge are not the review's gates and wait for the owner's
  ask either way. An owner who says "auto ack" with no end is asked
  for one, with a proposal such as this review's ledger as the task,
  which once the ledger is open is `brain ack on --until-done <its key>`
  and ends when it closes, or a time tonight, and nothing is recorded
  until they answer.
- Every sub agent gets the scope, one fetch command to run first, its
  slice and its angle or its findings, and the block shape it returns.
  It never gets the diff pasted in and never hears what the main
  session thinks.
- A sub agent returns blocks, one per candidate, fix or verdict, in the
  shapes [references/prompts.md](references/prompts.md) gives. The main
  session files them with the brain tool and never re reads what a sub
  agent read.
- Finders, verifiers and hunters read and judge. They never edit, never
  commit, never run the test suite and never write the ledger. A fixer
  edits the files of its group and no other, runs the tests of those
  files and never the whole suite, and never commits or writes the
  ledger. The main session runs the gates, commits and writes the
  ledger.
- Parallel wherever it can be. Finders by slice and angle, fixers by
  group, a verifier per group, hunters by slice of what a round
  changed. Nothing waits for a wave to end. A run that has to go again
  goes the moment it returns, and a verifier starts the moment its
  fixer returns. In Claude Code no more than twenty sub agents run at
  once, and a wider pass runs in waves. Ledger writes are the one
  exception and go one at a time, since the tool holds no lock and two
  at once would lose one.
- What sub agents say lives in files. Every report is saved as it came
  to a scratch folder outside the repository, and a task that needs
  earlier blocks, a list of findings or a page of rules is written to
  a file there and handed over as the file's path. The main session
  never retypes a block and reads a report only for what it has to
  decide, a result that is not FIXED, a verdict that is not GONE, a
  change a fixer needs outside its files.
- One commit per group of fixes, pushed, its hash on every finding of
  the group. The gates run once per round, when every group is quiet.
- The main session stays small, since every call costs what the
  caller's context holds. A review starts in a fresh session where the
  agent can, and the main session reads no code a sub agent can read
  for it, a group it takes over aside. A sub agent whose last report
  shows its context past about 250k tokens is not resumed again. A
  fresh one takes its place with the replacement brief of
  [references/prompts.md](references/prompts.md).
- Every report follows [references/report.md](references/report.md),
  and the rule behind it is SYSTEM.md section 7.6.
- In Claude Code the sub agents are the definitions under
  `.claude/agents/`, on Opus at the session's effort. The finder, the
  verifier and the hunter have Read and Bash, and the fixer has Edit
  and Write besides. Claude Code reads them when a session starts, so
  after a port, an upgrade or an edit to a definition the running
  session keeps the old text, or has none, until it restarts. The
  prompt carries every rule and every shape on its own, so the review
  runs the same either way, and a session with no definition spawns a
  general purpose sub agent with the definition's text at the top of
  its prompt. Another agent uses the strongest model it has. Each
  definition caps the turns a sub agent may take, wide enough for a
  finder to read its slice file by file. One that stops at its cap has
  read and not reported, so it is resumed once with the cap resume
  line of [references/prompts.md](references/prompts.md), a hunter
  included. A finder or a hunter whose report ends with (more remain)
  had more candidates than its cap, or files it never reached, and
  runs again, fresh, with every block reported so far by every run
  pasted under Already found, and, after a cap resume, with the files
  it named unread as its file list. A finder runs at most three times
  in a pass and a hunter three times in a round, each counted on its
  own, and a report names one cut short that way, with the files it
  never reached, or that candidates past its cap remained.

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
every sub agent prompt. In a project the files the kit writes whole
come off the list: its skills under `.agents/skills/`, `SYSTEM.md`,
the brain's own `README.md` and `house-rules.md`, the specs, the
version stamp in `.agents/VERSION`, the sub agent definitions under
`.claude/agents/`, the skill links under `.claude/skills/`, the chat
style, `CLAUDE.md`, `GEMINI.md`, `CONTRIBUTING.md` and the kit's words
in `AGENTS.md` below its marker line, since a finding there is the
kit's to fix and the next upgrade writes them back, and the project's
rule refuses reading the tool's code besides. The kit's own checkout is
the repository that ships the tool, and there every file is the work
and stays. Uncommitted work is in scope too. The third command lists
it file by file, tracked and untracked alike, the kit's files left out
the same way, and a prompt names an untracked file as one to read
whole, since no diff shows it.

## The slices

```bash
brain slices main...HEAD --size 300
```

Run from the project's root, the command cuts the range into slices
from git's own line counts and prints them, each a list of files. A
test file rides with its code file, docs go together, and a file too
big for one slice is cut at its functions and listed with the lines of
each part, which a finder can take since it only reads. What the scope
leaves out is left out here with git's own pathspecs after the range,
such as `':!.agents/skills'`. An uncommitted file no diff shows joins
the slice that holds its neighbours, by hand.

Pick the size so the finders of the pass fit one wave where they can,
and never above 400. A finder with more to report than its cap has to
run again, and those runs come one after another, which is where a
finding pass loses its time, so the cap is wide and the slice small.
[references/angles.md](references/angles.md) says which angles read by
slice and which read the whole branch.

## The finding pass

1. Open the ledger before anything is found, so the review's folder
   exists the moment it starts, with the level recorded and the clock
   started. The summary comes in on standard input like every line the
   agent writes from the branch, so the shell never touches it. The
   open puts the review on the current work chain, under the todo or
   the bug the work is on, which is the one it reviews when the work
   was set as the rule asks, or as the root when nothing is on, and
   every hook line then names the batch the review stands at. When the
   chain keeps it off, the open says so, and the review goes on with
   `brain task on <its key>` once the work in the way is finished or
   dropped with `brain task off`, or with `--replace` on the owner's
   word, and once a step points at it, under the plan, the todo or the
   bug whose current step that is.

   ```bash
   brain ledger open feat/billing --level high --summary - <<'EOF'
   what the branch did, one line
   EOF
   ```

2. Cut the slices and spawn the finders, all at once, each with the
   finder prompt. An angle that reads by slice gets one finder per
   slice, and an angle that reads the whole branch gets one finder
   over the whole range. A finder returns candidate blocks and nothing
   else.
3. Hand the pool to one sub agent with the merge prompt, which makes
   one finding of the candidates one fix settles and gives each its
   type, its theme and the group that will own it. It drops none and
   judges none.
4. Beside the merge, look again, once. One finder per slice runs with
   the second look angle and the candidates of its own slice as
   Already found. What the look returns is placed against the merged
   list with the placing prompt, as a further case of a finding or as
   a finding of its own. The look is never repeated, since each repeat
   costs as much as the first pass and brings a fraction of it, and
   the hunts and the closing pass read the code again.
5. A candidate that turns on how another product behaves, an agent's
   own permission rules or a parser's, goes to a sub agent that checks
   that product's docs before anything is built on it.
6. Grade and batch the merged list. Every finding is filed, and no
   verifier reads it first, since the fixer proves a claim with a
   failing test before it fixes and a verifier judges every claim a
   fixer calls wrong. Severity is breaks, bug, debt or nit per
   [spec/reviews.md](../../spec/reviews.md). Batches are by theme in
   severity order, correctness first, nits last, five at most, which
   the tool holds, so a theme is wide enough to take every finding of
   its kind. The claims go in on standard input inside a quoted
   heredoc, one per line, so the shell never touches a backtick or a
   dollar sign in them, and one call files every claim of a batch that
   shares a severity. The scenario of each stays with the main session
   for the fixer's prompt.

   ```bash
   brain ledger batch 2026-09-feat-billing --theme correctness
   brain ledger add 2026-09-feat-billing - --severity breaks --batch 1 <<'EOF'
   upgrade.py:412 the dirty guard skips ignored files
   upgrade.py:388 the migration rewrites a file git ignores
   EOF
   ```

7. Report with the findings shape. The batches start on the owner's
   word, every one the word covers at once, so stop there, unless the
   standing word holds, in which case they all start on it and the
   report's last line says so. When nothing was found, there is no
   batch and nothing was fixed, so no closing pass is owed. The report
   says so, the ledger closes, and the branch is ready to merge on the
   owner's ask.

## The round of fixes

Every batch that has the owner's word is fixed in one round, and a
round has no order among its batches.

1. Record the word on each batch it covers, which starts it.

   ```bash
   brain ledger batch 2026-09-feat-billing 1 --status fixing --ack 2026-09-23
   brain ledger batch 2026-09-feat-billing 2 --status fixing --ack 2026-09-23
   ```

2. Group the round's open findings by file, then by cause. Findings
   that name the same file are one group, a test file counts with its
   code file, and a group of more than about ten is split by cause,
   each part the findings one mechanism or one set of functions
   explains. The parts of a split share their file. Each is told the
   functions that are its own and touches no line outside them, puts
   every new test into a test file of its own, reads a file again
   right before it edits it, and names a failure it did not cause
   without chasing it. A doc several groups need belongs to the docs
   group, and every other fixer names the change it needs there in its
   report, which the main session hands on.
3. Write the model first where a group's findings are one mechanism,
   a parser, a merge, a check of who something is. The model says what
   the code has to do for every case of the kind and what it will not
   cover, and it goes into the group's first prompt with the model
   brief. A mechanism patched one finding at a time comes back every
   round.
4. Spawn one fixer per group, all at once, with the fixer prompt, the
   group's findings with their scenarios, the files it owns, and the
   command that runs the tests of those files under every interpreter
   the gates name.
5. The moment a fixer returns, the verifier of its group starts, fresh
   the first time and resumed after, with the verifier prompt over the
   working tree. No group waits for another.
6. A verdict of STILL THERE, NEW PROBLEM or REAL goes back to the
   group's fixer, resumed with the fixer's follow up, and the verifier
   is resumed after it. Three rounds at most inside a group. What
   still stands after the third comes to the main session, which reads
   the code, writes the model where step 3 wrote none, or writes it
   again, and hands it to a fresh fixer or fixes it itself. The same
   holds when a fixer answers BLOCKED since the fix needs a mechanism
   the code does not have. What a model leaves out is stated in the
   docs as a limit.
7. Once every group is quiet, every verdict GONE or REFUTED, run the
   gates once. A red gate names a test, the test names its group, and
   the failure goes to that group's fixer like a verdict. Green, each
   group becomes one commit of its own files, the parts of a split
   together since they share their file, pushed, and its hash goes on
   every finding of the group in one call. A refuted claim is set
   refuted with the verifier's reason.

   ```bash
   brain ledger set 2026-09-feat-billing F-03 F-04 F-09 status=fixed fix=abc1234
   brain ledger set 2026-09-feat-billing F-05 status=refuted reason="line 212 already guards it"
   ```

8. Hunt over what the round changed. Cut it with
   `brain slices <the commit before the round>..HEAD` and spawn one
   hunter per slice, all at once, fresh, with the hunter prompt. What
   the hunters return is filed with `--found-by hunter` into the batch
   whose theme fits, and the next round takes it, the fixers and the
   verifiers of the same groups resumed. No backlog. The rounds repeat
   until a hunt returns nothing, each hunt reading only what the round
   before it changed.
9. A finding not worth fixing is set `wontfix`, and the tool wants the
   reason.

   ```bash
   brain ledger set 2026-09-feat-billing F-09 status=wontfix reason="the guard is on purpose"
   ```

   The batches close on the first hunt that returns nothing, with
   every finding landed and every verdict in. Verification is what
   closes a batch, so both marks go in at once, batch by batch, and
   then the report, with the round shape.

   ```bash
   brain ledger batch 2026-09-feat-billing 1 --status verified
   brain ledger batch 2026-09-feat-billing 1 --status done
   ```

10. The report's call is the ack of the batches still pending, which
   starts their round as in step 1, or, after the last batch, the
   closing pass where house rule 7 owes one. Where none is owed, the
   ledger closes with no word and the report says so.

## The closing pass

House rule 7 says which reviews owe a closing pass, the tool holds the
same rule, and the report's next line says when it is due. Once the
last batch is done, fresh finders read the whole branch as it now
stands, the slices cut anew since the fixes grew it, in the layout of
the finding pass, one look, with the closing line added to their
prompt, looking only for what the fixes introduced or the review
missed. The pass opens one batch themed `closing pass`, so the ledger
knows it ran. What the finders return is filed into it and reported
with the finding pass shape, findings first like any other, and the
batch then runs on the owner's word as a round of fixes like any
other, its hunts included. A pass that found nothing leaves the batch
empty and sets it done, which needs no ack. The empty pass is batch 2
here.

```bash
brain ledger batch 2026-09-feat-billing --theme "closing pass"
brain ledger batch 2026-09-feat-billing 2 --status done
```

## Closing the ledger

Once every batch is done, and the closing pass with it where one was
owed, the ledger closes and the report says the branch is ready to
merge on the owner's ask, with the time the review took, which the
ledger's clock gives. The close follows the last batch with no word.
The PR and the merge wait for the owner's ask whether or not a
standing word holds.

```bash
brain ledger close 2026-09-feat-billing
```

## Without sub agents

An agent that cannot spawn sub agents works through the slices and the
angles of its level itself, one after another in the same context,
fixes group by group the way the fixer prompt says, a failing test
before each fix, reads each fix again against its claim before the
gates, and says so in every report, right after the state lines.
