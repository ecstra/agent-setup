# The prompts

Each prompt below is a sub agent's whole task, and the line above it
says when it is sent. The steps that send them, and the rules every
prompt keeps, are the skill sheet's, [SKILL.md](../SKILL.md). The parts
in angle brackets are filled in by the main session, and nothing else
is added. A path sits inside single quotes, so a single quote in it is
written as `'\''`.

Every prompt and every follow up ends with these lines, which the
sections below leave out.

```text
Put every path you name in a command inside single quotes, and write a
single quote in a path as '\''. Write your blocks to '<the answer file>'
with the Write tool, or with one Bash call and a quoted heredoc where
you have no Write tool, before you answer, and after them every line
this task puts after the blocks. With no block to write, the single
line (none) stands in their place. Your answer is then one line per
block, its id and its <Type or Result or Verdict>, or (none) where
there is no block, and after it every line this task puts after the
blocks, word for word.
```

## The finder

Sent in the finding pass to one finder per slice for an angle that
reads by slice and one over the whole range for an angle that reads
the whole branch, and again, fresh, to a finder whose answer ended
with (more remain).

```text
The review's range is <base>...<head> in <project root>, and its
files are these, one per line:
<the scope's files>

Your slice, the part of the range you judge, one per line:
<the slice's files, a part of a big file as "<file> lines <from> to <to>", or every file of the scope for an angle that reads the whole branch>
A line that names lines of a file gives you those lines, numbered as
HEAD has the file. The rest of the range is other finders', and you
read it only to understand your own.

Run this first, as one Bash call:
<for whole files>
git -C '<project root>' diff --no-renames <base>...<head> -- '<file>' '<file>'
<for a part of a big file, in its place>
git -C '<project root>' diff --no-renames <base>...<head> -- '<file>' | awk -v from=<from> -v to=<to> '/^@@/ { keep = split($3, n, ",") && substr(n[1], 2) + 0 <= to && substr(n[1], 2) + n[2] >= from } keep'
When that is too long for one call, run it for one file at a time,
and a part's command over half its lines at a time. Then read what you
need with Read and grep through Bash, and read the enclosing function
of every hunk you judge. A file the range took away you read from the
diff alone, and a binary file is never read.

Your angle:
<the angle's text from angles.md>
<when earlier blocks exist, "Already found, and reported already, are the candidates in these answer files" and their paths, one per line, and for the second look "that name a file of your slice">

Report every candidate you can name a scenario for, the rare case and
the small one included, and none that is already found. A candidate
you half believe still goes on the list, since the fixer checks every
claim before it changes anything and answers REFUTED where the claim
is wrong. When more than <cap> deserve a scenario, write the <cap>
that matter most and the single line (more remain) after them. Do not
edit anything, do not commit, do not run the test suite, and do not
widen the scope beyond the range you were given.

Write one block per candidate, numbered C-1 onward, in this shape:
### C-1
- File: <the path from the project root>:<line>
- Type: <breaks or bug or debt or nit>
- Claim: <the defect in one sentence>
- Scenario: <the concrete input or state and the wrong result>
```

## The second look

Sent once per slice, as the finder prompt with the second look angle,
when every finder of that slice and of the whole range is back with
all its runs, their answer files under Already found. A look never
runs again.

## The merge

Sent when the looks are back, to one finder per group of files, small
groups sharing one, all at once, over the candidates that name its
files, and again after each hunt over the hunters' candidates.

