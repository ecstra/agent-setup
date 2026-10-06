# Every command and flag

All of them run as `python3 .agents/skills/agent-brain/scripts/brain.py`,
shortened here to `brain`. A command exits 0 when done, 1 when refused,
with the reason on standard error, and 2 when doctor still has findings.
A write that landed its entry and then lost a second write, a step
cell, a step's pointer or the chain, exits 0 with that failure on
standard error, since the command did its work and doctor reports what
is left, while an index rebuild that fails exits 1 like any refusal,
the entry written all the same.

## Reading

| Command | What it answers |
|---|---|
| `brain version` | The kit version this project carries, from `.agents/VERSION`. |
| `brain status [--json]` | The clock, the standing word and the current work first, then version, doctor health, counts per tracker, open reviews, the note waiting for the next session with the branch it was written on and when, unreadable files. A claimed note a session start could not remove, `handover/handover.md.reading`, is the note waiting while none sits at `handover/handover.md`, and its line says it was read before. The JSON form carries all of that but the clock and the word. The note is under `handover`, null when none waits, else its `branch` and its `written` moment, the first null where the header names none and the second where the header gives none in the one ISO shape the tool writes a moment in, with `again` beside them, true for a note read before. The chain is under `task`, which is null when the file does not read as a chain. The `latest_handover` key and the `handover` count of 1.4.0 are gone. |
| `brain ack` | The clock and where the owner's standing word to proceed stands, off, held, or on with what is left of it and what ends it. |
| `brain list <kind> [--status X] [--severity X] [--area X] [--by X] [--type X] [--branch X] [--date X] [--json]` | One line per entry of that kind, narrowed by any field. The kinds are bug, decision, doc, memory, plan, review and todo. |
| `brain show <key> [--meta]` | The whole file, or with `--meta` its frontmatter only. |
| `brain path <key>` | The absolute path behind a key. |
| `brain links <key> [--json]` | What the entry links to, and every entry that links to it. |

A `<key>` is an id such as `BUG-004`, a name such as
`stripe-retries-twice`, or a path. A path is written from the brain,
such as `docs/systems/login.md`, or from the project's root, such as
`.agents/docs/systems/login.md`. A longer path is a key only when what
stands in front of the brain's folder leads to this brain, which is an
absolute path to this project's own folder, a path that lands in this
brain when read from the current folder, or the path git prints from a
top above the project, such as `apps/web/.agents/docs/systems/login.md`
for a project in `apps/web`, whose folders in front are the last
folders of the project's own path. A path into another project's brain
answers nothing. Every command that takes a key reads it this way.

## Writing

| Command | What it does |
|---|---|
| `brain new <kind> --title T --description D [fields] [--category C] [--link P]...` | Files a new entry. Prose on standard input. `--category` places a doc in a folder under `docs/`. `--link` repeats, takes a path, an id or a name, and is refused when it reaches nothing inside `.agents/`, a path into `handover/` included, since no link goes into the folder whose one note is read once. |
| `brain set <key> field=value ...` | Changes fields, checks values and dates, applies the lifecycle rules, stamps `updated`. |
| `brain refile <key> --title T` | Renames for a new title. The id stays, every link follows. |
| `brain refile <key> --kind bug\|todo --description D [fields]` | Turns a todo into a bug or the reverse, new body on standard input. Both files stay, linked both ways, the old one marked `refiled` with the new one's id in `became`, which every step that pointed at the old one follows, save a step whose own entry the new one's steps point back at, which stays on the old one as skipped while the new one is open and follows once it closes. Refused when a step of the new body points at the old entry, or at an open entry whose steps point back at it at any remove, since the new entry takes the old one's pointers over. |
| `brain index` | Rebuilds every `INDEX.md` and prints the ones that changed. |

Fields by kind, all passed as flags to `new` or as `field=value` to `set`.

- bug: `--severity breaks|bug|debt|nit` and `--area` required. `status`
  is open, branched, fixed, wontfix or refiled, `reported` defaults to
  today, `parent` optional, `became` the id of the todo a refiled bug
  was filed as, which the refile writes and `set` takes only on a
  refiled entry when it names one todo the brain knows.
- todo: `--by owner|agent` and `--area` required. `status` is open,
  done, dropped or refiled, `born` defaults to today, `done` is the
  closing date, `became` the id of the bug a refiled todo was filed
  as, held to the same rule.
- plan: `--by owner|agent`, owner unless said otherwise. `status` is
  open, done or dropped, `born` defaults to today, `done` is the
  closing date.
- decision: `--area` required. `status` is standing or superseded,
  `date` defaults to today, `superseded-by` names the successor.
- memory: `--type project|feedback|reference` required.
- review: `--branch` required. `status` is open or closed. Prefer
  `brain ledger open`, which writes the body shape too.
- doc: no extra fields.

The body must carry its kind's required headings. A plan carries `Why`
and `Done when`, with `Steps` added by the tool when the prose has
none, a bug `Problem` and `Evidence`, a todo `What` and `Done when`, a
decision `Decision`, and a review `Summary`, `Batches` and `Findings`.
An empty standard input writes the headings and nothing else, for
filling in afterwards, a plan aside, which is filed from its prose or
not at all.

## The standing word

The owner's ack is the word to proceed with what the agent proposed
next. Said once as "auto ack" with an end, it stands until that end,
and the agent passes the review's gates that normally wait for it,
house rule 6 names them, saying in each report that it did. It never
starts a review, never opens a PR or merges, since those stay on the
owner's ask, and never passes a gate the rulebook or section 0 holds
for a person.

