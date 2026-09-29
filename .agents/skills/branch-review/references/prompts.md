# The prompts

Each prompt is the sub agent's whole task. The parts in angle brackets
are filled in by the main session. Nothing else is added, not the diff
and not the main session's opinion of the branch. Every prompt names one
fetch command to run first as a single Bash call, so the sub agent
spends its turns thinking rather than fetching, and says what to do
when the diff is too long for one call, since the shell pages output
over about 25000 characters.

A prompt longer than a few lines is written to a file in the review's
scratch folder, outside the repository, and the sub agent is handed
one line, that its whole task is in that file and to read it first.
Blocks a prompt carries, the candidates already found or a group's
findings, are put into that file from the files the reports were
saved to, so the main session never retypes them.

## The shapes

A candidate, returned by a finder or a hunter, is one block, numbered
C-1 onward.

```markdown
### C-3
- File: ledger.py:307
- Type: bug
- Claim: next_step counts a done batch as acked without reading the ack cell
- Scenario: batch 1 set done with no ack, batch 2 pending, and the report says start batch 2
```

A fix, returned by a fixer, is one block per finding.

```markdown
### F-07
- Result: FIXED
- Cause: next_step reads a row's status and never its ack cell, so every done row counts as acked
- Cases: a done batch with no ack, a verified one with no ack, a done one whose ack is a stamp from a word since ended
- Test: tests/test_ledger.py, test_a_done_batch_with_no_ack_is_asked_for_one, failed before the fix
- Outside: none
```

A verdict, returned by a verifier, is one block per finding.

```markdown
### F-07
- Verdict: GONE
- Why: line 307 now reads the ack cell before it counts the row, and the three cases of the test each reach that line
```

Type is breaks, bug, debt or nit. Claim is the defect in one sentence,
Scenario the concrete input or state and the wrong result, Cause the
reason the code does it, Why the line that decides the verdict, quoted.
A sub agent with nothing to return sends the single line (none).

## The finder

```text
Review scope: the range <base>...<head> in <project root>. The files:
<one file per line from git diff --name-only>
<when git status --porcelain --untracked-files=all lists anything: "Uncommitted work is in scope too. git diff HEAD shows the tracked changes, and read these untracked files whole, since no diff shows them:" followed by their paths>

Your slice, the part of the range you judge:
<the slice's lines as brain slices printed them, or "the whole range" for an angle that reads the whole branch>
A line that names lines of a file gives you that part of the file. The
rest of the range is another finder's, and you read it only to
understand your own.

Run this first, as one Bash call:
git diff <base>...<head> -- <the slice's files>
When that is too long for one call, read it file by file with
git diff <base>...<head> -- <one file>. Then read what you need with
Read and grep through Bash, and read the enclosing function of every
hunk you judge.

Your angle:
<the angle's text from angles.md>

Return up to <cap> candidates as blocks in this shape, numbered C-1
onward, and nothing else before or after:
### C-1
- File: <file>:<line>
- Type: <breaks or bug or debt or nit>
- Claim: <the defect in one sentence>
- Scenario: <the concrete input or state and the wrong result>

Report every candidate you can name a scenario for, the rare case and
the small one included. A candidate you half believe still goes on the
list, since a fixer proves it with a failing test before anything is
changed. When more than <cap> deserve a scenario, report the <cap> that
matter most and end with the single line (more remain). When this task
ends with blocks under the heading Already found, those are reported
already, so report only what is not among them. Return the single line
(none) when the angle finds nothing. Do not edit anything, do not
commit, do not run the test suite, and do not widen the scope beyond
the range you were given.
```

A finder or a hunter that ends with (more remain) is spawned again,
fresh, with the same prompt and every block reported so far by every
run of it pasted under the heading "Already found". When the line
followed a cap resume, the files the run named unread are the file
list of the next run. The runs stop when one returns without that
line, or at three runs of a finder in a pass or of a hunter in a
round, and the report then carries the cut short line of
[report.md](report.md) for it.

## The second look

The finder prompt with the second look angle and the slice the look is
for, and the candidates of that slice's own finders after it as blocks
under the heading "Already found", never the whole pool, which costs
the look its time. It numbers its own candidates from C-1 like any
finder.

## The merge

