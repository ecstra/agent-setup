# Every command and flag

All of them run as `python3 .agents/skills/agent-brain/scripts/brain.py`,
shortened here to `brain`. A command exits 0 when done, 1 when refused,
with the reason on standard error, and 2 while findings remain, doctor's
or the check's. `brain gates` says why it stopped on standard output,
among the gates' own output, and [its row](#the-gates) says what each of
its codes means. A write that landed its entry and then lost a second
write, a step cell, a step's pointer or the chain, exits 0 with that
failure on standard error, since the command did its work and doctor
reports what is left, while an index rebuild that fails exits 1 like any
refusal, the entry written all the same.

Every path the tool writes, into a file, a link or an index line, every
path it compares, and every path it prints or names in a finding or a
message, a refusal and the port's and the upgrade's report among them,
is spelled with forward slashes on every system, Windows included. The
paths it hands the system or another program keep the system's
spelling, a file it opens or gives a linter, a folder git runs in, the
Python the gates run, a skill link's target and two paths the system
puts in one form before the tool compares them. So does a full path,
the one `brain path` prints, the project's folder on the report's first
line or the project's or the kit's folder a refusal names, and so do
the system's own words on an error a message passes on.

## Reading

| Command | What it answers |
|---|---|
| `brain version` | The kit version this project carries, from `.agents/VERSION`. |
| `brain status [--json]` | The clock, the standing word and the current work first, then version, doctor health, counts per kind by status, the build specs among them, open reviews, the note waiting for the next session with the branch it was written on and when, unreadable files. A claimed note a session start could not remove, `.handover/handover.md.reading`, is the note waiting while none sits at `.handover/handover.md`, and its line says it was read before. A note still in `handover/` from before 2.2.0 is named only once it moves in, as [the handover](#the-handover) says. The JSON form carries all of that but the clock and the word. The note is under `handover`, null when none waits, else its `branch` and its `written` moment, the first null where the header names none and the second where the header gives none in the one ISO shape the tool writes a moment in, with `again` beside them, true for a note read before. The chain is under `task`, which is null when the file does not read as a chain. The `latest_handover` key and the `handover` count of 1.4.0 are gone. |
| `brain ack` | The clock and where the owner's standing word to proceed stands, off, held, or on with what is left of it and what ends it. |
| `brain list <kind> [--status X] [--severity X] [--area X] [--by X] [--type X] [--branch X] [--date X] [--json]` | One line per entry of that kind, narrowed by any field. The kinds are bug, build-spec, decision, doc, memory, plan, review and todo. |
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
| `brain new <kind> --title T --description D [fields] [--category C] [--link P]...` | Files a new entry from the prose on standard input and prints its path, then any slip the check finds in it, as [the check](#the-check) says. The header names whoever files it as `author` and `editor`, as the paragraph under the fields by kind says. `--category` places a doc in a folder under `docs/`. `--link` repeats, takes a path, an id or a name, and is refused when it reaches nothing inside `.agents/`, a path into `.handover/` included, since no link goes into the folder whose one note is read once. |
| `brain set <key> field=value ...` | Changes fields, checks values and dates, applies the lifecycle rules, stamps `updated`, and prints the entry's path. Where the new status skips the steps that point at the entry, a todo or a build spec dropped or a todo or a bug refiled, it then prints one line for each step of an open entry that now reads skipped, `<id> step <n> now reads skipped, since <key> is <status>`, so the plan or the build spec that lost the step is seen to, and the entry that lost it stays valid. |
| `brain refile <key> --title T` | Renames for a new title. The id stays, every link follows, and a body link that carries a title after its path, in double quotes, single quotes or round brackets, such as `[x](path "Title")`, keeps it. |
| `brain refile <key> --kind bug\|todo --description D [fields]` | Turns a todo into a bug or the reverse, new body on standard input, and prints the new one's path and any slip the check finds in it, as `brain new` does. Both files stay, linked both ways, the old one marked `refiled` with the new one's id in `became`, which every step that pointed at the old one follows, save a step whose own entry the new one's steps point back at, which stays on the old one as skipped while the new one is open and follows once it closes. Refused when a step of the new body points at the old entry, or at an open entry whose steps point back at it at any remove, since the new entry takes the old one's pointers over. |
| `brain index` | Rebuilds every `INDEX.md` and prints the ones that changed. |

Fields by kind, all passed as flags to `new` or as `field=value` to `set`.

- bug: `--severity breaks|bug|debt|nit` and `--area` required. `status`
  is open, branched, fixed, wontfix or refiled, `reported` defaults to
  today, `parent` optional, the bug or the review finding it came
  from, `became` the id of the todo a refiled bug
  was filed as, which the refile writes and `set` takes only on a
  refiled entry when it names one todo the brain knows.
- todo: `--by owner|agent` and `--area` required. `status` is open,
  done, dropped or refiled, `born` defaults to today, `done` is the
  closing date, `became` the id of the bug a refiled todo was filed
  as, held to the same rule.
- plan: `--by owner|agent`, owner unless said otherwise. `status` is
  open, done or dropped, `born` defaults to today, `done` is the
  closing date.
- build-spec: `--branch` required. `status` is draft, which it is
  filed as, acked, closed or dropped, `born` defaults to today, `done`
  is the closing date, which closed and dropped both want.
- decision: `--area` required. `status` is standing or superseded,
  `date` defaults to today, `superseded-by` names the successor.
- memory: `--type project|feedback|reference` required.
- review: `--branch` required. `status` is open or closed. Prefer
  `brain ledger open`, which writes the body shape too.
- doc: no extra fields.

Every entry also carries `author` and `editor`, which no flag of `new`
takes and no index or file of the kit's carries. `brain new` writes
both as the project's git user.name, or the login name where git names
none, each one line of plain text the house style never judges. Every
later write to an entry through the tool, `set`, `refile`, `steps`,
`task`, `ledger` and every doctor repair but the fill of a missing
name, sets `editor` to whoever runs it, while a hand edit of the prose
leaves it, since git holds every change. `set` takes `author=` to put
a name right, while an `editor=` given to it yields to the name of
whoever runs it. Doctor fills a name an entry lacks from git, as
[its section](#doctor) says.

The body must carry its kind's required headings. A plan carries `Why`
and `Done when`, with `Steps` added by the tool when the prose has
none, a build spec `Goal`, `Behaviour`, `Edge cases`, `Out of scope`,
`Decisions` and `Proof`, with `Changes` optional and `Steps` added the
same way, a bug `Problem` and `Evidence`, with `Steps`, `Fix` and
`Verification` optional, a todo `What` and `Done when`, with `Why` and
`Steps` optional, a decision `Decision`, with `Alternatives` and
`Consequences` optional, and a review `Summary`, `Batches` and
`Findings`. An empty standard input writes the headings and
nothing else, for filling in afterwards, a plan and a build spec
aside, which are filed from their prose or not at all. A heading inside
code or an HTML comment is no heading, to the required headings and to
every section the tool looks up.

## The standing word

The owner's ack is the word to proceed with what the agent proposed
next. Said once as "auto ack" with an end, it stands until that end,
and the agent passes the review's gates that normally wait for it,
SYSTEM.md rule 9.6 names them, saying in each report that it did. It never
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
belongs to one machine and one stretch of work, and
[the brain's files](../SKILL.md#the-brains-files) say the rest. A file
that does not read as a word, a moment with no zone in it included,
counts as no word, and the status
line says so until `brain ack off` clears it, as `brain ack on` does
too where the file can be written. While it stands,
`brain ledger batch <ledger> <n> --status fixing --ack auto` records
the ack as `auto` with the day, so the ledger says which batches ran
on the standing word. Any ack that starts with auto, in any case, is
that call. It is refused on a batch left pending, since the word is
checked at the batch's start, refused on a batch that already carries
the owner's own ack, which it never writes over, refused on a batch
past the third of a ledger at quick, standard or deep, a round past
the third that runs on the owner's own word alone, and off, held or
run out it is refused anywhere. On a batch that already started on the
word, the stamp it carries stays. A pending batch that holds findings
and still carries a stamp from an earlier word takes the standing word
again when it starts, so a start that gives no ack is refused while
the word is off, and the report says it waits for the owner's word.

## The conclude word

The time the owner names for the session to wrap itself up, "stop at
17:15". Every hook block that prints the `now:` line adds a line for it
while it stands, in Claude Code, Codex and Gemini CLI, and so does
`brain status`.

| Command | What it does |
|---|---|
| `brain conclude` | The clock and where the word stands, the time left, or `conclude off`. |
| `brain conclude at <time>` | Records the time, read the way `brain ack on --until` reads one, so a bare time already past today means tomorrow and the line names the day. A second one replaces the first. |
| `brain conclude in <length>` | Records the time a length from now, such as 2h or 90m. |
| `brain conclude off` | Clears the word. |

The line reads `conclude at 17:15 today, 45 min left`. From 15 minutes
before, it adds that the agent winds down, finishes the step in hand
and starts no new work, sub agent or round of a review, the standing
word included, and concludes once the step is done, clearing the word
with `brain conclude off` after the handover that concludes the
session, never after one written before a compaction. Once the time has
passed it reads `conclude now`, and says to stop the sub agents, commit
only what passed the gates, save the working paper, write the handover
with `brain handover` and stop, whatever is left of the standing word.
An hour past the time the line orders nothing, and reads `the conclude
word for 17:15 today has passed, so it orders nothing now, and brain
conclude off clears it`, so a session that starts the next day, or one
beside it, is never told to stop. A handover written past the time
clears the word, and the command says so, while one written before it,
in the wind down before a compaction among them, keeps it. Nothing else
clears it but `brain conclude off`, a session start included.

A time not still to come, an empty one, and one past the year 2999 are
refused, and so are `at` or `in` with no time and `off` with one. The
state is one dotted file at the root of the brain, `.agents/.conclude`,
which git ignores like the standing word's, and a file there that does
not read as a time gives a line that says so until
`brain conclude off` clears it.

Two limits stand. The word is one file for the checkout, so two
sessions open on it share one time, and a handover the second writes
past the time clears the word for the first, which is why one session
at a time works a checkout while a word waits. And a session
whose next hook comes over an hour past the time, a single tool call
that runs that long, gets the line that orders nothing rather than the
order to conclude.

## The current work

The chain from the plan down to the step the agent is on, per
[the brain's files](../SKILL.md#the-brains-files), which every hook
prints under the clock and the standing word, one line per link,
outermost first, `task none` when nothing is on. A plan prints as
`plan <name>, step <n> of <m>, <text>`, a todo as
`task <id>, step <n> of <m>, <text>`, a build spec as `build <id>` and
a bug as `bug <id>` the same way, a review as
`review <name>, batch <n> of <m>, <status>`, the first batch not yet
done. The step is the first pending row of the
entry's steps table, read fresh each time with a pointed step's mark
taken from its entry, so nothing is stored beside the table itself, a
todo or a bug with no table prints its id alone, and an entry whose
every step is settled says so and how to close it.

| Command | What it does |
|---|---|
| `brain task` | The chain as it stands, or `task none`. |
| `brain task on <key> [--replace]` | Starts work on an open plan, build spec, todo, bug or review, by id, name or path, a build spec counting as open while draft or acked. With nothing on, it is the root, a build spec with no plan above it included. With a chain on, it goes under the innermost link only where the rules allow, which is a review under a build spec, a todo or a bug, and under a plan, a build spec, a todo or a bug the entry its current step points at. The entry already innermost is left where it is. Anything else is refused with the link that stands, and `--replace` sets the whole chain aside for it. Refused for a closed entry, a decision, a doc or a memory, an unknown key, or one several entries share. |
| `brain task done`, `brain task skip` | Marks the step the innermost link stands on done or skipped in the entry's file, so the work moves to the next pending one. Refused on a review, whose step is its batch, on a step that points at an entry, which takes its mark from that entry, on an entry with no steps, and once every step is settled. Once every step is settled the line gives the set command that closes the entry, with the closing date a plan, a build spec or a todo wants, and the Fix section a bug wants and the Done when a todo wants named. |
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
[the brain's files](../SKILL.md#the-brains-files), which the session
start hook puts whole in front of the next session and removes, so it
is read once.

| Command | What it does |
|---|---|
| `brain handover [--replace]` | Writes `.handover/handover.md` from the prose on standard input, in place of the note there. The header carries the branch, the head and the moment. The body opens with the record the tool reads off the machine, the branch at its head with the commit's subject, the uncommitted files, the standing word as `brain ack` prints it at the note's moment and the current work as `brain task` prints it, then the prose as it came, less the blank lines before and after it, so a first line's indentation and a last line's trailing spaces stay. The uncommitted files are listed one per line with their state, modified, added, deleted, renamed, copied, type changed, unmerged or untracked, git's own letter for any other, the first fifty and then one line, `and N more`, for the rest. A project below its repository's top lists only its own files, named from its own folder, a file renamed out of it reading `moved out of the project` under the name it left, and the note under either of its names and its lock are left out, each path matched as git's listing matches it, so where `core.ignorecase` is true two paths that differ in an ASCII letter's case alone are one. A path or a subject that holds a line break or a carriage return is written with it escaped, so each stays one line. A detached head reads as the branch a rebase or a bisect in progress works on, else `detached`. Where the file git keeps for that cannot be read, it reads `git could not answer` with the reason. The branch and the head read `no git` where git is not installed or no `.git` stands at the project's root or above it, `no commits yet` in a repository with none, and `git could not answer` with the first line git gave where it refuses the repository, or with the seconds it waited where git gives no answer in 10. Refused with no words on standard input, and with a folder standing at the note's path or at `.handover/handover.md.reading`, or a file standing where their folder goes. Refused too over a file at the note's path the tool never wrote or cannot read, which `--replace` never writes over, and while another session holds the note's lock past the wait below. Which waiting note a write replaces is in [the brain's files](../SKILL.md#the-brains-files), and one it does not, a note for another branch, is refused with its branch and its moment, which `--replace` writes over on the owner's word. With nothing at the path, a claimed note a session start could not remove, `.handover/handover.md.reading`, is the note waiting and is judged the same. With neither name in `.handover/`, a note of the tool's left in `handover/` before 2.2.0, `handover.md` first and then `handover.md.reading`, is the one note waiting and is judged the same, so one for another branch is refused until `--replace`. The write moves nothing, and removes a claimed note or an old one it replaces once the new note is in place. |

[The brain's files](../SKILL.md#the-brains-files) say which session
start takes the note, how the hook claims it under
`.handover/handover.md.reading` and removes it, and what it leaves for
another session. `brain status` names a waiting note of the tool's
whatever branch it is for, and never a file under either name that the
tool never wrote or one it cannot open, which the hook names in one
line in the note's place. Where the removal fails, the hook says so on
standard error alone, since the context is out.

A session start and a write take turns on the note's lock,
`.handover/handover.lock` beside the note. The start holds it from its
first look for the note until it has removed it, so a second start
waits and then finds none, and only one session gets the note. A write
holds it from its first look at what waits until its note is written
and the claimed note it replaces is removed, so a start and a write
never meet halfway and neither loses a note. Each waits up to 10
seconds for its turn. Past that a start leaves what waits where it is,
with one line that says another session is reading or writing it, and
a write is refused with words to run it again in a moment. The lock is
`fcntl.flock` on macOS and Linux and `msvcrt.locking` on Windows, which
the system frees when the process ends, however it ends, so a crash
never leaves it held. A fork takes no note and so no lock. A start with
no folder yet takes no lock and makes no folder, unless it moves an old
note in as below, and a write makes the folder before it locks. Where
the folder or the file system cannot hold the lock, the start and the
write go on without it. The lock holds between sessions on one machine
alone, never across machines that share a checkout or on a network file
system where the system's lock does not hold.

The folder carries an ignore file of its own, `.handover/.gitignore`,
which holds `*` and so ignores everything there, itself included. The
tool writes it where it is missing each time it asks for the lock or
moves a note into the folder. That keeps the folder out of git even on
a branch whose own `.gitignore` predates 2.2.0. The ignore file and the
lock stay in the folder once made, since removing the lock while another
session waits on it would let two sessions hold it.

A note left in `handover/`, where it lived before 2.2.0, moves into
`.handover/` at the next session start that would take it, by the
branch rules of [the brain's files](../SKILL.md#the-brains-files), the
tool's note and its claimed copy alike. A checkout that came to 2.2.0
through a pull or a merge, with no upgrade run, still hands its note on
that way. The start moves it without a word, and the upgrade makes the
same move and names it, as [its row](#port-and-upgrade) says. A note
for another branch stays in `handover/`, where that branch's own hook
reads it while the branch is on a kit before 2.2.0, and moves in at a
start on that branch. Where `.handover/` already holds a note, as
`handover.md` or as `handover.md.reading`, the old one never replaces
it. It waits behind that note and moves in at a start once that one is
gone. Where the
system refuses the move, the note stays where it is and the next start
tries again. A start that takes no note says in its one line in the
note's place what stays in `handover/` and why, a note for another
branch, one held behind a note in `.handover/`, or a move the system
refused. A write moves nothing, and counts a note left in `handover/`
as the one note waiting, as its row above says. The old folder goes
once the move leaves it empty. A file in `handover/` the tool never
wrote stays, a stray to [doctor](#doctor).

The move has a limit. A branch cut before 2.2.0 runs its own older
hook, which reads only `handover/`. So where one checkout passes a note
between such a branch and one on 2.2.0, a note waiting in `.handover/`
reaches a session on the older branch only once that branch reaches
2.2.0.

The tool's git calls keep the environment they are given, so one run
from inside a git hook reads that hook's `GIT_DIR`. Run from inside a
brain that is a symlink, the tool finds the brain at the link's target,
so the note and the git its record reads are the target's. On Windows a
git that starts a child process holding its output can run past the
10 second limit, since the tool stops only the git it started.

Branch names and paths compare as git's `core.ignorecase` says, so a
flag set wrong for the disk takes two spellings for one where the disk
keeps them apart, or for two where it folds them, and setting the flag
right is the owner's to do. Where the flag is true, branch names fold
by Unicode's case folding, which takes a few pairs NTFS keeps apart for
one, ß and ss among them, so two branches that differ only by such a
pair share a note there. A branch whose name ends in a character
Unicode counts as white space, a no break space among them, is named
without it, the way every header value is read, so two branches that
differ only by such an ending share a note too.

## The steps

A plan, a build spec, a todo or a bug carries its steps as a table the
tool keeps, per [the brain's files](../SKILL.md#the-brains-files), a
plan and a build spec always, a todo or a bug when its work has steps.
Whoever files the entry lists the steps as numbered lines under a Steps
heading, and `brain new` turns them into the table, each line free to
open with the id or the name of a build spec, a todo, a bug or a review
followed by a comma or a colon, which points the step at that entry,
the id in any case and stored in upper case, `by` being the plan's or
the todo's own `by` and agent for a build spec or a bug.
A word shaped like an id or a review's name that reaches nothing at all
is refused, one that reaches a decision or another kind a step cannot
point at reads as prose, and so does a plain date. A line under Steps
that is not a numbered step is refused too, a wrapped step's lines
indented under it aside, since a line the table cannot carry is never
dropped without a word. A pipe in a step is written into its cell as
`\|`, the way markdown reads it, and read back as a pipe. Once the
section holds the table, a row or a numbered step inside code or an
HTML comment there reads as nothing, so a draft can wait in a comment
under the table.

| Command | What it does |
|---|---|
| `brain new plan --title T --description D [--by owner\|agent] [--link P] [--category C]` | Files a plan from its prose on standard input, the Why and the Done when at least, its listed steps as the table, or an empty table when it lists none, a goal to find out. The steps go under a heading that reads `## Steps` and nothing more, and a Steps heading at another level or with a colon after it is refused, since the readers would never find it. `by` is owner unless said otherwise, `--link`, `--category` and what it prints work as for any kind, and a field flag a plan does not carry is refused. |
| `brain steps <key>` | The entry in a few lines, its status and the count of settled steps, then one line per step with what it points at and its mark. |
| `brain steps <key> add "step"`, `brain steps <key> add - [--by owner\|agent]` | Appends one step, or one per line of standard input, numbered after the last, and prints the numbers, then any slip the check finds in the entry, as `brain new` does. A todo or a bug with no Steps section gets one where its kind's sections put it, and a numbered list written under Steps by hand becomes the table first, its rows set by the plan's or the todo's own `by` and by agent on a build spec or a bug. Refused on an entry that is not open, for a step that points at the entry itself, for one that points at an entry whose steps point back here at any remove, since the two would wait on each other for good, and on a plan whose steps sit under a heading that is not `## Steps`. |
| `brain steps <key> step <n> pending\|done\|skipped` | Marks a step that points at nothing, or one whose pointer reaches nothing the brain can read, a dead key or an id two files carry after a merge, which doctor reports. A step that points at an entry takes its mark from that entry, done when the todo is done, the bug fixed or wontfix, or the build spec or the review closed, skipped when the entry was dropped, and a step whose todo or bug was refiled follows it to the entry filed in its place. The tool refreshes it whenever the entry's status changes, a ledger close included, while the holder is open, and a retitle rewrites a cell naming the entry by hand as its id in every holder, or as the new name for a file with no id, which doctor reports, so marking a pointed step by hand is refused. Refused on an entry that is not open, whose table is its record. |

A plan goes done, a todo done, a build spec closed and a bug fixed
with `brain set` once every step is done or skipped, and the tool
refuses it before then, a todo or a bug with no Steps section closing
freely and an entry with an empty table closing on its Done when
alone. A todo or a bug whose Steps holds anything but the table is
refused its close too, a numbered list not yet turned into it as much
as prose or bullets from before the table, since the tool reads only
the table there. On an
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
or naming nothing, two files or the wrong kind, an entry done, fixed
or closed with a step still pending, since dropped, wontfix and
refiled close as they are, and a plan with no Steps section at all.
Four of those it repairs under `--fix`, the drifted mark, the pointer,
which it moves on to the entry filed in the refiled one's place or
writes as the id,
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
| `brain ledger open <branch> --summary S [--level quick\|standard\|deep]` | Creates `reviews/<yyyy-mm>-<branch-slug>/ledger.md` with the three sections and an empty batch table, the level recorded in its header, standard unless given. The old levels, low, medium, high and max, still read in a ledger opened before 2.0.0, and a new one never takes them. The summary is one line, or `-` to read it from standard input inside a quoted heredoc, which keeps the shell off it, and it is refused when empty or when it runs to more than one line. Standard input is read as UTF-8 wherever the tool takes it, and a byte that is not is refused. |
| `brain ledger batch <ledger> --theme T` | Adds the next batch, numbered past the highest one, status pending, and prints its number. The theme is one line with no pipe. A batch past the cap of five that [the ledger](../SKILL.md#the-brains-files) holds to is refused whatever its theme, and a batch themed `closing pass`, which a ledger from before 2.0.0 may carry, counts toward the cap like any other. |
| `brain ledger batch <ledger> <n> [--status pending\|fixing\|verified\|done] [--ack DATE\|auto] [--theme T]` | Sets a batch's status, the owner's ack, or its theme. The ack is the owner's word that starts a batch, recorded on it, so `fixing`, `verified` and `done` on a batch that holds findings are refused until the batch carries one, and verification closes the batch with no further word. An ack of `auto` is the standing word's stamp, and the standing word section says when it is taken, when it is refused, and what a stamp left on a pending batch means. Refuses when given none of them, and refuses `verified` or `done` while a finding in the batch is still open. A batch with no findings runs and closes without an ack. A batch starts whatever the batches before it stand at, since their order is the review's. A batch takes any new theme, since a rename never changes the count. An open finding filed into a batch already verified or done, or reopened there, or a finding moved in already fixed, puts the batch back to `fixing` with its ack kept, since the word covered it, so the late fix is verified like the rest. A batch that had none, an empty one closed without an ack and then given a finding, asks for the ack before anything else. The ack, like the theme, is one line with no pipe. |
| `brain ledger add <ledger> "claim" --severity S [--found-by review\|recheck] [--batch n]` | Records the next finding, numbered past the highest one, and prints its id. A finding the recheck of a fix found takes `recheck`, and an old ledger's `hunter` still reads. The claim is one line. A batch number must name a row of the table, so no finding is filed where the report cannot see it. With `-` in place of the claim, the claims come in on standard input inside a quoted heredoc, one per line, all filed with the same severity, batch and found-by in one write, so they land whole or not at all, and the ids print one per line. That keeps the shell off a backtick or a dollar sign in a claim, and files a batch's worth in one call. Empty standard input is refused. |
| `brain ledger set <ledger> F-NN [F-NN ...] field=value ...` | Changes a finding, or every finding named, each value one line taken as written. The findings come first and the changes after them, so no word meant for one finding lands on another. Several findings take the same changes in one write, so the findings a group's commit fixed get its hash in one call, whole or not at all, and a finding the ledger does not have refuses the call. The call is refused too, with a message that names the word, for a finding's id after the first change, a change before the first finding, a field given twice, a finding named twice, and an id in lower case such as `f-03`, and it is refused for findings with no change. A ledger given as a finding's id, in either case, is refused as the ledger's key left out. The fields are severity, found-by, batch, status, fix and reason, and a line a hand edit lost comes back. A fixed finding always names its commit, `fix=<hash>`, a refuted, a wontfix or a deferred one says why in the same call, `reason=<one line>`, and the reason leaves with the status, as the fix does with a status moved away from fixed, save a `fix=` the same call gives, which stands on every finding the call names, whatever its status. A finding that moves into fixed names its commit in the same call or the call is refused whole, whatever fix an earlier call left on it, and one fixed already and set fixed again keeps its commit. A batch must be one the table has. The statuses are open, fixed, refuted, wontfix and deferred, and a refuted finding, like a wontfix, has landed and needs no batch. |
| `brain ledger report <ledger>` | The ledger's state in a few lines, counted from the file, with a blank status read as open the way close reads it. The first line gives the status and the counts, then one line per batch with its status, ack and counts, then a last line saying what comes next. That last line names an open or a fixed finding filed into no batch the table has before anything else, since a fix is verified by its batch, then walks the batches in order and says what the first unfinished one needs, the owner's word for a pending one, or its start when the ack is already on it or the standing word holds, a stamp from an earlier word counting only while the word holds, the ack on record for one that holds findings and has none, the standing word's while one holds, then its open findings, a late one included, its verification, and its marking done. Once every batch is done it says to close the ledger. |
| `brain ledger close <ledger>` | Flips the ledger to closed and writes the count under Summary. Refuses while a finding is open or has no status, and until the report's next line says to close the ledger, so a batch not yet done holds it open. |

A batch row, a finding or a finding's `- field:` line inside code or an
HTML comment reads as nothing, so a draft kept in a comment in the
ledger is never counted, numbered past or written to.

## Doctor

| Command | What it does |
|---|---|
| `brain doctor [--json]` | Every finding, one per line, `[fixable]` or `[flag]`. Exit 2 while any remain. The checks cover the headers, the sections, the links, the names, the indexes, the steps tables, the review ledgers, the style copies, the skill links, the front doors' imports, [the read guard](#the-read-guard) in a project and what a write left behind. |
| `brain doctor --fix` | Applies every fixable repair, in passes until a pass changes nothing, then reports what is left. A repair that fails is reported as a flag with the reason. |

Doctor checks that nothing was left behind by an interrupted write, that
there are no stray files, meaning every markdown file under `.agents/`
outside a dotted path, `.handover/` among them, is either an entry the
store lists or a file the kit owns, so one left in `handover/`, where
the note lived before 2.2.0, is a stray to file or delete, and the
tool's own note waiting there is one until it moves in or a write
replaces it, as [the handover](#the-handover) says, frontmatter present
and complete, an entry's `author` and
`editor` present, `updated` a real date, names
matching filenames and unique, kind matching folder, fields and values
against the kind, required headings, the lifecycle rules, filename
patterns kept and no id carried twice, links that resolve, links written
as paths with each file once, body links that resolve, one with a title
after its path among them, a link of either kind into `.handover/`
reported as reaching nothing even while the note is there, the steps
tables as the steps section says, indexes current, no dash or semicolon
in a header's name, description or links, which flow into the indexes,
no machine paths, nothing shaped like a secret,
the version stamp a version, the chat style copies for Codex and Gemini
CLI matching the Claude Code one where the project keeps those agents'
folders, and the skill links Claude Code needs, one per skill the kit
ships and one per skill folder the project keeps, each of which must
reach its skill rather than point at nothing or be a plain file. It
reports too a real folder copy of a kit skill that fell behind the
brain's, a dangling link doctor once made for a project skill since gone
from the brain, and a skills folder it cannot list. Doctor reads no file
in `.handover/`, nor in a folder whose name differs from it in case
alone, since each is a dotted folder. To every link check such a folder
is `.handover/` itself where git's `core.ignorecase` is true or git
gives no answer for that flag, outside any repository it opens or past
its time limit. A kit folder named in
another case, such as `Skills/` for `skills/`, is the kit's only where
git says the flag is true, so where git gives no answer on a disk that
ignores case, its files are named as strays under that name, the casing
to put right.

Doctor reads the front doors, `AGENTS.md`, `CLAUDE.md` and `GEMINI.md`,
for their `@` imports. It reads `AGENTS.md` always, `CLAUDE.md` while
the project keeps a `.claude/` folder and `GEMINI.md` while it keeps a
`.gemini/` folder, since a project without one runs no such agent. Each
door is judged once, the same way whichever agents read it, and a front
door that is a link to `AGENTS.md` is read once, as that file. A front
door that is not there is reported, `AGENTS.md` always and the other
two while their agent's folder is there, since the rules then never
load in that agent, and the next upgrade writes it back. So is a front
door spelled in another case, such as `Claude.md`, since only the exact
name is read, one that is there but cannot be read, and one that is not
a regular file, such as a folder or a named pipe, which doctor never
opens, so a pipe never holds it waiting. A front door that is not UTF-8
is still read, each byte it cannot decode taken as the replacement
character. A carriage return before a line's end, or alone, reads as
the line's end, as both agents read it, so a door or a file it imports
written with Windows line ends is judged like any other.

Doctor first blanks what holds no import, the code, the HTML comments
and the raw HTML. Both agents find code the same way, and doctor finds
it as they do, through the one reader of markdown the rest of the tool
uses. Code sits in a fence of backticks or tildes, closed or not,
in an indented block, which is a line four columns in from the margin
where no paragraph is open, the margin inside a list item being where
its text starts, or in a span, which a backtick escaped by a backslash
never opens and which keeps to its cell in a table, inside a block
quote as much as outside one. A thematic break of any kind, `***`,
`___`, `---` or a spaced one such as `* * *` or `- - -`, is no list
item, so an indented line after it is code. A comment that opens a line
or a list item's text runs to its `-->`, or else to the end of the list
item or the quote it sits in, or of the file, and a fence inside it
opens nothing. Outside a list item the tool's other readers, the check
among them, take such an opener with no `-->` for no comment, and only
doctor runs it on to the end, as the agents do. An empty comment,
`<!-->` or `<!--->`, closes where it stands and hides nothing past it,
and one opened inside a sentence closes inside its paragraph or is
plain text. A raw HTML block, as CommonMark reads one, holds no import
either. One that opens with `<pre`, `<script`, `<style` or `<textarea`
runs to its closing tag. One that opens with a block tag, opening or
closing, such as `<details>` or `</div>`, even inside a paragraph, runs
to the next blank line, and so does one that opens with a line holding
nothing but one complete tag of any name, such as
`<span class="rules">`, where no paragraph is open. A heading ends the
paragraph before it, so such a tag right under a heading opens a block.
A blank line is one with nothing on it as written, so a line that holds
only a comment never ends a block. A block nothing closes runs to the
end of the file. So an `@AGENTS.md` on the line
under `<details>` is no import, while one set off from the tags by
blank lines is.

Only an import line is judged. That is a line that holds one `@path`
and nothing else once its code and comments are blanked, with nothing
before it but quote markers such as `>` or `> >`, a list marker such as
`-`, `*`, `+`, `1.` or `1)`, or quote markers and then a list marker.
So `<!-- note --> @AGENTS.md`, `- @docs/setup.md` and
`> @docs/setup.md` are import lines, while `# @docs/setup.md`, a line
with two imports and an `@` inside a sentence are not. Every other `@`
in a front door is silent, since each agent reads the rest by rules of
its own and a check that cannot tell says nothing.

A line whose path holds an escaped space, such as
`@docs/team\ notes.md`, or a `#` fragment, such as
`@docs/style.md#setup`, is not judged, since the two agents read those
differently. Nor is one whose path ends in emphasis markers, `*` or
`_`, punctuation after them or not, since Claude Code takes them off
only when an opener earlier in the paragraph pairs them, which a line
alone cannot tell. Nor is one whose token is no import. A token is an
import when it opens with `~`, `/`, `./` or `../`, names a markdown
file, or leads to a file under any spelling of its case, its trailing
punctuation set aside and a backslash read as a slash, so a handle such
as `@alice`, a package such as `@tanstack/query@5.59.0` or a decorator
such as `@pytest.fixture` is no import, even alone on its line.

On an import line doctor reports punctuation glued to the path, any of
`.`, `,`, `;`, `:`, `!`, `?` and `)`, which the parser takes as part of
the name so the file never loads, and a backslash in the path, which no
agent reads as a folder's slash, in one message whichever agents read
the door. It reports an import from the root of the disk, one that
opens with `/`, since it is there on one machine and missing on the
next, and one that climbs out of the project's folder and comes back in
by retracing the folders it climbed out of, such as
`@../../apps/web/x.md` in a project at `repo/apps/web`, since another
checkout may go by other names. Neither is looked up. One that climbs
out and stays out, such as `@../../packages/web/README.md` there, is
looked up like any other. An import from the home folder, one that
opens with `~`, is checked for those first two slips alone and never
for being there, since it is there on one machine and missing on the
next. Every other import is looked up. Its target has to be there under
its own case, since another spelling loads only where the file system
ignores case, and it has to be a regular file, since a folder or a
named pipe is no file to load and is never opened, one that can be
read, and text, since Claude Code never loads anything else. Doctor
tells text by the first 8 KB, where a NUL byte alone says it is not, so
text in another encoding than UTF-8, such as a markdown file saved as
Latin-1, is text, as a front door in one is. A target that is
not there is reported unless git ignores it, such as a
`@CLAUDE.local.md` each clone keeps for itself, and outside a
repository, or where git gives no answer, it is reported all the same.
Each import line gives one finding at most, and a slip written on two
lines is named twice.

The rules imports are asked of a door as a whole. `CLAUDE.md` and
`GEMINI.md` are reported when nothing in them leads to `AGENTS.md`,
since the rules then never load. Here every `@` an agent may open
counts, anywhere outside code, comments and raw HTML, at a line's start
or after whitespace, `*`, `_`, `(`, `[` or `>`, in a sentence or on a
line of its own, so an import line such as `>@AGENTS.md`, its quote
marker right before the `@`, counts too. Emphasis markers, trailing punctuation and a fragment are set
aside, an escaped space is read as a space, and the path may reach
`AGENTS.md` under any spelling of its case, through `./` or through a
link that resolves to it. The markdown files the door imports are
followed too, each `@` in one read the same way from that file's own
folder, up to five imports deep, as deep as Claude Code follows them,
and each file once a walk, as Claude Code walks them, so files that
import each other cost one read each. A path from the root of the disk or the home folder, or one that climbs
out and back in by the folders' names, never counts, since it leads
there on one machine alone, and nor does one with any other backslash.
`GEMINI.md` is not reported while `.gemini/settings.json` names
`AGENTS.md` under `context.fileName`, alone or in a list, since Gemini
CLI then loads it as a context file. The settings are read with their
`//` and `/* */` comments taken out, as Gemini CLI reads them, while a
string keeps what it holds. An import line of `AGENTS.md`
with a slip on it, such as glued punctuation or another case, counts
all the same, so the slip gives its own finding alone, and so does a
path that reaches `AGENTS.md` where that is no file to load, such as a
folder. `AGENTS.md` is reported when the brain holds its rulebook,
`.agents/SYSTEM.md`, and no `@` in `AGENTS.md` itself leads there, read
the same way, since that import carries the rulebook.

Where doctor cannot judge, it says nothing, which leaves some slips
unnamed. Every `@` that is not alone on its line is silent, so a slip
in a sentence, such as the full stop in `See @docs/setup.md.`, goes
unnamed, and so does a line passed over above. A sentence such as
`The rules are in @AGENTS.md.` counts as the rules import and gives no
finding, though the full stop glued on keeps the file from loading. A
token with no `.md` ending that leads nowhere reads as a mention, so
`@docs/SETUP.` alone on a line is silent until `docs/SETUP` is there.
Only a front door's own import lines are judged, never the imports in
the files it imports, which doctor reads only for the rules import, and
an `@AGENTS.md` more than five imports deep is never found.

`--fix` repairs a missing or blank `updated` date, blank `links`
written as `[]`, an entry's missing `author` or `editor`, which it fills
from git as the end of this section says, a name that disagrees with
its filename, a link written as a name, a file linked more than once in
one header, which keeps the first, a pointed step's mark that drifted
from its entry or its pointer left behind by a refile or written by
name, a numbered list under a plan's or a todo's Steps and a plan with
no Steps section, which get the table, a stale index, a stale chat
style copy, a skill link when it is missing, dead, pointing elsewhere
or a plain file, git's stand in for a link where `core.symlinks` is off
among them, which the link replaces, a real folder copy of a kit
skill that fell behind the brain's, which is refreshed from it, and a
rule or a sandbox entry of [the read guard](#the-read-guard) missing
from `.claude/settings.json` while `.claude` stays inside the project.
Each repaired file gets today's date, and a repaired entry the name of
whoever runs the fix as its `editor`, save one whose only repair is
that fill, which keeps its date. The only things `--fix` removes are
what an interrupted write left behind, a temporary file or a scratch
folder named the way the tool names them, the plain file or the wrong
link sitting where a skill link belongs, and a link under
`.claude/skills` into the brain's skills folder that dangles, leading
to nothing at all, the way a link doctor made for a project skill does
once that skill is gone. The stray pass never removes a link or a
folder that still leads somewhere, whatever it holds. A link sitting where a skill link belongs and leading
elsewhere is replaced by the right one, and a repair that rewrites a
file, a stale index, a chat style copy or the settings the read guard
goes into, writes a real file in place of any link standing there. No
other file is removed.

The skill link's repair makes the link under a name of its own beside
its place, `.<name>.link`, clearing one an interrupted repair left
there, and only then moves it into place. So where the system refuses
a symbolic link, as Windows does without Developer Mode, whatever stood
in the link's place stays exactly as it was, git's stand in for the
link among them. Nothing is copied and git is never asked. The repair
fails, and its flag says how to get links, which is to turn on Windows
Developer Mode, run `git config core.symlinks true`, then
`git checkout -- .claude/skills` to bring the skill links back as
links, and run `brain doctor --fix`.

The fill reads the brain's history in one walk of git, names read
through the project's mailmap. The author is the git author of the
commit that added the file, followed through a rename and through the
brain's old `.agent/` folder, and the editor the git author of the last
commit that touched it, a merge among them where it resolved a conflict
in the file. A file git has not seen, which is every file of a
repository with no commit yet, and a commit with a blank name take the
name of whoever runs the fix, the way `brain new` takes it, and so does
every entry where no repository holds the project. A shallow clone that
hides the commit that added a file fills only a missing editor and
flags the author until `git fetch --unshallow` brings that commit in
for the next fix, or `brain set <key> author=<name>` names it. Where a
repository holds the project but git is missing, refuses it, as it does
one another user owns, fails on the walk or cannot finish it in a
minute, the fill writes nothing and each entry that lacks a name is
flagged until git can read it.

## The check

Doctor reads the brain against its formats. The check reads the
project's own markdown and the branch's commits against the rules of
SYSTEM.md a machine can judge without reading for meaning. Code is not
the check's, since the project's own linters judge it, as
[the lint hook](#the-lint-hook) says. It reports and never rewrites,
since most of its slips need new words that only the writer can
choose.

| Command | What it does |
|---|---|
| `brain check [paths...] [--json]` | Prints one line per slip, `path:line: message`, or `path: message` for a slip with no line such as a file that cannot be read, or `commit <hash>: message` for a commit, then `clean` or the count of findings. With `--json` it prints one JSON list in their place, each slip with its `path`, its `line`, 0 where it has none, and its `message`. Exit 2 while any slip remains. Each note goes to standard error and is no slip, such as a file named and passed over, a file that is not markdown among them, a warning git gave as it listed the files, or the commits not read. With no paths it reads the project's files and the branch's commits, and with paths the files named and those under each folder named, never the commits. A path that is not there, or that leads outside the project once its links are resolved, is refused, exit 1, and so is a run where git cannot list the files, as outside a repository, or read their attributes. |

With no paths the check reads the markdown files git lists, those it
tracks and the new ones it does not ignore. A file counts as markdown
by its suffix alone, `.md` in any case, so a `.markdown`, `.mdx` or
`.rst` file and code of any language are never read. A name git lists
that is gone from the disk, or is a link, a folder or a pipe there, is
left out. A folder git warns it could not open is one slip, since the
new files under it went unread, and git's other warnings are notes. A
folder named on the command line stands for what git lists under it,
dotted folders included, and outside git for the markdown files under
it that no dotted folder holds. Each file is read once, by the file it
resolves to, and a file that cannot be read or decoded as UTF-8 is one
slip.

Some files are passed over wherever the check meets them. A file git's
attributes mark `linguist-generated` or `linguist-vendored` is one,
which is how a project leaves out text it did not write, and where git
cannot read the attributes the run is refused in git's words. The files
the tool writes are others, the indexes, the review ledgers and the
handover note, since no hand puts them right. In a project the files the
kit writes whole are passed over too, since a slip there is the kit's
and the next upgrade writes them back. Which files those are goes by the
project's version stamp, as the upgrade decides, so a project's own file
under a name the kit took later is read. The project's `AGENTS.md` is
read above the kit's marker alone. In the kit's own checkout, which
holds the tool's tests under
`.agents/skills/agent-brain/scripts/tests/`, the kit's files are the
work and are read, the tool's own files aside. A file named on the
command line and passed over is named on standard error with the reason,
and one under a folder named is passed over in silence.

In markdown each line is read as it renders, an HTML entity as the
character it shows. An em dash is a slip, whether typed as the mark, as
`&mdash;` or as two hyphens between words with a space on each side,
while an en dash or a hyphen is none. A semicolon is a slip. A colon is
a slip anywhere but in a table row or as a list item's label, which is
the text before the item's first colon where that text holds no sentence
end. A sentence ends at a `.`, `!` or `?` followed by a space and an
upper case letter, the period of a known abbreviation such as `e.g.` or
`etc.` aside. So a colon in a heading, a setext one included, one mid
sentence, one past the sentence an item opens with and a second one in
an item are each a slip. A table row is a line of a table as GitHub
reads one, the header row straight above a delimiter row, the delimiter
row and the rows under it up to a blank line, a heading or a line with
no pipe, and it takes any colon. A row splits into its cells at each
pipe no backslash escapes before its code spans are read, as GitHub
splits it, so a span never pairs backticks across two cells.

What carries literal punctuation is stepped over before a line is
judged. That is the header block, a `---` line that opens the file with
a key line straight under it, up to the closing `---`, code fenced,
indented or in a span, a quote's code too, HTML comments, raw HTML,
which is a tag with its attributes, a `code`, `kbd` or `samp` element,
or a `pre`, `script`, `style` or `textarea` block, a link reference
definition, a footnote definition's label, a URL, a word that opens with
`mailto:`, `tel:`, `urn:`, `data:` or `file:`, git's `user@host:path`, a
drive path such as `C:\`, a path's line number or a host's port such as
`check.py:12` or `localhost:8080`, a colon between two digits such as a
time or a ratio, an emoji shortcode such as `:tada:`, and the quote
markers.

With no paths the check reads the branch's commits too, those of HEAD
that no `main` git knows reaches, the local one or any remote's, so on
main itself there are none. A commit carries a slip for a line that
opens with `Co-authored-by:`, in any case, and for an AI attribution, a
line that opens with `Assisted-by:` or `Generated-by:`, or with
generated, written, created or made and then with or by, and names an
agent right after it, Claude, Codex, Gemini, Copilot, ChatGPT, Cursor or
Aider, with no more than a maker's name such as Anthropic or a link's
bracket between. A list marker, a bracket or an emoji before such a
line's words is read past, and `CLAUDE.md`, `.claude/` or an agent named
later in the line is no attribution. Where git knows no main, or cannot
give the log, a note on standard error says the commits were not read
and why.

The post write hook runs the check on each file an agent writes, as
[Hooks](#hooks) says. `brain new`, `brain refile --kind` and
`brain steps add` write through the shell, which the post write hook
never sees, so each runs the check over the file it wrote and prints
any slip on standard output after the path or the numbers, under
`brain check after that write:`, with the notes on standard error. A
refile that lost a second write prints no path, since its message on
standard error names the new file and the write it lost, and then prints
the slips the same way. A slip there changes no exit code. `brain gates`
runs the check with no paths before a review and before a merge.

The check falls short in these places.

- A wrapped line of a paragraph that opens with a number and a period,
  such as `2026. Then`, reads as a numbered list item, so keep such a
  number off the start of a line.
- A copy of the kit's tests kept in a project, under
  `.agents/skills/agent-brain/scripts/tests/`, makes the check take the
  project for the kit's own checkout.
- Two hyphens set between words with a space on each side that mean no
  dash, such as a flag written outside a code span, are named as an em
  dash, and the fix is a code span.
- A colon in a table cell is never judged.
- A label that holds an abbreviation the check does not know, before an
  upper case word, reads as past the end of a sentence, so drop the
  period or reword.
- The check finds code nested one level deep. An HTML block or an
  indented code block nested deeper, inside a list item, or opened in a
  quote right under a list or a paragraph, is read as prose and its
  punctuation named, and the fix is a fenced block.
- A fence, or an HTML block such as `<pre>` or `<script>`, left open in
  a quote inside another quote runs on through the outer quote's lines,
  which are then stepped over as code, a slip missed and never a false
  one.
- An HTML block in a quote that holds a fence is cut at the fence, so
  its lines after the fence are judged, and the fix is a fenced block. A
  list in a quote whose sub item holds a fence is read as no list past
  the fence, so a paragraph four columns in reads as code and goes
  unjudged.
- A `---` or `===` inside or right after an HTML block that interrupts a
  paragraph makes the paragraph a setext heading, whose colon is named
  as one in a heading, and the fix is a blank line before the block.
- In a list item's label, a tag, a comment and literal text such as a
  URL or a path each read as a space, so a sentence that opens with
  literal text is read on to the next upper case word, and a tag set
  flush after a period reads as the space after it. Reword a label that
  this misreads.
- A paragraph line that holds a pipe, over a line of pipes and hyphens,
  reads as a table whatever its count of cells, and a quote that takes
  up its marker again after a lazy line reads as two quotes. A code span
  across either cut is lost and its punctuation named, so keep the span
  on one line or the marker on every line. A span that holds a pipe in
  a line read as a table this way is cut at the pipe too, as a cell's
  would be, and its punctuation named.
- A tab after a quote's marker can make the text after it read as an
  indented code block, so that line goes unjudged.
- Git's warning that it could not open a folder is read in git's
  English. Where git still speaks another language, no folder is named,
  and its warning is passed on as a note as it stands.
- The check takes git's `GIT_TRACE` variables out of its git calls, but
  a trace git's own config sends to standard error, such as through
  `trace2.normalTarget`, still reaches the notes as git's words, though
  never as a slip.
- `brain check` writes its notes to standard error plainly, so with
  standard error closed it puts them on standard output, ahead of the
  list under `--json`, and with the reader of its standard error gone it
  ends with exit 120. Give it a standard error.

## The gates

| Command | What it does |
|---|---|
| `brain gates` | Runs the gates the project names, in order, then the check with no paths, over the project's files and the branch's commits, then doctor over the brain, and prints what it finds on standard output. Each gate is named on one line, `gate <n> of <m>, <name>`, before it runs, and the first red one stops the run, saying which, with its exit code or the signal that killed it, and that the rest did not run, exit 1, with neither the check nor doctor run. Past the gates the check and doctor both run whatever the other finds, each slip, note and finding printed, then `check clean` or its count and `doctor clean` or its count, a note counting as no finding. A check that cannot run, since git cannot list the files or read their attributes, is one line that counts as a finding. Exit 0 when every gate is green and both are clean, 2 while the check or doctor has findings or a Gates heading holds no gate. An `AGENTS.md` that cannot be read or decoded exits 1 in words that name it, with nothing run. |

The gates sit in section 0 of the project's `AGENTS.md`, under each
heading whose text holds the word gates, such as `### Gates` or
`### 0.2 Merge gates`, at any level, with hashes or underlined. A word
in an HTML comment, a tag's attribute, an image or a link's target does
not count, nor does one with an ASCII letter, a digit or an underscore
against it, such as `ci_gates.yml`. A heading that sits under no Gates
heading and is none as it shows, though its text as written, outside
code spans and HTML comments, holds gates with no ASCII letter or digit
right beside it, is named in one line that says it holds the word as
written and not as shown, so its blocks do not run. Each Gates heading
runs to the next heading at its level or above, or to the end of section
0, and each fenced block under it is a gate, in order. The block's info
string picks the shell, `bash`, `shell` or none for bash, `sh` for sh
and `zsh` for zsh. A block of another language, or one with nothing but
blank lines and comments, is named in one line as not run and left out
of the count. A block inside a quote, an indented code block and
anything inside an HTML comment are no gate. A gate's name is its first
line that is neither a comment nor a `set` line.

Where section 0 has no such heading, or the project has no section 0,
the run says so in one line, and the check and doctor are the gates.
Where a Gates heading holds no gate, the run names it with the shape a
gate takes and goes on, and exits 2 where no gate turns red.

Each gate runs from the project's root with its output passed straight
through, a bash block under `bash --noprofile --norc -eo pipefail`, the
shell GitHub Actions gives a `shell: bash` step, an sh block under
`sh -e` and a zsh block under `zsh --no-rcs -e -o pipefail`, so a
failing line, or a failing stage of a pipeline where the shell takes
pipefail, turns the gate red. Where bash is not on the path, a bash gate
runs under `sh -e` on a POSIX machine and says so in one line, and is
red elsewhere, as is an sh or a zsh gate whose shell is missing, with a
line on standard error that names the shell. On Windows a bash under the
Windows folder, the WSL launcher, is passed over for the next one on the
path.

In the kit's own checkout the tool's own tests come first, as one gate,
`<interpreter> -m tests.parallel` in the scripts folder, which runs
each test class, a long one cut into batches of six tests, in a
process of its own, as many at once as the machine has cores, and
turns red where a batch fails or a test module will not import. It
runs them under the interpreter running the command and under
`/usr/bin/python3` where that is another interpreter and answers at the
kit's floor of 3.9 or above, given as `--python /usr/bin/python3`. One
below 3.9 is named in one line as not run, and the gate names the
Python versions it runs under. Two gates of ruff follow in the same
folder, `ruff format --check .` and `ruff check .`, under the config
the scripts folder carries, which [the lint hook](#the-lint-hook)
describes. Where ruff is not on the path, one line says the tool's code
is not linted and both are left out. Section 0's gates follow, where
the kit's `AGENTS.md` names any. An interpreter whose `sys.executable`
is empty exits 1 with nothing run.

The gates fall short in these places.

- A section 0 that names its gates under no heading holding the word
  gates runs none of them, and says so in one line.
- A gate that relies on a command failing without stopping the block
  needs `|| true` or its own `set +e`, as it would in a CI step.
- An sh gate takes no pipefail, since POSIX sh has none.
- On Windows the gates need a bash such as Git Bash on the path.
- A heading's shown text is read with its comments, tags, images and
  link targets taken off. Other markup can leave the word gates in what
  the heading does not show, an HTML comment before a link or an image
  or inside its text, a link whose text holds brackets, a reference link
  whose definition the reader does not take, such as one whose title
  wraps, holds an escaped quote or sits in a quote, or a footnote
  reference such as `[^gates]`, and that word opens the heading's
  blocks. Keep the word out of the markup of a heading in section 0 that
  is not the gates.
- Every doubt reads toward the word, so a heading whose markup leaves
  gates whole inside a longer word, such as `Dele<b>gates</b>`, or one
  where a letter of another script stands against it, such as
  `délégates`, opens its blocks too, each named as it runs.
- A run of `*` or `_` beside a link is read against the link's text, so
  where that text opens or ends in a space inside its brackets, as in
  `_[Gates ](docs/ci.md)_`, the run stays as written and the heading is
  no Gates heading, which the line on a word held as written and not as
  shown says. Drop the space inside the brackets.
- A run of `*` or `_` pairs only with a run of the same length, so runs
  of different lengths around the word, as in `__gates___`, leave a mark
  against it and the heading is no Gates heading, which the same line
  says. Use runs of one length.
- A tag that holds a backslash escape or a link anywhere inside it is
  not read as a tag, so the whole tag shows in both readings, its
  attributes too. A word gates in it opens the heading's blocks, each
  named as it runs, while a `*` or `_` in it can pair with a run outside
  it and leave the heading no Gates heading, which the same line says.
  Keep escapes and links out of a heading's tags.
- A `<!--` that section 0 never closes hides from GitHub everything down
  to the kit's marker, while the run cuts section 0 at the marker, where
  that comment hides nothing, so a Gates heading under it still runs its
  blocks, each named as it starts. Close the comment.
- A `<!--` left open on the kit's marker line, before or after the
  marker, hides the marker, so section 0 runs on into the kit's words,
  and the check judges them as the project's. Close the comment or move
  it off the marker's line.

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
and `--project` has to name a folder that is there. Both refuse, before
the first write, a project where a kit file they would write under
`.agents/` or in the agent folders sits behind a link that leads out of the
project, naming the file and where the link leads, until the link is
moved aside. Each file under `.agents/` is checked at its place under
`.agent/` too, the brain's folder before 1.0.0, since the upgrade's
migration renames that folder to `.agents/` before the install writes
through it. So a `.claude` folder linked into a kit checkout never gets
the project's settings.

| Command | What it does |
|---|---|
| `brain port [--kit PATH] [--project PATH]` | Installs the kit into a project with no brain, which means the kit's files under `.agents/`, the front doors with the project's `## 0. Project Rules` kept from any old `AGENTS.md`, `CLAUDE.md` or `GEMINI.md`, or, with no such section anywhere, a front door's own words carried whole under that heading for the agent to read against the rulebook (a port does this, an upgrade never, since a front door without a section is then the kit's own earlier text), the hook configs merged beside the project's own hooks, Claude Code's with [the read guard](#the-read-guard), the review's sub agent definitions, the chat style, the ignore lines, the version stamp, then `doctor --fix`. Ends by listing what is left to file through `brain new`, the markdown git sees outside the dot folders, root files one by one and deeper ones counted by folder, with `docs/` marked as the one the rules let a project keep (outside git, the root markdown and the usual folder names, a dot named file left out either way since the brain never files one). Refuses when a brain exists. |
| `brain upgrade [--kit PATH] [--project PATH]` | Brings a project that has a brain up to the kit. Runs the migrations the tree calls for first, then the same install. The one migration so far, to 1.0.0, runs while a `.agent/` folder is there. It moves it to `.agents/`, points every file git tracks or sees that names the old folder at the new name, the kit's own skill folders aside since the install replaces those (outside git, the root markdown, the ignore file and the brain's own markdown), refuses by name while a file git ignores names it, since such a file can neither be saved first nor be left behind, and carries section 0 out of the old `CLAUDE.md`. The stamp in `.agents/VERSION` says which release the project is on, and a kit older than it is refused. Every run removes what the kit wrote and no longer ships, each file named in the report, a file the kit dropped from one of its skill folders, the brain's spec files the kit kept under `.agents/spec/` before 2.0.0, with the folder once it is empty, and the review's fixer and hunter definitions under `.claude/agents/` where the project's stamp says the kit wrote them, from the release each shipped in up to 2.0.0. A file of the project's own in `.agents/spec/` stays, named in the report to file under `docs/` through `brain new`. The doctor run at its end fills the `author` and `editor` of each entry that lacks them from git, as [doctor](#doctor) says, and the report says how many entries it filled. Refuses without a brain, refuses while a file it would replace holds uncommitted work, and refuses, before its first write, a project stamped before a kit skill shipped that keeps its own folder under that skill's name, in `.agents/skills` or in `.claude/skills` where the link goes, and a project stamped before a sub agent definition shipped that keeps a file of its own under that definition's name, each definition counted from its own release since a skill gains them later, until the folder or file is moved aside. A folder or a file the kit itself wrote is known by its bytes and passes. Refuses too a project that is the kit itself, or a worktree or a clone of it, since that is where the tool's code is the work. It knows one by the folder under any spelling, or where the two folders, each the top of its own work tree, meet on walking back through their local origins, at most eight clones and a bare repository among them, to a folder or a remote repository both come from, so a kit vendored inside a project's repository, or a project folder inside the kit's, is no clone of it. The walk looks for a local origin under the names git's clone tries for it, the path with `/.git` after it, the path itself, then with `.git/.git` and with `.git` after it, and goes into the first that is a folder, where git is asked under `GIT_CEILING_DIRECTORIES` set to that folder's parent, so it answers for that folder alone and never for a repository above it. Every git call of the walk runs without the variables `git rev-parse --local-env-vars` names, so a `GIT_DIR` or a `GIT_WORK_TREE` a git hook exported never answers for a folder the walk asks about, while config given in command scope, through `git -c` or `GIT_CONFIG_COUNT` with its keys and values, still holds, so a `safe.directory` or a `safe.bareRepository` given that way reaches every git the walk runs. The walk asks git only `rev-parse` and `remote get-url`, so it opens no transport and runs no command a walked folder's config names. It reaches a folder whose name holds a byte that is not UTF-8 on every POSIX file system, while such a path on Windows, and under a locale that is not UTF-8 a name outside its codec, is taken as not there. It ends where git opens no repository, at a plain folder standing under a name git's clone tries first, such as `/srv/hub` beside the bare `/srv/hub.git` a project was cloned from by `git clone /srv/hub`, and at one git keeps closed for safety, a bare origin while the owner's config sets `safe.bareRepository` to `explicit` or a folder git refuses for its owner. Two clones of one such folder still meet there, since a folder is recorded before git is asked. An origin that is a file naming its repository is no folder to go into, so the walk ends at its path. Two clones that name it by two spellings of that path do not meet. A clone the walk misses in any of these ways is upgraded as any project is, the kit's files written over its copies of them under the refusal over uncommitted work. A walked folder holding a named pipe called `HEAD` holds the walk up as it holds git's own clone up, since the upgrade's git runs with no time limit. Git matches the ceiling against the folder's path as text, in the system's spelling, so an origin spelled another way on a disk that takes two spellings for one, by case or by Unicode form, or reached through a second path to the same volume such as macOS's `/System/Volumes/Data`, leaves git free to answer for a repository above it. Git also reads a `:` in the ceiling, or a `;` on Windows, as a break between folders, so an origin whose parent's path holds that separator does the same. That matters only where one repository holds both the kit and the project, and there the upgrade takes the project for a clone of the kit and installs nothing, which writes over no work. The walk is built for git 2.28 or later. Every run moves the tool's note and its claimed copy for the checkout's branch, `handover.md` and `handover.md.reading`, out of `handover/`, where the note lived before 2.2.0, into `.handover/`, the move a session start makes too under the same branch rules, as [the handover](#the-handover) says. The report names each note it moved, each for another branch, which stays there for that branch, each that waits behind a note `.handover/` already holds under either name until that one is gone, and each the system refused to move, with the reason, to move by hand, and the run goes on. The kit's ignore block keeps the `.agents/handover` line beside `.agents/.handover`, so a note an older session left there never enters git before it moves. Every run names too, while they remain, the notes a project filed under `handover/` before the folder became the tool's, any markdown file there, nested too, that is not the tool's note, one at the note's own path whose header is not the tool's included, and says to move what still matters into `docs/` or `memory/` through `brain new` and delete the rest, which the upgrade never does itself. |

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
file, so the move shows as one. The ignore file is written with a
carriage return and a line feed at each line's end where any of its
lines ends that way, else a line feed alone, a new one too, and a file
the 1.0.0 migration points at `.agents/` keeps its own line ends, so on
Windows neither gains a second carriage return. The exit code is
doctor's, 0 clean and 2 while findings remain, and those are the
project's own prose to put right. A finding in a file the install writes whole is the kit's to
fix, printed apart and never counted, since the install replaces that
file every time. Such a file is a skill the kit ships, the brain's own
`SYSTEM.md`, `README.md` or `house-rules.md`, the version stamp
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

## The read guard

The port and the upgrade write the read guard into the project's
`.claude/settings.json`, merged with what the project keeps there, so
the agent leaves the tool's code alone, as section 8 of `SYSTEM.md`
asks. Under `permissions.deny` go two rules that refuse reading that
code, `Read(/.agents/skills/agent-brain/scripts/**)` by the brain's path
and `Read(/.claude/skills/agent-brain/scripts/**)` by the skill link's,
the leading slash anchoring each at the project. A deny rule on Read
that names that folder at the project, by either path or by the brain's
old `.agent/` one, counts as the kit's and is replaced, so a release
that rewords a rule leaves no double. The project's own rules stay in
their order.

Under `sandbox.filesystem.allowRead` go the same two folders,
`.agents/skills/agent-brain/scripts` and
`.claude/skills/agent-brain/scripts`. Claude Code's sandbox takes the
Read deny rules as reads it refuses every command it runs, the brain
tool's own Python among them, so without these entries no brain command
could open its own code while the sandbox is on. With them every brain
command runs, one that carries a heredoc, such as `brain new` or
`brain handover`, included. The kit never turns the sandbox on. The
project's own sandbox settings, `enabled` and its own allowed and
denied reads among them, stay as they were, and the kit's two entries
go once after the project's own. A `permissions`, `sandbox` or
`sandbox.filesystem` that is not a JSON object, or a `permissions.deny`
or `sandbox.filesystem.allowRead` that is not a JSON list, is refused in
words before the first write.

The guard leaves one way through. With the sandbox on, the sandbox lets
every command it runs read the tool's code, so a shell read such as
`cat` of it gets through, while the Read tool stays refused. With the
sandbox off nothing changes, and the deny rules refuse both. A live run
on 2026-11-03 showed this. Under the sandbox, then, the agent's own word
is all that keeps a shell read off the code.

In a project, doctor names a rule or a sandbox entry of the guard
missing from `.claude/settings.json` as
`the read guard is missing from .claude/settings.json, which brain doctor --fix writes`,
and `--fix` writes both in, the rest of the file kept. So a project an
older tool upgraded gets the guard at the next fix. Doctor asks only
that the two rules and the two entries be there, in any order among the
project's own. It stays silent where the file is missing, which the
next upgrade writes, and where it is not valid JSON, is not a JSON
object or holds one of the keys above in the wrong shape, which the
next upgrade refuses in words. The kit's own checkout is never asked
for the guard, since its code is the work there. Doctor knows it by the
tool's tests under `.agents/skills/agent-brain/scripts/tests`, which
never ship to a project.

Where `.claude` is a link that leads out of the project, such as into a
kit checkout, doctor still reads the file, silent in the same cases,
and never writes through the link, since the file is not the project's.
Where the two rules and the two entries are there it says nothing, and
where one is missing it names that in a flag with no fix,
`the read guard is missing from .claude/settings.json, which sits behind a link that leads out of the project, to <folder>, so move the link aside and run brain upgrade, which writes the project its own`,
with `<folder>` the folder the link leads to. The port and the upgrade
refuse such a project too, with the same advice to move the link aside,
as [port and upgrade](#port-and-upgrade) says.

## Hooks

`scripts/hooks.py` is what the agents call, with the event JSON on
standard input.

| Event | What happens |
|---|---|
| `session-start` | Prints into the agent's context the clock, the standing word and the current work, then the note the last session left in `.handover/handover.md`, whole under a line that says how it was taken, or the one line that says why a file there stays, another session holding the note's lock among the reasons, then `brain status`, counted once the note is taken, so it names a note this start read only where the start could not take it aside and read it in place, which the next session reads again. Under the counts one line names the full call and the commands that read the brain through it, `list <kind> --status <status>`, `status` and `show <key>`, and says never to read it by a grep of its fields or a listing of its folders. `--with-rules` adds `SYSTEM.md` and the agent's own chat style copy after those, for an agent that does not expand imports. The note is taken on every start the event's `source` names but a fork, since a fork carries the context it came from, and the handover section above says how, when it waits for the lock, how a note left in `handover/` before 2.2.0 moves in, and what the start says of one that stays. |
| `prompt` | On each prompt the owner sends, puts the clock, the standing word and the current work in front of the model, since a model does not know the time and forgets what it was told and what it is on. |
| `tick` | After the agent's tool calls, the clock, the standing word and the current work again, off and none included, so a long stretch of work never loses any of them and sees the word end or the chain move. Under the moment it adds a line for any call that read or wrote the brain by hand, as [the nudge](#the-nudge) says. Claude Code fires it once after each round of tool calls, whatever the tools, Codex after each shell call, and Gemini CLI after each call to `run_shell_command`, `grep_search`, `search_file_content`, `glob`, `list_directory` or `read_many_files`. |
| `pre-write` | Blocks, exit 2, a write that would create a new brain file by hand, an `INDEX.md`, a dotted path, which the brain never lists or checks, the `.ack` file, which `brain ack on` writes, the `.task` file, which `brain task on` writes, anything in the `.handover/` folder, which holds the one note `brain handover` writes, a rename of a brain file, which `brain refile` does, or a change to the header block of an existing brain file, its `updated` date aside, or to a row of the steps table a plan, a todo or a bug holds, a mark moving through `brain task` or `brain steps` or following the entry the step points at, a step never reworded, repointed or deleted by hand, a cell left empty by an older write filled in by hand, and the table never taken away, a plan's not even empty. A row after the last passes when it is held to what `brain steps add` holds a step to, with text, pending, pointing at an entry the brain knows, one file carries and whose steps do not lead back here, or at nothing, and on an open entry. A numbered list under Steps, new or written to, is the list the tool turns into the table, so it is held to the same, whole, as the write leaves it, and refused on a closed entry. A patch that reaches several brain files is judged across them too, the pointers on disk and the rows it adds walked together, so a loop it closes through two files is refused, though a pointer it removes still counts until it lands. A write that would leave the table unreadable is refused, a table that does not read now is doctor's, and the hook's keys and names come from the store, whatever case the path is spelled in. Edits to the prose of an existing file, the kit's own files and anything under `skills/` pass. The header and table checks judge the file as the write would leave it, the whole new text, the text after the edit, or the file after the patch's hunks. A delete is not refused, and doctor runs after it. A file the hook cannot read is already broken, so the write is taken as its repair and doctor judges the result. The hunks of a patch are placed one after another as the patch applies them, and the result is judged. A hunk that fits nowhere is refused if any line it carries, kept, removed or added, is a fence, a field the file's header carries or its kind allows, a table row, a numbered step opening with a key or the Steps heading, and on a closed entry any numbered line it adds, since the hook cannot tell where it would land, and the refusal names the line. A loose hunk that carries only prose is left alone. |
| `post-write` | After a write, runs the project's own linters on each file just written, as [the lint hook](#the-lint-hook) says, and hands back what they left under `lint after that write:`. Then runs the check on each file just written inside the project, a file reached through a link that leads out of it left out, and hands its slips back as context under `brain check after that write:`, so they are fixed in the same round, a file the check passes over left out as the check leaves it out. A file the check could not judge, since git cannot read its attributes, is named on standard error and never in the context, and a standard error that cannot take the note loses it and nothing else. After a write inside `.agents/`, runs doctor too and hands its findings back the same way, or its error in words where it cannot read the brain, and still exits 0, since an exit 1 would show the person the error and lose the slips. |

What a hook puts on standard error, a refusal, the error that stopped
it or a note, goes out as UTF-8 whatever the locale's encoding, since
every agent reads it that way, so a file name the locale cannot
encode, as a Windows code page often cannot, reaches the agent whole.

Context goes back as one JSON object naming the event, which all three
agents read on every event. Codex also takes plain text at the start of
a session and on a prompt, and gets it there. On its tool events plain
text is dropped, so those get the JSON object too. A Claude Code context
past the 10,000 characters Claude Code shows from a hook opens, on any
event, with a line that asks the model to read whole the file Claude
Code keeps it in, and the shipped Codex config sets
`additionalContextLimit` to 0 on the session start and after a write, so
Codex takes those whole.

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
carries the kit's four settings, `"outputStyle": "Plain & Short"` for
the chat style, `CLAUDE_CODE_SUBAGENT_MODEL` for the sub agents' model,
`CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` for how many tool calls may run
at once, and `"idleCompaction": false`, which
keeps Claude Code from compacting a long session that sat idle for
about an hour, while compaction when the context fills runs as before.
The port and the upgrade add each where the project lacks the key and
leave a value the project set, so a project turns idle compaction back
on with `"idleCompaction": true` in its own `.claude/settings.json`. A
Claude Code older than 2.1.290 ignores the key.

## The nudge

The tick reads the tool calls its event carries, Claude Code's round of
them or the one call Codex and Gemini CLI hand over, and adds a line
under the moment for each kind of hand work on the brain those calls
did, a read or a write. It runs after the calls, so nothing is refused.
A tick says each line once however many of its calls match, the read's
before the write's.

A tracker folder here is one the brain indexes, `docs/`, `memory/`,
`bugs/`, `todos/`, `decisions/`, `plans/`, `build-specs/` or
`reviews/`. The brain's own files are `INDEX.md`, `.ack`, `.task`,
`.conclude` and `.handover/`, which the tool alone writes. A pattern in
place of a folder's name, as in `.agents/*/*.md` or
`.agents/{bugs,todos}/*.md`, reaches each tracker folder it matches.
Nothing else in the brain's folder is an entry, the kit's own
`SYSTEM.md`, `README.md`, `house-rules.md`, `VERSION` and `skills/`
among them, so a read or a write there adds nothing.

A read is any of these.

- A field grep: grep, egrep, fgrep, rg, awk, or sed without `-i`, whose
  pattern names a field an entry's state lives in, `status`,
  `severity`, `area`, `branch`, `born`, `done`, `reported`, `became`,
  `parent`, `superseded-by`, `author` or `editor`, over the brain's
  folder, a tracker folder, a path in one or one of the brain's own
  files. The field counts at a line's start, as `^status`, as any
  choice of a group opened there, as `^(status|severity)` and
  `^(title|status)` both are, or with its colon anywhere, as `status:`.
  One word of a search for either of two with no `^` in front, as
  `nudge|status` is, counts for nothing, and so does a field prose and
  code use too, such as `name` or `type`. The pattern is the value of
  `-e`, or else the first word that is no option or an option's value,
  an awk or sed script among them. An rg with no path, or a grep with
  `-r` and none, searches the folder it stands in, so it counts when it
  stands in the brain's folder or a tracker folder.
- A listing: ls, find, tree or wc over a tracker folder, a folder in
  one or a pattern of a tracker's files, or find or tree over the
  brain's folder. A listing needs a folder or a pattern and never one
  named file, so `ls -la` or `wc -l` of one entry, or of two, adds
  nothing. A listing by ls or tree with no path lists the folder it
  stands in, and a find counts by the folders it starts from, whatever
  its tests, so `find .agents -name "BUG-*"` is a listing.
- A print: cat, head or tail over a pattern of a tracker's files, as
  `cat .agents/bugs/*.md` is, or over two files or more in tracker
  folders. A printer that a loop, a listing or xargs feeds counts when
  the paths handed on hold such a pattern, as a loop of `head` over
  `TODO-0*` after a `cd` into `.agents/todos` does.
- A search tool: Claude Code's Grep and Gemini CLI's `grep_search` and
  `search_file_content` when the pattern names a field as a field grep
  does and the folder searched, or its glob read from that folder,
  reaches the brain as a field grep's path does. Claude Code's Glob and
  Gemini CLI's `glob` when the pattern holds a wildcard and, read from
  its folder, lands in a tracker folder, so a Glob of one named entry
  adds nothing. Gemini CLI's `list_directory` of a tracker folder or a
  folder in one, and its `read_many_files` when what it includes is a
  pattern of a tracker's files or two files or more in tracker folders.

After a read the line names, with the full call in front,
`list <kind> --status <status>` for the entries, `status` for the
counts and `show <key>` for one.

A write is tee, mv, rm, touch, mkdir, `sed -i`, `perl -i`, `git mv` or
`git rm` on a path in a tracker folder, one of the brain's own files or
the brain's folder itself, a cp whose last path, where the copy lands,
is one of those, so a copy out of the brain is no write, or a find from
one of those with `-delete` or with an `-exec` that runs a writer. A
redirect, `>`, `>>` or `&>`, onto a path in a tracker folder or one of
the brain's own files is a write too, whatever program it follows.
After a write the line names `new`, `set`, `refile`, `steps`, `task`,
`ledger`, `handover` and `index` as the commands that do that work, and
`brain doctor` with the full call to see what the hand change left. A
write through the edit tools adds nothing here, since the `pre-write`
hook judges it before it lands, as its row says.

A word search in the brain's prose adds nothing, and so do a print of
one entry, by a printer or Claude Code's Read, a call that reaches
nothing in the brain, and with no redirect into the brain a call to the
brain tool and git but for `git mv` and `git rm`, so `git status`,
`diff`, `log`, `add` and `commit` over the brain say nothing, whatever
a commit message names. The programs and tools named here are the only
ones the nudge knows.

A shell call is any call whose input carries a command, whatever the
agent names the tool, and a Codex command handed over as a list is read
as the script after its `-c` or `-lc`, or else as the words it holds.
The command is read line by line, as the shell runs it. A backslash at
a line's end joins it to the next, a line break inside quotes, such as
a commit message's, stays inside its line, a comment is left out, and
the body of a heredoc opened outside quotes is left out too, since it
is text and not shell, so prose handed to the brain tool that names
`rm` or `cat` never reads as a command. A line splits into parts at the
shell's separators, pipes and parentheses, a redirect kept with its
part, and a `cd` part moves the folder the later parts count from, on
its line and after it. A part's program is its first word, known by its
bare name, past `sudo`, `env`, `command`, `exec`, `xargs` and its
options, the shell's own words such as `do` or `then`, and any
assignment. A word is a path unless it is an option or the value an
option takes, such as grep's `-m 1`, a number, a word with a space in
it, a variable, or the pattern or script a reader or an edit in place
takes first.

A loop, a listing, a find and a grep that prints file names hand their
paths on to the parts that work on them. A loop hands on its words
after `in`, ls the paths it names, a find the folders it starts from,
and grep or rg with `-l` or `-L` the paths it searched, or the folder
it stands in when it searches that. A part that xargs feeds, or whose
path is a variable such as `$f` or find's `{}`, works on every path
any of those hands on anywhere in the same command, so a loop that
names a tracker's files in one part and greps, prints or edits each in
another counts, and
`grep -l '^status: done' .agents/todos/*.md | xargs rm` is a read and a
write. A find's `-exec`, `-execdir`, `-ok` or `-okdir` runs its program
on the folders the find starts from, and what that program reads or
writes counts as the find's.

The limits are plain. The line comes after the call, which has run by
then. A relative path counts from the call's folder, the event's `cwd`
or the `dir_path` Gemini CLI's shell names, from where an earlier `cd`
in the same command moved, or for git's paths from the folder its `-C`
names, and from nowhere else, so a `pushd` moves nothing. A path is
placed as text, joined to the folder it counts from and normalized, and
only the call's folder and the brain's are followed through their
links, so no word of a command touches the disk and a path that reaches
the brain through any other link goes unseen. For the same reason a
listing tells a folder from a file by its name alone, a name with no
dot but those in front taken for a folder. A variable stands only for
the paths a loop, a listing, a find or a `grep -l` hands on, never for
the value an assignment gives it, and it stands for every such path in
the command, its own loop's or not. A write a program makes on its own, a
python script's among them, goes unseen, since the hook reads the
command line and not what the program does, so only a redirect or one
of the commands above shows it. A field grep from above the brain's
folder, such as one over the whole project from its root, names no
brain path and adds nothing. A line longer than 10,000 characters, or
one the hook cannot split, adds nothing, and so does an event the hook
cannot read for its calls, while the moment still prints.

## The lint hook

The post write hook runs the project's own linters on each file the
agent writes, adds or moves with its edit tools inside the project, a
deleted file and one reached through a link that leads out of the
project left out, and in a project never on a file inside `.agents/`.
Section 0 of `AGENTS.md` names them under each heading whose text is
Lint, such as `### Lint` or `### 0.3 Lint`, at any level, in the fenced
blocks up to the next heading at its level or above. Each line of a
block is a file pattern, then one command with `{file}` as a word of
its own where the file goes, such as
`*.py ruff check --fix --unfixable F401 {file}`, and a blank line or
one that opens with `#` is passed over. A fixer that deletes what looks
unused, such as an import, wants that fix turned off, since the hook
runs after every write and the agent often adds the import one edit
before the line that uses it. Where
section 0 has no Lint heading, or `AGENTS.md` has no section 0, nothing
runs and nothing is said.

A pattern with no slash matches the file's name, and one with a slash
matches its path from the project's root, where a `*` crosses folders
and each `**/` matches no folder too, so `src/**/*.py` takes
`src/app.py` as well as `src/api/app.py`. Patterns match case for case.
Every line that matches runs, in the order section 0 gives. A line is
split into words the way a POSIX shell splits them, quotes holding a
word together, and its command runs from the project's root with no
shell, `{file}` replaced by the file's absolute path as one argument,
so a space, a quote, a leading dash or a letter outside ASCII in the
file's name reaches the command whole and never reads as an option.

A line the hook cannot run as one command is not run, and the context
names it with the reason after every write the hook lints, until
section 0 is put right. That is a line that does not split into words,
such as one with a quote left open, a line of one word, a line with a
shell operator outside quotes, `;`, `|`, `&`, `>`, `<`, `(` or `)`,
alone or glued to a word as in `{file}&&` or `2>&1`, a line whose
command opens with a word that holds `=`, which a shell reads as a
variable, and a line with no word `{file}`. A quoted operator is an
argument like any other. A line written beside the fences under a Lint
heading as one code span that holds `{file}`, in a list item or not,
is named as sitting outside a fenced block, and a Lint heading with no
line in a fenced block is named in one line that says how a line is
written. A line beside a fence in any other form, such as a bullet with
no backticks, reads as prose, so it runs nothing and nothing names it.

Each command has 20 seconds, and one write has 40 seconds over every
file it touched, so a patch over many files still ends inside the 60
seconds Claude Code and Gemini CLI give a hook by default, since the
kit sets no hook timeout of its own. A command past its time is
stopped with every process it started, its process group, or its
process tree on Windows, so none writes the file later, and the
context names it with the seconds it had. Once the 40 seconds are
spent, the command next in line is named as not run and the file's
other lines are left. A program that is not installed is named in one
line, and one that cannot start for another reason with that reason.
The write stands either way.

Under `lint after that write:`, ahead of the check's slips, the hook
hands back each command that exited with an error, with the first 30
lines it printed, standard output then standard error, as what the
linters could not fix, then each lint line or command it could not
run, and
`the linters rewrote <name>, so read it again before the next edit`
where the file's bytes changed, each line once. It never blocks the
write and exits 0.

In the kit's own checkout the hook runs the kit's own lines in place of
section 0's, `ruff format {file}` then `ruff check --fix {file}` on each
`*.py` file, the brain's own files included, under the `ruff.toml` in
the scripts folder, which the kit's gates run too. That config holds
the code to Python 3.9, lets a line run to 320 characters, selects
ruff's rules F, E9, TID251 and RET505, bans
`from __future__ import annotations`, and never removes an unused
import on its own, since the hook runs on every write and an import is
often added one edit before its use, so ruff names it and the agent
removes it. A copy of the kit's tests kept in a project, under
`.agents/skills/agent-brain/scripts/tests/`, makes the hook take the
project for the kit's checkout, so section 0's lines do not run there.