| Command | What it does |
|---|---|
| `brain ack on --for 8h` | Records the word for a duration, in minutes, hours or days, such as 90m, 8h or 2d. |
| `brain ack on --until "tomorrow 22:00"` | Records it until a moment, a time today, which means tomorrow when it has passed, `today HH:MM`, which never rolls over, `tomorrow HH:MM`, a date, which means that whole day through its last moment, or a date and time. |
| `brain ack on --until-done <key>` | Records it until a todo, a bug or a review is done, by id, name or path, a bug on a branch still counting as open. The word follows the entry's id, so a retitle leaves it standing, and it is taken back the moment the entry is done, gone from the brain, or doubled by a merge, where the brain's folder can be written, and the status line says when it could not be. An entry the brain cannot read right now, one a rebase stopped on, holds the word off until the entry reads again, and the status line says so. A review ledger that is missing holds it the same way rather than ending it, since the ledger lives on its branch and is back once that branch is checked out again, and the status line says it is not in this checkout and that `brain ack off` clears it. Refused for an entry of any other kind, for one already past open, and for a key that names more than one entry, which says to give the path where a path would tell them apart. Given with a time, the earlier end wins. |
| `brain ack off` | Takes the word back, and clears whatever sits where the word goes short of a folder. |

A word with no end is refused, so the agent proposes one to the owner
and waits. A second `brain ack on` replaces the word outright, ends
and all. `brain ack on` also refuses an end that does not read as a
duration or a moment, one already past, a duration of zero or less, an
end past the year 2999 on the word's own clock, the last year every
machine can place on its clock, an empty end flag, a task the brain
does not know, one of any other kind than a todo, a bug or a review,
one already past open, a key several entries share, an id doubled by a
merge among them, a todo or a bug whose file carries no id, and a
review with no name. `brain ack` given an end with no `on`, and
`brain ack off` given any end, are refused too, each with a line that
says so. A folder where the word goes, which the tool never made and
never removes, has `brain ack on` and `brain ack off` refused and
`brain ack` say so. The state is one dotted file at the root of the
brain, `.agents/.ack`, the tool's own, which git ignores since it
belongs to one machine and one stretch of work, and the brain's
conventions say the rest. A file that does not read as a word, a
moment with no zone in it included, counts as no word, and the status
line says so until `brain ack off` clears it, as `brain ack on` does
too where the file can be written. While it stands,
`brain ledger batch <ledger> <n> --status fixing --ack auto` records
the ack as `auto` with the day, so the ledger says which batches ran
on the standing word. Any ack that starts with auto, in any case, is
that call. It is refused on a batch left pending, since the word is
checked at the batch's start, refused on a batch that already carries
the owner's own ack, which it never writes over, and off, held or run
out it is refused anywhere. On a batch that already started on the
word, the stamp it carries stays. A pending batch that holds findings
and still carries a stamp from an earlier word takes the standing word
again when it starts, so a start that gives no ack is refused while
the word is off, and the report says it waits for the owner's word.

## The current work

The chain from the plan down to the step the agent is on, per
[spec/conventions.md](../../../spec/conventions.md), which every hook
prints under the clock and the standing word, one line per link,
outermost first, `task none` when nothing is on. A plan prints as
`plan <name>, step <n> of <m>, <text>`, a todo as
`task <id>, step <n> of <m>, <text>`, a bug as `bug <id>` the same
way, a review as `review <name>, batch <n> of <m>, <status>`, the
first batch not yet done. The step is the first pending row of the
entry's steps table, read fresh each time with a pointed step's mark
taken from its entry, so nothing is stored beside the table itself, a
todo or a bug with no table prints its id alone, and an entry whose
every step is settled says so and how to close it.

| Command | What it does |
|---|---|
| `brain task` | The chain as it stands, or `task none`. |
| `brain task on <key> [--replace]` | Starts work on an open plan, todo, bug or review, by id, name or path. With nothing on, it is the root. With a chain on, it goes under the innermost link only where the rules allow, which is a review under a todo or a bug, and under a plan, a todo or a bug the entry its current step points at. The entry already innermost is left where it is. Anything else is refused with the link that stands, and `--replace` sets the whole chain aside for it. Refused for a closed entry, a decision, a doc or a memory, an unknown key, or one several entries share. |
| `brain task done`, `brain task skip` | Marks the step the innermost link stands on done or skipped in the entry's file, so the work moves to the next pending one. Refused on a review, whose step is its batch, on a step that points at an entry, which takes its mark from that entry, on an entry with no steps, and once every step is settled. Once every step is settled the line gives the set command that closes the entry, with the closing date a plan or a todo wants, and the Fix section a bug wants and the Done when a todo wants named. |
| `brain task step <n>` | Marks step `n` of the innermost link pending again, and the work stands on the first pending step, which is `n` unless an earlier step is pending too. Refused on a review, on a step that points at an entry, on an entry with no steps or no step `n`, and on a step that is pending already. |
| `brain task off [--all]` | Drops the innermost link, or with `--all` the whole chain, and takes the file away once it is empty. |

The state is one dotted file at the root of the brain, `.agents/.task`,
the tool's own, which git ignores like `.ack`. A link whose entry goes
done, dropped, fixed, wontfix, refiled or closed drops off on the next
read with everything under it, and only such a link drops. A link
whose entry the brain cannot read right now, one two files carry the
id of or answer to the name of after a merge, one whose entry is not
in this checkout, filed on another branch, and one whose status is
none the tool knows all stay, and the line says which. A plan is on
the chain by its file and a review by its folder, and a retitled plan
keeps its place, since the chain follows through `brain refile` and
through the doctor's name repair, a review's link and the steps that
point at it too. A name changed on another branch leaves the link
saying not in this checkout until `brain task off` drops it or
`--replace` sets it aside. A reading never writes the file, so the
hook line cannot write over a chain set meanwhile, and a closed link
stays in the file until the next command that moves the chain.
`brain task off`, `brain task done`, `brain task skip` and
`brain task step` take the innermost link as written, so off after a
close drops the closed link and keeps the one above it, and a mark
after a close is refused until off drops it, since the step above is
one nobody did. A file that does not read as a chain counts as none,
the line says so, `brain task on`, `brain task done`, `brain task skip`
and `brain task step` refuse until `brain task off --all` clears it,
and `--replace` writes over it. A folder standing in the file's place,
which the tool never made, is named by every line and moved away by
hand. `brain ledger open` puts the new review on the chain where the
rules allow, and says on standard error when they keep it off.