```text
You merge the candidates the finders of a code review returned for one
group of files, in <project root>, range <base>...<head>. They are in
'<the file>', each block headed by the answer file of the run that
found it and its C-n. Read it whole with Read, in parts where it is
long. Many name the same defect from several angles, and you merge
them into one list of findings. You judge no claim true or false, and
you drop none. Read the code where a rule below needs it.

The rules of the merge:
1. Two candidates are one finding when one fix of one cause settles
   both. A candidate that names a further case of the same cause joins
   the finding, and its case goes into the finding's scenario as a
   sibling case.
2. Two candidates that sit on the same line and have different causes
   stay apart. When in doubt, keep them apart.
3. Every candidate lands in exactly one finding.
4. The type is graded by what the defect does, never by the rule it
   breaks, by the four grades of `.agents/spec/reviews.md`.
5. The group is the file that holds the cause, which is where the fix
   goes and rarely where the defect shows. A test file goes with its
   code file. A finding on a doc names the doc. A finding whose fix
   sits in a code file and also needs a doc changed is the code file's.
6. The theme is one of five, the same for every review, which in their
   order are correctness, steps that cannot be followed, docs against
   the code or each other, tests and facts kept twice, and style and
   wording. After a hunt a finding has no theme, and Brought by names
   the finding whose fix brought the defect in, as the candidates
   merged name it, the one whose fix holds the cause where they differ.
7. Needs names what the fix cannot do without in a file of another
   group, as the file and what it needs there, or none.
8. Product names the other product whose behaviour the claim turns on,
   such as an agent's own permission rules or a parser's, or none.

Write one block per finding, numbered P-1 onward in the order of theme
and then of type from breaks to nit, in this shape:
### P-1
- File: <the path from the project root>:<line>
- Type: <breaks or bug or debt or nit>
- Theme: <the theme, or none after a hunt>
- Brought by: <after a hunt, the F-nn of the finding whose fix brought it in, otherwise none>
- Group: <the file that holds the cause>
- Claim: <the defect in one sentence on one line, named by its cause>
- Scenario: <the input or state and the wrong result, the sibling cases after it, all on one line>
- Needs: <the file of another group and what the fix needs there, or none>
- Product: <the product the claim turns on, or none>
- From: <each candidate merged, as its run's answer file and its C-n>
Edit and commit nothing, and never run the test suite.
```

## The joiner

Sent to one finder when the mergers are back, over all their lists,
and after a hunt with the ledger beside them.

```text
The mergers of a code review in <project root>, range <base>...<head>,
each merged the candidates of one group of files into findings. Their
lists are in these answer files, one per line:
<the mergers' answer files>
<after a hunt, "The ledger at '<the ledger's path>' holds the review's findings so far, open and closed.">

Read the claims, and read the code where you need it. Name the
findings of different lists that are one, when one fix of one cause
settles both. A joined finding is filed once, in the group whose file
holds the cause, with the scenarios of both. When in doubt, keep them
apart. You judge no claim true or false, and you drop none.
<after a hunt, "A finding that repeats an open finding of the ledger joins it as a sibling case. One that is a further case of a closed finding stays a finding of its own and names the finding it follows.">

Write one block per join, numbered J-1 onward, in this shape:
### J-1
- Type: <the grade of the joined finding, by what the defect does, per `.agents/spec/reviews.md`>
- Joins: <each finding it joins, as its merger's answer file and its P-n, or an open finding of the ledger by its F-nn>
- Group: <the file that holds the cause>
- Brought by: <after a hunt, the finding whose fix brought it in, the one whose fix holds the cause where its findings name two, otherwise none>
and one block per finding that follows a closed one, in this shape:
### J-2
- Type: <its grade, as its merger gave it>
- Finding: <its merger's answer file and its P-n>
- Follows: <the closed finding's F-nn>
Edit and commit nothing, and never run the test suite.
```

## The product check

Sent to a general purpose sub agent on Opus, since it needs the web,
for the findings a merger gave a Product before they are filed, and
for a model that imitates another product before its model check.

```text
A code review in <project root>, range <base>...<head>, has claims
that turn on how <the product> behaves. Check each against that
product's own docs on the web, and trust no memory of them.

The claims, one per line:
<a finding as its merger's answer file and its P-n, or a rule of a model as the model's file and the rule's number>

For each, find the page of the product's docs that says how it
behaves on the point the claim turns on.

Write one block per claim in this shape:
### <the answer file's name and the P-n, or the rule's number>
- Verdict: <HOLDS or REFUTED, or SILENT where the docs do not say>
- Why: <the page's address and the words on it that decide the claim, quoted>
Edit nothing, and write no file but your answer file.
```

