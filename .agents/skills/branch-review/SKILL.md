---
name: branch-review
description: The kit's code review, run on the owner's word over one branch. Finder sub agents in parallel, one per slice for an angle that reads by slice and one over the whole branch for the others, the ledger through the brain tool, then rounds of fixes by fixer sub agents in parallel by file group, each checked by verifiers and followed by a hunt until a hunt finds nothing. Use it when the owner asks for a review, and never start one on your own.
argument-hint: [low|medium|high|max] [<base>...<head>]
---

# The review

The review protocol of [house-rules.md](../../house-rules.md), run by
the agent, step by step. The level names how wide the finding pass goes
and never how hard the model thinks, which is the session's effort and
the owner's to set. Sub agents do the work wherever the agent has them,
and the last section says what to do without them. The main session
coordinates them.

## Words

- Round: a round of fixes over the batches that have the owner's word,
  from its fixers to its commits and its hunt.
- Pass: one exchange inside a group, the fixer's work and the
  verifier's vote on it. A finding gets three passes at most. The
  stages of the review, such as the finding pass, keep their own names.
- Group: the findings one fixer owns, with the files it may edit, cut
  as step 2 of the round says.

## What holds throughout

- The owner said "review". The agent never decides a branch is ready,
  and no standing word starts one.
- Every finding lands, and none is dropped for being rare or small.
  Fixed is the rule. Refuted means the claim is wrong, and it needs the
  verifier's agreement, or for a claim about another product the page
  of that product's docs that says so. Left as it is, which the ledger
  calls wontfix, means the claim is true and the behaviour is on
  purpose. The fixer answers LEFT with the line or the doc that says
  so, and the verifier agrees or answers REAL. The report names the
  reason. Deferred means it cannot be fixed inside the branch. It
  leaves for `.agents/bugs/` on the owner's word alone, through
  `brain new bug`, linked both ways, the bug to the ledger and the
  finding's reason to the bug, and the finding is set `deferred` with
  that reason. Where the owner says no, the finding is left as it is on
  the owner's reason, or fixed the way the owner names. Once every
  finding of a batch has landed, the batch closes the way the last pass
  says.

  ```bash
  brain new bug --title "the invoice total rounds each line" --description "a finding of the feat/billing review the branch cannot fix" --severity bug --area billing --link 'reviews/2026-09-feat-billing/ledger.md' <<'EOF'
  ## Problem
  The invoice total rounds each line, where the billing service rounds the sum.

  ## Evidence
  F-07 of the feat/billing review, whose fix needs the billing service's own repository.
  EOF
  brain ledger set 2026-09-feat-billing F-07 status=deferred reason="BUG-012, the fix needs the billing service's own repository"
  ```

- A finding is the branch's own. A case is the branch's when it sits in
  a function the range changed or in code the change made reachable,
  and older when it sits outside those and behaves the same on the
  base. The fixer and the verifier say which from
  `git diff <base>...<head> -- '<the case's file>'`, and name an older
  case on a line that opens with Older. The main session files it as a
  bug at once through `brain new bug`, and the report names it. It
  never counts against a finding. A finding widened to take such cases
  in never closes, since the code before the branch has no end of them.
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
- The sub agents are four definitions, each on Opus at the session's
  effort, under `.claude/agents/` in Claude Code. The finder reads and
  reports, and the second look, the merger, the joiner and the closing
  finder are finders. The fixer edits, and the docs writers and the
  sweep's fixers are fixers. The verifier judges, and the model check
  is a verifier's. The hunter hunts. The finder, the verifier and the
  hunter have Read, Bash and Write, the Write for their answer file
  alone, and the fixer has Edit besides. The check of another product's
  docs needs the web, so it goes to a general purpose sub agent on
  Opus, which writes nothing but its answer file. Claude Code reads the
  definitions when a session starts, so after a port, an upgrade or an
  edit to a definition the running session keeps the old text, or has
  none, until it restarts. The prompt carries every rule and every
  shape on its own, so the review runs the same either way, and a
  session with no definition spawns a general purpose sub agent with
  the definition's text at the top of its prompt. Another agent uses
  the strongest model it has.