## The handover

The one note a session leaves for the next, per
[spec/handover.md](../../../spec/handover.md), which the session start
hook puts whole in front of the next session and removes, so it is
read once.

| Command | What it does |
|---|---|
| `brain handover [--replace]` | Writes `handover/handover.md` from the prose on standard input, in place of the note there. The header carries the branch, the head and the moment. The body opens with the record the tool reads off the machine, the branch at its head with the commit's subject, the uncommitted files, the standing word as `brain ack` prints it at the note's moment and the current work as `brain task` prints it, then the prose as it came, less the blank lines before and after it, so a first line's indentation and a last line's trailing spaces stay. The uncommitted files are listed one per line with their state, modified, added, deleted, renamed, copied, type changed, unmerged or untracked, git's own letter for any other, the first fifty and then one line, `and N more`, for the rest. A project below its repository's top lists only its own files, named from its own folder, a file renamed out of it reading `moved out of the project` under the name it left, and the note under either of its names is left out, each path matched as git's listing matches it, so where `core.ignorecase` is true two paths that differ in an ASCII letter's case alone are one. A path or a subject that holds a line break or a carriage return is written with it escaped, so each stays one line. A detached head reads as the branch a rebase or a bisect in progress works on, else `detached`. Where the file git keeps for that cannot be read, it reads `git could not answer` with the reason. The branch and the head read `no git` where git is not installed or no `.git` stands at the project's root or above it, `no commits yet` in a repository with none, and `git could not answer` with the first line git gave where it refuses the repository, or with the seconds it waited where git gives no answer in 10. Refused with no words on standard input, and with a folder standing at the note's path or at `handover/handover.md.reading`, or a file standing where their folder goes. Refused too over a file at the note's path the tool never wrote or cannot read, which `--replace` never writes over. Which waiting note a write replaces is in the spec, and one it does not, a note for another branch, is refused with its branch and its moment, which `--replace` writes over on the owner's word. With nothing at the path, a claimed note a session start could not remove, `handover/handover.md.reading`, is the note waiting and is judged the same. The write removes it once the new note is in place. |

The spec says which session start takes the note, how the hook claims it
under `handover/handover.md.reading` and removes it, what it leaves for
another session, and where the tool's reading of git and the disk falls
short. `brain status` names a waiting note of the tool's whatever branch
it is for, and never a file under either name that the tool never wrote
or one it cannot open, which the hook names in one line in the note's
place. Where the removal fails, the hook says so on standard error
alone, since the context is out.

## The steps

A plan, a todo or a bug carries its steps as a table the tool keeps,
per [spec/plans.md](../../../spec/plans.md), a plan always, a todo or
a bug when its work has steps. Whoever files the entry lists the steps
as numbered lines under a Steps heading, and `brain new` turns them
into the table, each line free to open with the id or the name of a
todo, a bug or a review followed by a comma or a colon, which points
the step at that entry, the id in any case and stored in upper case,
`by` being the plan's or the todo's own `by` and agent for a bug. A
word shaped like an id or a review's name that reaches nothing at all
is refused, one that reaches a decision or another kind a step cannot
point at reads as prose, and so does a plain date. A line under Steps
that is not a numbered step is refused too, a wrapped step's lines
indented under it aside, since a line the table cannot carry is never
dropped without a word. A pipe in a step is written into its cell as
`\|`, the way markdown reads it, and read back as a pipe.

| Command | What it does |
|---|---|
| `brain new plan --title T --description D [--by owner\|agent] [--link P] [--category C]` | Files a plan from its prose on standard input, the Why and the Done when at least, its listed steps as the table, or an empty table when it lists none, a goal to find out. The steps go under a heading that reads `## Steps` and nothing more, and a Steps heading at another level or with a colon after it is refused, since the readers would never find it. `by` is owner unless said otherwise, `--link` and `--category` work as for any kind, and a field flag a plan does not carry is refused. |
| `brain steps <key>` | The entry in a few lines, its status and the count of settled steps, then one line per step with what it points at and its mark. |
| `brain steps <key> add "step"`, `brain steps <key> add - [--by owner\|agent]` | Appends one step, or one per line of standard input, numbered after the last, and prints the numbers. A todo or a bug with no Steps section gets one where its spec puts it, and a numbered list written under Steps by hand becomes the table first, its rows set by the plan's or the todo's own `by` and by agent on a bug. Refused on an entry that is not open, for a step that points at the entry itself, for one that points at an entry whose steps point back here at any remove, since the two would wait on each other for good, and on a plan whose steps sit under a heading that is not `## Steps`. |
| `brain steps <key> step <n> pending\|done\|skipped` | Marks a step that points at nothing, or one whose pointer reaches nothing the brain can read, a dead key or an id two files carry after a merge, which doctor reports. A step that points at an entry takes its mark from that entry, done when the todo is done, the bug fixed or wontfix, or the review closed, skipped when the entry was dropped, and a step whose todo or bug was refiled follows it to the entry filed in its place. The tool refreshes it whenever the entry's status changes, a ledger close included, while the holder is open, and a retitle rewrites a cell naming the entry by hand as its id in every holder, or as the new name for a file with no id, which doctor reports, so marking a pointed step by hand is refused. Refused on an entry that is not open, whose table is its record. |