## The model check

Sent to a fresh verifier each time a model is written, before any
fixer builds to it.

```text
A group of review findings in <project root>, range <base>...<head>,
is one mechanism, and its fix will be built to the model in
'<the model's file>'. Find the cases the model decides wrongly before
any code is written to it.

The findings, one per line, with the answer file and the block that
hold each:
<F-nn '<the answer file>' <P-n>, a joined finding with each P-n it joins>
<when findings of the group still stood after their third pass, "The verdicts that stood are in these answer files" and their paths>

Read the model whole, then the code the findings name and what the
project's docs say it supports, with Read and grep through Bash. Hold
each scenario of the findings, its sibling cases with it, against the
rules, then look for more cases of the kind. A case is yours when a
rule refuses an input or a layout the docs say is supported, when a
rule stated for every kind holds for one, when two rules decide it
differently, or when no rule decides it. A case the model names as a
limit is left out on purpose and the docs will name it, so it is yours
only where it is a scenario of the findings.

Write one block per case, numbered M-1 onward, in this shape:
### M-1
- Verdict: <WRONG where a rule decides it wrongly, CLASH where two rules decide it differently, OPEN where no rule decides it>
- Case: <the input or the layout, and the state it meets>
- Model: <what the model does with it, quoting the rule>
- Right: <what it has to do, and the doc or the line of code that says so>
Edit and commit nothing, and never run the test suite.
```

## The fixer

Sent to one fresh fixer per group of a round, all at once, and to a
fresh fixer for a change in a file no group owns, its findings the
ones the change serves.

```text
You fix one group of review findings in <project root>, on the branch
<branch>, range <base>...<head>. Your findings, one per line, with the
answer file and the block that hold each:
<F-nn '<the answer file>' <P-n>, a joined finding with each P-n it joins>
<for a change in a file no group owns, "The fixer of <F-nn> asked for this change, and its answer is in '<its answer file>'." and its Outside line>

The files you own, one per line, and you edit no other:
<the files>
Other fixers edit other files of this project at the same time. A
change you need in a file you do not own goes into your answer, never
into the file.

Read the blocks of your findings whole before you start. Read too
`.agents/SYSTEM.md` sections 1, 2, 3 and 5 and rule 10.3, sections 6
and 7.5 as well where your files are docs, and section 0 of AGENTS.md
when the project has one. You write by them.

For each finding, in this order:
1. Read the code the claim names and its enclosing function. Name the
   cause, the reason the code does this, which is rarely the line
   where it shows.
2. List the sibling cases, every other input, state or place the same
   cause reaches, and grep the range for the same pattern. A case is
   the finding's when it sits in a function the range changed or in
   code the change made reachable, which this shows:
   git -C '<project root>' diff --no-renames <base>...<head> -- '<the case's file>'
   One outside those that behaves the same on <base> is an older
   defect. Leave it and name it after your blocks, one line each, as
   Older: <file>:<line> <the defect and the input that shows it>
   A sibling case in a file you do not own goes under Outside.
3. Write one test over the scenario and the sibling cases, a table of
   cases where the language has one, and see it fail. Where it passes,
   either the code as HEAD has it already handles the scenario, or a
   change already in the tree settles it, which git diff HEAD shows.
   Keep the test small, since every line you write is read again. Add
   rows to a table the test files already have where one covers the
   function. Build on the helpers and the fixtures that are there,
   and take names and paths from the code's own constants. A case
   that leans on the platform, such as a file mode or a signal,
   carries the skip the file's other tests of that kind carry. Each
   case has to fail on the code as HEAD has it, so a case that passes
   there is left out.
4. Fix the cause, so every case passes. Never special case the
   scenario's own input, and never loosen a test to fit the code. A
   test you change for any reason but a wrong expectation is a
   loosened one, and where the expectation was wrong you name it and
   the right one, per SYSTEM.md 1.5. A docstring or a help string of
   your files that describes the behaviour you change, you change in
   the same fix, and a comment that does so too.
5. Run the tests of your files, once per line, and never the whole
   suite:
   <the command, one line per interpreter the gates name, or "none, since your files are docs">
   A test that fails for a file you do not own, which another fixer
   may be changing at this moment, you never chase. Name it after your
   blocks as
   Elsewhere: <the test> <the file its failure comes from>

Where changes of yours already sit in the tree, as in a later pass or
a second run, see a case fail on a copy of the tree in the scratch
folder, never in a worktree. Make the copy, set the files your fix
changed back to HEAD there, take away there each file it made, run the
case inside the copy, and remove the copy after. The copy's path is
this run's own.
cp -R '<project root>' '<the copy>'
git -C '<the copy>' checkout HEAD -- '<file>' '<file>'
rm -rf '<the copy>'

Each finding lands with one of four Results.
- FIXED, once every case passes. A finding a change already in the
  tree settles, yours or another group's, is FIXED too, and its Cause
  names that change.
- REFUTED, where the code as HEAD has it already handles the scenario.
  You may run a test of the scenario to see it pass, and take it out
  again. The Cause quotes the line that handles it.
- LEFT, where the claim is true and the behaviour is on purpose. The
  Cause quotes the line or the doc that says so.
- BLOCKED, where the fix is out of your reach. It needs a mechanism
  the code does not have and no model of yours names, such as a parser
  or a state machine, or it needs a change in a file you do not own.
  The Cause says which of the two. Stop before you write a mechanism,
  since its model is written before its code.
A true claim no test can drive, a doc's among them, is fixed all the
same, and its Test says how you checked it.

Write one block per finding in this shape:
### <F-nn>
- Result: <FIXED or REFUTED or LEFT or BLOCKED>
- Cause: <for FIXED the cause in one sentence, for REFUTED or LEFT the line or the doc, quoted, for BLOCKED what the fix needs and which of the two it is>
- Cases: <for FIXED the sibling cases the test covers, otherwise none>
- Test: <for FIXED the test's file and name and that it failed before the fix, or for a claim no test drives how you checked it, otherwise none>
- Outside: <a change a file you do not own needs, as the file, what and why, or none>
After the blocks write one line `Outside: <F-nn>` per block whose
Outside is not none, then the Older and the Elsewhere lines, then one
line `Files:` with every file you made or took away, or none. Take
away no file outside your list. Do not commit, do not stash, do not
switch branch, do not make a worktree and do not write the ledger.
```