- Every prompt carries the range and the project's root, and names the
  path of its answer file. The ones that read a diff also carry the
  file list and one fetch command to run first, so no prompt holds the
  diff itself. Every path in a command is single quoted. The prompts
  are in [references/prompts.md](references/prompts.md). The main
  session's view reaches a sub agent in two forms only, a model and a
  finding's blocks.
- Every sub agent writes its blocks to its answer file, with the Write
  tool where it has one and otherwise with one Bash call and a quoted
  heredoc. Every run has an answer file of its own, a second run and a
  resumed one too. Earlier blocks reach a sub agent as the paths of the
  answer files that hold them. The answer itself is one line per block,
  its id and its Type, Result or Verdict, then every line the task puts
  after the blocks, word for word. Those are the line (more remain) and
  the lines that open with Older, Elsewhere or Doc, and a sub agent that
  edits adds one line `Outside: <F-nn>` per block whose Outside is not
  none and one line `Files:` with every file it made or took away. The
  main session opens an answer file only for what a line of the answer
  names.
- The scratch folder is the review's own, named for the ledger, in the
  place where the agent's harness lets sub agents write without asking,
  the session's scratchpad in Claude Code and a folder under the
  system's temporary folder elsewhere. It lies outside the repository
  and is working paper, so the rule on writes of SYSTEM.md 10.3 does
  not reach it. It does not outlive its session everywhere, which the
  review leaves as a limit. When it is lost, the claims in the ledger
  are what is left, and a fixer starts from the claim.
- As many sub agents run at once as the harness allows, twenty in
  Claude Code, and the next one starts as one returns. There are no
  waves. Ledger writes are the one exception and go one at a time,
  since the tool holds no lock and two at once would lose one.
- Each definition caps the turns a sub agent may take. One that stops
  at its cap with no answer file runs again, fresh, with the same
  prompt, once. A fixer's second run gets the replacement brief after
  its prompt, since the working tree holds the earlier changes. A
  second stop is named in the report as cut short. There is no rule on
  the size of a sub agent's context, since every round starts with
  fresh fixers and verifiers.
- Only a fixer edits, and only the files of its group. No sub agent
  commits or writes the ledger, which the main session alone does. A
  fixer runs the tests of its files and never the whole suite. A
  verifier never runs the project's test suite. It may run one snippet,
  and each fixed finding's test once with the fix taken out, on a copy
  of the tree in the scratch folder, never a worktree, removed after.
- The main session stays small, since every call costs what the
  caller's context holds. A review starts in a fresh session where the
  agent can, and the main session reads code for two things only, to
  write a model and to read a red gate that names no group's file.
- Every report follows [references/report.md](references/report.md),
  and the rule behind it is SYSTEM.md section 7.6. Of the review's own
  run a report says only the lines report.md lists for it.

## The gates

Before the review, every suite, analyzer and build that AGENTS.md
section 0 names is green, and `brain doctor` is clean. A red gate stops
the review, and the report says which one.

The working tree is clean too before the ledger opens. A review reads
committed work only, a limit it keeps on purpose, so where
`git status --porcelain` prints anything the review says so and stops,
and the owner commits the work or puts it aside. The clean tree is a
check of the start and no gate of a round.

## The scope

```bash
git diff --name-only --no-renames <base>...<head> -- ':!.agents/reviews' ':!.agents/bugs' ':!.agents/INDEX.md'
git log --oneline <base>..<head>
```

The range is `main...HEAD` unless the owner gave one, and
`<base>...<head>` stands for it in every command here. The first
command lists every changed file whole. With `--no-renames` a rename is
a file taken away and a file added, so every line names a file. The
pathspecs keep out what the review itself writes, its ledger and the
bugs it files with their indexes, the brain's own index among them, and
every command that takes the scope carries them, the hunts' and the
closing pass's too.