```text
The finders of a code review returned their candidates, and many name
the same defect from several angles. Merge them into one list of
findings. You judge nothing else: you do not decide whether a
candidate is true, and you drop none.

The review's range is <base>...<head> in <project root>.

Run this first, as one Bash call:
cat <the scratch folder's pool files>
When that is too long for one call, read the files one by one with
Read. Each file is one finder's run, named for its angle and its
slice, and holds blocks numbered C-1 onward. Read the code only where
two candidates cannot be told apart without it.

The rules of the merge:
1. Two candidates are one finding when one fix of one cause settles
   both. A candidate that names a further case of the same cause joins
   the finding, and its case goes into the finding's scenario as a
   sibling case.
2. Two candidates that sit on the same line and have different causes
   stay apart. When in doubt, keep them apart.
3. Every candidate lands in exactly one finding.
4. The type is graded by what the defect does, never by the rule it
   breaks, per spec/reviews.md.
5. The group is the code file whose fixer will own the finding. A test
   file goes with its code file. A doc is its own group. A finding
   whose fix sits in a code file and also needs a doc changed belongs
   to the code file's group. A finding that is only about how code is
   written, a call by position, a name, a comment that restates the
   line, has the group style.
6. The theme is one of at most five themes you choose for the whole
   list, by kind, in the order they would be fixed, correctness first
   and nits last.
7. Needs names what the fix cannot do without in a file of another
   group, as the file and the function, or none.

Answer with the themes on the first lines, one per line as
"Theme 1: <name>", then one block per finding, in this shape, numbered
P-1 onward in the order of theme, then type from breaks to nit, then
group, and nothing else before or after:
### P-1
- File: <the path from the repository root>:<line>
- Type: <breaks or bug or debt or nit>
- Theme: <the theme's number>
- Group: <the code file or the doc that owns it, or style>
- Claim: <the defect in one sentence on one line, named by its cause>
- Scenario: <the input or state and the wrong result, the sibling cases after it, all on one line>
- Needs: <the file and the function of another group, or none>
- From: <the candidates merged, as the file's name and the id>
Do not edit anything, do not commit, do not run the test suite.
```

After a hunt the same prompt merges the hunters' reports. The themes
are the ledger's own, given by number in place of rule 6, and the
findings the rounds already closed are handed over as a file, so a
candidate that is a further case of one says which on a line
`- Joins: <F-nn or none>` after Needs.

## The placing

```text
A code review merged its finders' candidates into a list of findings,
and the second look returned more candidates. Place each of them: it
either joins a finding of the list, or it is a finding of its own. You
judge nothing else, and you drop none.

Run this first, as one Bash call:
cat <the file the merged list was saved to>
Then read the look's candidates in <the files they were saved to>.

A candidate joins a finding when one fix of one cause settles both.
One with a cause no finding of the list has is a finding of its own,
and when in doubt it is its own. Type, group and theme are given as
the merge gives them, the theme one of the list's own.

Answer with one block per candidate and nothing else. For one that
joins:
### <the look file's name> <C-n>
- Joins: <P-n>
- Case: <the further case it adds, on one line>
For one that is its own, the merge's block shape under the same
heading, without its From line.
Do not edit anything, do not commit, do not run the test suite.
```

## The fixer

```text
You fix one group of review findings in <project root>, on the branch
<branch>, range <base>...<head>. One block per finding:
### <F-nn>
- File: <file>:<line>
- Type: <breaks or bug or debt or nit>
- Claim: <the claim>
- Scenario: <the scenario>

The files you own, and you edit no other:
<one per line, the code files and their test files>
Other fixers edit other files of this project at the same time. A
change you need in a file you do not own goes into your answer, never
into the file.

Read first `.agents/SYSTEM.md` sections 1, 2, 3 and 5, and section 0
of AGENTS.md when the project has one. You write by them.

For each finding, in this order:
1. Read the code the claim names and its enclosing function. Name the
   cause, the reason the code does this, which is rarely the line
   where it shows.
2. List the sibling cases, every other input, state or place the same
   cause reaches, and grep your files for the same pattern.
3. Write one test over the scenario and the sibling cases, a table of
   cases where the language has one, and see it fail. A claim whose
   test cannot be made to fail is refuted, so answer REFUTED and
   change nothing for it. A finding no test can show, a doc or a rule,
   is checked against the code or the rule it quotes.
4. Fix the cause, so every case passes. Never special case the
   scenario's own input, and never loosen a test to fit the code.
5. Run the tests of your files, once per line, and never the whole
   suite:
   <the command, one line per interpreter the gates name>

When a fix needs a mechanism the code does not have, a parser, a
mapping between two worlds, a state machine, stop before writing it
and answer BLOCKED with what it has to do, since its model is written
before its code.

A sibling case is the finding's when the range changed the code it
sits in or made it reachable. One you meet in code the range never
touched, which behaves the same on <base>, is an older defect. Leave
it as it is and name it after your blocks, one line each, as
Older: <file>:<line> <the defect and the input that shows it>.

Answer with one block per finding, in this shape and nothing else:
### <F-nn>
- Result: <FIXED or REFUTED or BLOCKED>
- Cause: <for FIXED the cause in one sentence, for REFUTED the line that makes the claim wrong, quoted, for BLOCKED what the fix needs>
- Cases: <for FIXED the sibling cases the test covers, otherwise none>
- Test: <for FIXED the test's file and name and that it failed before the fix, for a doc or a rule what you checked it against, otherwise none>
- Outside: <a change a file you do not own needs, as file, what and why, or none>
Do not commit, do not stash, do not switch branch, do not write the
ledger, and do not delete a file or a folder you did not make.
```

