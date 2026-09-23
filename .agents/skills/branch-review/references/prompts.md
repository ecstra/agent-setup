# The prompts

Each prompt is the sub agent's whole task. The parts in angle brackets
are filled in by the main session. Nothing else is added, not the diff
and not the main session's opinion of the branch. Every prompt names one
fetch command to run first as a single Bash call, so the sub agent
spends its turns thinking rather than fetching, and says what to do
when the diff is too long for one call, since the shell pages output
over about 25000 characters.

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

A verdict, returned by a verifier, is one block per candidate or
finding.

```markdown
### C-3
- Verdict: CONFIRMED
- Why: line 307 sets acked_before on every done row, and the empty batch case prints start batch 2
```

Type is breaks, bug, debt or nit. Claim is the defect in one sentence,
Scenario the concrete input or state and the wrong result, Why the line
that decides the verdict, quoted. A sub agent with nothing to return
sends the single line (none).

## The finder

```text
Review scope: the range <base>...<head> in <project root>. The files:
<one file per line from git diff --name-only>
<when git status --porcelain --untracked-files=all lists anything: "Uncommitted work is in scope too. git diff HEAD shows the tracked changes, and read these untracked files whole, since no diff shows them:" followed by their paths>

Run this first, as one Bash call:
git diff <base>...<head> -- <the files>
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

Report every candidate you can name a scenario for. A candidate you
half believe still goes on the list, since a verifier judges it next.
When more than <cap> deserve a scenario, report the <cap> that matter
most and end with the single line (more remain). When this task ends
with blocks under the heading Already found, those are reported
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
batch, and the report then carries the cut short line of
[report.md](report.md) for it.

## The verifier, in the finding pass

```text
Candidates to verify in <project root>, range <base>...<head>, in
<the file, or the files, one per line>:
<the candidate blocks as the finders returned them, with their ids>

Run this first, as one Bash call:
git diff <base>...<head> -- <the files>
When that is too long for one call, read it hunk by hunk with Read on
the file at the lines the candidates name. Then read the enclosing
code with Read and grep through Bash until you can decide each one.

Answer with one block per candidate, in this shape and nothing else:
### <C-n>
- Verdict: <CONFIRMED or PLAUSIBLE or REFUTED>
- Why: <for CONFIRMED the input or state that triggers it and the wrong result, for PLAUSIBLE the real mechanism and what would confirm the trigger, for REFUTED why it is wrong or already guarded, quoting the line that decides it>

Refute only from the code: the line does not say that, an invariant or
a type makes it impossible, this diff already guards it, or it is style
with no observable effect. A rare but reachable path is PLAUSIBLE, not
refuted. A house rule candidate is CONFIRMED when the quoted rule and
the quoted line match. Do not edit anything, do not commit, do not run
the test suite, and do not judge anything outside these candidates.
```

## The hunter

```text
A batch of review findings was just fixed in <project root>, range
<base>...<head>. The findings, one per line:
<F-nn> <file>:<line> <the claim>
The fix commits: <the hashes>.

Run this first, as one Bash call:
git show --stat <the hashes>
git diff <the commit before the batch>..<head> -- <the files the fixes touched>
When that is too long for one call, read it file by file. Then read
with Read and grep through Bash.

Look for two things only: defects of the same kind as these findings
that the review missed anywhere in the range, and defects the fixes
introduced. Return up to 8 candidates as blocks in this shape, numbered
C-1 onward, and nothing else:
### C-1
- File: <file>:<line>
- Type: <breaks or bug or debt or nit>
- Claim: <the defect in one sentence>
- Scenario: <the concrete input or state and the wrong result>
When more than 8 deserve a scenario, report the 8 that matter most and
end with the single line (more remain). When this task ends with blocks
under the heading Already found, those are reported already, so report
only what is not among them. Return the single line (none) when there
is nothing. Do not edit anything, do not commit, do not run the test
suite, and do not widen the scope beyond the range you were given.
```

## The cap resume

Sent to a finder, a sweep or a hunter that stopped at its turn cap
with no report. A report that ends with (more remain) runs the agent
again the way a capped list does, over the files it named unread.

```text
You hit the turn cap. Read nothing more. Report now, from what you have
already read, every candidate you can name a scenario for, in the block
shape the task gave, numbered C-1 onward, or the single line (none).
When files of the scope went unread, name them on one line and end with
the single line (more remain).
```

## The batch verifier

```text
Review findings fixed in <project root>, in <the file, or the files,
one per line>, one finding per line with the commit that fixed it:
<F-nn> <file>:<line> <the claim>, fixed by <hash>

Run this first, as one Bash call:
git show <the hashes> -- <the files>
When that is too long for one call, read it one hash at a time. Then
read the code as it now stands with Read and grep through Bash. You
may run one small snippet against the code on a temporary copy to
reproduce a scenario, never the project's test suite.

Answer with one block per finding, in this shape and nothing else:
### <F-nn>
- Verdict: <GONE or STILL THERE or NEW PROBLEM>
- Why: <for GONE how the code now handles the scenario, for STILL THERE the input or state that still triggers it, for NEW PROBLEM what the fix broke as file:line and the scenario, quoting the line that decides it>
Do not edit, do not commit.
```

## The follow up, sent to a resumed batch verifier

```text
Commit <hash> landed for <F-nn>. Run git show <hash> -- <file> first,
or when that is too long for one call read the file at the changed
lines with Read, re read those lines before voting, and answer in the
same block shape.
```

## The closing finder

The finder prompt, with the review's range read against the branch as
it now stands and this line added after the angle.

```text
The branch was reviewed and its findings fixed. Report only what the
fixes introduced or what the review missed.
```

## The sweep finder

The finder prompt with the sweep angle, and the pooled candidates of
the other angles pasted after it as blocks under the heading "Already
found". The sweep numbers its own candidates from C-1 like any finder,
and the main session renumbers them after the pooled list when it
files them.