In a project the files the kit writes whole come off the list: its
skills under `.agents/skills/`, `SYSTEM.md`, the brain's own
`README.md` and `house-rules.md`, the specs, the version stamp in
`.agents/VERSION`, the sub agent definitions under `.claude/agents/`,
the skill links under `.claude/skills/`, the chat style, `CLAUDE.md`,
`GEMINI.md`, `CONTRIBUTING.md` and the kit's words in `AGENTS.md` below
its marker line, since a finding there is the kit's to fix and the next
upgrade writes them back, and the project's rule refuses reading the
tool's code besides. The kit's own checkout is the repository that
ships the tool, and there every file is the work and stays.

## The slices

```bash
git diff --numstat --no-renames <base>...<head> -- ':!.agents/reviews' ':!.agents/bugs' ':!.agents/INDEX.md'
git diff --name-only --no-renames --diff-filter=D <base>...<head> -- ':!.agents/reviews' ':!.agents/bugs' ':!.agents/INDEX.md'
```

The main session cuts the slices itself from git's count of changed
lines per file, which the first command prints, each slice a list of
files that holds about 300 changed lines. What the scope leaves out is
left out here. A test file rides with its code file, and docs go
together. A file of more than 400 changed lines is cut into parts by
its hunks, which `git diff -U0 <base>...<head> -- '<file>'` lists, each
part a range of lines of the file as HEAD has it. The finder of a part
judges its lines and reads the rest of the file to understand them. A
slice is above 400 only where a single hunk, or a code file with its
test, is.

A file the range took away, which the second command lists, belongs to
no slice, and the angles that read the whole branch read it from the
diff. A binary file, which the count shows as `-` for both numbers, is
named in the scope and not read.
[references/angles.md](references/angles.md) says which angles read by
slice and which read the whole branch.

## The finding pass

1. Open the ledger before anything is found, so the review's folder
   exists the moment it starts, with the level recorded. The summary
   comes in on standard input like every line the agent writes from
   the branch, so the shell never touches it. The open puts the review
   on the current work chain, under the todo or the bug the work is
   on, which is the one it reviews when the work was set as the rule
   asks, or as the root when nothing is on, and every hook line then
   names the batch the review stands at. When the chain keeps it off,
   the open says so, and the review goes on with
   `brain task on <its key>` once the work in the way is finished or
   dropped with `brain task off`, or with `--replace` on the owner's
   word, and once a step points at it, under the plan, the todo or the
   bug whose current step that is.

   ```bash
   brain ledger open feat/billing --level high --summary - <<'EOF'
   what the branch did, one line
   EOF
   ```

   Commit the review's paper at once, and again wherever a step below
   says so. A paper commit takes what the brain tool wrote for the
   review and nothing else. That is the review's folder, the bugs the
   review filed, the plan, the todo or the bug whose step points at the
   review, which the close rewrites, and the indexes the tool rebuilt.
   The tree was clean before the review and the groups' files are
   committed by then, so these are the paths under `.agents/` that
   `git status --porcelain` still lists, and the commit names them one
   by one. In the kit's own checkout, whose `.agents/` is the template
   the kit ships, the paper lives in a brain kept outside the checkout
   and is committed there.

   ```bash
   git status --porcelain --untracked-files=all -- '.agents'
   git add -- '.agents/INDEX.md' '.agents/reviews/INDEX.md' '.agents/reviews/2026-09-feat-billing/ledger.md'
   git commit -m "added: the review of feat/billing" -- '.agents/INDEX.md' '.agents/reviews/INDEX.md' '.agents/reviews/2026-09-feat-billing/ledger.md'
   ```

2. Cut the slices and spawn the finders, all at once, each with the
   finder prompt and its angle from
   [references/angles.md](references/angles.md). An angle that reads by
   slice gets one finder per slice, and an angle that reads the whole
   branch gets one finder over the whole range. A finder reports up to
   20 candidates. One whose answer ends with (more remain) runs again
   at once, fresh, with its earlier answer files as Already found,
   three runs at most, and after the third the report names it as cut
   short.
3. The second look runs once per slice, as a finder with the second
   look angle. It starts once that slice's finders and the finders of
   the whole range are back, their reruns with them, and its Already
   found is every candidate that names a file of the slice. A look
   never runs again, and one that ends with (more remain) is named in
   the report as cut short.
