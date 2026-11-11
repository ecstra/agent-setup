# Every command and flag

All of them run through the launcher in the brain's folder, as
`python3 .agents/brain` from the project's root and
`python3 ../.agents/brain` from a folder one level below it, the same
in every shell on every system. The launcher is a small Python file
that runs `.agents/skills/agent-brain/scripts/brain.py` with every argument,
standard input and exit code as they came, and that long call still
works. A Python file rather than a shell script, since cmd would read a
batch file's arguments a second time, a `%NAME%` among them, and a shell
script stops when git checks it out with CRLF line ends, which Python
reads the same as LF. On macOS and Linux `.agents/brain` alone runs it
too while its line ends are LF, since the system reads its first line
to find Python, and a checkout git made with CRLF line ends runs only
through `python3 .agents/brain`. Both are shortened here to `brain`. A kind takes its
plural wherever a command takes a kind, the name of its folder, so
`list todos` reads as `list todo`. A command exits 0 when done, 1 when refused,
with the reason on standard error, and 2 while findings remain, doctor's
or the check's. An argument a command does not take, a kind it does not
know or `--open` beside `--status` among them, stops it before it runs,
with its usage and the reason on standard error, and exits 2 as well.
`brain gates` says why it stopped on standard output,
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
Python the gates run and two paths the system
puts in one form before the tool compares them. So does a full path,
the one `brain path` prints, the project's folder on the report's first
line or the project's or Agent Setup's folder a refusal names, and so do
the system's own words on an error a message passes on.

Every line a command prints, on standard output and on standard error,
spells each control character a terminal acts on as `\xNN`, such as
`\x1b` for the escape, all but the tab and the line feed. That takes in
`brain list`, `brain show`, `brain links`, `brain steps`, `brain task`,
`brain status`, the ledger's report, doctor, the check, the lines
`brain gates` writes of its own, the port's and the upgrade's report,
and every refusal and note. So a file name or a header a cloned
repository brings shows its bytes and never drives the terminal. What a
gate's own commands print reaches the terminal as they wrote it. The
JSON forms escape them as JSON does. The hooks write to the agent, which
is no terminal, and spell out the findings and slips they hand back the
same way. A count reads `1 finding` for one and `2 findings` for more.

## Reading

| Command | What it answers |
|---|---|
| `brain version` | The version of Agent Setup this project carries, from `.agents/VERSION`. |
| `brain status [--json]` | The clock, the standing word and the current work first, then version, doctor health, counts per kind by status, the build specs among them, open reviews, the note waiting for the next session with the branch it was written on and when, unreadable files. A claimed note a session start could not remove, `.handover/handover.md.reading`, is the note waiting while none sits at `.handover/handover.md`, and its line says it was read before. Where more than one note waits, each session's own among them, the line gives their count and names `brain handover list` in place of the branch and the moment. A note still in `handover/` from before 2.2.0 is named only once it moves in, as [the handover](#the-handover) says. The JSON form carries all of that but the clock and the word. The note is under `handover`, null when none waits, else its `branch` and its `written` moment, the first null where the header names none and the second where the header gives none in the one ISO shape the tool writes a moment in, with `again` beside them, true for a note read before. Where more than one waits, those three are the reader's own note's where it has one, else the oldest's, and `count` beside them gives how many wait. The chain is under `task`, which is null when the file does not read as a chain. The `latest_handover` key and the `handover` count of 1.4.0 are gone. |
| `brain ack` | The clock and where the owner's standing word to proceed stands, off, held, or on with what is left of it and what ends it. |
| `brain ack tests` | The clock and each test file the owner's word to change its assertions holds for, with what is left of it, as [the test guard](#the-test-guard) says. |
| `brain list <kind> [--open \| --status X] [--severity X] [--area X] [--by X] [--type X] [--branch X] [--date X] [--json]` | One line per entry of that kind, narrowed by any field. Entries with an id come in the order of its number, so TODO-1000 follows TODO-999, as they do in each group of the todo, bug and build spec indexes, and the rest by their path. The kinds are bug, build-spec, decision, doc, memory, plan, review, rule and todo, each by its plural too. `--open` keeps every entry whose status keeps work open, a bug open or branched, a todo or a plan open, a build spec draft or acked, a review open, so one call answers what is still open. Beside `--status` it stops as an argument the command does not take, and it is refused for a decision, a doc, memory or a rule, which have nothing that stays open. Each file of the kind the list cannot read, and each folder of it the list cannot open, the kind's own folder among them, is named on standard error after the list, `not listed, since it cannot be read:` with its path from `.agents/` and the reason, so no entry is left out without a word, and the list still exits 0. |
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
answers nothing. On Windows a path whose part in front of the brain's
folder lies on a WSL share, `\\wsl.localhost\<distro>` or
`\\wsl$\<distro>` in any case and with either slash, the long
`\\?\UNC\` and `\\.\UNC\` spellings among them, is asked of the
disk only where the registry shows a WSL distro installed, since
Windows answers a read there by starting WSL and, with no distro,
offering to install it. Without one such a path answers nothing, as no
project can lie there. On Windows a path whose part in front lies on a
share of any other host, `\\host\share` or `//host/share`, the long
`\\?\UNC\` and `\\.\UNC\` spellings among them, is never asked of the
disk, since Windows hands the user's credentials to the host of a share
it reads and a cloned brain file could name any host. A device path,
`\\?\` or `\\.\` with either slash, is never asked of the disk either,
all but the long spelling of a local drive or volume, `\\?\C:\` or
`\\?\Volume{...}\`, since another such as
`\\?\GLOBALROOT\Device\Mup\host\share` reaches a share through the
redirector. No path that opens with `\\` or `//` and holds a `..` part
is asked of the disk, the long spelling of a local drive and a WSL share
among them, since Windows folds the `..` away before it reads the path,
so one such as `\\.\C:\..\UNC\host\share` may land on a share. Such a
path leads to this brain only where it spells the project's own folder.
A review answers to its folder too, by its name or its path,
`reviews/2026-11-fix-login` or `.agents/reviews/2026-11-fix-login/`,
a slash at the end or not. Every command that takes a key reads it this
way.

## Writing