A group that another group needs something from, or that needs
something itself, gets these lines after the list of files, from the
Needs lines of the merge.

```text
Built against, at the same time as you, by the fixer of <the other group>:
<the function's name, its parameters with their types, what it returns and what it raises>
<"You write it." or "You call it and never write it. Until it lands your tests of it fail, which you name under Outside.">
```

## The fixer's follow up, sent to a resumed fixer

```text
The verifier read your fixes. These still stand, one block each:
<the verifier's blocks that say STILL THERE, NEW PROBLEM or REAL>
<when the gates named a test of the group: "The gates failed on this test of your files:" and the test's name with the first lines of its failure>
<when another group needs a change in a file you own: "Another fixer needs this in your files:" and its Outside lines>

Go through the same five steps for each, the failing test first, and
answer in the same block shape.
```

## The verifier

```text
One group of review findings was just fixed in <project root>, range
<base>...<head>, and not yet committed. The group's files:
<one per line>
One line per finding, with the fixer's answer:
<F-nn> <file>:<line> <the claim>. Scenario: <the scenario>. Fixer: <FIXED, the cause and the cases, or REFUTED, the line it quoted>

Run this first, as one Bash call:
git status --porcelain --untracked-files=all -- <the files>
git diff HEAD -- <the files>
When that is too long for one call, read it file by file, and read an
untracked file whole, since no diff shows it. Then read the code as it
now stands with Read and grep through Bash. You may run one small
snippet against the code on a temporary copy to reproduce a scenario,
never the project's test suite.

Judge the bug and not the look of the code. For a fixed finding, ask
whether the scenario is gone, whether the sibling cases are gone with
it, and whether the test would fail without the fix. For a refuted
one, ask whether the line the fixer quoted makes the scenario
impossible. Ask too whether the fix refuses or changes what the
project's docs say it supports, which is a NEW PROBLEM.

A case counts against a finding when the range changed the code it
sits in or made it reachable. One in code the range never touched,
which behaves the same on <base>, is an older defect. It never makes a
verdict STILL THERE. Name it after your blocks, one line each, as
Older: <file>:<line> <the defect and the input that shows it>.

Answer with one block per finding, in this shape and nothing else:
### <F-nn>
- Verdict: <for a fixed finding GONE or STILL THERE or NEW PROBLEM, for a refuted one REFUTED or REAL>
- Why: <for GONE how the code now handles the scenario and its sibling cases, for STILL THERE the input or state that still triggers it, for NEW PROBLEM what the fix broke as file:line and the scenario, for REFUTED the line that makes the claim wrong, for REAL the input or state that triggers the claim, quoting the line that decides it>
Do not edit, do not commit.
```

## The follow up, sent to a resumed verifier

```text
The fixer changed <the files> again for <F-nn>. Run
git diff HEAD -- <the files> first, or when that is too long for one
call read each file at the changed lines with Read, re read those
lines before voting, and answer in the same block shape.
```

## The hunter

```text
A round of review fixes just landed in <project root>, range
<base>...<head>. The findings it fixed, one per line:
<F-nn> <file>:<line> <the claim>
The round's commits: <the hashes>.

Your slice of what the round changed:
<the slice's lines as brain slices printed them>

Run this first, as one Bash call:
git diff <the commit before the round>..<head> -- <the slice's files>
When that is too long for one call, read it file by file. Then read
with Read and grep through Bash, and read the enclosing function of
every hunk you judge.

Look for two things only: defects the fixes introduced, and defects of
the same kind as these findings in the code the round touched. A
defect the code had before the range, the same on <base>, is outside
the hunt unless the round's change is what makes it reachable, and so
is a limit the project's docs name. How code is written, and a doc
that has not yet followed the code, are the last pass's and no
candidate of yours. Return up to 20 candidates as blocks in this
shape, numbered C-1 onward, and nothing else:
### C-1
- File: <file>:<line>
- Type: <breaks or bug or debt or nit>
- Claim: <the defect in one sentence>
- Scenario: <the concrete input or state and the wrong result>
When more than 20 deserve a scenario, report the 20 that matter most
and end with the single line (more remain). When this task ends with
blocks under the heading Already found, those are reported already, so
report only what is not among them. Return the single line (none) when
there is nothing. Do not edit anything, do not commit, do not run the
test suite, and do not widen the scope beyond the range you were
given.
```