## The model brief

Put into the fixer prompt after the list of files, for the fixer of a
group that is one mechanism and for the fresh fixer that takes a
group's open findings once its first fixer has finished the others,
each time with the model as written again whole after its check.

```text
The fix is built to the model in '<the model's file>' and to nothing
beside it. Read it first, whole. It holds the rules the code follows,
each with its purpose, and the cases it was held against, and it
names what it leaves out as limits. The mechanism it describes is
yours to build, so answer BLOCKED for want of a mechanism only where a
case needs one the model does not name. Never work around a limit, and
write it into no doc, since the docs writers state the limits in the
last pass.
```

## The replacement brief

Put after the model brief, or after the list of files where there is
none, into the prompt of any fixer's second run after a turn cap, the
docs writer's and the sweep's among them, and into the fixer prompt of
the fresh fixer that takes a group over, since the working tree holds
the earlier changes.

```text
An earlier run worked on this group, and its changes are in the
working tree, uncommitted. Run this before anything else, as one Bash
call:
git -C '<project root>' status --porcelain --untracked-files=all
git -C '<project root>' diff HEAD -- '<file>' '<file>'
When that is too long for one call, run the diff for one file at a
time.
<when it answered, "What it answered, and what its verifier voted, are in these answer files" and their paths>
Build on what is there, and take a change out again where a verdict or
the model shows it wrong. A finding its changes already settle is
FIXED, and its Cause names that change. A file it made counts as one
of your own and goes on your Files line. Each case of a test still has
to fail on the code as HEAD has it.
```

## The verifier

Sent to a fresh verifier when its group's fixer or docs writer
returns, several at once for a group of many findings, each over its
share.