A plan goes done, a todo done and a bug fixed with `brain set` once
every step is done or skipped, and the tool refuses it before then,
a todo or a bug with no Steps section closing freely and an entry with
an empty table closing on its Done when alone. A todo or a bug whose
Steps holds anything but the table is refused its close too, a
numbered list not yet turned into it as much as prose or bullets from
before the table, since the tool reads only the table there. On an
open entry `brain steps add` turns a numbered list into the table, and
so does `--fix` on a todo, never on a bug, while prose or bullets
neither turns, so make them a numbered list first or move them under
another heading by hand, and doctor names the line meanwhile.
Reopening a closed entry with `brain set` is refused while its steps
and another open entry's would point at each other, and while its own
table, or the steps of an entry it points at, does not read, since
the tool cannot tell. Doctor reports a Steps section with no table or
one that does not read, a step line sitting outside the table, a step
whose pointer reaches nothing, a pointed mark that drifted, a pointer
left on a refiled entry or written by name, two open entries whose
steps wait on each other, a `became` on an entry that is not refiled
or naming nothing, two files or the wrong kind, an entry done or fixed
with a step still pending, since dropped, wontfix and refiled close as
they are, and a plan with no Steps section at all. Four of those it
repairs under `--fix`, the drifted mark, the pointer, which it moves
on to the entry filed in the refiled one's place or writes as the id,
a numbered list under a plan's or a todo's Steps, which becomes the
table with its rows marked by the entry's own status, pending while
it is open, done once it is done, skipped once it was dropped or
refiled, and the plan with no Steps section, which gets an empty
table. A list under a bug's Steps is only flagged, since it may be the
reproduction, which goes under Evidence by hand, and on an open bug
`brain steps <key> add` keeps it as the fix's steps when that is what
it is.

## The review ledger

| Command | What it does |
|---|---|
| `brain ledger open <branch> --summary S [--level low\|medium\|high\|max]` | Creates `reviews/<yyyy-mm>-<branch-slug>/ledger.md` with the three sections and an empty batch table, the level recorded in its header, high unless given. The summary is one line, or `-` to read it from standard input inside a quoted heredoc, which keeps the shell off it, and it is refused when empty or when it runs to more than one line. Standard input is read as UTF-8 wherever the tool takes it, and a byte that is not is refused. |
| `brain ledger batch <ledger> --theme T` | Adds the next batch, numbered past the highest one, status pending, and prints its number. The theme is one line with no pipe. A batch past the cap that [spec/reviews.md](../../../spec/reviews.md) sets is refused, the one themed `closing pass` aside, however it is cased. The tool takes that theme at any step and as often as it is given, and the review says when. |
| `brain ledger batch <ledger> <n> [--status pending\|fixing\|verified\|done] [--ack DATE\|auto] [--theme T]` | Sets a batch's status, the owner's ack, or its theme. The ack is the owner's word that starts a batch, recorded on it, so `fixing`, `verified` and `done` on a batch that holds findings are refused until the batch carries one, and verification closes the batch with no further word. An ack of `auto` is the standing word's stamp, and the standing word section says when it is taken, when it is refused, and what a stamp left on a pending batch means. Refuses when given none of them, and refuses `verified` or `done` while a finding in the batch is still open. A batch with no findings runs and closes without an ack. A batch starts whatever the batches before it stand at, since their order is the review's. The one change of theme refused is the batch themed `closing pass` given a theme the cap counts while the cap is full, and the refusal says that batch keeps its theme. An open finding filed into a batch already verified or done, or reopened there, or a finding moved in already fixed, puts the batch back to `fixing` with its ack kept, since the word covered it, so the late fix is verified like the rest. A batch that had none, an empty one closed without an ack and then given a finding, asks for the ack before anything else. The ack, like the theme, is one line with no pipe. |
| `brain ledger add <ledger> "claim" --severity S [--found-by review\|hunter] [--batch n]` | Records the next finding, numbered past the highest one, and prints its id. The claim is one line. A batch number must name a row of the table, so no finding is filed where the report cannot see it. With `-` in place of the claim, the claims come in on standard input inside a quoted heredoc, one per line, all filed with the same severity, batch and found-by in one write, so they land whole or not at all, and the ids print one per line. That keeps the shell off a backtick or a dollar sign in a claim, and files a batch's worth in one call. Empty standard input is refused. |
| `brain ledger set <ledger> F-NN [F-NN ...] field=value ...` | Changes a finding, or every finding named, each value one line taken as written. The findings come first and the changes after them, so no word meant for one finding lands on another. Several findings take the same changes in one write, so the findings a group's commit fixed get its hash in one call, whole or not at all, and a finding the ledger does not have refuses the call. The call is refused too, with a message that names the word, for a finding's id after the first change, a change before the first finding, a field given twice, a finding named twice, and an id in lower case such as `f-03`, and it is refused for findings with no change. A ledger given as a finding's id, in either case, is refused as the ledger's key left out. The fields are severity, found-by, batch, status, fix and reason, and a line a hand edit lost comes back. A fixed finding always names its commit, `fix=<hash>`, a refuted, a wontfix or a deferred one says why in the same call, `reason=<one line>`, and the reason leaves with the status, as the fix does with a status moved away from fixed, save a `fix=` the same call gives, which stands on every finding the call names, whatever its status. A finding that moves into fixed names its commit in the same call or the call is refused whole, whatever fix an earlier call left on it, and one fixed already and set fixed again keeps its commit. A batch must be one the table has. The statuses are open, fixed, refuted, wontfix and deferred, and a refuted finding, like a wontfix, has landed and needs no batch. |
| `brain ledger report <ledger>` | The ledger's state in a few lines, counted from the file, with a blank status read as open the way close reads it. The first line gives the status and the counts, then one line per batch with its status, ack and counts, then a last line saying what comes next. That last line names an open or a fixed finding filed into no batch the table has before anything else, since a fix is verified by its batch, then walks the batches in order and says what the first unfinished one needs, the owner's word for a pending one, or its start when the ack is already on it or the standing word holds, a stamp from an earlier word counting only while the word holds, the ack on record for one that holds findings and has none, the standing word's while one holds, then its open findings, a late one included, its verification, and its marking done. Once every batch is done it says the closing pass is owed, per house rule 7, until a batch themed `closing pass` records that the pass ran, and then to close the ledger. |
| `brain ledger close <ledger>` | Flips the ledger to closed and writes the count under Summary. Refuses while a finding is open or has no status, and until the report's next line says to close the ledger, so a batch not yet done or a closing pass still owed holds it open. |

