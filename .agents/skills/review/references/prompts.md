# The prompts

Each prompt is the sub agent's whole task. The parts in angle brackets
are filled in by the main session. Nothing else is added, in particular
not the diff, not the main session's opinion of the branch, and not what
another sub agent returned. Every prompt names one fetch command to run
first as a single Bash call, so the sub agent spends its turns thinking
rather than fetching.

The candidate line, returned by finders and hunters:

```text
<file>:<line> | <breaks or bug or debt or nit> | <the defect in one sentence> | <the concrete input or state and the wrong result>
```

## The finder

```text
Review scope: the range <base>...<head> in <project root>. The files:
<one file per line from git diff --name-only>
<when git status --porcelain --untracked-files=all lists anything: "Uncommitted work is in scope too. git diff HEAD shows the tracked changes, and read these untracked files whole, since no diff shows them:" followed by their paths>

Run this first, as one Bash call, before anything else:
git diff <base>...<head> -- <the files>
Then read what you need with Read, Grep and Glob. Read the enclosing
function of every hunk you judge.

Your angle:
<the angle's text from angles.md>

Return up to <cap> candidates, one per line, in this shape and nothing
else, no heading and no prose before or after:
<file>:<line> | <breaks or bug or debt or nit> | <the defect in one sentence> | <the concrete input or state and the wrong result>

Report every candidate you can name a scenario for. A candidate you
half believe still goes on the list, since a verifier judges it next.
Return the single line (none) when the angle finds nothing. Do not run
the test suite, do not edit anything, do not commit.
```

## The verifier, in the finding pass

```text
One candidate defect to verify in <project root>, range <base>...<head>:
<C-n> <file>:<line> | <severity> | <defect> | <scenario>

Run this first, as one Bash call:
git diff <base>...<head> -- <file>
Then read the enclosing code with Read and Grep until you can decide.

Answer with exactly one line, in one of these shapes:
<C-n> | CONFIRMED | <the input or state that triggers it and the wrong result, quoting the line>
<C-n> | PLAUSIBLE | <the mechanism is real, and what would confirm the trigger>
<C-n> | REFUTED | <why it is wrong or already guarded, quoting the line that proves it>

Refute only from the code: the line does not say that, an invariant or
a type makes it impossible, this diff already guards it, or it is style
with no observable effect. A rare but reachable path is PLAUSIBLE, not
refuted. A house rule candidate is CONFIRMED when the quoted rule and
the quoted line match. Do not edit, do not commit.
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
Then read with Read and Grep.

Look for two things only: defects of the same kind as these findings
that the review missed anywhere in the range, and defects the fixes
introduced. Return up to 8 candidates in this shape and nothing else:
<file>:<line> | <breaks or bug or debt or nit> | <the defect in one sentence> | <the concrete input or state and the wrong result>
Return the single line (none) when there is nothing. Do not edit, do
not commit.
```

## The batch verifier

```text
One review finding was fixed in <project root>. The finding:
<F-nn> <file>:<line> | <severity> | <the claim>
The fix: commit <hash>.

Run this first, as one Bash call:
git show <hash>
Then read the code as it now stands with Read and Grep. Run the one
test that covers the finding if there is one, never the whole suite.

Answer with exactly one line, in one of these shapes:
<F-nn> | GONE | <how the code now handles the scenario, quoting the line>
<F-nn> | STILL THERE | <the input or state that still triggers it>
<F-nn> | NEW PROBLEM | <what the fix broke, as file:line and the scenario>
Do not edit, do not commit.
```

## The follow up, sent to a resumed batch verifier

```text
Commit <hash> landed for <F-nn>. Run git show <hash> first, re read the
changed lines before voting, and answer in the same one line shape.
```

## The closing finder

The finder prompt, with the review's range read against the branch as
it now stands and this line added after the angle:

```text
The branch was reviewed and its findings fixed. Report only what the
fixes introduced or what the review missed.
```

## The sweep finder

The finder prompt with the sweep angle, and the verified candidates
listed after it, one per line, under the heading "Already found".