| Command | What it does |
|---|---|
| `brain new <kind> --title T --description D [fields] [--category C] [--link P]...` | Files a new entry from the prose on standard input and prints its path, then any slip the check finds in it, as [the check](#the-check) says. The header names whoever files it as `author` and `editor`, as the paragraph under the fields by kind says. `--category` places a doc in a folder under `docs/`. `--link` repeats and takes a path, an id or a name, a path read as [a key](#reading) is, so `.agents/SYSTEM.md` reaches Agent Setup's rulebook as `SYSTEM.md` does. It is refused when it reaches nothing inside `.agents/`, a path into `.handover/` included, since no link goes into the folder whose one note is read once. A rule takes no `--category`, which is refused with `a rule takes no category, since a rule loads only from rules/ itself`. A rule whose title makes the name `rust` is refused too, since that name is [Agent Setup's Rust rule](#the-rust-rule)'s. A rule also gets its import in `AGENTS.md`, and the command then prints `a new rule loads only once the session is reloaded, so ask the owner to reload the session`, or, where `AGENTS.md` still does not import it, since the file is missing, cannot be read or carries no line the rules are imported below, `AGENTS.md does not import the rule, so it does not load, and brain doctor says why`, as [the rules](#the-rules) says. |
| `brain set <key> field=value ...` | Changes fields, checks values and dates, applies the lifecycle rules, stamps `updated`, and prints the entry's path. A field given twice in one call, such as `status=done status=open`, is refused, since one of the two values would be lost. Where the new status skips the steps that point at the entry, a todo or a build spec dropped or a todo or a bug refiled, it then prints one line for each step of an open entry that now reads skipped, `<id> step <n> now reads skipped, since <key> is <status>`, so the plan or the build spec that lost the step is seen to, and the entry that lost it stays valid. |
| `brain refile <key> --title T` | Renames for a new title. The id stays, every link follows, a body link written with percent escapes such as `my%20notes.md` among them, and a body link that carries a title after its path, in double quotes, single quotes or round brackets, such as `[x](path "Title")`, keeps it. A rule is refused a title that makes the name `rust`, and Agent Setup's Rust rule is refused any title, since it keeps its name, as [the Rust rule](#the-rust-rule) says. |
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
- rule: no extra fields and no status.

Every entry also carries `author` and `editor`, which no flag of `new`
takes and no index or file of Agent Setup's carries. `brain new` writes
both as the project's git user.name, or the login name where git names
none, each one line of plain text the house style never judges. Every
later write to an entry through the tool, `set`, `refile`, `steps`,
`task`, `ledger` and every doctor repair but the fill of a missing
name, sets `editor` to whoever runs it, while a hand edit of the prose
leaves it, since git holds every change. `set` takes `author=` to put
a name right, while an `editor=` given to it yields to the name of
whoever runs it. Doctor fills a name an entry lacks from git, as
[its section](#doctor) says.

Every header value a command takes is one line and is held to the
house style, `author` and `editor` aside. So a value with a semicolon
or an em dash, typed as the mark or as two hyphens between words with a
space on each side, is refused, while an en dash, as in a page range
such as `10–20`, passes. Code keeps its own punctuation, so a dash
inside a code span, such as the two hyphens of `git log -- docs` in
backticks, is no dash, while a semicolon is refused there too. A
control character in a value is no reason to refuse it, since every
line the tool prints spells it out, as the top of this page says.

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
every section the tool looks up. A section that holds nothing but HTML
comments says nothing a reader sees, so it is empty where a status
wants it written, a bug's Fix to go fixed, its Problem to go wontfix
and a todo's Done when to go done, and doctor names one left that way.

## The rules

A project's own instructions are its rules, one markdown file each in
`.agents/rules/`, every one loaded as a system instruction as a session
starts. A rule is a durable instruction this project alone needs,
written sparingly, never a note, a todo or a doc. `rules/project.md` is
the project's own and always there, since the port and the upgrade
write it where it is missing, as a placeholder whose comment says what
a rule is for. `rules/rust.md` is Agent Setup's, there exactly while the
project's root holds a `Cargo.toml`, as [the Rust rule](#the-rust-rule)
says. Any other is filed through `brain new rule`, which makes
the file's name a slug of the title. Only a file named with a lowercase
slug, such as `release-steps.md`, is a rule, so one whose name holds a
capital or a space never loads and doctor names its filename as it
does any kind's, and a dotted file is never read at all. A rule loads
only from `rules/` itself, so `brain new rule` takes no category, and a
markdown file in a folder below `rules/` is no rule, which doctor
flags.

`AGENTS.md` is Agent Setup's whole, written by the port and the upgrade, so
nothing in it is edited by hand, and the `pre-write` hook refuses a
write to it, as [its row](#hooks) says. Its
prose imports `@.agents/SYSTEM.md`, and below one comment line, which
says the lines under it are the brain tool's to write, it carries one
`@.agents/rules/<name>` import per rule, `project.md` first and the
others by name. That is the order every reader of the rules takes them
in. `CLAUDE.md` and `GEMINI.md` import `AGENTS.md`, so Claude Code and
Gemini CLI load every rule through it, and Codex gets each one from its
session start hook, after the rulebook. `brain new rule` adds the new
rule's import and, once `AGENTS.md` imports it, says to ask the owner
to reload the session, since a rule loads only as a session starts, and
the same holds for a rule changed or removed. Where `AGENTS.md` still
does not import it, the command says so in place of the reload, and
doctor names why. `brain refile` moves a retitled rule's import with it
and says the same. After a rule added or deleted by hand, or a merge
that leaves git's conflict markers in the import lines, doctor names
each stale line and `--fix` writes the imports again, as
[doctor](#doctor) says.

The lint hook reads the Lint headings of every rule, and `brain gates`
the Gates headings, `project.md` first and the others by name, as
[the lint hook](#the-lint-hook) and [the gates](#the-gates) say, while
headings in `AGENTS.md` never count. The check judges each rule as the
project's own prose, all but Agent Setup's `rust.md`, which it passes
over.

## The Rust rule

A project whose root holds a `Cargo.toml` is a Rust project to
Agent Setup, and it gets its Rust rule, `rules/rust.md`, which `AGENTS.md`
imports and every session loads like any rule. The rule stands exactly
while that file is there. Doctor holds that on every run, so Rust that
arrives after the port gets the rule, and Rust that leaves takes it
away. Its words come from the template the tool carries,
`.agents/skills/agent-brain/templates/rust/rust.md`, under a header
block doctor writes, so the rule is Agent Setup's whole, like
`AGENTS.md`.
The project's own Rust rules go in `project.md` or a rule of their own,
in addition to Agent Setup's. Only the root counts, so a project whose Rust
sits only in a folder below it gets no rule, no config and no finding,
a named limit, and it files a rule of its own.

Its Lint heading holds one line, `*.rs cargo fmt -- {file}`, which takes
the edition from `Cargo.toml` and formats the whole crate along with
the file. Its Gates heading holds five gates, which `brain gates` runs
in the rules' order, as [the gates](#the-gates) says.

- `cargo fmt --all --check`.
- `cargo clippy --workspace --all-targets --all-features --locked -- -D warnings`.
- `cargo test --workspace --locked`.
- `cargo mutants --in-diff` over the branch's diff from where it left
  the default branch, the first of `main`, `master`, origin's default
  branch, `origin/main` and `origin/master` that is there, edits not
  yet committed included and files git does not track left out. The
  diff is taken from the folder the gate runs in, the project's root, so
  a project in a folder of a larger repository tests its own change and
  no other. A mutant that every test survives turns it red, and a
  change that plants no mutant, the default branch itself among them,
  passes. Where none of those branches is there, it turns red and says
  so.
- `cargo deny --locked check`, which fetches the advisory database and
  so needs the network.

A gate whose tool is missing turns red with the line that installs it,
`rustup component add rustfmt` or `rustup component add clippy`, rustup
for cargo itself, `cargo install --locked cargo-mutants` or
`cargo install --locked cargo-deny`.

Beside the rule the fix writes Agent Setup's reference configs at the
project's root, `rustfmt.toml`, `clippy.toml` and `deny.toml`, each only
where it is missing. One the project keeps under another name its tool
reads, `.rustfmt.toml`, `.clippy.toml`, `.deny.toml` or
`.cargo/deny.toml`, counts as there, so no reference copy goes beside
it. Once written they are the project's to tune, and doctor never
judges or rewrites them. The fourth reference file,
`workspace-lints.toml` in the same templates folder, holds the lint
tables, which the project pastes into its root `Cargo.toml` itself.

Doctor's check of the rule gives these findings.

- A root `Cargo.toml` and no rule is fixable. `--fix` writes the rule,
  its import in `AGENTS.md` and the configs the project lacks, and the
  rule loads once the session is reloaded. So a run that writes it
  prints, before its findings,
  `wrote rules/rust.md, Agent Setup's Rust rules, with its import and the configs the project lacked, and a new rule loads only once the session is reloaded, so ask the owner to reload the session`,
  on standard error with `--json` so the JSON stays whole, and the
  port's and the upgrade's report carry the same line where their
  doctor run wrote the rule.
- A rule whose words below its header say other than the template is
  fixable, and `--fix` writes the template's words back under the header
  it keeps. So is a rule whose header still carries the `description`
  line an earlier release wrote, from before the product was called
  Agent Setup, and the same fix writes today's line over that one. A
  `description` a hand wrote is never touched. One that does not read
  as text is written again whole.
- A rule with no `Cargo.toml` at the root is fixable while it says
  Agent Setup's words, today's or those an earlier release from 3.1.0
  on wrote, untouched since, and `--fix` deletes it with its import,
  since git keeps its history and doctor writes it again once a
  `Cargo.toml` is back. One that says anything else is only flagged, so
  what is the project's moves into a rule of its own before the file
  goes.
- Another entry already named `rust` is flagged and the rule is not
  written, since a name is an entry's one key. Retitle that entry with
  `brain refile` and the next fix writes the rule.
- A missing `rust-toolchain.toml` is flagged, since the rule asks for
  the latest stable toolchain pinned there. The older `rust-toolchain`
  file counts as the pin too, since rustup still reads it and prefers
  it where both are there, so with it at the root nothing is flagged.
- Missing lints are flagged, a missing table with
  `workspace-lints.toml` named to paste from. A root `Cargo.toml` with
  a `[workspace]` table and no `[workspace.lints]` table is one finding,
  and each crate of the workspace that never sets `workspace = true`
  under its `[lints]` table is another, the root among them where it
  holds a `[package]` table too. A single crate, with no `[workspace]`
  table, is flagged where it has no `[lints]` table of its own.
- A template the tool cannot read is flagged, and the upgrade writes it
  back.

Only the workspace's own crates are held to its lints. Those are the
folders its `members` name, by glob, and every crate inside the root
that the root or one of those crates names by `path` in its dependency
tables, each followed in turn, less those under a path its `exclude`
names. A `path` under `[patch]`, `[replace]` or
`[workspace.dependencies]` is not followed. So a crate the workspace
never takes in, one it excludes, a vendored one, a test's fixture or a
separate workspace such as a fuzz folder's, is left alone.

A write of the root `Cargo.toml` through the agent's edit tools, a
delete among them, runs doctor in the post write hook, so the finding
is in the agent's context at once, as [its row](#hooks) says. A
`Cargo.toml` a shell command makes, such as `cargo init`, goes unseen
by every write hook. It is counted in the doctor line of `brain status`
at the next session start, and `brain gates` stays red on it until it
is fixed. The port and the upgrade run `doctor --fix` at their end, so
a Rust project gets the rule there with no step of their own.

The `pre-write` hook refuses a hand write to `rules/rust.md`, in any case of its name, a delete aside, after
which doctor names the rule missing and the fix writes it again.
`brain check` passes over it, as it does every file Agent Setup
writes whole. `brain new rule` and `brain refile` refuse a rule named
`rust`, and Agent Setup's rule keeps its name, since doctor would otherwise write
over a rule of the project's.

Before 3.1.0 a `rules/rust.md` was a rule of the project's own. So the
upgrade refuses, before its first write, a project stamped before 3.1.0
whose `rules/rust.md` says other than Agent Setup's words, and says to
retitle it first with `brain refile`, which the project's own tool,
still on its older release, runs. Once it is retitled that refusal is
gone, and in a Rust project the upgrade's doctor run writes
Agent Setup's rule.

## The standing word

The owner's ack is the word to proceed with what the agent proposed
next. Said once as "auto ack" with an end, it stands until that end,
and the agent passes the review's gates that normally wait for it,
SYSTEM.md rule 9.6 names them, saying in each report that it did. It never
starts a review, never opens a PR or merges, since those stay on the
owner's ask, and never passes a gate the rulebook or a project rule
holds for a person.

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
review with no name. `brain ack` given an end with no `on`,
`brain ack off` given any end, and either given a file, which goes with
`brain ack tests` alone, are refused too, each with a line that says
so. A folder where the word goes, which the tool never made and
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

## The test guard

An assertion a test file already holds is the spec's word on what the
code must do, so it changes or goes only on the owner's word, in every
language the guard knows. The `pre-write` hook refuses, exit 2, a write
that changes or removes one, unless the owner's word for that file
holds. A test file deleted or moved by a patch loses all it held, and
so does one a patch moves another file onto, which the move writes
over, so each is refused the same way. An assertion added, moved,
reindented or rewrapped passes, and so do a new test file and every
change to the code under test. The refusal names the first assertion
lost and the command that records the owner's word.

| Command | What it does |
|---|---|
| `brain ack tests <file>... --for 1h` | Records the owner's word for each file named, a path read from the folder the shell is in, with an end read the way `brain ack on` reads one, `--for`, `--until` or `--until-done`, the earlier end winning. The word is kept under the file's path from the project's root as the disk spells it, the way the hook spells the file it judges, so a name given in another case on a disk that folds case still reaches it. A word with no end is refused, and so are a file outside the project and a file that is not there, `<file> is no file, read from the folder the shell is in, and the owner's word holds for a test file that is there`. A second word for a file replaces the first. |
| `brain ack tests off <file>...` | Takes the word back for each file named, read the same way, a file gone since among them. It takes no end, and with no file it is refused. |
| `brain ack tests` | The clock and each file whose word holds, with what is left of it, or the one line that none does. |

The words live in one dotted file at the root of the brain,
`.agents/.ack-tests`, each under its file's path from the project's
root. Git ignores it like `.ack`, and the hook refuses a hand write to
it. A word holds until its time ends or its task is done, and the word
for a moved file is the word for the path it moves from, while a move
onto a test file that stands needs the word for that file too. A task done,
gone from the brain or doubled by a merge takes the word back for good,
as it does the standing word, so it never comes back when the task
reopens or a new entry takes its id. The session start, each prompt and
each tick after the agent's tool calls take back every such word, so a
task done and reopened between two writes still ends the word. Where the
brain's folder cannot be written the word stays in its file, off while
its task stays ended, and the next hook tries again, so only a task
reopened before then gives it back. A task the brain cannot read right
now, or a review ledger this checkout lacks, holds the word off until
it is back.

A file is a test file by its name or by its folder.

- By name: `test_*.py`, `*_test.py`, `tests.py`, `*_test.go`,
  `*_test.dart`, `*_test.rb`, `*_spec.rb`, `tests.rs`, `*_tests.rs`,
  `*.test.ts`, `*.spec.js` and the like in JavaScript and TypeScript,
  and a name that ends in `Test` or `Tests` in Java, Kotlin and Swift. A
  lone `test.py` or `test.rs` and a `*_test.rs` are not, since such a
  file is as often a test command's code, so a Rust one is guarded
  through its tests' attributes, as below.
- By folder: a code file of those languages inside a folder named
  `tests`, `test`, `__tests__`, `spec` or `specs`, in any case, so
  Swift's `Tests` counts.
- A snapshot: a `.snap` file anywhere, which is an assertion whole,
  every line below its header.
- A Rust file anywhere else: only the items a test attribute stands on
  count, a `#[cfg(test)]` on a `mod tests` block or a function, or a
  test function's own `#[test]` or `#[<path>::test]`, such as
  `#[tokio::test]`. A check in the code beside them is the code's. An
  item counts from the line the attribute opens, so
  `#[cfg(test)] mod tests {` on one line counts, and runs to its closing
  brace, a header with a `;` inside brackets, such as
  `fn check(bytes: [u8; 4])`, running on to its body. A test module kept
  in a file of another name, such as `parser_test.rs`, is guarded
  through its tests' attributes, and a helper there with no test
  attribute of its own is the code's. A `#[cfg(test)] mod tests;` keeps
  its tests in a file of their own, such as `tests.rs`, and counts for
  nothing in the file that names it.

The guard knows a check by the way its language writes one.

- Rust: every `assert` macro, such as `assert_eq`, `debug_assert`,
  proptest's `prop_assert` and insta's `assert_snapshot`, along with
  `#[should_panic]` and a `.assert()` call, such as assert_cmd's.
- Python: a line that opens with `assert`, a call of an `assert` method
  such as `self.assertEqual`, `pytest.raises` and `self.fail`.
- Go: `t.Error`, `t.Errorf`, `t.Fatal`, `t.Fatalf`, `t.Fail`,
  `t.FailNow` and testify's `assert` and `require`.
- Swift: the `XCTAssert` calls, `XCTFail`, `#expect` and `#require`.
- Java and Kotlin: calls of `assert` methods and `fail`.
- Ruby: `expect`, `assert`, `must_`, `.should` and `.should_not`, and
  a bare `should` or `should_not` where a matcher or an operator follows
  it, such as `it { should validate_presence_of(:name) }`,
  `it { should == 5 }` or `its(:name) { should =~ /bob/ }`. A shoulda
  block such as `should "be valid" do` names an example and is no check,
  and so is one with options after its name, such as
  `should "be valid", :before => lambda { setup } do`.
- Dart, JavaScript and TypeScript: `expect`, `expectLater`, the
  `assert` calls and `.should`.

A check's word inside a string on its line is no check, so a line that
names an example, such as `it "should add an item" do` or
`test "should get index" do`, is none, and the example holds only the
checks in its body, each on its own. In Rust, Go, Java, Kotlin and Swift
the guard takes out a quote in `'` only where it holds one character,
so an apostrophe in a Kotlin test name in backticks, such as
``fun `doesn't drop the quote`()``, pairs with nothing, and the check on
its line is still read and held whole. In the other languages a string
in `'` is taken out whole.

A check is held whole, over every line a formatter wraps it onto. It
runs on while a bracket it opens stays open, a bracket inside a string
aside, past a line that ends in a `\`, and on to a next line that opens
with a `.`, a chained call such as `.toBe(3)`. In Ruby only an RSpec
`expect do` block runs on to the `end` that closes it, the matcher on
its `end.to` line included, over any block inside it that a `do` at a
line's end or a keyword such as `if` at a line's start opens. Another
block check, such as `assert_raises(ArgumentError) do` or
`assert_difference("Product.count") do`, says what it expects on its
first line, so that line alone is held and its body is the test's
code, each check in it held on its own. A Go test's `t.Error` and the
other `t` calls only report a check made on an `if` line, so the `if`
line of the block the call sits in, the nearest line above with less
indent, is part of the check, a `} else if` among them. A comment or a
`t.Logf` between the two is no part of it, and a call in a block that
opens on any other line, such as a `for`, is held alone. Each check is
compared with its lines joined and their indent taken off, as often as
it stands, so one of two copies removed counts as lost. Its strings are
compared as written, a string in backticks among them, such as a
JavaScript or TypeScript template literal or a Go raw string, so the
spaces inside one stay, and the rest without the space a formatter adds
or takes away or the comma a wrap leaves before a closing bracket, so a
check a formatter wraps onto several lines, or joins back onto one,
reads as the same check. A space between two words stays, so
`assert not ready` is no `assert notready`. A comma right against its
bracket stays, and so does the comma of a tuple of one item, a paren
that holds no other comma and calls nothing, however it is wrapped, so
`(1,)` is no `(1)`. A snapshot's lines are
compared as they stand, since their spaces are the output they hold.
Any other change to a line of a check is a change to the check.

A patch's hunks that fit the file are applied in turn. Each hunk that
fits only by looser spacing is then placed as Codex's `apply_patch`
places it, where its lines match the file's with the spacing at each
end taken off, and the file is judged as all of them leave it, so a
check is read whole wherever the hunk lands. A hunk that fits nowhere
even so is judged on its own, by the assertions its lines before carry
that its lines after do not, the lines it keeps counted on both sides.
An edit whose old string the file does not hold word for word may land
all the same, so it is placed as the agents' tools place one, first
with a curled quote read as a straight one, as Claude Code's Edit reads
it, then as whole lines matched whatever their indent, as Gemini CLI's
replace matches them. An edit meant for every occurrence, Claude Code's
`replace_all`, Gemini CLI's `allow_multiple` or an
`expected_replacements` above 1, is placed at every place it matches.
The whole file is judged as the edit leaves it, so a check is read
whole wherever the edit lands. One that fits nowhere even so is judged
by its strings alone, by the assertions the old string carries that the
new one does not.

The guard falls short in these places.

- A value the check reads from elsewhere, a variable or a table of
  cases, is the code's, so a change to it passes.
- A Rust file that is no test file by its name or folder counts only
  what a `#[cfg(test)]`, a `#[test]` or a `#[<path>::test]` stands on,
  so tests behind another cfg, such as `#[cfg(all(test, unix))]`, or
  under a test attribute of another name, such as rstest's `#[rstest]`,
  are not guarded. A `#[should_panic]` there counts only inside a test
  module or below its test's own attribute.
- A Go `if` whose condition runs over several lines, or a failure call
  in an `else` block, leaves the call held alone, without the condition
  it reports.
- A Ruby block opened mid line, such as `x = if ready`, is not counted
  as open, so an `expect do` block around it ends early, at that
  block's `end`.
- A check's word inside a string that spans lines, such as a heredoc or
  a triple quoted string, or inside a JavaScript template literal or a
  Go raw string in backticks, is read as a check, since the guard takes
  out only a string that opens and closes in `"` or `'` on one line.
- A task done and reopened inside one tool call, such as one shell
  command, is never seen ended, so the owner's word for its test files
  stands.
- A write or a delete by a shell command is unseen, since no write hook
  sees it, so there the rule the agent works by is all that holds.
- A language not named above is not guarded.

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
or the one in its line's folder for a session on a line of its own, as
[the lines of work](#the-lines-of-work) say, with how the word follows
its session from line to line. Git ignores it like the standing word's,
and a file there that does not read as a time gives a line that says so
until `brain conclude off` clears it.

Two limits stand. The word is one file for a line of work, so two
sessions on one line share one time, and a handover the second writes
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
| `brain task on <key> [--replace] [--beside]` | Starts work on an open plan, build spec, todo, bug or review, by id, name or path, a build spec counting as open while draft or acked. With nothing on, it is the root, a build spec with no plan above it included. With a chain on, it goes under the innermost link only where the rules allow, which is a review under a build spec, a todo or a bug, and under a plan, a build spec, a todo or a bug the entry its current step points at. The entry already innermost is left where it is. Anything else is refused with the link that stands, and `--replace` sets the whole chain aside for it. Refused for a closed entry, a decision, a doc or a memory, an unknown key, or one several entries share. `--beside` starts a line of work of the session's own for the entry and leaves the chain in hand as it is, and an entry that is the root of another line puts the session on that line with no flag, both as [the lines of work](#the-lines-of-work) say. |
| `brain task done`, `brain task skip` | Marks the step the innermost link stands on done or skipped in the entry's file, so the work moves to the next pending one. Refused on a review, whose step is its batch, on a link whose entry closed, a review's among them, which the refusal names as closed for `brain task off` to drop, on a step that points at an entry, which takes its mark from that entry, on an entry with no steps, and once every step is settled. Once every step is settled the line gives the set command that closes the entry, with the closing date a plan, a build spec or a todo wants, and the Fix section a bug wants and the Done when a todo wants named. |
| `brain task step <n>` | Marks step `n` of the innermost link pending again, and the work stands on the first pending step, which is `n` unless an earlier step is pending too. Refused on a review, on a link whose entry closed, named as closed the same way, on a step that points at an entry, on an entry with no steps or no step `n`, and on a step that is pending already. |
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

### The lines of work

Two agents can work in one project folder, each on work of its own.
The folder has one line of work to begin with, the one every session
is on, whose chain, standing word and conclude word are the dotted
files at the root of the brain. A second agent, given other work while
the first one's chain stands, starts it with
`brain task on <key> --beside`. That makes a line of its own, a folder
under `.agents/.lines/`, with its own `.task`, `.ack` and `.conclude`,
and puts the session on it. From then on every command and every hook
line of that session reads and writes its line's three alone, so
`brain task`, `brain ack`, `brain conclude` and a review's gates never
touch the first agent's. The standing word stays behind with the work it
was given for, and the word to change a test file's assertions stays
the folder's, since it is about files.

The conclude word goes where its session goes, since the owner named
that time to the session and not to the work. It comes along to a line
the session starts with `--beside`, to one it joins by `brain task on`
or by taking a note, and back to the folder's line when its own line
ends. It goes along only while it still orders something, which is
until an hour past its time, and never over a time the other line still
counts down to, which the sessions there were given. The line left
keeps its own for whoever stays on it.

The tool knows the session from what the agent puts into the
environment of the commands it runs, `CLAUDE_CODE_SESSION_ID`,
`CODEX_SESSION_ID` or `CODEX_THREAD_ID`, the first that is set. It keeps
a short hash of it and never the id, no command takes one and none
prints one. A hook has to read the session its commands run in, and
each agent names it to a hook in its own way.

- Claude Code: puts its variable into hooks and commands alike. Its
  desktop app was seen on 2026-11-10 to do so and to keep one id through
  a resume and five compactions, and its docs say the same of the CLI.
- Codex: puts the session's id into its commands and hands a hook the
  same id in its event, which the Codex hook reads. A sub agent's
  commands carry their parent's session beside a thread of their own,
  and the session is the one read. That is how Codex's source read on
  2026-11-11. It was not run here, so Codex's support is unproven.
- Gemini CLI: gives its commands no id, only its hooks, so a Gemini
  session names none. There the folder keeps its one line of work and
  its one unnamed note, as before 3.2.0.

Where none is set, as in a plain terminal, the session is on the
folder's line, and `--beside` and a join are refused with that reason.

`brain task on <key>` with the root of another line's chain puts the
session on that line, with no flag and no refusal, and with the root of
the folder's own chain puts it back there. So a new session, which
starts on the folder's line, picks a line up by naming its work.
`--beside` for an entry that already roots a line joins that line too.
`--beside` is refused with nothing in hand, where a plain start is the
way, for an entry already on the chain in hand, and together with
`--replace`. Two sessions on one line share it. The refusal of a second
root, started plain over a chain that stands, names `--beside` with the
entry's key wherever the session is known, since that is where a second
agent finds itself stuck.

A line ends with its chain. `brain task off` that empties it takes the
line's folder away with its standing word, and each session that was
on it is on the folder's line again, its conclude word carried there
as above. A line whose
work closed stays until that session next starts work, since a reading
never writes, and that start is then judged from the folder's line.
`brain status` names every other line that has work in hand, one line
each that opens with `beside`, with the root's key, its description
and since when it stands, and with `--json` gives them under `beside`.
No hook names them. A retitle is followed in every line's chain. Git
ignores `.agents/.lines` through Agent Setup's ignore lines, doctor
never reads it, and the write hook refuses a hand write there.

## The handover

The note a session leaves for the next, per
[the brain's files](../SKILL.md#the-brains-files), which the session
start hook puts whole in front of the session it is for and removes, so
it is read once. Each session keeps a note of its own where the agent
names the session, as [a note per session](#a-note-per-session) says,
and the folder's one unnamed note is what the first row writes where it
names none.

| Command | What it does |
|---|---|
| `brain handover [--replace]` | Writes the caller's note from the prose on standard input, in place of the one there, and prints its path, `.handover/handover.md` for the unnamed note and `.handover/<hash>/handover.md` for a session's own, which replaces the note that session wrote before with nothing else judged, so what this row says of a waiting note for another branch and of `--replace` holds for the unnamed note alone. The header carries the branch, the head and the moment. The body opens with the record the tool reads off the machine, the branch at its head with the commit's subject, the uncommitted files, the standing word as `brain ack` prints it at the note's moment and the current work as `brain task` prints it, then the prose as it came, less the blank lines before and after it, so a first line's indentation and a last line's trailing spaces stay. The uncommitted files are listed one per line with their state, modified, added, deleted, renamed, copied, type changed, unmerged or untracked, git's own letter for any other, the first fifty and then one line, `and N more`, for the rest. A project below its repository's top lists only its own files, named from its own folder, a file renamed out of it reading `moved out of the project` under the name it left, and the note under either of its names and its lock are left out, each path matched as git's listing matches it, so where `core.ignorecase` is true two paths that differ in an ASCII letter's case alone are one. A path or a subject that holds a line break or a carriage return is written with it escaped, so each stays one line. A detached head reads as the branch a rebase or a bisect in progress works on, else `detached`. Where the file git keeps for that cannot be read, it reads `git could not answer` with the reason. The branch and the head read `no git` where git is not installed or no `.git` stands at the project's root or above it, `no commits yet` in a repository with none, and `git could not answer` with the first line git gave where it refuses the repository, or with the seconds it waited where git gives no answer in 10. Refused with no words on standard input, and with a folder standing at the note's path or at `.handover/handover.md.reading`, or a file standing where their folder goes. Refused too over a file at the note's path the tool never wrote or cannot read, which `--replace` never writes over, and while another session holds the note's lock past the wait below. Which waiting note a write replaces is in [the brain's files](../SKILL.md#the-brains-files), and one it does not, a note for another branch, is refused with its branch and its moment, which `--replace` writes over on the owner's word. With nothing at the path, a claimed note a session start could not remove, `.handover/handover.md.reading`, is the note waiting and is judged the same. With neither name in `.handover/`, a note of the tool's left in `handover/` before 2.2.0, `handover.md` first and then `handover.md.reading`, is the one note waiting and is judged the same, so one for another branch is refused until `--replace`. The write moves nothing, and removes a claimed note or an old one it replaces once the new note is in place. |
| `brain handover list` | One line for each note that waits, in the order of their numbers, which [a note per session](#a-note-per-session) says how a note gets and keeps. Each gives the note's number, when and on which branch it was written, the root of the work chain it recorded or `no work in hand`, and `this session's own` on the caller's, which is its session's note or, where the agent names no session, the unnamed one. `no handover waits` with none. Refused with a number, and while another session holds the notes' lock past the wait. |
| `brain handover take <n>` | Prints the note under that number whole and removes it, its number and a session's own folder with it. Where another session wrote the note and the work it recorded stands at the root of another line of work than the caller's, the session is put on that line and a last line says so, and where the agent names no session one line on standard error says why it stays where it is. The caller's own note leaves it on the line it is on. Refused with the list of the notes that wait for a number none of them carries, one whose note was taken, removed or written again among them, and without exactly one number. A note that could not be printed stays. |
| `brain handover cleanup [<n>...]` | Removes every note that waits but the caller's own, or with numbers the notes numbered, the caller's own among them where it is numbered, and prints one line for each it removed with its number. With nothing to remove it says so, and whether the caller's own still waits. Refused with the list, and nothing removed, where a number is no waiting note's. It runs on the owner's word alone, as SYSTEM.md section 8.4 says. |
| `brain handover off` | Removes the caller's own waiting note and says so, or says it has none and changes nothing. Refused with a number. |

[The brain's files](../SKILL.md#the-brains-files) say which session
start takes the unnamed note, how the hook claims it under
`.handover/handover.md.reading` and removes it, and what it leaves for
another session. `brain status` names a waiting note of the tool's
whatever branch it is for, and never a file under either name that the
tool never wrote or one it cannot open, which the hook names in one
line in the note's place. Where the removal fails, the hook says so on
standard error alone, since the context is out.

### A note per session

Where the agent names the session to the commands and hooks it runs, as
[the lines of work](#the-lines-of-work) say it does, each session keeps
a note of its own. It lives in a folder named by the session's hash,
`.handover/<hash>/`, under the two file names of the unnamed note, and
the folder goes with its note. `brain handover` writes it in place of
the one that session wrote before, whatever branch either was written
on, and touches no other note.

At a session start the hook takes the session's own note, whatever its
branch, on every start but a fork. A session with none of its own whose
start is `startup` or `clear` takes the one note that waits, the
unnamed one or another session's, whatever its branch. Where more than
one waits it takes none, and one line in the note's place gives their
count and names `brain handover list` and `brain handover take`. A
start whose source is `resume` or `compact` takes its own note and no
other. So an agent that gives a session a new id at a compaction leaves
that session's note waiting, which the status names and
`brain handover take` reads. A session that takes a note another
session wrote, at a start or through `take`, is put on the line of work
whose root is the work the note recorded, wherever such a line stands.
A session that takes back its own note stays on the line it is on,
which it may have gone to since it wrote the note.

Where the agent names no session, the folder keeps the one unnamed
note, written and taken by the branch rules of
[the brain's files](../SKILL.md#the-brains-files). A start with no
session named takes that note and never a session's own. The unnamed
note, one an older release wrote among them, is listed, taken and
cleaned up like any other, and an upgrade moves nothing.

A waiting note keeps one number for as long as it waits.
`brain handover list`, `take` and `cleanup`, and the line
`brain task on` prints below, give a note the number after the last one
ever given the first time they show it, the oldest first. The number
is kept in a file named `number` beside the note, and the last number
given in `.handover/numbered`, so no number is given twice. A note that was
taken, removed or written again leaves its number naming nothing, and
the next note in its place gets a new one. So a number read off the
list never reaches another note than the one it named, and `take` or
`cleanup` with a number that names nothing is refused with the list.

`brain task on` that puts the session on another line of work names,
under the chain, each waiting note another session wrote for that
line's work, with the number `take` reads it by. While another session
holds the notes' lock it names none, and `brain handover list` still
shows them.

A session start and a write take turns on the note's lock,
`.handover/handover.lock`, which every note shares, a session's own
among them. `list`, `take`, `cleanup` and `off` take it too, each
refused with words to run it again where another session holds it past
the wait.
The start holds it from its first look for the note until it has
removed it, so a second start waits and then finds none, and only one
session gets the note. A write
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
reads it while the branch is on a release before 2.2.0, and moves in at a
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
brain that is a symlink, the command line walks up from the folder as
the shell names it, `PWD` where that is the folder it runs in, so it
finds the brain through the link, and the note and the git its record
reads are those of the project that holds the link. Started where
`PWD` names another folder or none, it walks up from the folder the
system names, which lies past the link, so a brain it finds from there
is the target's, and so are the note and the git. On Windows a git
that starts a child process holding its output can run past the
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
| `brain new plan --title T --description D [--by owner\|agent] [--link P] [--category C]` | Files a plan from its prose on standard input, the Why and the Done when at least, its listed steps as the table, or an empty table when it lists none, a goal to find out. The steps go under a heading that reads `## Steps` and nothing more, and a Steps heading at another level or with a colon after it is refused, since the readers would never find it, while one inside code or an HTML comment is no heading and passes. `by` is owner unless said otherwise, `--link`, `--category` and what it prints work as for any kind, and a field flag a plan does not carry is refused. |
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
| `brain ledger set <ledger> F-NN [F-NN ...] field=value ...` | Changes a finding, or every finding named, each value one line taken as written. The findings come first and the changes after them, so no word meant for one finding lands on another. Several findings take the same changes in one write, so the findings a group's commit fixed get its hash in one call, whole or not at all, and a finding the ledger does not have refuses the call. A finding is known by its number, so `F-3` names `F-03`. The call is refused too, with a message that names the word, for a finding's id after the first change, a change before the first finding, a field given twice, a finding named twice, `F-3` beside `F-03` among them, and an id in lower case such as `f-03`, and it is refused for findings with no change. A ledger given as a finding's id, in either case, is refused as the ledger's key left out. The fields are severity, found-by, batch, status, fix and reason, and a line a hand edit lost comes back. A fixed finding always names its commit, `fix=<hash>`, a refuted, a wontfix or a deferred one says why in the same call, `reason=<one line>`, and the reason leaves with the status, as the fix does with a status moved away from fixed, save a `fix=` the same call gives, which stands on every finding the call names, whatever its status. A finding that moves into fixed names its commit in the same call or the call is refused whole, whatever fix an earlier call left on it, and one fixed already and set fixed again keeps its commit. A batch must be one the table has. The statuses are open, fixed, refuted, wontfix and deferred, and a refuted finding, like a wontfix, has landed and needs no batch. |
| `brain ledger report <ledger>` | The ledger's state in a few lines, counted from the file, with a blank status read as open the way close reads it. The first line gives the status and the counts, then one line per batch with its status, ack and counts, then a last line saying what comes next. That last line names an open or a fixed finding filed into no batch the table has before anything else, since a fix is verified by its batch, then walks the batches in order and says what the first unfinished one needs, the owner's word for a pending one, or its start when the ack is already on it or the standing word holds, a stamp from an earlier word counting only while the word holds, the ack on record for one that holds findings and has none, the standing word's while one holds, then its open findings, a late one included, its verification, and its marking done. Once every batch is done it says to close the ledger. |
| `brain ledger close <ledger>` | Flips the ledger to closed and writes the count under Summary. Refuses while a finding is open or has no status, and until the report's next line says to close the ledger, so a batch not yet done holds it open. |

A ledger's key is `<yyyy-mm>-<branch-slug>`, so `brain ledger batch`
given digits alone in its place, such as
`brain ledger batch 3 --status fixing`, is refused, the digits named as
a batch's number with the ledger's key left out.

A batch row, a finding or a finding's `- field:` line inside code or an
HTML comment reads as nothing, so a draft kept in a comment in the
ledger is never counted, numbered past or written to.

## Doctor

| Command | What it does |
|---|---|
| `brain doctor [--json]` | Every finding, one per line, `[fixable]` or `[flag]`, then their count, or `clean` where there is none. With `--json` it prints one JSON list in their place, each finding with its `path`, its `check`, its `message` and whether it is `fixable`. Exit 2 while any remain. The checks cover the headers, the sections, the links, the names, the indexes, the steps tables, the review ledgers, the style copies, the skill stubs, the front doors' imports, the import lines inside each rule, the rules' imports in `AGENTS.md`, [the Rust rule](#the-rust-rule) where the project's root holds a `Cargo.toml` or the rule stands, [the read guard](#the-read-guard) in a project and what a write left behind. |
| `brain doctor --fix` | Applies every fixable repair, in passes until a pass changes nothing, then reports what is left. A repair that fails is reported as a flag with the reason. |

Doctor checks that nothing was left behind by an interrupted write, that
there are no stray files, meaning every markdown file under `.agents/`
outside a dotted path, `.handover/` among them, is either an entry the
store lists or a file Agent Setup owns, so one left in `handover/`, where
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
tables as the steps section says, indexes current, no em dash, typed
as the mark or as two hyphens between words, or semicolon in a header's
name, description or links, which flow into the indexes, an en dash
and a dash inside a code span passing, no machine paths, nothing shaped
like a secret, the version stamp a version, the chat style copies for
Codex and Gemini CLI matching the Claude Code one where the project
keeps those agents' folders, and the skill stubs Claude Code finds each
skill through, one per skill Agent Setup ships and one per skill folder the
project keeps, each `.claude/skills/<name>/SKILL.md` holding the
sheet's header exactly as the sheet writes it, a folded value or a list
among them, over a fixed body that sends the agent to the sheet. A stub
is known by that body, whatever its header holds. It reports too a
stub whose header fell behind its sheet's, and where a stub belongs a
link of any kind, a Windows junction among them, a plain file, or a
copy of the sheet, which is a byte for byte one or, for a skill
Agent Setup ships, any SKILL.md of the skill's name, such as the copy an older
release kept.
It reports a sheet it cannot make a stub from, one that is not UTF-8
or has no header block, with the reason, a stub Agent Setup wrote or a
dangling link an older release made for a project skill since gone from
the brain, a real folder where a stub belongs that holds no SKILL.md
or a skill of its own, which is a person's, a skills folder it
cannot list, and a launcher `.agents/brain` that is missing, which an
upgrade through a tool older than it leaves out, a link there that
leads to no file counted as missing. Doctor reads no file
in `.handover/`, nor in a folder whose name differs from it in case
alone, since each is a dotted folder. To every link check such a folder
is `.handover/` itself where git's `core.ignorecase` is true or git
gives no answer for that flag, outside any repository it opens or past
its time limit. A folder of Agent Setup's named in
another case, such as `Skills/` for `skills/`, is Agent Setup's only where
git says the flag is true, so where git gives no answer on a disk that
ignores case, its files are named as strays under that name, the casing
to put right. A markdown file whose `.md` is in another case, such as
`rules/style.MD` or `todos/TODO-007-loud.Md`, outside a dotted path and
`skills/`, is flagged as a stray too,
`ends in .MD, which the brain reads as no entry on any system, so rename it to end in .md`,
since the tool reads only a lower case `.md` as an entry, so a rule
there would never load and nothing else would say so.

A machine path is a path from the root that runs through a `Users` or
`home` folder to a name under it, such as `/mnt/c/Users/someone`, behind
`file:` or inside a link too, or a drive letter's root in either case,
such as `C:\` or `c:\`, with no letter before the letter and, for a
lower case one, no backslash either, since that is an escape.
A web address, one that opens with `http://`, `https://`, `ws://` or
`wss://`, passes up to its query or a pipe, so a path in its query is
still reported, and so is one in an address of any other scheme. A path
that starts with a name or a dot passes, as in `web/home/page.tsx`, and
so does such a folder with nothing under it, as in `/home/`, and
anything in code. Two limits stay on purpose. A home folder under a
mount whose name holds a space is not seen, since that name cannot be
told from the words before a path. A route from the root through a
`home` folder, such as `/app/home/feed`, is reported like any machine
path, so it goes in a code span.

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
paragraph before it, a `#` heading or an underlined one, `===` or `---`
under a paragraph line, so such a tag right under either opens a block.
A line that holds only a comment or a fence's marks ends the paragraph
before it too, while a line of nothing but code spans is part of one.
A blank line is one with nothing on it as written, so a line that holds
only a comment never ends a block. A block nothing closes runs to the
end of the file. So an `@AGENTS.md` on the line under `<details>` is no
import, while one set off from the tags by blank lines is. Whether a
paragraph is open is the shared reader's word, and that reader knows no
raw HTML block, so a lone tag on the line right after a one line
`<pre>` block, with no blank line between, opens no block.

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
differently, save a rule's import with a fragment written from the
project's root, which the rules' paragraph below names. Nor is one
whose path ends in emphasis markers, `*` or
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
opens with `/` or with a drive, such as `@D:/team/notes.md`, which
Windows reads from that drive's root, since it is there on one machine
and missing on the next, and one that climbs out of the project's
folder and comes back in by retracing the folders it climbed out of,
such as `@../../apps/web/x.md` in a project at `repo/apps/web`, since
another checkout may go by other names. Neither is looked up. One that climbs
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
A missing chat style copy, `.codex/plain-and-short.md` or
`.gemini/plain-and-short.md`, says `brain doctor --fix` writes it where
the fix does, beside the agent's folder while the Claude Code style it
copies reads. Each import line gives one finding at most, and a slip written on two
lines is named twice.

The rules imports are asked of a door as a whole. `CLAUDE.md` and
`GEMINI.md` are reported when nothing in them leads to `AGENTS.md`,
since the rules then never load. Here every `@` an agent may open
counts, anywhere outside code, comments and raw HTML, at a line's start
or after whitespace, `*`, `_`, `(`, `[` or `>`, in a sentence or on a
line of its own, so an import line such as `>@AGENTS.md`, its quote
marker right before the `@`, counts too. Emphasis markers, trailing
punctuation and a fragment are set aside, and the path may reach
`AGENTS.md` under any spelling of its case, through `./` or through a
link that resolves to it. The markdown files the door imports are
followed too, each `@` in one read the same way from that file's own
folder, up to five imports deep, as deep as Claude Code follows them.
They are walked breadth first, so each file is reached first by its
shortest path and read once a walk, the door itself counted as read,
and a deeper path to a file never keeps a shorter one from reaching
what it imports. A path that opens with `/` or `~`, or one that climbs
out and back in by the folders' names, never counts, since it leads
there on one machine alone, and nor does one with a backslash, an
escaped space such as `@docs/team\ notes.md` among them.
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

Doctor reads every rule in `.agents/rules/` for its import lines too,
since a project's section 0 sat in `AGENTS.md` up to 2.7.1, where the
front door check read it, and is `rules/project.md` from 3.0.0. A rule
is read as a door is, its code, comments and raw HTML blanked, and its
import lines alone are judged. They are held to the slips above, glued
punctuation, a backslash, a path from the root of the disk, a climb out
of the project and back in by its name, and a target that is not
there, is spelled in another case, is not a regular file, cannot be
read or holds no text. Each finding is named under the rule's path in
the brain with the check `import`, such as
`rules/project.md: import: imports @gone.md, which is not there in .agents/rules/`.
A path in a rule is read from `.agents/rules/`, as Claude Code and
Gemini CLI read an import from the folder of the file that holds it,
and whether a token leads to a file, which makes it an import, is asked
from there first. So `@../docs/setup.md` is `.agents/docs/setup.md`,
and `@README.md` is `.agents/rules/README.md`, named while it is not
there. A path that climbs out of the rules folder and stays inside the
project, such as `@../../README.md`, is looked up like any other. A
`..` steps up from the folder named before it, as the agents read a
path by its text, here as in a door and in each file a door imports, so
it never climbs through the target of a linked folder. Where `.agents`
is a link to a brain kept outside the project, as a brain shared
between checkouts is, `@../../README.md` in a rule still reaches the
project's own `README.md`, never a file beside the shared brain. The
finding on a path from the root of the disk, or on one that climbs back
in by name, says to write it from
`.agents/rules/, the folder the rule is read from`, where a door's says
from the project's folder. Whether git ignores a missing target, and
whether `--fix` writes it as a chat style copy, are asked by its path
from the project's root, so `@local.md` in a rule is each clone's own
while git ignores `.agents/rules/local.md`. A token that leads to no
file from the rules folder but to one from the project's root, a
`@package.json` as much as a `@README.md`, is an import written from
the wrong folder, whatever git ignores, and its finding gives the path
that reaches it,
`imports @package.json, which is not there in .agents/rules/, though the project's root holds it, so write @../../package.json`.
So a `@CLAUDE.local.md` in a rule gets that finding while the root
holds the file, though a git ignore pattern with no slash, such as
`CLAUDE.local.md`, matches inside the rules folder too. The path it
gives is spelled as the root spells the file, so a `@Package.json`
where the root holds `package.json` is told to write
`@../../package.json`, which loads where case counts too. That finding
is never given for a path with a `..` in it, which doctor takes as
written from some folder on purpose, nor for one from the root of the
disk, a drive or the home folder, which is no path from the project's
root. So in a project inside a larger repository, a rule's
`@../docs/setup.md` is named as not there in `.agents/rules/`, with no
path to write, even where the folder above the project holds
`docs/setup.md`. An import with a `#` fragment, such as
`@docs/setup.md#install`, gets that finding too, held to the same
rules, its path up to the fragment looked up and the fragment kept in
the path it gives, `@../../docs/setup.md#install`. Any other import
with a fragment is not judged, nor is one that also holds an escaped
space. A rule that cannot be read is left to the header
check, which names it as `frontmatter: the file cannot be read`, so it
is named once, and the next rule is still read. Codex gets each rule as
text from its session start hook and reads no import, so an import in a
rule loads in Claude Code and Gemini CLI alone, and doctor judges it as
those two read it.

Where doctor cannot judge, it says nothing, which leaves some slips
unnamed. Every `@` that is not alone on its line is silent, so a slip
in a sentence, such as the full stop in `See @docs/setup.md.`, goes
unnamed, and so does a line passed over above. A sentence such as
`The rules are in @AGENTS.md.` counts as the rules import and gives no
finding, though the full stop glued on keeps the file from loading. A
token with no `.md` ending that leads nowhere reads as a mention, so
`@docs/SETUP.` alone on a line is silent until `docs/SETUP` is there.
Only the import lines of a front door or a rule are judged, never those
of another file a door or a rule imports, which doctor reads at most
for the rules import, and an `@AGENTS.md` more than five imports deep
is never found.

The rules check reads the lines of `AGENTS.md` below the comment line
the rules are imported under, and holds them to one import of each of
[the rules](#the-rules), `project.md` first and the others by name, and
nothing else. It names a rule left out, which never loads, an import of
a file that is no rule, a rule imported more than once, every other
line there, git's conflict markers from a merge among them, and
imports out of that order, each fixable. Above that comment line the
text is Agent Setup's, which doctor cannot tell from an edit, since a
project holds no copy of Agent Setup's words, so an import or a sentence
added there is left for the upgrade to write back. An
`AGENTS.md` with no such comment line is flagged, since no rule loads
there, and the upgrade writes it. A missing or unreadable `AGENTS.md` is
the front door check's to name. A markdown file in a folder below
`rules/` is flagged too, since a rule loads only from `rules/` itself.

`--fix` repairs a missing or blank `updated` date, blank `links`
written as `[]`, an entry's missing `author` or `editor`, which it fills
from git as the end of this section says, a name that disagrees with
its filename, a link written as a name, a file linked more than once in
one header, which keeps the first, a pointed step's mark that drifted
from its entry or its pointer left behind by a refile or written by
name, a numbered list under a plan's or a todo's Steps and a plan with
no Steps section, which get the table, a stale index, a stale chat
style copy, a skill stub that is missing or whose header fell behind
its sheet's, and where a stub belongs a link of any kind or a Windows
junction, a plain file, git's stand in for a link where
`core.symlinks` is off among them, or a copy of the sheet, each of
which the stub replaces, a missing launcher, written from the text the
tool holds, a link in its place replaced rather than written through,
the rules' import lines in `AGENTS.md`, written again from the rules on
disk, Agent Setup's Rust rule, written with its import and the configs the
project lacks, its words written back where they drifted and the rule
retired where no `Cargo.toml` is left, as
[the Rust rule](#the-rust-rule) says, and a
rule or a sandbox entry of [the read guard](#the-read-guard) missing
from `.claude/settings.json` while `.claude` stays inside the project.
Each repaired file gets today's date, and a repaired entry the name of
whoever runs the fix as its `editor`, save one whose only repair is
that fill, which keeps its date, and the Rust rule whose words were
written back, which keeps its header's people, and its `description`
too but one an earlier release wrote. The only things `--fix` removes are
what an interrupted write left behind, a temporary file or a scratch
folder named the way the tool names them, the half made stub an
interrupted stub repair left beside its place, which the next repair
of that stub clears, the link or the plain file sitting where a
skill's stub belongs, which the stub replaces, and for a project skill
since gone from the brain, its stub, whatever sits beside it, with its
folder once nothing else is left there, or a link an older release made
under `.claude/skills` into the brain's skills folder that dangles,
leading to nothing at all, and Agent Setup's Rust rule with its import
once no `Cargo.toml` stands at the root, while it still says
Agent Setup's words, today's or an earlier release's. The stray pass never removes a link or a
folder that still leads somewhere, whatever it holds, nor a file
beside a stub. A repair that rewrites a file, a stub, a
stale index, a chat style copy or the settings the read guard goes
into, writes a real file in place of any link standing there. No other
file is removed.

Where a link, a plain file or nothing stands in a stub's place, the
repair makes the stub in a folder of its own beside the place,
`.<name>.stub`, clearing one an interrupted repair left there, and only
once the stub is written takes away what stood there, a link as the
link alone, and moves the folder in. So nothing is ever written
through a link, and a write that fails leaves the place as it was for
the next fix. Into a real folder, one holding a copy or a stub behind
its sheet, the repair writes the one `SKILL.md` whole in place, and the
rest of the folder, the other files of an old copy among them, stays.
The repair runs the same on every system, Windows without Developer
Mode included. In a checkout whose git still holds the old links, it
leaves them deleted and the stubs new, for the next commit. A stub
follows its sheet's header alone, so a change to the sheet's body
needs no new stub.

Some layouts keep a stub's repair back, and doctor names the trouble
with the reason and writes and removes nothing at that place. Where
`.claude/skills` itself leads into the brain, a stub written there
would land on a sheet, so the repair waits until `.claude/skills` is a
real folder,
and the stray pass removes nothing there either. Where the brain's own
way to a skill's sheet passes through what the repair would take away
or write over, such as a `.agents/skills/<name>` linked to its folder
under `.claude/skills`, or a sheet that is a link to the `SKILL.md`
there, the repair waits until the sheet sits under `.agents/skills`
with no link through `.claude/skills`. Doctor walks that way link by
link, the way the system follows it, and a way of more than 40 links,
a loop among them, counts as passing through. In a skills folder
shared outside the project, a link, a copy or a stub of the skill
passes, and any other stub to write, or stray to remove, there is a
person's. Whether `.claude/skills` leads into the brain or out of the
project is asked by the disk's identity, so on a disk that folds case a
link to `../.AGENTS/skills` leads into the brain, and one into the
project under another case of its folder stays inside it.

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
| `brain check [paths...] [--json]` | Prints one line per slip, `path:line: message`, or `path: message` for a slip with no line such as a file that cannot be read, or `commit <hash>: message` for a commit, then `clean` or the count of findings. With `--json` it prints one JSON list in their place, each slip with its `path`, its `line`, 0 where it has none, and its `message`. Exit 2 while any slip remains. Each note goes to standard error and is no slip, such as a file named and passed over, a file that is not markdown among them, a warning git gave as it listed the files, or the commits not read. With no paths it reads the project's files and the branch's commits, and with paths the files named and those under each folder named, never the commits. A path that is not there, or that leads outside the project once its links are resolved, is refused, exit 1, and so is a run where git cannot list the files, as outside a repository, or read their attributes. The project's folder is known by the disk's identity, so on a disk that folds case a path through another case of it lies inside. |

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
handover note, since no hand puts them right. The files Agent Setup writes
whole are passed over too, since a slip there is Agent Setup's
and the next upgrade writes them back. Which files those are goes by the
project's version stamp, as the upgrade decides, so a project's own file
under a name Agent Setup took later is read. `AGENTS.md` is among them,
and so is Agent Setup's Rust rule, `rules/rust.md`, whatever the stamp, while
the project's own rules are its own prose and are read. A file named on the
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
| `brain gates` | Runs the gates the project names, in order, then the check with no paths, over the project's files and the branch's commits, then doctor over the brain, and prints what it finds on standard output. Each gate is named on one line, `gate <n> of <m>, <name>`, before it runs, and the first red one stops the run, saying which, with its exit code or the signal that killed it, and that the rest did not run, exit 1, with neither the check nor doctor run. Past the gates the check and doctor both run whatever the other finds, each slip, note and finding printed, then `check clean` or its count and `doctor clean` or its count, a note counting as no finding. A check that cannot run, since git cannot list the files or read their attributes, is one line that counts as a finding. Exit 0 when every gate is green and both are clean, 2 while the check or doctor has findings or a Gates heading holds no gate. A rule that cannot be read or decoded exits 1 in words that name it, `rules/<name> cannot be read, <reason>, so no gate ran`, with nothing run. |

The gates sit in the project's [rules](#the-rules), `project.md` first
and the others by name, under each heading whose text holds the word
gates, such as `### Gates` or `### 0.2 Merge gates`, at any level, with
hashes or underlined. A word in an HTML comment, a tag's attribute, an
image or a link's target does not count, nor does one with an ASCII
letter, a digit or an underscore against it, such as `ci_gates.yml`. A heading that sits under no Gates
heading and is none as it shows, though its text as written, outside
code spans and HTML comments, holds gates with no ASCII letter or digit
right beside it, is named in one line that says it holds the word as
written and not as shown, so its blocks do not run. Each Gates heading
runs to the next heading at its level or above, or to the end of its
rule, and each fenced block under it is a gate, in order. The block's info
string picks the shell, `bash`, `shell` or none for bash, `sh` for sh
and `zsh` for zsh. A block of another language, or one with nothing but
blank lines and comments, is named in one line as not run and left out
of the count. A block inside a quote, an indented code block and
anything inside an HTML comment are no gate. A gate's name is its first
line that is neither a comment nor a `set` line.

Where no rule has such a heading, the run says so in one line, and the
check and doctor are the gates.
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

The tool has no gates of its own, so the gates the rules name are the
only ones that run.

The gates fall short in these places.

- Gates a rule names under no heading holding the word gates do not
  run, and where no rule has such a heading the run says so in one line.
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
  blocks. Keep the word out of the markup of a heading in a rule that is
  not the gates.
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
- A `<!--` that a rule never closes hides from GitHub everything after
  it, while the run takes a comment with no `-->` as hiding nothing, so
  a Gates heading under it still runs its blocks, each named as it
  starts. Close the comment.

## Port and upgrade

Both run from a checkout of Agent Setup, since a project without the
tool has nothing to run, so the port is
`python3 <agent-setup>/.agents/skills/agent-brain/scripts/brain.py port`
from the project's root, with `<agent-setup>` the folder of your clone
of Agent Setup, and the shorter `python3 <agent-setup>/.agents/brain port`
works too. A project that already carries the tool can run
its own copy with `--kit` pointing at the newer checkout. Without
`--project`, a port works on the top of the git repository around the
current folder and an upgrade on the nearest folder at or above the
current one that carries a brain, and neither ever works on your home
folder. The report's first line names the folder either one works on,
and `--project` has to name a folder that is there. Both refuse, before
the first write, a project where a file of Agent Setup's they would write under
`.agents/` or in the agent folders sits behind a link that leads out of the
project, naming the file and where the link leads, until the link is
moved aside. Each file under `.agents/` is checked at its place under
`.agent/` too, the brain's folder before 1.0.0, since the upgrade's
migration renames that folder to `.agents/` before the install writes
through it. So a `.claude` folder linked into a checkout of Agent Setup never gets
the project's settings. A link that leads back into the project under
another case of its folder, on a disk that folds case, stays inside it,
since the project is known by the disk's identity.

Both refuse as well, before the first write, where the install would
stop part way. That is a file, or a link that leads to no folder,
standing where they make a folder, such as a file named `.claude` or
one in place of `.agents/bugs`, and a folder standing where they write
a file, each named until it is moved aside. The brain's places are
asked where the brain stands when the run starts, so on the layout
before 1.0.0 a file in place of `.agent/bugs` is named, since the move
to `.agents/` comes before the install. It is also a run that has a sub
agent definition of the review to write, or one Agent Setup retired to
remove, under `.claude/agents` where nothing can be written, which they
find out by making a file there and taking it away again. A run with
nothing to write or remove there, a file of the project's own under a
retired definition's name left as it is among them, makes no such try.
Claude Code's sandbox refuses every write there whatever a project's
settings say, so run the port and the upgrade from a terminal, or let
Claude Code run that one command outside the sandbox.

| Command | What it does |
|---|---|
| `brain port [--kit PATH] [--project PATH]` | Installs Agent Setup into a project with no brain, which means its files under `.agents/`, the front doors, `AGENTS.md` with an import of each of [the rules](#the-rules), and `.agents/rules/project.md`, which carries the first `## 0.` section an old `AGENTS.md`, `CLAUDE.md` or `GEMINI.md` held, or else the placeholder, with every other word those doors held of their own quoted in `.agents/docs/front-door-words.md`, as the paragraphs under this table say, the hook configs merged beside the project's own hooks, Claude Code's with [the read guard](#the-read-guard), the review's sub agent definitions, the chat style, the ignore lines, the version stamp, then `doctor --fix`. Ends by listing what is left to file through `brain new`, the markdown git sees outside the dot folders, root files one by one and deeper ones counted by folder, with `docs/` marked as the one the rules let a project keep (outside git, the root markdown and the usual folder names, a dot named file left out either way since the brain never files one). Refuses when a brain exists. |
| `brain upgrade [--kit PATH] [--project PATH]` | Brings a project that has a brain up to Agent Setup. Runs the migrations the tree calls for first, then the same install. The one migration so far, to 1.0.0, runs while a `.agent/` folder is there. It moves it to `.agents/`, points every file git tracks or sees that names the old folder at the new name, Agent Setup's own skill folders aside since the install replaces those, and a copy of Agent Setup kept in a folder inside the project aside too, known by the dotfile `.kit` beside the tool's code at `.agents/skills/agent-brain/scripts/.kit`, which ships into no project, or by the tool's tests beside its code in a copy from before they moved out, since its files name the old folder as Agent Setup's own history (outside git, the root markdown, the ignore file and the brain's own markdown), refuses by name while a file git ignores names it, since such a file can neither be saved first nor be left behind, and carries section 0 out of the old `CLAUDE.md` into `.agents/rules/project.md`. The stamp in `.agents/VERSION` says which release the project is on, and a release of Agent Setup older than it is refused. Every run removes what Agent Setup wrote and no longer ships, each file named in the report, a file it dropped from one of its skill folders, the brain's spec files it kept under `.agents/spec/` before 2.0.0, with the folder once it is empty, and the review's fixer and hunter definitions under `.claude/agents/` where the project's stamp says Agent Setup wrote them, from the release each shipped in up to 2.0.0. A file of the project's own in `.agents/spec/` stays, named in the report to file under `docs/` through `brain new`. The doctor run at its end fills the `author` and `editor` of each entry that lacks them from git, as [doctor](#doctor) says, and the report says how many entries it filled. Refuses without a brain, refuses while a file it would replace holds uncommitted work, a hand edit to the stub of one of Agent Setup's skills under `.claude/skills` among them since the doctor run at its end rewrites it, and refuses, before its first write, a project stamped before one of Agent Setup's skills shipped that keeps its own folder under that skill's name, in `.agents/skills` or in `.claude/skills` where the stub goes, and a project stamped before a sub agent definition shipped that keeps a file of its own under that definition's name, each definition counted from its own release since a skill gains them later, until the folder or file is moved aside. A folder or a file Agent Setup itself wrote is known by its bytes, a stub by its body, and passes. Refuses as well, before its first write, a brain holding an entry named `project` anywhere but `rules/project.md`, or `front-door-words` anywhere but `docs/front-door-words.md`, since a name is an entry's one key and those are the names the project's own rule and the doc of the front doors' own words take, with words such as `.agents/docs/project.md is named project, the name the project's own rule takes from 3.0.0, so retitle it first with brain refile`. Refuses the same way a project stamped before 3.1.0 whose `rules/rust.md` says other than Agent Setup's Rust rule, since that file was the project's own rule before Agent Setup took its name, as [the Rust rule](#the-rust-rule) says. Refuses too a project that is Agent Setup itself, or a worktree or a clone of it, since that is where the tool's code is the work. It knows one by the folder under any spelling, or where the two folders, each the top of its own work tree, meet on walking back through their local origins, at most eight clones and a bare repository among them, to a folder or a remote repository both come from, so a copy of Agent Setup vendored inside a project's repository, or a project folder inside Agent Setup's, is no clone of it. The walk looks for a local origin under the names git's clone tries for it, the path with `/.git` after it, the path itself, then with `.git/.git` and with `.git` after it, and goes into the first that is a folder, where git is asked under `GIT_CEILING_DIRECTORIES` set to that folder's parent, so it answers for that folder alone and never for a repository above it. Every git call of the walk runs without the variables `git rev-parse --local-env-vars` names, so a `GIT_DIR` or a `GIT_WORK_TREE` a git hook exported never answers for a folder the walk asks about, while config given in command scope, through `git -c` or `GIT_CONFIG_COUNT` with its keys and values, still holds, so a `safe.directory` or a `safe.bareRepository` given that way reaches every git the walk runs. The walk asks git only `rev-parse` and `remote get-url`, so it opens no transport and runs no command a walked folder's config names. It reaches a folder whose name holds a byte that is not UTF-8 on every POSIX file system, while such a path on Windows, and under a locale that is not UTF-8 a name outside its codec, is taken as not there. It ends where git opens no repository, at a plain folder standing under a name git's clone tries first, such as `/srv/hub` beside the bare `/srv/hub.git` a project was cloned from by `git clone /srv/hub`, and at one git keeps closed for safety, a bare origin while the owner's config sets `safe.bareRepository` to `explicit` or a folder git refuses for its owner. Two clones of one such folder still meet there, since a folder is recorded before git is asked. An origin that is a file naming its repository is no folder to go into, so the walk ends at its path. Two clones that name it by two spellings of that path do not meet. On Windows an origin on a WSL share, a path or a file URL, is gone into only where a WSL distro is installed, as [a key](#reading) on such a share is read, and without one the walk records it by its spelling, a `.git` at its end taken off, and ends there, so WSL never starts. A clone the walk misses in any of these ways is upgraded as any project is, Agent Setup's files written over its copies of them under the refusal over uncommitted work. A walked folder holding a named pipe called `HEAD` holds the walk up as it holds git's own clone up, since the upgrade's git runs with no time limit. Git matches the ceiling against the folder's path as text, in the system's spelling, so an origin spelled another way on a disk that takes two spellings for one, by case or by Unicode form, or reached through a second path to the same volume such as macOS's `/System/Volumes/Data`, leaves git free to answer for a repository above it. Git also reads a `:` in the ceiling, or a `;` on Windows, as a break between folders, so an origin whose parent's path holds that separator does the same. That matters only where one repository holds both Agent Setup and the project, and there the upgrade takes the project for a clone of Agent Setup and installs nothing, which writes over no work. The walk is built for git 2.28 or later. Every run moves the tool's note and its claimed copy for the checkout's branch, `handover.md` and `handover.md.reading`, out of `handover/`, where the note lived before 2.2.0, into `.handover/`, the move a session start makes too under the same branch rules, as [the handover](#the-handover) says. The report names each note it moved, each for another branch, which stays there for that branch, each that waits behind a note `.handover/` already holds under either name until that one is gone, and each the system refused to move, with the reason, to move by hand, and the run goes on. Agent Setup's ignore block keeps the `.agents/handover` line beside `.agents/.handover`, so a note an older session left there never enters git before it moves. Every run names too, while they remain, the notes a project filed under `handover/` before the folder became the tool's, any markdown file there, nested too, that is not the tool's note, one at the note's own path whose header is not the tool's included, and says to move what still matters into `docs/` or `memory/` through `brain new` and delete the rest, which the upgrade never does itself. |

What is the project's stays the project's, which is everything under
`.agents/` that is not Agent Setup's, its rules among them but
Agent Setup's `rules/rust.md`, which [the Rust rule](#the-rust-rule) says doctor
writes, `README.md`,
`CODEOWNERS`, and any hook or setting of its own in the agent folders.
From 3.0.0 on every front door is Agent Setup's whole, so the upgrade reads
no section 0 there and quotes nothing, and a door edited by hand is
written back like `SYSTEM.md`, its old text still in git, the rules
left as they were.

The port, and the upgrade of a project stamped before 3.0.0, move the
first `## 0.` section with words in it that a front door holds,
`AGENTS.md` read first, or `CLAUDE.md` on the old `.agent/` layout,
into `.agents/rules/project.md` under its title, the section's own
heading left off. The section alone moves, and it moves live, as it was
live in the door, so its Lint and Gates headings run from the rule.
Every relative markdown link and `@path` import in it, one inside a
sentence or inside emphasis among them, is written again from the rules
folder, since an agent reads an import from the folder of the file that
holds it. So is an import with a `#` fragment, such as
`@docs/setup.md#install`, or an escaped space, such as
`@my\ docs/a.md`, the fragment and the escape kept. A fence it left
open is closed where it ends, as an older release's marker line closed it. A
comment it left open stays open, since the tool reads an opener with no
closer as hiding nothing. The report
says `moved section 0 from AGENTS.md into .agents/rules/project.md`.
With no such section the rule is the placeholder. In a door an older
release wrote, section 0 ends at that release's marker line, so it is found the
same way whatever a release said after it. In a file the first release
wrote, before that line existed, it ends where that release's opening
paragraph stood, and that paragraph is history, so it never moves.
Anywhere else it runs to the next `#` or `##` heading. A `project.md`
that is there already, the project's own or one a stopped run left, is
never written into, and its section 0 is quoted with the rest below,
under `## From AGENTS.md, its section 0`, the report saying
`left .agents/rules/project.md as it was, since it was there already, and quoted the section 0 AGENTS.md held beside the rest`,
so a second run never runs a gate twice.

Every other word a front door held of its own goes, quoted, into the
doc `.agents/docs/front-door-words.md`, under a `## From <door>` heading
per door, in a `text` fence longer than any run of backticks the words
hold, and a part the doc holds already is not written again. A doc
never loads, runs as a gate or lints, so nothing in those words runs or
loads, since none of it did in the door, and nothing in `project.md`
reaches them. On a port that is each door whole, its title and the
section that moved left off, so a second door's section 0 and its
imports are quoted too. A door that says what Agent Setup's copy of it says
is Agent Setup's and gives nothing, each rule import below the line the
rules are imported under set aside, so Agent Setup's own `AGENTS.md`
brought from another project with that project's rule imports, such as
`@.agents/rules/rust.md`, is Agent Setup's copy too, while any other line
there is the project's own. A door that copies another, or links to
it, is quoted once, and a door holding nothing but comments and imports
of the front doors at the root, such as `@AGENTS.md`, says nothing of
its own. On an upgrade it is what a door an older release wrote held above
that release's marker line, its title and the section that moved left
off, and a door with no such line gives nothing, since its words cannot
be told from Agent Setup's. The report says
`quoted what AGENTS.md held of its own in .agents/docs/front-door-words.md, where nothing in it runs or loads, so read it against the rulebook and write what still holds as a rule`,
naming every door it quoted, and the doc asks the agent to write what
still holds as a rule, through `brain new rule` or into `project.md`,
then delete each part it has read, and the doc once it is empty.

Agent Setup's earlier hook groups are replaced under every
event, told apart by a command that is nothing but a call of the tool's
own script, so a group of the
project's own that calls the script bare counts as Agent Setup's and goes
with them, while a group that wraps that call, or calls a copy kept
elsewhere, is the project's and stays, and an event left with no group
stays as an empty list. A rename goes through git where git tracks the
file, so the move shows as one. Agent Setup's ignore lines sit in one
block at the top of the ignore file, under the heading
`# Agent Setup's own ignores.`, rebuilt there on every run, and a block
an earlier release wrote under its older heading is taken as that block
and given today's. The ignore file is written with a
carriage return and a line feed at each line's end where any of its
lines ends that way, else a line feed alone, a new one too, and a file
the 1.0.0 migration points at `.agents/` keeps its own line ends, so on
Windows neither gains a second carriage return. The exit code is
doctor's, 0 clean and 2 while findings remain, and those are the
project's own prose to put right. A finding in a file the install writes whole is Agent Setup's to
fix, printed apart and never counted, since the install replaces that
file every time. Such a file is a skill Agent Setup ships, the brain's own
`SYSTEM.md`, `README.md` or `house-rules.md`, its launcher `brain`, the version stamp
`VERSION`, or a file copied into the agent folders, which is a sub
agent definition, the chat style source or one of its copies. An import
slip in a front door that Agent Setup's own text of that door gives too
counts the same way, as many times as that text gives it, while an
import slip in a rule is the project's every time. The chat style
copies in `.codex/` and `.gemini/` are the doctor's to make from the
source in `.claude/output-styles/`, and the skill stubs under
`.claude/skills/` are the doctor's to write from the project's own
sheets, so the install copies none, not even the ones Agent Setup's own
repository holds.

A root file Agent Setup replaces is named in the report with a `git show`
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
and `Read(/.claude/skills/agent-brain/scripts/**)` by the one the skill
links of releases before 2.5.0 gave it,
the leading slash anchoring each at the project. A deny rule on Read
that names that folder at the project, by either path or by the brain's
old `.agent/` one, counts as Agent Setup's and is replaced, so a release
that rewords a rule leaves no double. The project's own rules stay in
their order. No rule names Edit, yet an existing file of the tool's code
cannot be edited through Claude Code's Edit tool either, since Edit
needs a Read of the file first. A new file under `scripts/` can still be
written.

Under `sandbox.filesystem.allowRead` go the same two folders,
`.agents/skills/agent-brain/scripts` and
`.claude/skills/agent-brain/scripts`. Claude Code's sandbox takes the
Read deny rules as reads it refuses every command it runs, the brain
tool's own Python among them, so without these entries no brain command
could open its own code while the sandbox is on. With them every brain
command runs, one that carries a heredoc, such as `brain new` or
`brain handover`, included. Agent Setup never turns the sandbox on. The
project's own sandbox settings, `enabled` and its own allowed and
denied reads among them, stay as they were, and Agent Setup's two entries
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

Doctor names a rule or a sandbox entry of the guard
missing from `.claude/settings.json` as
`the read guard is missing from .claude/settings.json, which brain doctor --fix writes`,
and `--fix` writes both in, the rest of the file kept. So a project an
older tool upgraded gets the guard at the next fix. Doctor asks only
that the two rules and the two entries be there, in any order among the
project's own. It stays silent where the file is missing, which the
next upgrade writes, and where it is not valid JSON, is not a JSON
object or holds one of the keys above in the wrong shape, which the
next upgrade refuses in words.

Where `.claude` is a link that leads out of the project, such as into a
checkout of Agent Setup, doctor still reads the file, silent in the same cases,
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
| `session-start` | Prints into the agent's context the clock, the standing word and the current work, then the note that is this session's to take, its own or on a fresh start the one that waits, as [a note per session](#a-note-per-session) says, whole under a line that says how it was taken, or the one line that says why a file there stays, another session holding the note's lock among the reasons, then `brain status`, counted once the note is taken, so it names a note this start read only where the start could not take it aside and read it in place, which the next session reads again. Under the counts one line names the launcher's call, `python3 .agents/brain`, and the commands that read the brain through it, `list <kind> --open`, `status` and `show <key>`, and says never to read it by a grep of its fields or a listing of its folders. `--with-rules` adds `SYSTEM.md`, then each of [the rules](#the-rules) in their order, each under `A rule of this project's own, from .agents/rules/<name>:`, and the agent's own chat style copy after those, for an agent that does not expand imports. The note is taken on every start the event's `source` names but a fork, since a fork carries the context it came from, and the handover section above says how, when it waits for the lock, how a note left in `handover/` before 2.2.0 moves in, and what the start says of one that stays. |
| `prompt` | On each prompt the owner sends, puts the clock, the standing word and the current work in front of the model, since a model does not know the time and forgets what it was told and what it is on. |
| `tick` | After the agent's tool calls, the clock, the standing word and the current work again, off and none included, so a long stretch of work never loses any of them and sees the word end or the chain move. Under the moment it adds a line for any call that read or wrote the brain by hand, as [the nudge](#the-nudge) says. Claude Code fires it once after each round of tool calls, whatever the tools, Codex after each shell call, and Gemini CLI after each call to `run_shell_command`, `grep_search`, `search_file_content`, `glob`, `list_directory` or `read_many_files`. |
| `pre-write` | Blocks, exit 2, a write that would create a new brain file by hand, an `INDEX.md`, a dotted path, which the brain never lists or checks, the `.ack` file, which `brain ack on` writes, the `.ack-tests` file, which `brain ack tests` writes, the `.task` file, which `brain task on` writes, anything in the `.lines/` folder, where a line of work started with `--beside` keeps its own, anything in the `.handover/` folder, which holds the notes `brain handover` writes, a rename of a brain file, which `brain refile` does, a patch's move of any file onto an existing brain file, which would write over its header and its steps by hand, or a change to the header block of an existing brain file, its `updated` date aside, or to a row of the steps table a plan, a todo or a bug holds, a mark moving through `brain task` or `brain steps` or following the entry the step points at, a step never reworded, repointed or deleted by hand, a cell left empty by an older write filled in by hand, and the table never taken away, a plan's not even empty. A row after the last passes when it is held to what `brain steps add` holds a step to, with text, pending, pointing at an entry the brain knows, one file carries and whose steps do not lead back here, or at nothing, and on an open entry. A numbered list under Steps, new or written to, is the list the tool turns into the table, so it is held to the same, whole, as the write leaves it, and refused on a closed entry. A patch that reaches several brain files is judged across them too, the pointers on disk and the rows it adds walked together, so a loop it closes through two files is refused, though a pointer it removes still counts until it lands. A write that would leave the table unreadable is refused, a table that does not read now is doctor's, and the hook's keys and names come from the store, whatever case the path is spelled in. Edits to the prose of an existing file, Agent Setup's own files and anything under `skills/` pass. The header and table checks judge the file as the write would leave it, the whole new text, the text after the edit, or the file after the patch's hunks. None of these refuses a delete, a stray index's or a dotted file's among them, and doctor runs after it. A file the hook cannot read is already broken, so the write is taken as its repair and doctor judges the result. The hunks of a patch are placed one after another as the patch applies them, and the result is judged. A hunk that fits nowhere is refused if any line it carries, kept, removed or added, is a fence, a field the file's header carries or its kind allows, a table row, a numbered step opening with a key or the Steps heading, and on a closed entry any numbered line it adds, since the hook cannot tell where it would land, and the refusal names the line. A loose hunk that carries only prose is left alone. It also blocks a write to the project's `AGENTS.md`, in any case of its name, a delete aside, since the port and the upgrade write that file whole, and the refusal says a project's own instruction is a rule, filed through `brain new rule`, and that `brain doctor --fix` writes the import lines again, a merge's conflict in them among what it settles. It blocks as well a write to Agent Setup's `rules/rust.md`, in any case of its name, a delete aside, as [the Rust rule](#the-rust-rule) says, and a write that changes or removes an assertion a test file holds, a test file deleted or moved by a patch, or written over by a patch's move onto it, among them, unless the owner's word for that file holds, as [the test guard](#the-test-guard) says. |
| `post-write` | After a write, runs the project's own linters on each file just written, as [the lint hook](#the-lint-hook) says, and hands back what they left under `lint after that write:`. Then runs the check on each file just written inside the project, a file reached through a link that leads out of it left out, and hands its slips back as context under `brain check after that write:`, so they are fixed in the same round, a file the check passes over left out as the check leaves it out. A file the check could not judge, since git cannot read its attributes, is named on standard error and never in the context, and a standard error that cannot take the note loses it and nothing else. After a write inside `.agents/`, to a front door, `AGENTS.md`, `CLAUDE.md` or `GEMINI.md` at the top of the project in any case of its name, or to the `Cargo.toml` at the top of the project under that exact name, which [the Rust rule](#the-rust-rule) follows, a delete among them, and after a Codex patch that deletes any file or moves one away, since a brain entry may link to it, runs doctor too and hands its findings back the same way, its front door findings with them, or its error in words where it cannot read the brain, and still exits 0, since an exit 1 would show the person the error and lose the slips. |

What a hook puts on standard error, a refusal, the error that stopped
it or a note, goes out as UTF-8 whatever the locale's encoding, since
every agent reads it that way, so a file name the locale cannot
encode, as a Windows code page often cannot, reaches the agent whole. A
standard error that is closed, or whose reader is gone, loses the line
and nothing else, so a refusal still exits 2 and the line never lands
on standard output.

A write hook spells each path inside the brain or the project as the
brain or the project and the disk spell it before it judges the path,
the brain asked first, each folder known by the disk's identity where
the text does not match. That spelling is what places a path, since
whether a path lies inside the brain is then read from its text alone
and the disk is never asked. So on a disk that folds case
`.AGENTS/.ack` is the standing word and `todos/index.md` the index,
each refused as the brain's own, and a file written under another case
of the project's folder is checked as the project's. A `.agents` that
is a link to a folder elsewhere stays the project's brain, found from a
folder inside the link too, and a path that reaches the hook through
the link's target, which lies outside the project, is spelled under the
link and so lies inside the brain, a name in another case there among
them. An event that is not a JSON object counts as an empty one. A
`cwd` that is not text names no folder, so the hook looks for the brain
from its own, and a `tool_input` that is not an object names no file
written.

Context goes back as one JSON object naming the event, which all three
agents read on every event. Codex also takes plain text at the start of
a session and on a prompt, and gets it there. On its tool events plain
text is dropped, so those get the JSON object too. A Claude Code context
past the 10,000 characters Claude Code shows from a hook opens, on any
event, with a line that asks the model to read whole the file Claude
Code keeps it in, and the shipped Codex config sets
`additionalContextLimit` to 0 on the session start and after a write, so
Codex takes those whole.

The config files that wire them up ship with Agent Setup, as
`.claude/settings.json`, `.codex/hooks.json` and
`.gemini/settings.json`. Every command in them is the same one line of
Python, which finds the script from the project folder the agent names
in `CLAUDE_PROJECT_DIR` or `GEMINI_PROJECT_DIR`, or by walking up from
the session's own folder where Codex names none, hands it the event,
and does nothing where no script is found, so a checkout that predates
Agent Setup never blocks a prompt or a write. The script that runs is
the one checked out, so a session whose hooks name an event and a
checkout of a release from before that event still block on it until
the session restarts, which this release's script no longer does for
events it will learn later. Each Codex hook carries the same line in a Windows form
beside it, run through the `py` launcher. The Claude Code one also
carries Agent Setup's four settings, `"outputStyle": "Plain & Short"` for
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
`reviews/`. The brain's own files are `INDEX.md`, `.ack`, `.ack-tests`,
`.task`, `.conclude`, `.handover/` and `.lines/`, which the tool alone
writes. A pattern in
place of a folder's name, as in `.agents/*/*.md` or
`.agents/{bugs,todos}/*.md`, reaches each tracker folder it matches.
Nothing else in the brain's folder is an entry, Agent Setup's own
`SYSTEM.md`, `README.md`, `house-rules.md`, the launcher `brain`,
`VERSION` and `skills/` among them, so a read or a write there adds
nothing.

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

After a read the line names, with `python3 .agents/brain` in front,
`list <kind> --open` for what is still open, `--status <status>` for
one status, `status` for the counts and `show <key>` for one entry.

A write is tee, mv, rm, touch, mkdir, `sed -i`, `perl -i`, `git mv` or
`git rm` on a path in a tracker folder, one of the brain's own files or
the brain's folder itself, a cp whose last path, where the copy lands,
is one of those, so a copy out of the brain is no write, or a find from
one of those with `-delete` or with an `-exec` that runs a writer. A
redirect, `>`, `>>` or `&>`, onto a path in a tracker folder or one of
the brain's own files is a write too, whatever program it follows.
After a write the line names `new`, `set`, `refile`, `steps`, `task`,
`ledger`, `handover` and `index` as the commands that do that work, and
`brain doctor` with `python3 .agents/brain` in front to see what the
hand change left. A write through the edit tools adds nothing here,
since the `pre-write` hook judges it before it lands, as its row says.

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
a line's end joins it to the next, save in PowerShell or cmd, where every
path is spelled with backslashes and one escapes nothing, a line break inside quotes, such as
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
project left out, and never on a file inside `.agents/`.
The project's [rules](#the-rules) name them, `project.md` first and the
others by name, under each heading whose text is Lint, such as
`### Lint` or `### 0.3 Lint`, at any level, in the fenced blocks up to
the next heading at its level or above. Each line of a
block is a file pattern, then one command with `{file}` as a word of
its own where the file goes, such as
`*.py ruff check --fix --unfixable F401 {file}`, and a blank line or
one that opens with `#` is passed over. A fixer that deletes what looks
unused, such as an import, wants that fix turned off, since the hook
runs after every write and the agent often adds the import one edit
before the line that uses it. Where
no rule has a Lint heading, nothing runs and nothing is said. Where a
rule cannot be read, no lint line of any rule runs, and the context
says so in one line,
`rules/<name> cannot be read, <reason>, so no rule's lint line runs`.

A pattern with no slash matches the file's name, and one with a slash
matches its path from the project's root, where a `*` crosses folders
and each `**/` matches no folder too, so `src/**/*.py` takes
`src/app.py` as well as `src/api/app.py`. Patterns match case for case.
Every line that matches runs, in the order the rules give. A line is
split into words the way a POSIX shell splits them, quotes holding a
word together and, on Windows, a backslash kept as the separator of a
path, and on Windows its program is found by the path's extensions
too, so a `.cmd` shim npm installs runs by its bare name, though a
batch file never runs on a file whose path holds a character cmd reads
as code, one of `& | < > ^ % !` or a quote, which the context names
instead. Its command runs from the project's root with no
shell, `{file}` replaced by the file's absolute path as one argument,
so a space, a quote, a leading dash or a letter outside ASCII in the
file's name reaches the command whole and never reads as an option.

A line the hook cannot run as one command is not run, and the context
names it with the reason after every write the hook lints, until
its rule is put right. That is a line that does not split into words,
such as one with a quote left open, a line of one word, a line with a
shell operator outside quotes, `;`, `|`, `&`, `>`, `<`, `(` or `)`,
alone or glued to a word as in `{file}&&` or `2>&1`, a line whose
command opens with a word that holds `=`, which a shell reads as a
variable, and a line with no word `{file}`. A quoted operator is an
argument like any other. A line written beside the fences under a Lint
heading as one code span that holds `{file}`, in a list item or not,
is named as sitting outside a fenced block, and where no Lint heading
of any rule holds a line in a fenced block, one line says how a line is
written. A line beside a fence in any other form, such as a bullet with
no backticks, reads as prose, so it runs nothing and nothing names it.

Each command has 20 seconds, and one write has 40 seconds over every
file it touched, so a patch over many files still ends inside the 60
seconds Claude Code and Gemini CLI give a hook by default, since
Agent Setup sets no hook timeout of its own. A command past its time is
stopped with every process it started, its process group, or on
Windows the job object it runs in, all at once, with taskkill over its
process tree where Windows gives no job, so none writes the file later, and the
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

The hook has no lines of its own, so the lines the rules name are the
only ones that run. The tool's scripts folder carries a `ruff.toml`,
and the see tool's carries the same, which ruff reads for a file of
either tool's code. That config holds the code to Python 3.9, lets a line run to 320
characters, selects ruff's rules F, E9, TID251 and RET505, bans
`from __future__ import annotations`, and never removes an unused
import on its own, since the hook runs on every write and an import is
often added one edit before its use, so ruff names it and the agent
removes it.