## Doctor

| Command | What it does |
|---|---|
| `brain doctor [--json]` | Every finding, one per line, `[fixable]` or `[flag]`. Exit 2 while any remain. The checks cover the headers, the sections, the links, the names, the indexes, the steps tables, the review ledgers, the style copies, the skill links, the front doors' imports and what a write left behind. |
| `brain doctor --fix` | Applies every fixable repair, in passes until a pass changes nothing, then reports what is left. A repair that fails is reported as a flag with the reason. |

Doctor checks that nothing was left behind by an interrupted write, that
there are no stray files, meaning every markdown file under `.agents/`
outside `handover/` is either an entry the store lists or a file the kit
owns, frontmatter present and complete, `updated` a real date, names
matching filenames and unique, kind matching folder, fields and values
against the spec, required headings, the lifecycle rules, filename
patterns kept and no id carried twice, links that resolve, links written
as paths with each file once, body links that resolve, a link of either
kind into `handover/` reported as reaching nothing even while the note
is there, the steps tables as the steps section says, indexes current,
no dashes or semicolons in prose, no machine paths, nothing shaped like
a secret, the version stamp a version, the chat style copies for Codex
and Gemini CLI matching the Claude Code one where the project keeps
those agents' folders, and the skill links Claude Code needs, one per
skill the kit ships and one per skill folder the project keeps, each of
which must reach its skill rather than point at nothing or be a plain
file. It reports too a real folder copy of a kit skill that fell behind
the brain's, a dangling link doctor once made for a project skill since
gone from the brain, and a skills folder it cannot list. Doctor reads no
file in `handover/`, and a folder whose name differs from it in case
alone is that folder, to doctor's walk and to every link check alike,
where git's `core.ignorecase` is true or git gives no answer for that
flag, outside any repository it opens or past its time limit. A kit
folder named in another case, such as `Skills/` for `skills/`, is the
kit's only where git says the flag is true, so where git gives no answer
on a disk that ignores case, its files are named as strays under that
name, the casing to put right. Doctor reads the front doors,
`AGENTS.md`, `CLAUDE.md` and `GEMINI.md`, the way each agent reads its
`@` imports. Claude Code reads `CLAUDE.md` and `AGENTS.md` while the
project keeps a `.claude/` folder, and Gemini CLI reads `GEMINI.md` and
`AGENTS.md` while the project keeps a `.gemini/` folder. A front door is
judged once for each agent that reads it, `AGENTS.md` by Claude Code's
rules when the project keeps neither folder, and a front door that is a
link to `AGENTS.md` is read once, as that file. Both agents find code
the same way, in a fence of backticks or tildes, closed or not, in an
indented block, which is a line four columns in from the margin where no
paragraph is open, the margin inside a list item being where its text
starts, or in a span, which a backtick after a backslash never opens. A
comment opened at the start of a line runs to its `-->` or to the end of
the file, and a fence inside it opens nothing. Claude Code skips HTML
comments too, while Gemini CLI reads them raw.

In both agents an `@` at the start or after whitespace opens an import
whose path runs to the next whitespace. Claude Code reads the lexer's
text, where a run of `*` or `_` is emphasis only when markdown pairs
it. A run can open when a character that is not whitespace follows it
and can close when one stands before it, a run of `_` inside a word
does neither, and a run that can close pairs with the nearest open run
of the same marker and length before it in its block. The lines of a
paragraph are read together, so a pair may open on one line and close
on a later one, but never across a blank line, a list item's start, a
heading or a fence. So an `@` right after a run used as an opener opens
an import too, a run used as a closer comes off the end of the path,
and a run left without a partner opens nothing and stays in the path. A
backslash before a space keeps the space, any other backslash ends the
path, and the path is cut at its first `#`. Gemini CLI reads the raw
text, so an `@` right after `*` or `_` opens nothing, markers after the
path are part of its name, a backslash before a space ends the path and
any other backslash is part of the name, and a `#` fragment stays in
the name it looks for. A token is an import when it opens with `~`,
`/`, `./` or `../`, names a markdown file, or leads to a file under any
spelling of its case, so a handle such as `@alice`, a package such as
`@tanstack/query@5.59.0` or a decorator such as `@pytest.fixture` is
passed over.

Doctor reports an import with punctuation glued to its path, which the
parser takes as part of the name so the file never loads, an import
that reaches no file, one found only under another spelling of its
case, which loads only where the file system ignores case, one with a
backslash in its path, where Claude Code's path ends, and a `CLAUDE.md`
or `GEMINI.md` with no import that resolves to the project's
`AGENTS.md`, whether in a sentence or on a line of its own. Under
Gemini CLI's reading it reports too an escaped space, a backslash kept
in the name, emphasis markers glued to the path, a fragment kept in the
name and, in a file both agents read, an import right after an emphasis
marker, which Gemini CLI never opens. A finding names the agent only
where the two read differently, and one both give is named once. An
import from the home folder, one that opens with `~`, is checked for
glued punctuation and never for being there, since it is there on one
machine and missing on the next. An import from the root of the disk,
one that opens with `/`, is reported for that same reason, never looked
up and never taken for the rules import. So is one that climbs out of
the project's folder and comes back in by retracing the folders it
climbed out of, such as `@../../apps/web/x.md` in a project at
`repo/apps/web`, since another checkout may go by other names, while
one that climbs out and stays out, such as
`@../../packages/web/README.md` there, is looked up like any other. A
front door that is not there is reported, `AGENTS.md` always and the
other two while their agent's folder is there, since the rules then
never load in that agent, and the next upgrade writes it back. So is a
front door spelled in another case, such as `Claude.md`, since only the
exact name is read, and one that is there but cannot be read.