4. The merge starts when the looks are back. Cut the groups first, as
   step 2 of the round says, and spawn one merger per group, all at
   once, with the merge prompt, each over the candidates that name its
   files, gathered by their File lines into one file in the scratch
   folder, each block headed by the answer file of its run and its C-n,
   since the merger's From line names every candidate that way. Small
   groups share a merger. A merger makes one finding of the candidates
   one fix settles, drops none and never judges whether one is true. It
   grades each finding by what the defect does, per
   [spec/reviews.md](../../spec/reviews.md), and names the group that
   will own it. A Needs line names what its fix needs in a file of
   another group, and a Product line names the other product a claim
   turns on. It puts each finding under one of the five themes every
   review uses, which in their order are correctness, steps that cannot
   be followed, docs against the code or each other, tests and facts
   kept twice, and style and wording. It numbers its findings P-1
   onward.
5. A joiner then reads the claims of the merged lists, with the joiner
   prompt, and names the findings of different groups that are one. A
   joined finding is filed once, in the group whose file holds the
   cause, with the scenarios of both.
6. A finding a merger gave a Product line is checked against that
   product's docs before it is filed, with the product check prompt.
   The sub agent answers whether the claim holds, with the page and the
   words that say so. A claim the docs refute is filed as refuted with
   that reason.
7. File the findings, a batch per theme that holds any, in the order of
   the themes, so a ledger never holds more batches than
   [spec/reviews.md](../../spec/reviews.md) allows. The ledger numbers
   them F-01 onward as they are filed. Each block's heading and its
   File, Type, Theme, Group and Claim lines come out of the mergers'
   answer files through one read only command, which leaves the
   scenarios where they are. The claims go in on standard input inside
   a quoted heredoc, one per line, so the shell never touches a
   backtick or a dollar sign in them, and one call files every claim of
   a batch that shares a grade. Keep one file in the scratch folder
   that maps each F-nn to its group, its P-n and the answer file that
   holds its block, since every later prompt finds a finding's block
   through it. Then commit the paper.

   ```bash
   brain ledger batch 2026-09-feat-billing --theme correctness
   brain ledger add 2026-09-feat-billing - --severity breaks --batch 1 <<'EOF'
   upgrade.py:412 the dirty guard skips ignored files
   upgrade.py:388 the migration rewrites a file git ignores
   EOF
   ```

8. Report with the findings shape, findings first and whole. The
   batches start on the owner's word, so stop there, unless the
   standing word holds, in which case they start on it and the report's
   last line says so. When nothing was found, there is no batch and
   nothing was fixed, so no closing pass is owed. The report says so,
   the ledger closes, and the branch is ready to merge on the owner's
   ask.

## The round of fixes

Every batch that has the owner's word is fixed in one round, and inside
a round the batches have no order. They start in number order. The tool
refuses to start a batch while an earlier one that holds findings is
pending, and the report asks for the pending ones in that order.

1. Record the word on each batch it covers, which starts it.

   ```bash
   brain ledger batch 2026-09-feat-billing 1 --status fixing --ack 2026-09-23
   brain ledger batch 2026-09-feat-billing 2 --status fixing --ack 2026-09-23
   ```

2. Cut the groups. Code files that share a test file, or that need each
   other, are one group with their tests, and findings with a Needs
   line between them make their groups one. A helper the tests share, a
   fixture project among them, belongs to one group like any file. A
   doc is a group of its own, and small docs share one. A group is
   never split, and two fixers never edit one file at the same time, so
   a group of many findings on one file takes one fixer as long as it
   takes, which the review leaves as a limit. A code file's docstrings,
   help strings and comments belong to the group that owns the file,
   and the fixer that changes a behaviour changes those that describe
   it in the same fix.

   Three kinds of finding wait for the last pass, since they follow the
   code and would be done again each time it moved. They are a doc that
   describes code the round changes, a finding on how code is written,
   and a finding on the wording of a comment or a docstring. Every
   other finding starts in the round, a finding on a doc's wording with
   that doc's group.
