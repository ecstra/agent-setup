# The prompts

Each prompt is sent as written, with the parts in angle brackets filled
in. Every sub agent writes its answer to the file its prompt names and
replies with one line per item.

Each prompt carries this line too, as section 8 of `SYSTEM.md` asks.

```text
Never read the brain tool's code under .agents/skills/agent-brain/scripts/, so leave that folder out of every diff and every search, as the pathspec ':!.agents/skills/agent-brain/scripts' does for git diff and git grep.
```

## The finder

```text
You review one branch of <project root>, the range <base>...<head>, for
one angle. Read the whole diff with
`git diff '<base>...<head>' -- ':!.agents/reviews' <one ':!path' per other path a commit of the review's paper named>`,
then any file you need to judge it, as much as you need, but never run
the project's whole test suite. Read the build spec at <path to the
build spec>, whose Behaviour and Edge cases say what the branch must
do.

Your angle is <the angle, as SKILL.md words it>.
<for deep's fresh read, "The findings in the ledger at <ledger path> are found already, so report none of them again.">
Never report a defect in these files, which the kit writes whole, <the list SKILL.md gives under What counts as a finding>.

Report a defect only where it has concrete harm, behaviour that breaks
for a user or differs from the spec, data lost, leaked or written
wrong, a security hole, an edge case a real input reaches, or for the
overbuilding angle, code the spec never asked for, dead code or a test
that can never fail. Never report style, wording, naming, layout or
docs. Never report a case no real input reaches. A case outside the
functions the range changed and the code the change made reachable,
which behaves the same on <base>, is older than the branch, so list it
apart under Older. Every other case is the branch's.

Ten findings at most, the worst first. Grade each breaks, bug or debt,
the ledger's own grades, and never nit, since style is never a finding.
Write each to <answer file> in this shape.

### C-1
- File: <path>:<line>
- Grade: <breaks, bug or debt>
- Claim: <the defect in one or two plain sentences>
- Scenario: <the input, what the code does, what it should do>

Then a line `Older:` with each older defect as file:line and one
sentence, or `Older: none`. Reply with one line per finding, its id and
its grade.
```

## The verifier

```text
Finders reviewed <project root>, the range <base>...<head>, and their
findings are in <the answer files>. Read each finding, then the code it
names, and decide whether the scenario really happens at <head>. Never
run the project's whole test suite.

Vote REAL where the code does what the claim says and the harm is
concrete. Vote NOT REAL where a line of the code shows it does not
happen, or the harm is style, wording or a case no real input reaches.
Two findings that one fix settles are the same, so say which.

Write one block per finding to <answer file>.

### <answer file name> C-<n>
- Vote: <REAL or NOT REAL>
- Why: <the line of code that decides it, as file:line>
- Same as: <the other finding it repeats, or none>

Reply with one line per finding, its name and its vote.
```

## The recheck

```text
The main agent fixed the findings of a review of <project root>, and
the fix is the commit <hash>, which `git show '<hash>'` shows. The
findings it fixed are in the ledger at <ledger path>, F-<n> to F-<m>.

Read the fix diff only, and the code around it as much as you need,
but never run the project's whole test suite. Report three things and
nothing else.
- a finding of that list the fix did not settle, with the input that
  still breaks
- a new break the fix brought in, with its scenario
- a fix that loosened or deleted a test, swallowed an error, hardcoded
  an answer or special cased the one input named

Never report style, docs, or a defect the fix did not touch. Write each
item to <answer file> in the finder's block shape, then reply with one
line per item, or `none`.
```

## The docs agent

```text
A branch of <project root>, the range <base>...<head>, changed code that
docs describe. Bring every doc of the project that the branch made
false up to the code, and add what a reader needs that no doc says,
such as a new command, flag or refusal. Read the build spec at <path>,
whose Changes say where the work left the plan.

Edit docs only, never code. Check each fact you write against the code
it describes. Follow .agents/SYSTEM.md sections 6 and 8.1, and the
project's rules in .agents/rules/. A file under .agents/ that
you change takes `updated=<today's date>` through `brain set` with the
file's name. One fact lives in one place, so link where another doc
holds it. Never edit a record, which is a decision, a bug, a memory or
a review ledger, nor the review's own paper, <each path a commit of
the paper named>, nor the files the kit writes whole,
<the list SKILL.md gives under What counts as a finding>.

Write to <answer file> one line per doc you changed and what it now
says, then reply with the number of docs changed.
```