Doctor does not follow the lexer everywhere, and in these cases it may
stay silent where an agent loads nothing, or report an import no agent
opens. They are an `@` inside link text or strikethrough, a backtick
after an escaped backslash, a thematic break of any kind, `***`, `___`,
`---` or a spaced one such as `* * *` or `- - -`, after which an
indented block is read as prose and the spaced ones are taken for list
items, a comment that opens inside a list item, and an import with no
`.md` ending that leads nowhere, which reads as a mention.

`--fix` repairs a missing or blank `updated` date, blank `links`
written as `[]`, a name that disagrees with its filename, a link written
as a name, a file linked more than once in one header, which keeps the
first, a pointed step's mark that drifted from its entry or its pointer
left behind by a refile or written by name, a numbered list under a
plan's or a todo's Steps and a plan with no Steps section, which get
the table, a stale index, a stale chat style copy, a skill link when
it is missing, dead, pointing elsewhere or a plain file, which the link
replaces, and a real folder copy of a kit skill that fell behind the
brain's, which is refreshed from it. Each repaired file gets today's
date. The only things `--fix` removes are what an interrupted write
left behind, a temporary file or a scratch folder named the way the
tool names them, the plain file or the wrong link sitting where a skill
link belongs, and a link under `.claude/skills` into the brain's skills
folder that dangles, leading to nothing at all, the way a link doctor
made for a project skill does once that skill is gone. The stray pass
never removes a link or a folder that still leads somewhere, whatever
it holds. A link sitting where a skill link belongs and leading
elsewhere is replaced by the right one, and a repair that rewrites a
file, a stale index or chat style copy, writes a real file in place of
any link standing there. No other file is removed.

## The check

Doctor reads the brain against its specs. The check reads the project's
own prose and code against the rules of SYSTEM.md a machine can judge
without reading for meaning, and it reports, never rewrites, since none
of these slips has one mechanical repair.

| Command | What it does |
|---|---|
| `brain check [paths...] [--json]` | One line per slip, `path:line: message`, then `clean` or the count, exit 2 while any remain. With paths, the files named and every markdown and Python file under a folder named, dotted folders left out, each once, and a path that is not there is refused. With none, every markdown and Python file git tracks in the project, refused in words where git cannot list them, plus the branch's commits. In markdown, line by line with the header block, fenced and indented code, code spans and HTML comments stepped over the way doctor reads a front door, and a URL or a time of day stepped over too: a dash the house style bans, a semicolon, and a colon anywhere but as a list item's label, which is the first colon of an item whose text before it holds no sentence end, so a colon in a heading, mid sentence, after the sentence that opens an item or second in an item is a slip, and a table row takes any. In Python, from the syntax tree: the import of `annotations` from `__future__`, a def whose parameters do not sit one per line below the def's line with a trailing comma after the last, a def with nothing but `self` or `cls` aside, and a call already broken across lines whose arguments do not sit one per line with a trailing comma, a lone generator argument aside since it takes none, and nothing inside a formatted string. A file that does not parse is one slip on its line. The branch's commits, `main..HEAD`, are read for a co-author line and for an AI attribution, each a slip named by the commit, and nothing is said of them outside git, on main itself or with no main branch. In a project the files the kit writes whole are never read, since a slip there is the kit's and the next upgrade writes them back, and the project's `AGENTS.md` is read above the kit's marker alone. The tool's own indexes and the review ledgers are never read either, since the ledger's claims name a file by its line. In the kit's own checkout every file is the work. |

The post write hook runs the check on the file just written, so the
slip is fixed in the same round, and the gates run it over the whole
tree before a review and before a merge.

## The gates

| Command | What it does |
|---|---|
| `brain gates` | Runs the gates in order, each named on one line, and stops at the first red one, saying which and with what exit code, exit 1. Then runs the check over the tracked tree and doctor over the brain, prints each slip and finding, and exits 2 while either has any, 0 when all is green. The gates are the fenced shell blocks, `bash`, `sh`, `zsh`, `shell` or bare, under a heading that reads `Gates` inside section 0 of the project's `AGENTS.md`, in order, up to the next heading at that level or above, each run from the project's root under bash where the machine has it and under the system shell otherwise, with its output passed straight through. A project that names none is told so, and the check and doctor are its gates. In the kit's own checkout the tool's own tests come first, under the interpreter running the command and, where it is another one, under the system's `/usr/bin/python3`, the floor the kit holds to. |

## Port and upgrade

Both run from a checkout of the kit, since a project without the tool
has nothing to run, so the port is
`python3 <kit>/.agents/skills/agent-brain/scripts/brain.py port` from
the project's root. A project that already carries the tool can run
its own copy with `--kit` pointing at the newer checkout. Without
`--project`, a port works on the top of the git repository around the
current folder and an upgrade on the nearest folder at or above the
current one that carries a brain, and neither ever works on your home
folder. The report's first line names the folder either one works on,
and `--project` has to name a folder that is there.