3. Write the model first where a group's findings are one mechanism,
   such as a parser or a merge. The model says what the code has to do,
   each rule with the purpose it serves. It lists the cases it was held
   against and names what it leaves out as limits, and it promises only
   what the code can keep. Where it imitates another product, the
   product check of step 6 of the finding pass holds its rules against
   that product's docs first. Then a fresh verifier checks the model
   with the model check prompt, the findings' scenarios beside it, and
   the model is written again whole with the check's cases taken in,
   never as points added to the old one. The model with its limits goes
   to the group's fixer and its verifiers, and to the hunters of later
   rounds. A case the model names as a limit is no NEW PROBLEM and no
   candidate, and the limits go into the docs in the last pass. A
   mechanism patched one finding at a time comes back every round.
4. Spawn one fixer per group, all at once, with the fixer prompt. It
   names the files the fixer owns, with the command that runs their
   tests under every interpreter the gates name. It gives each finding
   as its F-nn with its P-n and the answer file that holds its block.
   A fixer reads SYSTEM.md sections 1, 2, 3 and 5 and rule 10.3, and
   sections 6 and 7.5 where its files are docs. For each finding it
   names the cause, lists the sibling cases in the branch's code, greps
   the range for them, writes a failing test, fixes the cause and runs
   the tests of its files. A test that fails for a file it does not own,
   which another fixer may be changing, it names on an Elsewhere line
   and never chases. It answers each finding with one of four results.
   - FIXED, the rule. A finding another group's fix in the tree already
     settles is FIXED too, the Cause naming that fix. A true claim no
     test can drive is fixed, and the fixer says how it checked.
   - REFUTED, where the code as HEAD has it already handles the
     scenario. The fixer may run a test of the scenario to see it pass,
     takes it out again, and quotes the line that handles it, which is
     what the verifier judges.
   - LEFT, where the claim is true and the behaviour is on purpose,
     with the line or the doc that says so.
   - BLOCKED, where the fix is out of its reach, and the Cause says
     which of two holds. The fix needs a mechanism the code does not
     have, or a change in a file the fixer does not own.

   A fixer's answer names every file it made or took away, and it takes
   away only a file of its own list.
5. The verifier of a group starts the moment its fixer returns, with
   the verifier prompt, which carries the paths of the fixer's answer
   file and of the findings' blocks. A group of many findings has
   several verifiers at once, about fifteen findings each, since a
   verifier only reads. It reads what the answer names, and
   `git status` for new files. It judges every test the group's diff
   adds or changes by whether it fails on the code before the fix and
   whether any change to the code could make it fail, and a test's name
   has to say what its body checks. A loosened or deleted test is a NEW
   PROBLEM unless the fixer named the wrong expectation per SYSTEM.md
   1.5. A change of behaviour the finding asked for is no NEW PROBLEM,
   and where a doc describes that behaviour the verifier names the doc
   on a Doc line for the last pass. A failure that comes from a file
   outside the group is named on an Elsewhere line, and neither chased
   nor voted on.
6. A fixer is taken up again only once it has returned and every
   verifier of its group is back, so no verifier reads a file while its
   fixer changes it. It is resumed with the fixer's follow up, which
   carries the answer files of every verifier of the group, and takes
   up each finding whose verdict is not GONE, REFUTED or LEFT. After it
   each verifier that sent a finding back is resumed with the path of
   the fixer's new answer file and the ids of its own share that came
   back, and votes on those alone, so a finding has one verdict. An
   Outside line goes the same way to the fixer of the group that owns
   the file, as a follow up that names the finding it serves. The first
   verifier of that group votes on the change, on a follow up that
   carries the block of the other group's finding with what it asked,
   so a verifier's follow up names the findings it votes on, its own
   that came back and those of other groups. A change in a file no
   group owns makes a group of its own, with a fresh fixer and a fresh
   verifier. A change outside the project, such as in another
   repository, is one no group can make, so its finding is set aside at
   once as step 7 says.