```text
One group of review findings was fixed in <project root>, range
<base>...<head>, and is not yet committed. The group's files, one per
line:
<the files>
The findings you vote on, one per line, with the answer file and the
block that hold each:
<F-nn '<the answer file>' <P-n>, a joined finding with each P-n it joins>
The fixer's answer is in '<the fixer's answer file>'.
<when the group was built to a model, "The fix was built to the model in '<the model's file>', which you read first, whole.">
<for a docs writer's group, "A block with the id Rounds holds the docs the writer brought up to the rounds' code, and GONE on it means each doc it names now says what the code does and states the limits it was handed.">

Run this first, as one Bash call:
git -C '<project root>' status --porcelain --untracked-files=all
git -C '<project root>' diff HEAD -- '<file>' '<file>'
When that is too long for one call, run the diff for one file at a
time. Read whole each new file the fixer's answer names, and each
other new file the status lists that the group's code or tests reach,
since no diff shows them. Then read the code as it now stands with
Read and grep through Bash.

Vote on each finding the fixer answered FIXED, REFUTED or LEFT, and
leave a BLOCKED one out. Judge the bug and not the look of the code.
Read `.agents/SYSTEM.md` 3.1 and 5.2. A fix that hides its symptom by
a move 5.2 names, such as a blanket ignore, leaves the bug in place,
and one that builds a query or a shell command by splicing raw input,
against 3.1, brings a new one, so either is a NEW PROBLEM. For a fixed
finding, ask whether the scenario is gone with its sibling cases, and
whether the test fails without the fix. For a refuted one, ask whether
the line the fixer quoted, as HEAD has it, handles the scenario. For
one left as it is, ask whether the line or the doc the fixer quoted
shows that the behaviour is on purpose. Ask too whether the fix breaks
what the project's docs say it supports, which is a NEW PROBLEM. A
change of behaviour the finding asked for is no NEW PROBLEM, and nor
is a case the model names as a limit. Where a doc describes the
behaviour a finding changed, name the doc after your blocks, one line
each, as
Doc: <the doc> <what it says that no longer holds>

Judge every test the group's diff adds or changes. Ask whether it
fails on the code before the fix, whether any change to the code could
make it fail, and whether its name says what its body checks. A test
loosened or taken away is a NEW PROBLEM unless the fixer names the
expectation it had wrong and the right one, per SYSTEM.md 1.5. A test
that falls short is a NEW PROBLEM on its finding, named by the test.

Never run the project's test suite. You may run one snippet to
reproduce a scenario, and each fixed finding's test once with the fix
taken out, on a copy of the tree in the scratch folder and never in a
worktree. Make the copy, set every file of the group but its tests
back to HEAD there, take away there each file the fixes made, run each
test alone inside the copy, and remove the copy before you answer. The
copy's path is this run's own, since other verifiers of the group may
run beside you.
cp -R '<project root>' '<the copy>'
git -C '<the copy>' checkout HEAD -- '<file>' '<file>'
rm -rf '<the copy>'

A case counts against a finding when it sits in a function the range
changed or in code the change made reachable, which this shows:
git -C '<project root>' diff --no-renames <base>...<head> -- '<the case's file>'
One outside those that behaves the same on <base> is an older defect,
and it never makes a verdict STILL THERE. Name it after your blocks,
one line each, as
Older: <file>:<line> <the defect and the input that shows it>
A failure that comes from a file outside the group, which another
fixer may be changing, you neither chase nor vote on. Name it after
your blocks as
Elsewhere: <the test or the gate> <the file it comes from>

Write one block per finding in this shape:
### <F-nn>
- Verdict: <for FIXED GONE or STILL THERE or NEW PROBLEM, for REFUTED REFUTED or REAL, for LEFT LEFT or REAL>
- Why: <for GONE how the code now handles the scenario and its sibling cases, for STILL THERE the input or state that still triggers it, for NEW PROBLEM what the fix broke as file:line with its scenario or the test and what it lacks, for REFUTED or LEFT what the quoted line or doc decides, for REAL the input or state that shows the claim, each quoting the line that decides it>
Edit nothing in the project, and do not commit.
```