| Command | What it does |
|---|---|
| `brain port [--kit PATH] [--project PATH]` | Installs the kit into a project with no brain, which means the kit's files under `.agents/`, the front doors with the project's `## 0. Project Rules` kept from any old `AGENTS.md`, `CLAUDE.md` or `GEMINI.md`, or, with no such section anywhere, a front door's own words carried whole under that heading for the agent to read against the rulebook (a port does this, an upgrade never, since a front door without a section is then the kit's own earlier text), the hook configs merged beside the project's own hooks, Claude Code's with the rules under `permissions.deny` that refuse reading the kit's code, by the brain's path and by the skill link's, an earlier spelling of the kit's replaced and the project's own rules kept, the review's sub agent definitions, the chat style, the ignore lines, the version stamp, then `doctor --fix`. Ends by listing what is left to file through `brain new`, the markdown git sees outside the dot folders, root files one by one and deeper ones counted by folder, with `docs/` marked as the one the rules let a project keep (outside git, the root markdown and the usual folder names, a dot named file left out either way since the brain never files one). Refuses when a brain exists. |
| `brain upgrade [--kit PATH] [--project PATH]` | Brings a project that has a brain up to the kit. Runs the migrations the tree calls for first, then the same install. The one migration so far, to 1.0.0, runs while a `.agent/` folder is there. It moves it to `.agents/`, points every file git tracks or sees that names the old folder at the new name, the kit's own skill folders aside since the install replaces those (outside git, the root markdown, the ignore file and the brain's own markdown), refuses by name while a file git ignores names it, since such a file can neither be saved first nor be left behind, and carries section 0 out of the old `CLAUDE.md`. The stamp in `.agents/VERSION` says which release the project is on, and a kit older than it is refused. Refuses without a brain, refuses while a file it would replace holds uncommitted work, and refuses, before its first write, a project stamped before a kit skill shipped that keeps its own folder under that skill's name, in `.agents/skills` or in `.claude/skills` where the link goes, and a project stamped before a sub agent definition shipped that keeps a file of its own under that definition's name, each definition counted from its own release since a skill gains them later, until the folder or file is moved aside. A folder or a file the kit itself wrote is known by its bytes and passes. Refuses too a project that is the kit itself, or a worktree or a clone of it, since that is where the tool's code is the work. It knows one by the folder under any spelling, or where the two folders, each the top of its own work tree, meet on walking back through their local origins, at most eight clones and a bare repository among them, to a folder or a remote repository both come from, so a kit vendored inside a project's repository, or a project folder inside the kit's, is no clone of it. The walk looks for a local origin under the names git's clone tries for it, the path with `/.git` after it, the path itself, then with `.git/.git` and with `.git` after it, and goes into the first that is a folder, where git is asked under `GIT_CEILING_DIRECTORIES` set to that folder's parent, so it answers for that folder alone and never for a repository above it. Every git call of the walk runs without the variables `git rev-parse --local-env-vars` names, so a `GIT_DIR` or a `GIT_WORK_TREE` a git hook exported never answers for a folder the walk asks about, while config given in command scope, through `git -c` or `GIT_CONFIG_COUNT` with its keys and values, still holds, so a `safe.directory` or a `safe.bareRepository` given that way reaches every git the walk runs. The walk asks git only `rev-parse` and `remote get-url`, so it opens no transport and runs no command a walked folder's config names. It reaches a folder whose name holds a byte that is not UTF-8 on every POSIX file system, while such a path on Windows, and under a locale that is not UTF-8 a name outside its codec, is taken as not there. It ends where git opens no repository, at a plain folder standing under a name git's clone tries first, such as `/srv/hub` beside the bare `/srv/hub.git` a project was cloned from by `git clone /srv/hub`, and at one git keeps closed for safety, a bare origin while the owner's config sets `safe.bareRepository` to `explicit` or a folder git refuses for its owner. Two clones of one such folder still meet there, since a folder is recorded before git is asked. An origin that is a file naming its repository is no folder to go into, so the walk ends at its path. Two clones that name it by two spellings of that path do not meet. A clone the walk misses in any of these ways is upgraded as any project is, the kit's files written over its copies of them under the refusal over uncommitted work. A walked folder holding a named pipe called `HEAD` holds the walk up as it holds git's own clone up, since the upgrade's git runs with no time limit. Git matches the ceiling against the folder's path as text, in the system's spelling, so an origin spelled another way on a disk that takes two spellings for one, by case or by Unicode form, or reached through a second path to the same volume such as macOS's `/System/Volumes/Data`, leaves git free to answer for a repository above it. Git also reads a `:` in the ceiling, or a `;` on Windows, as a break between folders, so an origin whose parent's path holds that separator does the same. That matters only where one repository holds both the kit and the project, and there the upgrade takes the project for a clone of the kit and installs nothing, which writes over no work. The walk is built for git 2.28 or later. Every run names, while they remain, the notes a project filed under `handover/` before the folder became the tool's, any markdown file there, nested too, that is not the tool's note, one at the note's own path whose header is not the tool's included, and says to move what still matters into `docs/` or `memory/` through `brain new` and delete the rest, which the upgrade never does itself. |

What is the project's stays the project's, which is everything under
`.agents/` that is not the kit's, section 0, `README.md`, `CODEOWNERS`,
and any hook or setting of its own in the agent folders. Section 0
ends at the comment line in `AGENTS.md` that says where the kit's
words start, so it is found the same way whatever a release says after
that line. In a file the first release wrote, before that line
existed, it ends where that release's opening paragraph stood, and
that paragraph is history, so it never moves. The kit's earlier hook
groups are replaced under every event, told apart by a command that is
nothing but a call of the tool's own script, so a group of the
project's own that calls the script bare counts as the kit's and goes
with them, while a group that wraps that call, or calls a copy kept
elsewhere, is the project's and stays, and an event left with no group
stays as an empty list. A rename goes through git where git tracks the
file, so the move shows as one. The exit code is doctor's, 0 clean and
2 while findings remain, and those are the project's own prose to put
right. A finding in a file the install writes whole is the kit's to
fix, printed apart and never counted, since the install replaces that
file every time. Such a file is a skill the kit ships, the brain's own
`SYSTEM.md`, `README.md` or `house-rules.md`, a spec, the version stamp
`VERSION`, or a file copied into the agent folders, which is a sub
agent definition, the chat style source or one of its copies. An import
slip in `CLAUDE.md`, in `GEMINI.md` or in the kit's words of
`AGENTS.md` below its marker line counts the same way. The tool ships
without its own tests, and the chat style copies in `.codex/` and
`.gemini/` are the doctor's to make from the source in
`.claude/output-styles/`.