7. A finding that still stands after the third pass, and one answered
   BLOCKED for want of a mechanism, comes to the main session. The
   first fixer finishes its other findings, and its verifiers vote on
   them. The main session writes the model, or writes it again whole
   with the verdicts that stood beside it, has it checked as step 3
   says, and hands every finding of the group still open to one fresh
   fixer, with the group's first prompt whole followed by the model
   brief and the replacement brief. Each finding gets three passes of
   its own with that fixer. What still stands after them is set aside.
   The round goes on without it and its batch stays open. The report
   names it as one that cannot be fixed here and asks for the owner's
   word, as the rule on how a finding lands says. The main session never
   fixes code itself.
8. The groups are quiet when every finding of the round has a last
   verdict of GONE, REFUTED or LEFT, or is set aside. Then run the
   gates on the working tree, before any commit. A red test goes to the
   group that owns the test's file, or, where none does, to the group
   whose file the failure names. A red analyzer, build or doctor goes
   to the group whose file it names. What names no group's file the
   main session reads, and hands to the group whose change it follows,
   since the gates were green before the review and a red one follows a
   change of the round. Either way the failure reaches the fixer as a
   follow up that carries the gate's name and its output. The gates run
   again each time the groups are quiet after a red gate, and nothing
   is committed until they are green.

   Green, each group whose files changed is one commit of its own files
   by path, the ones its fixer made or took away among them, pushed.
   Its hash goes in one call on the fixed findings whose change that
   commit holds. A finding another group's change settled takes the
   hash of the commit that holds that change, and a group whose files
   did not change makes no commit. A refuted finding is set refuted
   with the verifier's reason, and a finding left as it is goes to
   wontfix with its reason. The gates prove the round's last commit. A
   commit before it holds one group's files and is not proven alone,
   which the review leaves as a limit, since an Outside change can sit
   in another group's commit.

   ```bash
   brain ledger set 2026-09-feat-billing F-03 F-04 F-06 status=fixed fix=abc1234
   brain ledger set 2026-09-feat-billing F-05 status=refuted reason="line 212 already guards it"
   brain ledger set 2026-09-feat-billing F-09 status=wontfix reason="the guard is on purpose"
   ```

   Here F-06 is another group's finding, settled by the change that
   commit abc1234 holds.

9. Hunt over the code the round changed. Cut it into slices the way the
   finding pass was cut, from
   `git diff --numstat --no-renames <the commit before the round>..HEAD`
   with the scope's pathspecs, the tests riding along with their code
   and not counted. Spawn one hunter per slice, all at once, fresh, with
   the hunter prompt, and a hunter whose answer ends with (more remain)
   runs again the way a finder does. Hunters look for defects the fixes
   brought in and nothing else. The hunt is narrow on purpose, which the
   review leaves as a limit. It does not look for defects of the kind
   the review found elsewhere in the range, since the fixer lists the
   sibling cases and the verifier checks them, and above low the
   closing pass reads the whole branch again.

   The hunters' candidates are merged and joined like a finder's pool,
   the joiner reading the ledger's findings as well. A candidate that
   repeats an open finding joins it as a sibling case. Every other one
   is filed with `--found-by hunter` into the batch of the finding
   whose fix brought it, one that is a further case of a closed finding
   as a finding of its own, its claim naming the finding it follows. A
   hunt's finding has no theme, so the read only command of the filing
   lifts its Brought by line in place of the Theme, and its batch is
   the batch of the finding that line names. Once the round's ledger
   writes are done, commit the paper. The next round takes the hunt's
   findings with fresh fixers and fresh verifiers, and the rounds repeat
   until a hunt returns nothing.

   ```bash
   brain ledger add 2026-09-feat-billing - --severity bug --batch 1 --found-by hunter <<'EOF'
   upgrade.py:430 a file whose name has a space slips past the guard, a further case of F-03
   EOF
   ```

## The last pass

The last pass follows the hunt that returned nothing, before the
batches close. It is a round with no hunt, over what the rounds of the
owner's word wrote, from the commit before their first round to the
head.

