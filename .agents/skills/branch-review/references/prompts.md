# The prompts

Each prompt is sent as written, with the parts in angle brackets filled
in. Every sub agent writes its answer to the file its prompt names and
replies with one line per item.

## The finder

```text
You review one branch of <project root>, the range <base>...<head>, for
one angle. Read the whole diff with `git diff '<base>...<head>'`, then
any file you need to judge it, as much as you need. Read the build spec
at <path to the build spec>, whose Behaviour and Edge cases say what
the branch must do.

Your angle is <the angle, as SKILL.md words it>.

Report a defect only where it has concrete harm, behaviour that breaks
for a user or differs from the spec, data lost, leaked or written
wrong, a security hole, an edge case a real input reaches, or for the
overbuilding angle, code the spec never asked for, dead code or a test
that can never fail. Never report style, wording, naming, layout or
docs. Never report a case no real input reaches. A defect that behaves
the same on <base> is older than the branch, so list it apart under
Older.

Ten findings at most, the worst first. Write each to <answer file> in
this shape.

### C-1
- File: <path>:<line>
- Harm: <breaks, bug or edge>
- Claim: <the defect in one or two plain sentences>
- Scenario: <the input, what the code does, what it should do>

Then a line `Older:` with each older defect as file:line and one
sentence, or `Older: none`. Reply with one line per finding, its id and
its harm.
```

## The verifier

```text
Finders reviewed <project root>, the range <base>...<head>, and their
findings are in <the answer files>. Read each finding, then the code it
names, and decide whether the scenario really happens at <head>.

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
the fix is <the commit range>, which `git diff '<range>'` shows. The
findings it fixed are in the ledger at <ledger path>, F-<n> to F-<m>.

Read the fix diff only, and the code around it as much as you need.
Report two things and nothing else.
- a finding of that list the fix did not settle, with the input that
  still breaks
- a new break the fix brought in, with its scenario

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
it describes. Follow the project's writing rules in .agents/SYSTEM.md
section 6. One fact lives in one place, so link where another doc
holds it. In a project, leave the files the kit writes whole as they
are.

Write to <answer file> one line per doc you changed and what it now
says, then reply with the number of docs changed.
```