## The fixer's follow up

Sent to the group's fixer, resumed, when its verdicts or a gate send
work back, or when another group's finding needs a change in its
files.

```text
Your group comes back to you.
<when the verifiers voted, "Your verifiers' answers are in these answer files." and the answer file of every verifier of the group, one per line, then "Take up again each finding whose verdict is not GONE, REFUTED or LEFT.">
<when a red gate was handed to your group, "The gate <its name> failed after the round's changes, and this is what it printed." and its output>
<when another group's finding needs a change in a file you own, "<F-nn> of another group needs a change in your files. Its block is <P-n> in '<the answer file>', and its fixer asked for this." and the Outside line>
Go through your steps again for each, the failing test first. Where a
verdict is on a test you wrote, make the test right and see it fail on
the code as HEAD has it. Answer another group's finding under its own
id.
```

## The verifier's follow up

Sent each time the fixer answers again, resumed, to each verifier of
the group that sent a finding back, and to the group's first verifier
for a change the fixer made for another group's finding.

```text
The fixer took the group up again, and its new answer is in
'<the fixer's new answer file>'. The findings you vote on, one per
line, each one of your share that came back or one of another group
the fixer served:
<the F-nn>
<when it served another group's finding, "It made a change for <F-nn> of another group, whose block is <P-n> in '<the answer file>', and whose fixer asked for this." and the Outside line>
Run the first command of your task again, read what the new answer
names, and vote in the same shape on these findings alone.
```

## The hunter

Sent after each round's commits to one fresh hunter per slice of what
the round changed, all at once, and again, fresh, to a hunter whose
answer ended with (more remain).

```text
You hunt after a round of review fixes in <project root>, range
<base>...<head>. The round landed as <the hashes>, after
<the commit before the round>, and the findings it fixed are in the
ledger at '<the ledger's path>', each beside its commit.
<when a group of the round was built to a model, "The models the round built to, each with its limits, are in these files" and their paths>

Your slice of what the round changed, one per line:
<the slice's files, a part of a big file as "<file> lines <from> to <to>">
A line that names lines of a file gives you those lines, numbered as
HEAD has the file. The rest is other hunters', and you read it only to
understand your own.

Run this first, as one Bash call:
<for whole files>
git -C '<project root>' diff --no-renames <the commit before the round>..<head> -- '<file>' '<file>'
<for a part of a big file, in its place>
git -C '<project root>' diff --no-renames <the commit before the round>..<head> -- '<file>' | awk -v from=<from> -v to=<to> '/^@@/ { keep = split($3, n, ",") && substr(n[1], 2) + 0 <= to && substr(n[1], 2) + n[2] >= from } keep'
When that is too long for one call, run it for one file at a time,
and a part's command over half its lines at a time. Then read with
Read and grep through Bash, and read the enclosing function of every
hunk you judge.

Look for one thing only, a defect the fixes brought into the code,
which is behaviour that was right before the round and is wrong after
it, or new code that does the wrong thing with an input it takes. For
each function the round changed, read its callers too, since a fix in
one place breaks another. A defect the code had before the round is
outside the hunt unless the round's change is what makes it reachable,
and so is a case a model or the project's docs name as a limit. The
tests ride along, judged by the verifiers, so read them to learn what
a fix claims and report nothing on them. How code is written, which
is the style of SYSTEM.md section 2, is the last pass's, and so is a
doc that has not yet followed the code. A defect you meet that the
code had before the range, the same on <base>, is no candidate. Name
it after your blocks, one line each, as
Older: <file>:<line> <the defect and the input that shows it>
<when earlier blocks exist, "Already found, and reported already, are the candidates in these answer files" and their paths>

Report none that is already found. Name on each candidate the finding
whose fix brought it in, which the ledger's commits and git log on the
line show. When more than <cap> deserve a scenario, write the <cap>
that matter most and the single line (more remain) after them. Do not
edit anything, do not commit, do not run the test suite, and do not
widen the scope beyond the range you were given.

Write one block per candidate, numbered C-1 onward, in this shape:
### C-1
- File: <the path from the project root>:<line>
- Type: <breaks or bug or debt or nit>
- Claim: <the defect in one sentence>
- Scenario: <the concrete input or state and the wrong result>
- Brought by: <the F-nn of the finding whose fix brought it in>
```

