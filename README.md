# Example Agent Setup

A small kit you drop into a project so a coding agent (Claude Code,
Codex, Gemini CLI, anything that reads `AGENTS.md`) knows how to
behave there and has a place to keep what it learns. It is two things,
a rulebook and a folder called `.agents/`, and both are plain files
committed to git. That is the whole trick. Because they live in the
repo, a fresh session on any machine picks up exactly where the last one
stopped.

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
| `AGENTS.md` | The front door every agent reads. It points at the rulebook, and it holds your project's own rules when you have some. |
| `CLAUDE.md` and `GEMINI.md` | One line each, pulling in `AGENTS.md`, because Claude Code and Gemini CLI look for their own filename. |
| `.agents/SYSTEM.md` | The rulebook. How to write code, how to talk to you, where docs go, how a branch gets reviewed, how git is used. |
| `.agents/` | The project's memory. Docs, todos, bugs, decisions, review ledgers, handovers, and small facts the agent learns. Ships empty apart from the rules that say how each folder is used. |
| `CONTRIBUTING.md` | The hard rules for humans and agents on one page. |
| `CODEOWNERS` | Names who owns the repo on the forge. Put your own handle in. |
| `.gitignore` | Keeps your `.env` out of git, along with any stray worktree folder. |

Everything is generic on purpose. Anything specific to your project goes
in a section called `## 0. Project Rules` at the top of `AGENTS.md`, and
into the files your project grows inside `.agents/`. The rest of the kit
stays as it ships, apart from your handle in `CODEOWNERS`.

## Installation

Three ways to get the kit in, easiest first. All of them end with the
kit's files sitting in your repo root next to your code.

### Ask your agent

If your machine can already reach the forge (you have cloned from
`forge.example.com` before, or `tea` is logged in), open Claude Code in
your project and paste this prompt.

```text
Clone https://forge.example.com/example/agent-setup into a temp folder.
Copy its .agents folder, AGENTS.md, CLAUDE.md, GEMINI.md,
CONTRIBUTING.md and CODEOWNERS into this repo. Append its .gitignore
lines to ours. Put my handle in CODEOWNERS. If this project already has
test, build, or lint commands, add a "## 0. Project Rules" section at
the top of AGENTS.md naming them as the gates. Then tell me what you
did.
```

### Terminal

Clone, then copy the files across.

```bash
git clone https://forge.example.com/example/agent-setup
cd your-project
cp -R ../agent-setup/.agents ../agent-setup/AGENTS.md ../agent-setup/CLAUDE.md \
      ../agent-setup/GEMINI.md ../agent-setup/CONTRIBUTING.md \
      ../agent-setup/CODEOWNERS .
echo >> .gitignore
cat ../agent-setup/.gitignore >> .gitignore
```

Adjust the `../agent-setup` path if you cloned somewhere else. The last
two lines append to your `.gitignore` rather than replacing it, which is
what you want whether or not you already have one. The `echo` guarantees
a line break before the kit's rules, so its first line cannot fuse onto
the end of yours.

### Download

Use the Code button at the top of this page and download the ZIP.
Unzip it and move `.agents`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
`CONTRIBUTING.md`, and `CODEOWNERS` into your project's root folder,
then add the lines from its `.gitignore` to yours. Two of those (`.agents` and `.gitignore`)
are hidden files, so if you are in Finder press `Cmd + Shift + .` to
see them.

> **Set up by hand?** The agent path does these two edits for you. The
> terminal and download paths leave them to you.
>
> 1. `CODEOWNERS`: replace `@ecstra` with your own handle.
> 2. `## 0. Project Rules`: optional. It goes at the top of `AGENTS.md`,
>    directly under the title, and holds what the general rules cannot
>    know about your project. The
>    gates (the exact test suites, analyzers, builds, and validators
>    that must be green before a review), the tooling (how PRs are
>    opened, how the app runs), anything else the general sections do
>    not cover. A project with no gates yet has nothing to put there,
>    so skip it and add it when the first gate exists.

Commit, and start your first session. The agent reads `.agents/INDEX.md`
on its own, you do not need to point at anything.

From then on `.agents/` fills up as a side effect of the work. The agent
writes docs as it builds things, files todos and bugs as they come up,
records decisions when they are made, and keeps small facts it learns.
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
three ways, and skip nothing. Keep your old `AGENTS.md`, `CLAUDE.md`,
`GEMINI.md`, or `CONTRIBUTING.md` aside, the copy overwrites all four
and the agent folds them back in.

### What the agent will do

1. **Sync with the new rulebook first**: read the new `AGENTS.md` and
   the rules it points at, then work by them from the first move. The port itself obeys the kit's
   rules, so every file is written by hand with the proper edit tools,
   no scripts, and the house style holds throughout.
2. **Read everything**: the whole project, the code, every doc and note
   it can find, then the specs in `.agents/spec/` so it knows the target
   format. It shows you a plan before it moves anything.
3. **File each thing where it belongs**: on its own branch, one file at
   a time, with the header block and index line each file needs, per
   the map below. Your wording is kept in todos and nothing gets
   shortened on the way.
4. **Port the old rules, never paste them**: the old `CLAUDE.md` or
   `AGENTS.md` is read against the new rules. Whatever the general
   sections already say is dropped, and only what is truly project
   specific is rewritten into `## 0. Project Rules` at the top of the
   new `AGENTS.md`.
5. **Do all of it**: a project can hold hundreds or thousands of files,
   old and new, and the port covers every one, never a sample. If the
   volume calls for it, the agent lists everything in a ledger first and
   works through it in batches, ticking each file off, so nothing is
   skipped and a later session can pick up where it stopped.