The docs writers take the doc findings that waited, every doc that
describes code the rounds changed, which they find themselves from the
rounds' commits, the docs a verifier named, and the limits of the
models. They read SYSTEM.md sections 6 and 7.5. Between them they own
every doc of the project, the review's own paper aside, so a doc that
lags is never outside their reach, and a docs writer has an Outside
line only for code. The sweep's fixers take the findings on how code
is written, wherever they sit in the range, and every line the rounds
wrote, each owning its group of files. They hold code to SYSTEM.md
section 2 and the prose inside code to sections 6.3 and 7.5. They
change no behaviour and rename nothing that is used outside their own
files. A sweep's fixer answers with one block per finding of its files
and one block for the lines of the rounds.

Each group of the last pass has its verifier and is one commit, like
any group, once the gates are green. The sweep's verifier has a prompt
of its own, which holds each changed line to the rule it names and
checks that no behaviour changed. Nothing hunts what the last pass
wrote, which the review leaves as a limit, and the gates and the
verifiers are its check.

Then the batches of the word are set verified and done, both marks at
once, batch by batch, the findings that waited carrying the last pass's
commits. A batch that holds a finding set aside stays open until that
finding lands. The report's next line may say to verify a batch before
the last pass has run, once its findings are fixed, and the batches
still wait for the last pass. Commit the paper and send one report, for
every batch the word covered, with the round shape. It asks for the
pending batches in number order, or for the closing pass where one is
owed.

```bash
brain ledger set 2026-09-feat-billing F-11 F-12 status=fixed fix=def5678
brain ledger batch 2026-09-feat-billing 1 --status verified
brain ledger batch 2026-09-feat-billing 1 --status done
```

While a batch stays open for a finding that was set aside, the report
asks the owner's word on that finding first. A word to fix it the way
the owner names starts a round like any other. A word that lands it as
deferred or left as it is starts no round, so the main session sets
the finding as the rule on how a finding lands says, closes its batch
and commits the paper. It then reports again in the round shape with
nothing fixed, and that report asks for what comes next or carries the
lines that close the review.

## The closing pass

House rule 7 says which reviews owe a closing pass, the tool holds the
same rule, and the report's next line says when it is due. Once every
batch is done, fresh finders read the whole branch as it stands, the
scope and the slices taken anew, with the angles of the level and no
second look. They get the ledger's findings with their statuses and
reasons as Already found, and with the closing line added to their
prompt they report what the fixes brought in or the review missed, of
any kind. Their candidates are merged and joined like any and filed,
whatever theme a merger gave them, into one batch themed
`closing pass`, which the tool takes only once the report's next line
names the closing pass, and which tells the ledger the pass ran. Then
commit the paper. The batch is reported with the finding pass shape,
findings first like any other, and runs on the owner's word as rounds
of fixes like any other, which end with a last pass of their own. A
pass that found nothing leaves the batch empty and sets it done, which
needs no ack. The empty pass is batch 3 here, after the two batches of
the round above.

```bash
brain ledger batch 2026-09-feat-billing --theme "closing pass"
brain ledger batch 2026-09-feat-billing 3 --status done
```

## Closing the ledger

Once every batch is done, and the closing pass with it where one was
owed, the ledger closes with no word and the paper is committed. The
report then says the branch is ready to merge on the owner's ask, with
the time the review took, which runs from the author date of the commit
that opened the ledger to the close. The author date is the one a
rebase keeps. The PR and the merge wait for the owner's ask whether or
not a standing word holds.

```bash
git log --reverse --format=%ad --date=iso -- '.agents/reviews/2026-09-feat-billing/ledger.md' | head -1
brain ledger close 2026-09-feat-billing
```

## Without sub agents

An agent that cannot spawn sub agents does every step itself, in the
same order, one after another in the same context. It reads each angle
of its level by slice or over the whole branch, as
[references/angles.md](references/angles.md) says, and merges its own
list. It fixes group by group, a failing test before each fix, and
reads each fix and each test it wrote a second time against the claim,
in place of the verifier. One read of the round's diff takes the place
of the hunt, and the last pass follows as written. Refuted and left as
it is stand on that second read. Every report says the review ran
without sub agents, in the line report.md gives it.