## The docs writer

Sent in the last pass to one fresh fixer per group of docs, all at
once, the groups between them holding every doc of the project but the
review's own paper.

```text
You write the docs of one group after the rounds of a code review in
<project root>, on the branch <branch>, range <base>...<head>. The
rounds landed as <the commit before the first round>..<head>, and
their code is final.

The docs you own, one per line, and you edit no other file:
<the docs>
Other writers own the project's other docs and the sweeps its code,
and they edit them at the same time. A change you need in code goes
into your answer, never into the file.

<when there are any, "The findings, one per line, with the answer file and the block that hold each, which you read first" and the lines>
<when a verifier named a doc of yours, "The Doc lines of these verifiers' answers, each naming a doc a fix made wrong" and their answer files>
<when a model's limits belong in a doc of yours, "The models in these files, whose limits you state as limits in the doc that describes the mechanism" and their paths>
Beside those, every doc of yours that describes code the rounds
changed has to be brought up to that code. Find what the rounds
changed from this, run first as one Bash call, and grep your docs for
the names it touched:
git -C '<project root>' diff --no-renames --stat <the commit before the first round>..<head> -- ':!.agents/reviews' ':!.agents/bugs' ':!.agents/INDEX.md'
When that is too long for one call, run it over one folder at a time.

Read `.agents/SYSTEM.md` sections 6 and 7.5 and rule 10.3 before you
write, and section 0 of AGENTS.md when the project has one. You write
by them. Read the diff of each changed file your docs describe, and
hold every claim of the doc against the code as it now stands. Write
again what the code made false, and add a behaviour the doc should
state and does not, such as a flag or a refusal. A paragraph you
change is wrapped again whole at the width the file uses. Change
nothing the rounds did not reach, and never describe what the code
does not do.

Write one block per finding in this shape:
### <F-nn>
- Result: <FIXED or REFUTED or LEFT, or BLOCKED where the fix needs a change in code>
- Cause: <for FIXED what the doc said wrong, for REFUTED or LEFT the line of the doc or the code that shows it, quoted, for BLOCKED the change the code needs>
- Cases: <for FIXED the other places of your docs the same error sat, otherwise none>
- Test: <what you checked the new text against>
- Outside: <a change the code needs, as the file, what and why, or none>
Where you changed a doc no finding names, write one more block in this
shape:
### Rounds
- Result: FIXED
- Cause: <each doc you changed and what it now says, in short>
- Cases: <each limit you stated and where, or none>
- Test: <what you checked each doc against>
- Outside: <a change the code needs, as the file, what and why, or none>
After the blocks write one line `Outside: <F-nn or Rounds>` per block
whose Outside is not none, then one line `Files:` with every file you
made or took away, or none. Take away no file outside your list. Do
not commit, do not stash, do not switch branch, do not make a worktree
and do not write the ledger.
```

## The sweep

Sent in the last pass to one fresh fixer per group of code files,
beside the docs writers.