A root file the kit replaces is named in the report with a `git show`
command for each old one the last commit holds, the file named as that
commit holds it, a name in another case matched only where git's
`core.ignorecase` is true, a flag set wrong for the disk followed all
the same. Each command names its file from the repository's top, quoted
for a POSIX shell where it needs it, and spelled so the bytes the
report's stream writes for it are the bytes git holds, or on Windows,
where git takes a command's characters, as git prints it. Where the
project's folder has no such spelling, its name holding a byte that is
not UTF-8, a character that does not print or one the stream's codec
cannot carry, the line names the folder as git quotes a path under its
default `core.quotePath`, in double quotes with its bytes escaped the
way git escapes them, a byte outside ASCII as an octal escape such as
`\351`, and gives each command as `git show HEAD:./<name>`, to run from
that folder. A stream whose codec is not ASCII compatible, UTF-16 or
UTF-32, gets that form for every folder, the top's included, under a
line that says to run it from the project's folder. A command pasted
into `cmd.exe` is not quoted for that shell, and a terminal that reads
the stream in another code page than the stream's may hand git other
bytes. The refusal over uncommitted work and the list of what is left to
file show a name from git's answer with the replacement character in
place of a byte that is not UTF-8, and a name the disk gave, an old note
under `handover/` among them, is printed as the disk spells it.

## Hooks

`scripts/hooks.py` is what the agents call, with the event JSON on
standard input.

| Event | What happens |
|---|---|
| `session-start` | Prints into the agent's context the clock, the standing word and the current work, then the note the last session left in `handover/handover.md`, whole under a line that says how it was taken, or the one line that says why a file there stays, then `brain status`, counted once the note is taken, so it names a note this start read only where the start could not take it aside and read it in place, which the next session reads again. `--with-rules` adds `SYSTEM.md` and the agent's own chat style copy after those, for an agent that does not expand imports. The note is taken on every start the event's `source` names but a fork, since a fork carries the context it came from, and the handover section above says how. A Claude Code context past the 10,000 characters Claude Code shows from a hook opens with a line that asks the model to read whole the file Claude Code keeps it in, and the shipped Codex config sets `additionalContextLimit` to 0 on the session start, so Codex takes the context whole. |
| `prompt` | On each prompt the owner sends, puts the clock, the standing word and the current work in front of the model, since a model does not know the time and forgets what it was told and what it is on. |
| `tick` | After the agent's tool calls, the clock, the standing word and the current work again, off and none included, so a long stretch of work never loses any of them and sees the word end or the chain move. Claude Code fires it once after each round of tool calls, Codex and Gemini CLI after each shell call. |
| `pre-write` | Blocks, exit 2, a write that would create a new brain file by hand, an `INDEX.md`, a file nested under `spec/`, a dotted path, which the brain never lists or checks, the `.ack` file, which `brain ack on` writes, the `.task` file, which `brain task on` writes, anything in the `handover/` folder, which holds the one note `brain handover` writes, a rename of a brain file, which `brain refile` does, or a change to the header block of an existing brain file, its `updated` date aside, or to a row of the steps table a plan, a todo or a bug holds, a mark moving through `brain task` or `brain steps` or following the entry the step points at, a step never reworded, repointed or deleted by hand, a cell left empty by an older write filled in by hand, and the table never taken away, a plan's not even empty. A row after the last passes when it is held to what `brain steps add` holds a step to, with text, pending, pointing at an entry the brain knows, one file carries and whose steps do not lead back here, or at nothing, and on an open entry. A numbered list under Steps, new or written to, is the list the tool turns into the table, so it is held to the same, whole, as the write leaves it, and refused on a closed entry. A patch that reaches several brain files is judged across them too, the pointers on disk and the rows it adds walked together, so a loop it closes through two files is refused, though a pointer it removes still counts until it lands. A write that would leave the table unreadable is refused, a table that does not read now is doctor's, and the hook's keys and names come from the store, whatever case the path is spelled in. Edits to the prose of an existing file, the kit's own files, files directly under `spec/` and anything under `skills/` pass. The header and table checks judge the file as the write would leave it, the whole new text, the text after the edit, or the file after the patch's hunks. A delete is not refused, and doctor runs after it. A file the hook cannot read is already broken, so the write is taken as its repair and doctor judges the result. The hunks of a patch are placed one after another as the patch applies them, and the result is judged. A hunk that fits nowhere is refused if any line it carries, kept, removed or added, is a fence, a field the file's header carries or its kind allows, a table row, a numbered step opening with a key or the Steps heading, and on a closed entry any numbered line it adds, since the hook cannot tell where it would land, and the refusal names the line. A loose hunk that carries only prose is left alone. |
| `post-write` | After a write anywhere in the project, runs the check on the file just written and hands its slips back as context, so they are fixed in the same round, a file the kit writes whole or the tool writes left out as the check leaves it out. After a write inside `.agents/`, runs doctor too and hands its findings back the same way. |

Context goes back as one JSON object naming the event, which all three
agents read on every event. Codex also takes plain text at the start of
a session and on a prompt, and gets it there. On its tool events plain
text is dropped, so those get the JSON object too.

The config files that wire them up ship with the kit, as
`.claude/settings.json`, `.codex/hooks.json` and
`.gemini/settings.json`. Every command in them is the same one line of
Python, which finds the script from the project folder the agent names
in `CLAUDE_PROJECT_DIR` or `GEMINI_PROJECT_DIR`, or by walking up from
the session's own folder where Codex names none, hands it the event,
and does nothing where no script is found, so a checkout that predates
the kit never blocks a prompt or a write. The script that runs is the
one checked out, so a session whose hooks name an event and a checkout
of a kit from before that event still block on it until the session
restarts, which this kit's script no longer does for events it will
learn later. Each Codex hook carries the same line in a Windows form
beside it, run through the `py` launcher. The Claude Code one also
carries the kit's two settings, `CLAUDE_CODE_SUBAGENT_MODEL` for the
sub agents' model and `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` for how
many tool calls may run at once. The port and the upgrade add each to
a project's `env` when it lacks the key and leave a value the project
set.
