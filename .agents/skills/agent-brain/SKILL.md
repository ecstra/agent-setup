---
name: agent-brain
description: The one way to read, list, count, file, change, move or check anything in the project's .agents/ brain. Use it to list or count the open entries, show one, file a plan, todo, bug, decision, doc, memory or rule, set the work in hand and mark its steps, run a review ledger, leave the next session's note, retitle a file, or check the brain. Never grep its fields, list its folders or write it by hand.
---

# The brain tool

One command does everything under `.agents/`. It is plain Python with no
dependencies, and it runs from anywhere inside the project through the
launcher in the brain's folder, the same in every shell on every
system, called by its path from the shell's folder, such as
`python3 ../.agents/brain` from a folder one level below the root.

```bash
python3 .agents/brain status
```

The examples below shorten that to `brain`. A kind takes its plural as
well, so `brain list todos` reads as `brain list todo`. Every flag is
listed in [references/commands.md](references/commands.md).

## What the tool holds to

- No brain file is written by hand. `brain new` picks the id, writes the
  header block, puts the file in the right folder and rebuilds the index.
  The header block of an existing file changes through `brain set` and
  `brain refile`, and the rows of a steps table through `brain task`
  and `brain steps`. The prose below and around them is yours to edit,
  and doctor reads the file after. A hook holds all of this in every
  agent that runs hooks, so a new file, an index, a rename, a header
  change or a step row changed by hand is refused. A delete is not,
  and doctor runs after it. A write into the brain through the shell
  is not refused either, and the tick names after it the commands that
  do that work and `brain doctor`, as
  [the nudge](references/commands.md#the-nudge) says.
- Ids only go up. A gap left by a moved or deleted file stays a gap.
- The indexes are generated. `brain index` rebuilds them, doctor rebuilds
  them too, and nobody edits an `INDEX.md`.
- A link in frontmatter is a path relative to `.agents/`, so a file opens
  without a search. `brain refile` carries every link along.
- `brain doctor` is a gate. It exits 0 only when the brain is clean, so
  it runs green before any review.
- The tool's code is never read by hand, save in the kit's own checkout
  where it is the work. SYSTEM.md section 8 carries the rule, and this
  sheet with the reference is what to read instead. In a project Claude
  Code's settings carry the read guard, deny rules that refuse the read
  and two entries under `sandbox.filesystem.allowRead` that let every
  brain command run while Claude Code's sandbox is on. With the sandbox
  on, a shell read such as `cat` of the code gets through and only the
  Read tool is refused, so there the rule holds by your word alone.
  [The read guard](references/commands.md#the-read-guard) says the rest.
- An assertion a test file already holds changes or goes only on the
  owner's word. Outside the kit's own checkout the pre write hook
  refuses an edit that loses one, a test file deleted or moved by a
  patch among them, until the owner gives their word for that file and
  you record it with an end, `brain ack tests <file> --for 1h`. New
  tests, new assertions and the code under test pass.
  [The test guard](references/commands.md#the-test-guard) says which
  files and checks it knows and where it falls short.

## When a session starts

The hook prints `brain status` when a session opens, after the note the
last session left where one waits for it, and under it a line naming
`brain list`, `status` and `show` as the way to read the brain. Every
number in it is counted from the files at that moment, so trust it over
anything remembered. If the hook did not run, run `brain status`, and
where it names a handover waiting,
[the brain's files](#the-brains-files) say whether the note is this
session's and which file holds it. Read that file yourself,
since no command shows it, then do with it what that section says.

```bash
brain status
brain list bugs --open
brain list todo --status open --area auth
brain show BUG-004
brain path BUG-004
brain links DEC-012
```

`show --meta` prints the frontmatter only. `--json` on `status`, `list`,
`links`, `doctor` and `check` gives the same answer for a script, less
the clock and the standing word that `status` opens with.

SYSTEM.md section 8 makes these the way the brain is read for its
fields, its lists and its counts, never a grep of its fields or a
listing of its folders. A word search in its prose and a read of one
entry are fine. After a call that greps the fields an entry's state
lives in, lists a tracker folder or prints several entries at once by
hand, the tick names the command that does the job, as
[the nudge](references/commands.md#the-nudge) says.

## Filing something

The prose goes in on standard input inside a quoted heredoc, which the
shell passes through untouched. The tool writes the structure around it
and refuses anything that breaks its kind's format, such as a missing
heading or a value outside the allowed set.

```bash
brain new bug --title "Token refresh loops after expiry" \
  --description "sign in loops once the refresh token expires" \
  --severity breaks --area auth <<'EOF'
## Problem

After the refresh token expires the sign in screen loops.

## Evidence

The auth log shows refresh, 401, refresh, 401.
EOF
```

The same shape files a todo (`--area`, `--by`), a decision (`--area`),
a memory (`--type project|feedback|reference`), a doc (`--category`),
a build spec (`--branch`) or a review. Each kind's required headings
are in [the reference](references/commands.md#writing), and the tool
names the one that is missing. A rule takes no field of its own and no
category, never the name `rust`, which is the kit's Rust rule's, and
`brain new rule` adds its import to `AGENTS.md`. It loads
only once the session is reloaded, so when the command says so, ask the
owner to reload it. Where it says `AGENTS.md` does not import the rule,
run doctor, which names why.

A plan is a goal with the steps that reach it, and the steps are a
table the tool keeps, on a plan and a build spec always and on a todo
or a bug whose work has steps. `brain new` turns a numbered Steps list
in the prose, each line free to open with the id or the name of the
build spec, todo, bug or review it points at, into that table.
`brain steps <key> add` appends steps as the work teaches them,
`brain steps <key> step <n> done` marks a step that points at nothing,
or one whose pointer reaches nothing the brain can read, a pointed
step follows its entry on its own, and `brain steps <key>` shows the
table with its marks. A plan or
a todo goes done, a build spec closed and a bug fixed only once every
step is done or skipped, while dropped, wontfix and refiled close as
they are, and a closed entry's table is its record, marked no more.

## Changing something

```bash
brain set BUG-004 status=branched
brain set TODO-012 status=done done=2026-09-16
brain refile BUG-004 --title "Token refresh loops on expiry"
```

`set` holds to the lifecycle rules. A bug goes `fixed` only once its Fix
section is written, a todo goes `done` only with a date and a filled
Done when, a build spec goes `closed` or `dropped` only with a date,
and a decision goes `superseded` only when it names what replaced it.
A section that holds nothing but an HTML comment counts as empty.
A set that drops or refiles an entry names each step of an open entry
that now reads skipped since it pointed there, so the plan or the
build spec that lost the step is seen to.

`refile --kind bug` turns a todo into a bug, or the reverse, with the
new body on standard input. Both files stay and link to each other, the
old one marked `refiled` and naming the new one in `became`, so the id
trail holds and every step that pointed at the old one follows it,
save one whose own entry the new one's steps point back at, which
stays on the old one as skipped while the new one is open. It is
refused when a step of the new body would point back, at any remove,
at an open entry that points at the old one.

## The brain's files

Every file opens with the header block the tool writes, `name`, `kind`,
`description`, `updated` and `links`, then its kind's own fields, one
`key: value` line each at the margin, nothing quoted, a list as
`[a, b]`, the name unique and matching the filename, a link a path from
`.agents/`. `SYSTEM.md` has none, and `skills/` follows the Agent
Skills standard. An entry's header also carries `author` and `editor`,
the git names of who filed it and who last changed it through the
tool, as [the reference](references/commands.md#writing) says, beside
the `by` of a todo or a plan, which still says whether the owner asked
for it or the agent raised it. Git ignores `.ack`, the owner's
standing word, `.ack-tests`, the owner's word to change a test file's
assertions, `.conclude`, the conclude word, and `.task`, the current
work, with their writes in flight, `.handover/`, the note for the next
session, and `handover/`, its folder before 2.2.0, `.worktrees/` and
the Python and ruff caches. The rest is
committed, and a closed bug, todo, plan or ledger is never deleted,
since it is the record. Every file
names the file each claim it makes about the code holds in, and stays
terse. An `area`, on a bug, a todo or a decision, is the word already
in use for that part of the project, so the todo index groups by it
and `brain list --area` finds every entry.

- A doc, in a category folder under `docs/`, is durable knowledge with
  no status, one fact in one place. The first docs go in the starting
  folders, `foundation/`, `systems/`, `ops/` and `research/`, and a new
  category folder is made once three docs fit none of those there, a
  lone doc going into the nearest. A change that makes a doc wrong fixes it in the same round,
  and a doc for a removed feature is deleted.
- A memory, in `memory/`, is one lasting project fact no doc owns, never
  a log or a fact about the owner as a person. Its `type` is project,
  feedback for a way of working the owner corrected or confirmed, or
  reference for a pointer outside, its body the fact, why it matters
  and how to apply it. A wrong one is fixed or deleted.
- A rule, in `rules/`, is a durable instruction this project alone
  needs, which every session loads as it starts, never a note, a todo
  or a doc, so rules are written sparingly. It has no status.
  `rules/project.md` is the project's own and always there, and the
  others load after it by name, as
  [the rules](references/commands.md#the-rules) says. In a project
  whose root holds a `Cargo.toml`, `rules/rust.md` is among them, the
  kit's Rust rule, which doctor writes whole from the tool's template
  and nobody edits by hand, so the project's own Rust rules go in a
  rule of its own, as
  [the Rust rule](references/commands.md#the-rust-rule) says.
- A bug, in `bugs/`, is wrong behaviour with evidence, graded `breaks`
  where a user's path fails or loses work, `bug` for a wrong result on
  some input or state, `debt` for what works and costs later, `nit` for
  wording. It goes `open`, `branched` while a branch carries the fix,
  named in the body, then `fixed` once Fix names the cause and the
  commit and Verification says how the fix was proven, `wontfix` with
  its reason under Problem, or `refiled` as a todo. What reproduces it
  goes under Evidence, and `parent`, where set, names the bug or the
  review finding it came from.
- A todo, in `todos/`, is work with a Done when, and work of more than
  one step gets one. One the owner wrote anywhere is filed `--by owner`
  with their words kept under What, cleaned in structure only, and a
  Why of a line or two follows where What leaves the reason out. It goes
  `open`, then `done` with its date and the commits under Done when,
  `dropped` with its date, or `refiled` as a bug. On done, tell the
  owner which of their own notes to tick, by name.
- A decision, in `decisions/`, records why, and never a status or a
  changelog. A new one gives the choice, with the gotcha that forced it
  where one did, under Decision, what it beat and why each lost under
  Alternatives, and what it commits to and forecloses under
  Consequences. It is `standing` until a new one reverses it, then
  `superseded` with `superseded-by` naming the new one.
- A plan, in `plans/`, is a long goal, its Why in the words of whoever
  set it, its steps and a Done when beyond them, and a goal with no
  steps yet means find out. A step row holds its number, what it points
  at, `owner` or `agent` for who set it, and `pending`, `done` or
  `skipped`, and is never renumbered or deleted. It goes `open`, then
  `done` with its date once every step is settled, or `dropped` with
  its date.
- A build spec, in `build-specs/`, is one branch's, filed with
  `--branch` before the code, under Goal, Behaviour, Edge cases, Out of
  scope, Decisions, Proof, Changes and Steps. It goes `draft`, `acked`
  on the owner's word, then `closed` with its date once every step is
  settled, before the PR, or `dropped` with its date. Work that leaves
  it adds a line under Changes, the rest catching up before the review.
- A review ledger is `reviews/<yyyy-mm>-<branch-slug>/ledger.md`, at
  level `quick`, `standard` or `deep`, `open` until every batch is
  done, then `closed`. A ledger from before 2.0.0 keeps its old level
  and its closing pass's batch. Its batches, one per round and five at
  most whatever their theme, an old closing pass's counted with the
  rest, go `pending`, `fixing` on the owner's ack, `verified`, then
  `done`. A finding takes a bug's grades and goes from `open` to
  `fixed` with the commit that holds its change, `refuted` where the
  claim is wrong, `wontfix` where it holds on purpose, or `deferred` on
  the owner's word into a bug that links the ledger, each of the last
  three with its reason.
- The handover note, `.handover/handover.md`, is the one note a session
  leaves for the next. A write replaces the note left on its branch or
  one that names no branch, `no git` or `git could not answer`, and
  refuses any other until `--replace`. A note is for a session on its
  branch, the three just named are for any session, and so is any note
  for a session whose own branch reads `no git` or
  `git could not answer`. The session start hook takes it on every
  start but a fork, renamed `handover.md.reading` while read, then
  removes it, and leaves a note for another branch in place. Without
  the hook, read `handover.md`, or `handover.md.reading` where
  `brain status` says it was read before, then delete it. A session
  that read a note and writes another carries over what of the old one
  still holds, the traps and the rules the owner gave in chat above
  all, since the old one is gone once read. Sessions on one machine
  take turns on the note's lock, so only one of them gets the note and
  none loses one, and a note left in `handover/` before 2.2.0 moves in
  at a start that would take it, as
  [the reference](references/commands.md#the-handover) says.

## A review

```bash
brain ledger open feat/billing --level standard --summary - <<'EOF'
The billing branch, six commits.
EOF
brain ledger batch 2026-09-feat-billing --theme 'round 1'
brain ledger add 2026-09-feat-billing - --severity breaks --batch 1 <<'EOF'
the guard is inverted
checkout fails for a saved card
EOF
brain ledger batch 2026-09-feat-billing 1 --status fixing --ack 2026-09-16
brain ledger set 2026-09-feat-billing F-01 F-02 status=fixed fix=abc1234
brain ledger batch 2026-09-feat-billing 1 --status verified
brain ledger batch 2026-09-feat-billing 1 --status done
brain ledger report 2026-09-feat-billing
brain ledger close 2026-09-feat-billing
```

Findings and batches number themselves, with no more batches than
[the ledger](#the-brains-files) allows, and `set` takes every
finding a commit fixed in one call, the findings first and the
changes after them. A finding the recheck found takes
`--found-by recheck`. A batch that holds findings runs only on the
owner's ack, the word that starts it, given as a date or as `auto`
while the owner's standing word holds, a fourth batch of a review at
quick, standard or deep taking the owner's own dated word alone, since
it is a round past the third. Verification closes a batch,
`report` says where the review stands and what comes next, and `close`
refuses while any finding is still open or the report names a step
before the close. The standing word is
`brain ack on` with an end, by time or by task, `brain ack off` takes
it back, `brain ack` says where it stands, and the reference says what
a second `brain ack on` does and what each refuses.

```bash
brain ack on --for 8h --until-done 2026-10-feat-search
brain ledger batch 2026-10-feat-search 1 --status fixing --ack auto
brain ack off
```

## The conclude word

When the owner names a time to stop, "stop at 17:15", the agent records
it, and every hook line counts down to it. From 15 minutes before, the
line says to wind down, finish the step in hand, start nothing new and
conclude once it is done, clearing the word with `brain conclude off`
after the handover that concludes the session, never after one written
before a compaction, and once the time passes it says to conclude,
stop the sub agents, commit only what passed the gates, save the
working paper, write the handover and stop. The conclude word wins over
the standing word, which covers what the agent may decide and never
how long it works. An hour past the time the line orders nothing, a
handover written past the time clears it, and one written earlier
keeps it.
[The reference](references/commands.md#the-conclude-word) has the rest.

```bash
brain conclude at 17:15
brain conclude in 2h
brain conclude off
```

## The current work

Work of more than one step starts with `brain task on` before the
first step, and SYSTEM.md section 8.3 is the rule for what may go
under what and when a link drops off, `--replace` being the owner's
call. The step the work stands on is the first pending row of the entry's
steps table, `brain task done` marks it done and moves on, `brain task
skip` marks it skipped, `brain task step <n>` reopens one, and
`brain task off` drops the innermost link. The reference says what
each line looks like and what each refuses.

```bash
brain task on kit-phase-7
brain task on TODO-015
brain task done
brain task off
```

## The handover

SYSTEM.md section 8.4 says when a session leaves the note for the next
one and how the note weighs against a compaction's summary,
[the reference](references/commands.md#the-handover) says what the note
holds, the tool's record and the prose on standard input, and
[the brain's files](#the-brains-files) say which session start takes
it. The reference gives every refusal, and `--replace`, which writes
over a note left for another branch, is the owner's call.

```bash
brain handover <<'END_OF_NOTE'
Verified: batch 3 is fixed and its tests pass on both interpreters.
Written, not verified: the docs of the closing round.
Next: the hunt over the round's code, then the last pass.
Traps: the second interpreter's tests run from scripts/ only.
From chat: no PR until the owner asks, ack all until the ledger closes.
END_OF_NOTE
```

A heredoc, quoted or not, ends at the first line that is its word
alone, so the word is one no line of the note is, which rules out `EOF`
once a trap quotes a heredoc of its own.

## Checking the brain and the project

```bash
brain doctor
brain doctor --fix
brain check
brain check README.md docs/guide.md
brain gates
```

Doctor reads the brain against its formats. The check reads the
project's own markdown and the branch's commits against the rules of
SYSTEM.md a machine can judge. In prose that is an em dash, a semicolon
or a colon outside a list item's label, and in a commit a co-author
line or an AI attribution. Code is never the check's, since the
project's own linters judge it. The check reports and never rewrites.
The post write hook runs the check on each file the agent writes, and
`brain new`, `brain refile --kind` and `brain steps add` run it on the
file they write, so a slip is fixed in the same round.

Before the check, the same hook runs the linters the project's rules
name under a Lint heading on each file the agent writes outside
`.agents/`. Under `lint after that write:` it hands back what
they could not fix, each lint line or command it could not run, and a
line when they rewrote the file, which is then read again before the
next edit. It never blocks the write.
[The lint hook](references/commands.md#the-lint-hook) says how a line
is written, what is refused and how long a command may run.

`brain gates` is the one command before a review and before a merge.
It runs the gates the project's rules name, then the check and doctor.
The [reference](references/commands.md#the-check) says which files the
check reads and where it falls short, and
[the gates row](references/commands.md#the-gates) says what makes a
gate, how each runs and what each exit code means.

Doctor reports each defect on its own line, marked `fixable` or `flag`.
`--fix` repairs the mechanical ones, a stale index, a name that
disagrees with its filename, a link written as a name or repeated in
one header, a pointed step's mark that drifted from its entry or its
pointer left on a refiled one or written by name, a numbered list
under a plan's or a todo's Steps and a plan with no Steps section,
which get the table, a chat style copy that drifted from the Claude
Code one, a skill stub that is missing or behind its sheet's header, a
link of any kind, a plain file or a copy of the sheet where a stub
belongs, which the stub replaces, a missing launcher `.agents/brain`,
written from the text the tool holds, the lines below the rules line
of `AGENTS.md` where they leave out a rule, name a file that is none,
repeat a rule, stand out of load order or hold anything but a rule's
import, a merge's conflict markers among them, the kit's Rust rule,
written where the root holds a `Cargo.toml` with its import and the
configs the project lacks, its words written back where they drifted
and the rule retired where Rust is gone, a read guard rule or
sandbox entry missing from `.claude/settings.json`
while `.claude` stays inside the project, an entry's missing `author` or `editor`, which it fills from
git's history, and stamps every file it touches, save one where it
only fills a name. The stubs are real files, so no system needs a link
for them, and a stub's repair that would take away or write over a
step of the brain's own way to its sheet is kept back and named, as
[doctor](references/commands.md#doctor) says. Whatever is left needs a
decision, so read it and act on it. Silencing a finding is never the
answer.

## Bringing a project to the kit

```bash
python3 <kit>/.agents/skills/agent-brain/scripts/brain.py port
python3 <kit>/.agents/skills/agent-brain/scripts/brain.py upgrade
```

Run from the project's root, with `<kit>` a checkout of agent-setup,
and outside Claude Code's sandbox, which refuses every write under
`.claude/agents`. Both refuse before their first write where they
would stop part way, and say why. `port` installs the kit into a
project with no brain and lists what is left to file through
`brain new`. `upgrade` brings an existing brain up to the kit, the old
`.agent/` layout included, migrations first. Both keep the project's
rules, its own hooks and everything it wrote, and end with
`doctor --fix`. The port, and the upgrade from a release
before 3.0.0, move the first section 0 an old front door holds, and
that section alone, into `rules/project.md`, where it runs as it ran
there. Every other word a door held of its own is quoted in
`docs/front-door-words.md`, where nothing loads, gates or lints, the
section 0 too where `project.md` was there already, since the run never
writes into it. When the report names that doc, read it against the
rulebook, write what still holds as a rule, then delete each part and
the doc once it is empty, as
[port and upgrade](references/commands.md#port-and-upgrade) says.