6. **Clean up**: once a doc lives in `.agents/`, the old copy is
   deleted. The one exception is anything a person wrote by hand, which
   stays where it is, untouched. The agent tells the two apart by the
   writing itself, since a human's notes do not read like generated
   docs, and it lists what it left alone so you can decide.
7. **Hand you the branch**: you say when it is ready for review, and
   the agent runs the review the way the house rules describe, findings
   in a ledger, fixed batch by batch with your ack on each. Then it
   opens the PR and merges, both on your word. When the PR opens and
   whether as a draft is your project's own rule in section 0, so the
   agent never asks. After that the root holds `README.md`, `AGENTS.md`,
   `CLAUDE.md`, `GEMINI.md`, `CONTRIBUTING.md`, and `CODEOWNERS`, plus
   your `docs/` folder if you keep one. What a person wrote by hand stays as it is,
   and anything new in there links into `.agents/docs/` rather than
   repeating it.

### Where things go

| What you have today | Where it goes |
|---|---|
| Your own `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md` | Read against the new rulebook and rewritten into `## 0. Project Rules` at the top of the new `AGENTS.md`. Never pasted whole, anything the general rules already cover is dropped. |
| A `docs/` folder, wiki pages, architecture or design notes | `.agents/docs/`, sorted into a category folder (`foundation/`, `systems/`, `ops/`, `research/`), one line each in `.agents/docs/INDEX.md`. What a person wrote by hand stays where it is. |
| ADRs or a decisions log | `.agents/decisions/`, one file per decision. |
| A TODO list, roadmap, or backlog | `.agents/todos/`, one file per item, your wording kept as is. |
| Known bugs, issue notes | `.agents/bugs/`, one file per bug. |
| Gotchas, tribal knowledge, "remember that" notes | `.agents/memory/`, one fact per file. |
| Your `CONTRIBUTING.md` | Replaced by the kit's. Extra rules of yours go into `## 0. Project Rules`. |
| Your `README.md` | Stays at the root, trimmed to what the project is and how to run it, with links onward. Detail moves into `.agents/docs/`. |
| Changelogs, status reports, meeting notes | Not agent knowledge. Left where they are or dropped. |

### The prompt

Paste this into your agent once the kit is in. It covers the whole flow
above.

```text
We are adopting the agent kit that now sits in this repo. Do the port
on a new branch. Before anything else, read the new AGENTS.md and the
rules it points at, and work by them from here on: every file written
by hand with the proper edit
tools, no scripts or heredocs, house style throughout. Then read the
whole project: the code, every doc and note, our old CLAUDE.md or
AGENTS.md if there is one, and every TODO list. Then read
.agents/INDEX.md and everything in .agents/spec/ so you know the target
format. Show me a plan of what goes where before you move anything.
Then file it all into .agents/ (docs, decisions, todos, bugs, memory,
everything) one file at a time with correct frontmatter and index
lines, keeping my wording in todos. Do not paste the old CLAUDE.md or
AGENTS.md into section 0: read it against the new rulebook, drop what
the general sections already cover, and rewrite only the truly project
specific parts into "## 0. Project Rules" at the top of AGENTS.md.
This may be hundreds or thousands of files. Do every one,
never a sample. If the volume needs it, list everything in a ledger
first and work in batches, ticking each file off. When it is all
filed, delete the old copies of the docs you moved, but leave anything
a human wrote by hand where it is and list those for me. Then tell me
what you did and where, and wait for me to call the review.
```

## Keeping the kit current

When this repo's rulebook changes, copy the kit's own files over yours
and leave everything your project wrote alone.

- `.agents/SYSTEM.md`: new over old. The rules are the kit's from end to
  end, so nothing of yours is in there to save.
- `AGENTS.md`: keep your `## 0. Project Rules` and take the kit's wording
  for the rest. `CLAUDE.md` and `GEMINI.md` never change.
- `CONTRIBUTING.md` and `.agents/house-rules.md`: new over old. They
  carry the same rules in shorter form, so they move with the rulebook.
- `.agents/README.md` and `.agents/spec/`: new over old. Nothing else
  inside `.agents/` is touched, because the rest of it is your project's.

Or, again, ask the agent to do it.

## What `.agents/` looks like

Here is how it ships, empty and ready.

```text
.agents/
├── SYSTEM.md             the rulebook every agent works by
├── INDEX.md              the spine, one line per file, read first
├── README.md             what the directory is and how an agent boots from it
├── house-rules.md        the branch contract and code review protocol
├── spec/                 the format rules, one per content folder
│   ├── conventions.md    the shared rules, header block, naming, links, indexes
│   ├── docs.md
│   ├── memory.md
│   ├── bugs.md
│   ├── todos.md
│   ├── decisions.md
│   ├── reviews.md
│   └── handover.md
├── docs/INDEX.md         the knowledge library
├── memory/INDEX.md       facts learned along the way
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
├── spec/
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
└── handover/
    └── billing-cutover.md
```

The trackers, the docs library, and memory each carry an `INDEX.md`
listing what is inside, and `.agents/INDEX.md` at the top lists
everything. `spec/` and `handover/` carry none, the spine covers both.
`handover/` is also the one folder that does not ship, it appears the
first time a session hands work over.

## Where to read next

- [`.agents/SYSTEM.md`](.agents/SYSTEM.md): the full rulebook.
- [`.agents/README.md`](.agents/README.md): how a cold agent boots.
- [`.agents/house-rules.md`](.agents/house-rules.md): the branch contract and review protocol.
- [`.agents/spec/conventions.md`](.agents/spec/conventions.md): the shared rules every file in `.agents/` obeys.
- [`CONTRIBUTING.md`](CONTRIBUTING.md): the absolutes on one page.
