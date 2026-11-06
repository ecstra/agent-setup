# Example Agent Setup

A small kit you drop into a project so a coding agent (Claude Code,
Codex, Gemini CLI, anything that reads `AGENTS.md`) knows how to behave
there and has a place to keep what it learns. It is one folder called
`.agents/`, holding the rules and everything the project knows, plus a
few short files at the root that point every agent into it. All plain
files, committed to git, all but what its ignore file keeps out. That
is the whole trick. Because they live in the repo, a fresh session on
any machine picks up exactly where the last one stopped.

## Why you would want it

Without something like this, every agent session starts from zero. The
rules live in someone's head and the project knowledge lives in old chat
logs, so the agent redoes the same discovery every morning. With the kit
in place, both are in the repo and the agent reads them before it
touches anything. You get the same behavior from every session and a
written record of what the project knows.

## What you get

| File | In plain terms |
|---|---|
| `AGENTS.md` | The front door every agent reads. It points at the rulebook and imports each of your project's own rules from `.agents/rules/`, and the port and the upgrade write it whole. |
| `CLAUDE.md` and `GEMINI.md` | Short files that pull in `AGENTS.md`, because Claude Code and Gemini CLI look for their own filename. `GEMINI.md` adds its chat style, and `CLAUDE.md` carries the instructions Claude Code compacts a session by, which ask it to keep what a handover carries and the rules you gave in chat, in your words. The port and the upgrade write both whole too, so your own rules go in `.agents/rules/`. |
| `.agents/SYSTEM.md` | The rulebook. How to write code, how to talk to you, where docs go, how a branch gets reviewed, how git is used. |
| `.agents/` | The project's memory. Its own rules, docs, plans, build specs, todos, bugs, decisions, review ledgers, and small facts the agent learns, plus the note one session leaves for the next, which never enters git. Ships empty apart from the rules and the tool that keeps the rest, whose [skill sheet](.agents/skills/agent-brain/SKILL.md#the-brains-files) says what each folder holds. |
| `.agents/skills/agent-brain/` | The brain tool. Reads, lists, counts, files, changes and checks everything in `.agents/`, so an id, a header block or an index line is never typed by hand and a tracker is never grepped for its fields. It also checks the project's own markdown and commit messages, runs your linters on each file the agent writes and your gates before a review, installs the kit into a project and brings it up to a newer release. Plain Python, no dependencies. |
| `.agents/skills/branch-review/` | The code review, run on your word at a quick, standard or deep level. Finder sub agents read the whole branch in parallel, one per angle, and two verifier sub agents vote on each finding, or the main agent alone at the quick level. The main agent fixes every confirmed finding itself in one go, a fresh verifier rechecks the diff of the fix, three rounds at most, and one docs agent brings the docs up to the code at the end. The report says where things stand first. |
| `.agents/skills/see/` | The see tool, for an agent that reads images but no video. It turns a screen recording into its bursts of motion, the regions that moved, the pacing and tagged sheets of every frame and every frame diff, lines two recordings up side by side, tells what moved from what changed between two screenshots, and measures a screenshot's elements, padding and gaps like a design tool's redline. Every image is labelled and sized so Claude reads it at full quality. Python and ffmpeg, nothing else. |
| `.agents/VERSION` | The kit release your project carries, so an upgrade knows where it starts from. |
| `.claude/`, `.codex/`, `.gemini/` | The hooks each agent runs, so each file the agent writes with its edit tools is linted and checked without anyone asking, the clock, your standing word and the work the agent is on stay in front of it, and a call that reads or writes the brain by hand is told which brain command does that, the stubs Claude Code finds the skills through, the review's sub agent definitions, and the Plain & Short chat style, once per agent in the form that agent reads. Claude Code's settings also turn off its idle compaction, so a long session you step away from keeps its full context, and a project can turn it back on in its own settings. |
| `CONTRIBUTING.md` | The hard rules for humans and agents on one page. |
| `CODEOWNERS` | Names who owns the repo on the forge. Put your own handle in. |
| `.gitignore` | Keeps your `.env`, your local Claude Code settings and the Python and ruff caches out of git, along with what the agent-brain [skill sheet](.agents/skills/agent-brain/SKILL.md#the-brains-files) says git ignores in `.agents/`. |

Everything is generic on purpose. Anything specific to your project goes
in its rules, `.agents/rules/project.md` and any rule your agent files
beside it through `brain new rule`, and into the files your project
grows inside `.agents/`. The rest of the kit
stays as it ships, apart from your handle in `CODEOWNERS`.

## Installation

The kit installs itself. Get a copy of it next to your project, then run
its port from your project's root, and the tool puts every file where
it belongs. Three ways to get the copy, easiest first.

### Ask your agent

If your machine can already reach the forge (you have cloned from
`forge.example.com` before, or `tea` is logged in), open your agent in
your project and paste this prompt.

```text
Clone https://forge.example.com/example/agent-setup into a folder beside
this repo, then run its port from our root:
python3 <that folder>/.agents/skills/agent-brain/scripts/brain.py port
It refuses while a file it would replace has uncommitted changes, so
commit first. Copy the kit's CODEOWNERS in with my handle in place of
@ecstra. If this project already has test, build, or lint commands, name
them in .agents/rules/project.md as the gates, and its linters as lint
lines, the way <that folder>/README.md shows. Read what the port
printed, and tell me what you did and what it listed as left to file.
```

### Terminal

Clone the kit beside your project, then run its port from your
project's root.

```bash
git clone https://forge.example.com/example/agent-setup ../agent-setup
python3 ../agent-setup/.agents/skills/agent-brain/scripts/brain.py port
cp ../agent-setup/CODEOWNERS .
```

Adjust the `../agent-setup` path if you cloned somewhere else.

### Download

Use the Code button at the top of this page and download the ZIP.
Unzip it beside your project, then run the port from your project's
root exactly as the terminal path does, with the unzipped folder's
path in place of `../agent-setup`.

### What the port does

It works on the git repository around the folder you run it in, never
on your home folder, and it refuses while a file it would replace holds
uncommitted work, so commit first. Then it does all of this in one run.

- The kit's files land: the rulebook, the house rules, the brain tool's
  launcher and the kit's three skills under `.agents/`, the front doors
  and `CONTRIBUTING.md` at the root, the hooks, the review's sub agent
  definitions and the chat style in the agent folders, and the version
  stamp.
- Your own rules are kept. A section 0 you already had, under a `## 0.`
  heading in `AGENTS.md`, `CLAUDE.md` or `GEMINI.md`, the first one
  found, goes into `.agents/rules/project.md` as it stood, its links
  written again from there, so its gates and linters run as they did,
  and the new `AGENTS.md` imports that file. Everything else those files said
  of their own is quoted in `.agents/docs/front-door-words.md`, a doc
  where none of it loads or runs, for your agent to read against the
  rulebook and turn what still holds into rules. The old files stay in
  git where the report says.
- Your own hooks stay. The kit's hooks are added beside them in each
  agent's config, and any other setting of yours is left as it was.
  The kit's own four settings for Claude Code, the Plain & Short chat
  style, the sub agent model, how many tool calls may run at once and
  idle compaction turned off, are added the same way, and a value you
  already set for any of them stays yours.
- Claude Code gets the read guard, rules that keep the agent from
  reading the brain tool's code, which it never needs, and two entries
  that let every brain command run should you turn Claude Code's
  sandbox on. The kit never turns it on. With the sandbox on, a shell
  read of the code gets through and only the Read tool is refused, as
  [the read guard](.agents/skills/agent-brain/references/commands.md#the-read-guard)
  says.
- Your `.gitignore` keeps every line it had. The kit's lines go in a
  block at the top, so your own lines sit below them and win.
- The tool's doctor runs once, builds the indexes and writes the skill
  stubs Claude Code finds the skills through.
- The report names each root file it replaced along with where git
  keeps the old one, and ends with what it found that belongs in the
  brain, for your agent to file. Keep that output, nothing prints it
  again.

A second port refuses, since the brain is there. An upgrade straight
after it writes nothing.

> **Two things every path leaves to you.**
>
> 1. `CODEOWNERS`: copy the kit's in and replace `@ecstra` with your
>    own handle. The port never touches ownership.
> 2. `.agents/rules/project.md`: optional to fill. The port writes it
>    with your old section 0, or else with a comment saying what it is
>    for, and it holds what the general rules cannot know about your
>    project. Every session loads it as it starts, so a change reaches
>    the agent once you reload. The gates (the
>    exact test suites, analyzers, builds, and validators that must be
>    green before a review), the linters, the tooling (how PRs are
>    opened, how the app runs), anything else the general sections do
>    not cover. The gates go under a `### Gates` heading, one fenced
>    `bash` block per gate, and `brain gates` runs them in order, as
>    [`commands.md`](.agents/skills/agent-brain/references/commands.md#the-gates)
>    says. The linters go under a `### Lint` heading, in a fenced block,
>    one line each, a file pattern and then one command with `{file}`
>    where the file goes, such as
>    `*.py ruff check --fix --unfixable F401 {file}`, which leaves an
>    import the agent just added for the edit that uses it. The brain
>    runs every line that matches on each file the agent writes
>    outside `.agents/`, with no shell, and hands back what the linters
>    could not fix, never blocking the write, as
>    [`commands.md`](.agents/skills/agent-brain/references/commands.md#the-lint-hook)
>    says with what it refuses and how long a command may run. A project
>    with no gates or linters yet has nothing to put there, so skip it
>    and add it when the first one exists.

Commit, and start your first session. The agent reads `.agents/INDEX.md`
on its own, you do not need to point at anything.

From then on `.agents/` fills up as a side effect of the work. The agent
writes a build spec before each branch's code, docs as it builds
things, files todos and bugs as they come up, records decisions when
they are made, and keeps small facts it learns.
You will never sit down to "maintain" it.

## Porting an existing project

> **Do not follow these steps by hand, the prompt is below.** Paste it
> into your agent and it runs the whole flow. The steps here describe
> what the agent will do, so you know what to expect and what to check.

Most projects that adopt the kit already have a pile of docs, an old
`CLAUDE.md`, a TODO list somewhere, and notes nobody has opened in
weeks. None of that is lost. All of it gets filed into `.agents/`, and
the agent does the filing, because there is a lot of it and every file
needs the right header block and index line.

Porting builds on the installation above, so do that first, any of the
three ways. Nothing of yours is thrown away by the port. Your old
section 0 moves into `.agents/rules/project.md`, everything else your
old front doors said of their own is quoted in
`.agents/docs/front-door-words.md` for the agent to sort, every root
file the kit replaces is named in the report
with where git keeps it, and your own hooks and ignore lines stay where
they were. The port ends by listing what it found that belongs in the
brain, and that list is where the agent starts, so paste the port's
output into the prompt below if the agent did not run the port itself.

### What the agent will do

1. **Sync with the new rulebook first**: read the new `AGENTS.md` and
   the rules it points at, then work by them from the first move. The
   port itself obeys the kit's rules, so prose is edited with the proper
   edit tools, no scripts, the structure inside `.agents/` is the tool's,
   and the house style holds throughout.
2. **Read everything**: the whole project, the code, every doc and note
   it can find, then the agent-brain skill sheet, whose section on the
   brain's files gives the target format. It shows you a plan before it
   moves anything.
3. **File each thing where it belongs**: on its own branch, one file at
   a time, through the brain tool, `brain new` with the prose on
   standard input, per the map below. The tool writes the header block,
   the id and the index line, so none of them is typed, and the hook
   refuses a brain file written any other way. Your wording is kept in
   todos and nothing gets shortened on the way.
4. **Sort the old rules, never keep them whole**: the section 0 the
   port moved into `.agents/rules/project.md` and the words it quoted
   in `.agents/docs/front-door-words.md` are read against the new
   rulebook. Whatever the general sections already say is dropped, and
   only what is truly project specific stays, as a rule in
   `project.md` or one of its own through `brain new rule`. Each quoted
   part is deleted once it is sorted, and the doc once it is empty.
   Your old `CONTRIBUTING.md` is read from git the same way, and what
   it adds becomes rules too.
5. **Do all of it**: a project can hold hundreds or thousands of files,
   old and new, and the port covers every one, never a sample. If the
   volume calls for it, the agent lists everything in a ledger first and
   works through it in batches, ticking each file off, so nothing is
   skipped and a later session can pick up where it stopped.
6. **Clean up**: once a doc lives in `.agents/`, the old copy is
   deleted. The one exception is anything a person wrote by hand, which
   stays where it is, untouched. The agent tells the two apart by the
   writing itself, since a human's notes do not read like generated
   docs, and it lists what it left alone so you can decide. Then it runs
   the tool's doctor with `--fix` and leaves the brain clean, and runs
   `brain gates`, which a review waits on. It fixes what the check names
   in the files it filed and lists for you whatever else is red, such
   as the check's slips in your other markdown and in what it left
   alone.
7. **Hand you the branch**: you say when it is ready for review, and
   the agent runs the review the way the house rules describe, findings
   confirmed by a vote and filed in a ledger, then fixed in three rounds
   at most, each on your ack. Then it opens the PR and merges, both on
   your ask. When the PR opens and whether as a draft is your project's
   own rule in `.agents/rules/`, so the agent never asks. After that the
   root holds `README.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
   `CONTRIBUTING.md`, and `CODEOWNERS`, plus your `docs/` folder if you
   keep one. What a person wrote by hand stays as it is, and anything
   new in there links into `.agents/docs/` rather than repeating it.

### Where things go

| What you have today | Where it goes |
|---|---|
| Your own `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md` | Its section 0 moved into `.agents/rules/project.md` by the port and the rest quoted in `.agents/docs/front-door-words.md`, then read against the new rulebook. Anything the general rules already cover is dropped, only the truly project specific parts stay, as rules. |
| A `docs/` folder, wiki pages, architecture or design notes | `.agents/docs/`, sorted into a category folder (`foundation/`, `systems/`, `ops/`, `research/`), one line each in `.agents/docs/INDEX.md`. What a person wrote by hand stays where it is, and a `docs/` folder you keep links into the brain rather than repeating it. |
| ADRs or a decisions log | `.agents/decisions/`, one file per decision. |
| A TODO list, roadmap, or backlog | `.agents/todos/`, one file per item, your wording kept as is, and a roadmap with its steps as `.agents/plans/`, one file per goal. |
| Known bugs, issue notes | `.agents/bugs/`, one file per bug. |
| Gotchas, tribal knowledge, "remember that" notes | `.agents/memory/`, one fact per file. |
| Your `CONTRIBUTING.md` | Replaced by the kit's, the old one kept by git. Extra rules of yours go into `.agents/rules/project.md`. |
| Your `README.md` | Stays at the root, trimmed to what the project is and how to run it, with links onward. Detail moves into `.agents/docs/`. |
| Changelogs, status reports, meeting notes | Not agent knowledge. Left where they are or dropped. |

### The prompt

Paste this into your agent once the kit is in. It covers the whole flow
above.

```text
We are adopting the agent kit that now sits in this repo. Do the port
on a new branch. Before anything else, read the new AGENTS.md and the
rules it points at, and work by them from here on: prose edited with
the proper edit tools, no scripts or heredocs, the header blocks and
indexes inside .agents/ left to the brain tool, house style throughout.
Then read the whole project: the code, every doc and note, and every
TODO list, and the list the port printed of what is left to file, which
I will paste if you did not run the port. Then read .agents/INDEX.md and
the agent-brain skill, its section on the brain's files above all, so
you know the target format and the tool that writes it. Show me a plan
of what goes where before you move anything. Then file it all into
.agents/ (docs, decisions, todos, bugs, memory, everything) one file at
a time through brain new with the prose on standard input, never by
hand, keeping my wording in todos. .agents/rules/project.md holds the
section 0 the port moved from our old rules, and
.agents/docs/front-door-words.md quotes what else our old AGENTS.md,
CLAUDE.md and GEMINI.md said. Read both against the new rulebook, drop
what the general sections already cover, and keep only the truly
project specific parts as rules, in project.md or through brain new
rule, then delete each quoted part and the doc once it is empty. Read
our old CONTRIBUTING.md from git the same way, and file what it adds
as rules too.
This may be hundreds or thousands of files. Do every one, never a
sample. If the volume needs it, list everything in a ledger first and
work in batches, ticking each file off. When it is all filed, delete
the old copies of the docs you moved, but leave anything a human wrote
by hand where it is and list those for me. Run brain doctor --fix and
leave it clean, then run brain gates, which the review waits on. Fix
what the check names in the files you filed, and list for me whatever
else is red. Then tell me what you did and where, and wait for me to
call the review.
```

## Keeping the kit current

When this repo puts out a new release, bring your copy of the kit up to
date, or clone one beside your project, and run its upgrade from your
project's root.

```bash
git -C ../agent-setup pull || git clone https://forge.example.com/example/agent-setup ../agent-setup
python3 ../agent-setup/.agents/skills/agent-brain/scripts/brain.py upgrade
```

The upgrade replaces what is the kit's and leaves what is yours.

- The kit's: the rulebook, the front doors, with `AGENTS.md` importing
  each of your rules, `CONTRIBUTING.md`, the house rules, the tool and
  its skills, the hooks, the review's sub agent definitions, the chat
  style, and the version stamp. All new over old. A skill folder or a definition under
  a kit name that you made before the kit shipped it is refused, not
  replaced, until you move it aside.
- Retired: what the kit wrote in an older release and no longer ships,
  each named in the report. That takes in the format specs under
  `.agents/spec/`, whose rules the tool and its
  [skill sheet](.agents/skills/agent-brain/SKILL.md#the-brains-files)
  now carry, and the review's old fixer and hunter definitions. A file
  of your own in `.agents/spec/` stays, and the upgrade names it for
  you to file under `docs/` through `brain new`.
- Yours: your rules in `.agents/rules/`, every file your project filed
  into `.agents/`, your own hooks and settings in the agent folders, and
  every line of your `.gitignore`.
- Rebuilt: the indexes and the skill stubs, by the doctor run at the
  end, never edited.
- Filled: from 2.1.0 every entry names its `author` and its `editor`,
  the git names of who filed it and who last changed it, beside the
  `by` of a todo or a plan, which still says whether a person asked for
  it or the agent raised it. The upgrade fills both from git history
  for each entry that lacks them, as
  [doctor's fill](.agents/skills/agent-brain/references/commands.md#doctor)
  says, and counts them in its report. An entry the fill cannot name,
  one whose first commit a shallow clone hides or any where git cannot
  read the history, stays among what doctor names.

From 2.0.0 `brain check` judges prose and commit messages only, and no
longer reads Python. Name your linters under a Lint heading in
`.agents/rules/project.md`, as
[the lint hook](.agents/skills/agent-brain/references/commands.md#the-lint-hook)
says, so they run on each file the agent writes, or your code is
checked only by whatever your gates run.

From 2.2.0 the note for the next session lives in the hidden
`.agents/.handover/`, and sessions on one machine take turns on it, so
only one of them gets the note. A note waiting in `.agents/handover/`
for the branch you are on moves there at the upgrade, or at the next
session start where a pull or a merge brought 2.2.0, and the old folder
goes once it is empty. One for another branch stays there for that
branch. Git keeps ignoring the old folder. Notes of your own left in it
stay, and the upgrade names them on every run, as doctor does, for you
to move into `docs/` or `memory/` through `brain new`, or delete.
[The handover](.agents/skills/agent-brain/references/commands.md#the-handover)
says when an old note waits its turn and what a branch cut before 2.2.0
still reads, and
[the upgrade's row](.agents/skills/agent-brain/references/commands.md#port-and-upgrade)
says what stays behind and why.

From 2.2.1 the read guard carries two entries under
`sandbox.filesystem.allowRead` in `.claude/settings.json`, so every
brain command runs with Claude Code's sandbox on. The upgrade writes
them beside your own sandbox settings. Where an older copy of the tool
ran the upgrade and left the guard out, `brain doctor` names it and
`brain doctor --fix` writes it. The port and the upgrade now refuse,
before the first write, a project where a file they would write sits
behind a link that leads out of it, such as a `.claude` folder linked
into a kit checkout, until you move the link aside, as
[port and upgrade](.agents/skills/agent-brain/references/commands.md#port-and-upgrade)
says. Doctor writes nothing behind such a `.claude` link either. It
reads the settings there and, only where the guard is missing, names
it and asks you to move the link aside and run `brain upgrade`, as
[the read guard](.agents/skills/agent-brain/references/commands.md#the-read-guard)
says.

From 2.2.2 the kit is built for Windows too. Every path the tool
writes, compares, prints or names in a finding or a message is spelled
with forward slashes there as well, all but the ones it hands the
system and the few
[the command reference](.agents/skills/agent-brain/references/commands.md)
names at its top. A `.gitignore` written with carriage returns keeps
one per line through the port and the upgrade, and the hooks write
their refusals and errors as UTF-8 whatever the locale. All of this
was built and tested on macOS with Windows imitated, and has not yet
run on Windows itself.

From 2.5.0 Claude Code finds each skill through a small stub under
`.claude/skills/`, a real file `brain doctor --fix` writes from the
skill's sheet, so no system needs a symbolic link and Windows needs no
Developer Mode. The next fix puts a stub in place of each old link, a
Windows junction included, each plain file git left for one where
links are off, and each copy of a kit skill's sheet an older release
kept. Where git still holds the old links, it leaves them deleted and
the stubs new for your next commit. Where the brain reaches a skill's
sheet through `.claude/skills/`, the fix leaves that skill's place as
it is and names it, as
[doctor](.agents/skills/agent-brain/references/commands.md#doctor)
says. This too was tested on macOS with Windows imitated.

From 2.6.0 the upgrade brings the launcher `.agents/brain`, a small
Python file, and the rules, the skill sheet and the hooks give the
agent `python3 .agents/brain` in place of the long Python call, which
still works. It runs the same in every shell, Git Bash, PowerShell and
cmd among them, and doctor writes it back where an upgrade through an
older tool left it out. It has yet to run on Windows itself.

From 3.0.0 your project's own rules live in `.agents/rules/`, one file
each, and `AGENTS.md` is the kit's whole, importing each of them, so the
hook refuses a hand edit of it. The upgrade moves your
`## 0. Project Rules` out of `AGENTS.md` into `.agents/rules/project.md`
as it stood, its links written again from there, so its gates and
linters run as they did, and it never writes into a `project.md` you
already have. Any other words your front doors held of their own are
quoted in `.agents/docs/front-door-words.md`, where none of it loads or
runs, for your agent to read against the rulebook and turn into rules.
The upgrade refuses before any write while another entry of your brain
is named `project` or `front-door-words`, until you retitle it with
`brain refile`. A later rule goes in through `brain new rule`, and it
loads once you reload the session.
[Port and upgrade](.agents/skills/agent-brain/references/commands.md#port-and-upgrade)
says what moves where.

It works on the nearest folder at or above you that carries a brain,
refuses a kit older than the one you are on, refuses while a file it
would replace holds uncommitted work, and names each root file it
replaces with where git keeps the old one. Run it on its own branch and
read the diff. Or hand your agent this.

```text
The agent kit at https://forge.example.com/example/agent-setup has a new
release. Pull the clone beside this repo, or clone it there, then run
its upgrade from our root:
python3 <that folder>/.agents/skills/agent-brain/scripts/brain.py upgrade
Read what it printed, fix whatever doctor still names, through brain
set for a header field and by hand for prose, and tell me what changed.
```

### Coming from the older layout

A project that took the kit before the rulebook moved has a `.agent/`
folder, a root `CLAUDE.md` carrying all the rules, and an `AGENTS.md`
that copies it. The same `upgrade` command carries it over. The folder
moves to `.agents/` through git, so the diff shows renames. Every file
git sees that named the old folder is pointed at the new one, and a file
git ignores that names it stops the run, by name, so nothing is left
half done. Your `## 0. Project Rules` comes out of `CLAUDE.md` into
`.agents/rules/project.md`, the kit's files land, the ignore lines
follow, and doctor rebuilds every index from the files.

## The brain tool

Everything inside `.agents/` goes through `brain`, the script under
`.agents/skills/agent-brain/scripts/`, which runs as
`python3 .agents/brain` from the project's root in any shell. Your
agent runs it, you rarely need to, but the commands are short enough
to know. A kind takes its plural too, so
`python3 .agents/brain list todos` works, and `--open` lists every
entry still open in one call.

| Command | What it does |
|---|---|
| `brain status` | The clock, where your standing word stands, on, held or off, the work the agent is on, then the brain in numbers, what each tracker holds and whether doctor is clean. The session start hook prints this into the agent's context, and two more hooks keep the clock and the work in front of the agent on every prompt and after tool calls, since a model does not know the time on its own and forgets what it was doing. |
| `brain list` and `brain show` | The entries of a kind, one line each, narrowed by status or any other field, and one entry whole. The agent reads the brain through these and `brain status`, never by a grep of its fields or a listing of its folders, and the hook that runs after its tool calls names them when a call read the brain by hand, as [`commands.md`](.agents/skills/agent-brain/references/commands.md#the-nudge) says. |
| `brain task on <entry>` | The work the agent is on, one chain at a time from a plan down to the step, which the agent sets before multi step work and moves with `brain task done`, a mark in the entry's own steps table, or which moves of itself when the entry a step points at closes, a refiled one handing the step on to the entry filed in its place. The agent cannot start a second piece of work while one stands, short of `--replace` on your word, and a link falls off the chain when its entry closes. |
| `brain doctor` and `brain doctor --fix` | Checks every file against its kind's format, and `--fix` repairs the mechanical slips, a stale index, a link written as a name, a chat style copy that drifted. |
| `brain check` | Holds the project's own markdown and the branch's commit messages to the rules of [`SYSTEM.md`](.agents/SYSTEM.md) a machine can judge, and reports without rewriting. Code is left to your linters. It reads the files given, or with none the project's own markdown and the branch's commits. The post write hook runs your linters and then the check on each file the agent writes with its edit tools, and the tool runs the check on the prose it files, so a slip is fixed in the same round. [`commands.md`](.agents/skills/agent-brain/references/commands.md#the-check) says what it judges and what it passes over. |
| `brain gates` | The one command before a review and before a merge. It runs the gates your rules name, in order, and stops at the first red one, and once all are green it runs `brain check` and `brain doctor`, as [`commands.md`](.agents/skills/agent-brain/references/commands.md#the-gates) says. |
| `brain new`, `brain set`, `brain refile` | Files a plan, a build spec, a todo, a bug, a decision, a doc, a memory or a rule with the prose on standard input, changes a header, retitles or refiles. The tool writes the id, the header block and the index line, and a rule's import in `AGENTS.md`. |
| `brain ledger` | Opens, fills and closes a code review ledger, and `brain ledger report` says where a review stands, counted from the file. |
| `brain ack on --for 8h` | Your standing word to proceed, for a time or until a task is done, so the agent passes the review's gates that normally wait for you, the house rules name them, and each report says which ack the step ran on. It never starts a review, and the PR and the merge still wait for your ask. `brain ack off` takes it back. |
| `brain conclude at 17:15` | The time the session wraps itself up. The hooks count down to it, the agent winds down in the last 15 minutes, and once it passes the agent stops its sub agents, commits what passed the gates and writes the handover. `brain conclude off` clears it. |
| `brain handover` | The note a session leaves for the next when it passes work on or stops mid task, kept on this machine and never in git. Section 8.4 of [`.agents/SYSTEM.md`](.agents/SYSTEM.md) says when the agent writes one and why to ask for one before you compact a session yourself. |
| `brain port` and `brain upgrade` | The two commands above, run from a kit checkout against your project. |

The full contract, every flag and every refusal, is in
[`commands.md`](.agents/skills/agent-brain/references/commands.md), and
[`SKILL.md`](.agents/skills/agent-brain/SKILL.md) is what the agent reads
to use it.

## What `.agents/` looks like

Here is how it ships, empty and ready.

```text
.agents/
├── SYSTEM.md             the rulebook every agent works by
├── VERSION               the kit release this project carries
├── INDEX.md              the spine, built by the tool from the files it lists
├── README.md             what the directory is and how an agent boots from it
├── house-rules.md        the branch contract and code review protocol
├── brain                 the launcher, python3 .agents/brain runs the brain tool
├── skills/agent-brain/   the brain tool and the format of every file here
├── skills/branch-review/ the code review, run on your word
├── rules/project.md      your project's own rules, loaded by every session
├── docs/INDEX.md         the knowledge library
├── memory/INDEX.md       facts learned along the way
├── plans/INDEX.md        the plans, each a goal with its steps
├── build-specs/INDEX.md  one build spec per branch, written before the code
├── todos/INDEX.md        the work tracker
├── bugs/INDEX.md         the defect tracker
├── decisions/INDEX.md    decisions taken and why
└── reviews/INDEX.md      code review ledgers
```

And here is a filled in example, so you can see the shape once files
land.

```text
.agents/
├── SYSTEM.md
├── INDEX.md
├── README.md
├── house-rules.md
├── rules/
│   ├── INDEX.md
│   ├── project.md
│   └── release-steps.md
├── docs/
│   ├── INDEX.md
│   ├── foundation/
│   │   ├── architecture.md
│   │   └── stack.md
│   ├── systems/
│   │   ├── auth.md
│   │   └── billing.md
│   └── ops/
│       └── deploy.md
├── memory/
│   ├── INDEX.md
│   └── stripe-webhooks-retry-twice.md
├── plans/
│   ├── INDEX.md
│   └── billing-launch.md
├── build-specs/
│   ├── INDEX.md
│   └── BUILD-001-card-checkout.md
├── todos/
│   ├── INDEX.md
│   ├── TODO-001-export-to-csv.md
│   └── TODO-002-dark-mode.md
├── bugs/
│   ├── INDEX.md
│   └── BUG-001-login-loop-on-expired-token.md
├── decisions/
│   ├── INDEX.md
│   └── DEC-001-postgres-over-sqlite.md
├── reviews/
│   ├── INDEX.md
│   └── 2026-09-feat-billing/
│       └── ledger.md
└── .handover/            the note for the next session, never in git
    ├── .gitignore
    ├── handover.lock
    └── handover.md
```

The rules, the trackers, the build specs, the docs library, and memory
each carry an `INDEX.md` listing what is inside, and `.agents/INDEX.md`
at the top names the rules, the docs, the trackers, the build specs and
memory with their counts. `.handover/` carries none, the spine covers
it. It holds the note for the next session, which the agent-brain
[skill sheet](.agents/skills/agent-brain/SKILL.md#the-brains-files)
governs, beside the lock sessions take turns on and an ignore file of
its own. Git ignores the folder, so a fresh clone has none.

## Where to read next

- [`.agents/SYSTEM.md`](.agents/SYSTEM.md): the full rulebook.
- [`.agents/README.md`](.agents/README.md): how a cold agent boots.
- [`.agents/house-rules.md`](.agents/house-rules.md): the branch contract and review protocol.
- [`.agents/skills/agent-brain/SKILL.md`](.agents/skills/agent-brain/SKILL.md#the-brains-files): the brain tool as the agent uses it, and the format every file in `.agents/` keeps.
- [`.agents/skills/agent-brain/references/commands.md`](.agents/skills/agent-brain/references/commands.md): every command of the tool, with its flags and refusals.
- [`.agents/skills/branch-review/SKILL.md`](.agents/skills/branch-review/SKILL.md): the review as the agent runs it, step by step.
- [`CONTRIBUTING.md`](CONTRIBUTING.md): the absolutes on one page.