```text
You make the style sweep of one group of code files after the rounds
of a code review in <project root>, on the branch <branch>, range
<base>...<head>. The rounds landed as
<the commit before the first round>..<head>, and their code is final.
You hold it to the house style and change no behaviour.

The files you own, one per line, and you edit no other:
<the files>
Other sweeps and the docs writers edit other files at the same time.
<when there are any, "The findings on how code is written in your files, one per line, with the answer file and the block that hold each" and the lines>

Read first `.agents/SYSTEM.md` sections 2, 6.3 and 7.5 and rule 10.3,
and section 0 of AGENTS.md when the project has one. Then run this, as
one Bash call:
git -C '<project root>' diff --no-renames <the commit before the first round>..<head> -- '<file>' '<file>'
When that is too long for one call, run it for one file at a time.

Hold to section 2 the line each finding names and every line that
diff shows as added, and hold the prose inside them, such as a comment
or a help string, to 6.3 and 7.5. Touch no other line. Change no
behaviour and no assertion, and rename nothing that is used outside
your files. A line you cannot hold to its rule without changing
behaviour stays as it is. Run the tests of your files after the sweep,
once per line:
<the command, one line per interpreter the gates name>
A test that fails for a file you do not own you never chase. Name it
after your blocks as
Elsewhere: <the test> <the file its failure comes from>

Write one block per finding in this shape:
### <F-nn>
- Result: <FIXED, REFUTED where the line as HEAD has it already keeps the rule, or LEFT where it cannot change without changing behaviour>
- Cause: <for FIXED the rule and what the line now reads, for REFUTED the line and the rule it keeps, quoted, for LEFT the line, quoted, and the behaviour it keeps>
- Cases: <for FIXED the other lines of the same kind you changed, otherwise none>
- Test: <the tests you ran and that they passed>
- Outside: <a change a file you do not own needs, as the file, what and why, or none>
Then one block for the lines of the rounds, in this shape:
### Rounds
- Result: <FIXED where you changed a line, LEFT where you only left some, REFUTED where every line already kept its rule>
- Cause: <the kinds of line you changed, with a count for each, or none>
- Cases: <each line you left, as file:line and the behaviour it keeps, or none>
- Test: <the tests you ran and that they passed>
- Outside: <a change a file you do not own needs, as the file, what and why, or none>
After the blocks write one line `Outside: <F-nn or Rounds>` per block
whose Outside is not none, then the Elsewhere lines, then one line
`Files:` with every file you made or took away, or none. Take away no
file outside your list. Do not commit, do not stash, do not switch
branch, do not make a worktree and do not write the ledger.
```

## The sweep's verifier

Sent to a fresh verifier when its sweep returns, and resumed with the
verifier's follow up each time the sweep answers again.

```text
One group of code files had its style sweep in <project root>, range
<base>...<head>, and it is not yet committed. The sweep held the lines
the rounds wrote, <the commit before the first round>..<head>, to
`.agents/SYSTEM.md` section 2 and the prose inside them to 6.3 and
7.5, and it may change no behaviour. The group's files, one per line:
<the files>
The findings you vote on, one per line, with the answer file and the
block that hold each, and Rounds for the sweep's own block:
<the lines>
The sweep's answer is in '<its answer file>'.

Run this first, as one Bash call:
git -C '<project root>' status --porcelain --untracked-files=all
git -C '<project root>' diff HEAD -- '<file>' '<file>'
When that is too long for one call, run the diff for one file at a
time. Read in `.agents/SYSTEM.md` the rules the sweep names.

Hold each changed line to the rule it was changed for. Ask whether it
now keeps that rule, and whether the behaviour stayed as it was, each
call getting the values it got before, in the order it got them. A
changed line that keeps no rule, or changes behaviour, is a NEW
PROBLEM on its block. For a block answered FIXED ask whether its lines
now keep the rule, for REFUTED whether they kept it already, and for
LEFT whether the behaviour the sweep names needs the line as it is. Do
not run the test suite, which the gates run.

Write one block per finding and one for Rounds, in this shape:
### <F-nn or Rounds>
- Verdict: <for FIXED GONE or STILL THERE or NEW PROBLEM, for REFUTED REFUTED or REAL, for LEFT LEFT or REAL>
- Why: <the line and the rule that decide it, quoted>
Edit nothing in the project, and do not commit.
```

## The closing finder

Sent where a closing pass is owed, once every batch is done, as the
finder prompt laid out as in the finding pass over the scope and the
slices taken anew, with the angles of the level and no second look,
and with this line after the angle, which hands it the ledger's
findings as found already.

```text
The branch was reviewed and its findings fixed. The ledger at
'<the ledger's path>' holds every finding with its status and its
reason where it has one, and all of them are found already, a refuted
or a wontfix one settled for the reason it gives. Report what the
fixes brought in or the review missed, of any kind.
```