## The cap resume

Sent to a finder or a hunter that stopped at its turn cap with no
report. A report that ends with (more remain) runs the agent again the
way a capped list does, over the files it named unread.

```text
You hit the turn cap. Read nothing more. Report now, from what you have
already read, every candidate you can name a scenario for, in the block
shape the task gave, numbered C-1 onward, or the single line (none).
When files of the scope went unread, name them on one line and end with
the single line (more remain).
```

## The replacement brief

A sub agent past about 250k tokens of context is not resumed again. A
fresh fixer gets the fixer prompt with the findings still open in the
group, and these lines after the list of files. A fresh verifier gets
the verifier prompt as it is, since the working tree tells it the
rest.

```text
An earlier fixer worked on this group and its changes are in the
working tree, uncommitted. Run git diff HEAD -- <the files> before
anything else and build on what is there. What it tried for the
findings above, and what the verifier answered:
<per finding, the fixer's last block and the verifier's last block>
```

## The model brief

Where a group is one mechanism, when a group comes to the main session
after three rounds, or when a fixer answered BLOCKED, the main session
writes the model and hands it to a fresh fixer as the fixer prompt
with these lines after the list of files. A model that comes back is
written again whole, never as points added to the old one.

```text
The fix follows this model and nothing beside it:
<what the code has to do for every case of the kind, as rules, each with the purpose it serves>
The cases it was held against:
<one per line, the layouts the project's docs say they support among them, each with what the code does for it>
What it does not cover, which you state in the docs you own as a limit
and never work around:
<the cases left out, or none>
```

## The model check

Sent to a fresh verifier before any fixer builds to a model.

```text
A group of review findings in <project root>, range <base>...<head>,
is one mechanism, and its fix will be built to the model below. Find
what the model gets wrong before any code is written to it.

The findings, one per line:
<F-nn> <file>:<line> <the claim>
The model:
<the model brief's lines>

Read the code the findings name and the project's docs on what it
supports, with Read and grep through Bash. Where the model imitates
another product, a parser or an agent's own rules, hold it against
that product's docs. Then look for a case the model decides wrongly:
an input or a layout the docs say is supported that a rule refuses, a
case two rules decide differently, a case no rule decides, a rule
stated for every kind where it holds for one.

Answer with one block per case, numbered M-1 onward, and nothing else,
or the single line (none):
### M-1
- Case: <the input, state or layout>
- Model: <what the model does with it, quoting the rule>
- Right: <what it has to do, and the doc or the line of code that says so>
Do not edit, do not commit, do not run the test suite.
```

## The last pass

The docs group of the last pass gets the fixer prompt over the docs
that describe what the rounds changed, with the commits of the rounds
to read first. The style sweep gets this prompt, one fixer per file
group, and its verifier the verifier prompt with the rules in place of
scenarios.

```text
You make one style sweep in <project root>, on the branch <branch>.
Rounds of review fixes landed as <the commit before the first
round>..<head>, and their code is final. You hold the lines they wrote
to the house style, and you change no behaviour.

The ledger's findings on how code is written, one per line:
<F-nn> <file>:<line> <the claim>

The files you own, and you edit no other:
<one per line>

Read first `.agents/SYSTEM.md` section 2, and section 0 of AGENTS.md
when the project has one. Then run this, as one Bash call, and work
only on the lines it shows as added:
git diff <the commit before the first round>..<head> -- <the files>

Hold every added line to those rules, and no line the rounds did not
write. No assertion, no expected value, no message and no behaviour
changes. A line you cannot hold to a rule without changing behaviour
is named in your answer and left. Run the tests of your files after
the sweep, once per line:
<the command, one line per interpreter the gates name>

Answer with one block per finding in the fixer's shape, Cause holding
the kinds of line you changed with a count for each.
Do not commit, do not stash, do not switch branch, do not write the
ledger, and do not delete a file or a folder you did not make.
```

## The closing finder

The finder prompt, with the review's range read against the branch as
it now stands and this line added after the angle.

```text
The branch was reviewed and its findings fixed. Report only what the
fixes introduced or what the review missed.
```
