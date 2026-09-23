# The prompts

Each prompt is the sub agent's whole task. The parts in angle brackets
are filled in by the main session. Nothing else is added, not the diff
and not the main session's opinion of the branch. Every prompt names one
fetch command to run first as a single Bash call, so the sub agent
spends its turns thinking rather than fetching, and says what to do
when the diff is too long for one call, since the shell pages output
over about 25000 characters.

## The shapes

A candidate, returned by a finder or a hunter, one block each, numbered
C-1 onward:

```markdown
### C-3
- File: ledger.py:307
- Type: bug
- Claim: next_step counts a done batch as acked without reading the ack cell
- Scenario: batch 1 set done with no ack, batch 2 pending, and the report says start batch 2
```

A verdict, returned by a verifier, one block per candidate or finding:

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
Return the single line (none) when the angle finds nothing. Do not run
the test suite, do not edit anything, do not commit.
```

## The verifier, in the finding pass

```text
Candidates to verify in <project root>, range <base>...<head>, all in
<file>:
<the candidate blocks as the finders returned them, with their ids>

Run this first, as one Bash call:
git diff <base>...<head> -- <file>
Then read the enclosing code with Read and grep through Bash until you
can decide each one.

Answer with one block per candidate, in this shape and nothing else:
### <C-n>
- Verdict: <CONFIRMED or PLAUSIBLE or REFUTED>
- Why: <for CONFIRMED the input or state that triggers it and the wrong result, for PLAUSIBLE the real mechanism and what would confirm the trigger, for REFUTED why it is wrong or already guarded, quoting the line that decides it>

Refute only from the code: the line does not say that, an invariant or
a type makes it impossible, this diff already guards it, or it is style
with no observable effect. A rare but reachable path is PLAUSIBLE, not
refuted. A house rule candidate is CONFIRMED when the quoted rule and
the quoted line match. Do not edit, do not commit, do not run the test
suite.
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
Return the single line (none) when there is nothing. Do not edit, do
not commit, do not run the test suite.
```

## The batch verifier

```text
Review findings fixed in <project root>, all in <file>, one per line
with the commit that fixed it:
<F-nn> <file>:<line> <the claim>, fixed by <hash>

Run this first, as one Bash call:
git show <the hashes>
Then read the code as it now stands with Read and grep through Bash.
You may run one small snippet against the code on a temporary copy to
reproduce a scenario, never the project's test suite.

Answer with one block per finding, in this shape and nothing else:
### <F-nn>
- Verdict: <GONE or STILL THERE or NEW PROBLEM>
- Why: <for GONE how the code now handles the scenario, for STILL THERE the input or state that still triggers it, for NEW PROBLEM what the fix broke as file:line and the scenario, quoting the line that decides it>
Do not edit, do not commit.
```

## The follow up, sent to a resumed batch verifier

```text
Commit <hash> landed for <F-nn>. Run git show <hash> first, re read the
changed lines before voting, and answer in the same block shape.
```

## The closing finder

The finder prompt, with the review's range read against the branch as
it now stands and this line added after the angle:

```text
The branch was reviewed and its findings fixed. Report only what the
fixes introduced or what the review missed.
```

## The sweep finder

The finder prompt with the sweep angle, and the pooled candidates of
the other angles listed after it, one line each, under the heading
"Already found".
