# Example Agent Setup

A small kit you drop into a project so a coding agent (Claude Code,
Codex, anything that reads `CLAUDE.md` or `AGENTS.md`) knows how to
behave there and has a place to keep what it learns. It is two things,
a rulebook and a folder called `.agent/`, and both are plain files
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
| `CLAUDE.md` | The rulebook. How to write code, how to talk to you, where docs go, how a branch gets reviewed, how git is used. Claude Code reads this one. |
| `AGENTS.md` | The same rulebook, saved under the name other agents look for. The two stay identical. |
| `.agent/` | The project's memory. Docs, todos, bugs, decisions, review ledgers, handovers, and small facts the agent learns. Ships empty apart from the rules that say how each folder is used. |
| `CONTRIBUTING.md` | The hard rules for humans and agents on one page. |
| `CODEOWNERS` | Names who owns the repo on the forge. Put your own handle in. |
| `.gitignore` | One line, so a stray worktree folder never gets committed. |

Everything is generic on purpose. Anything specific to your project goes
in a section called `## 0. Project Rules` at the very top of `CLAUDE.md`
(and `AGENTS.md`), and into the files your project grows inside
`.agent/`. The kit itself never needs editing.

## Setting up a new project

Two parts. Get the files in, then two small edits.

### Get the kit in

Three ways, easiest first. All of them end with the kit's files sitting
in your repo root next to your code.

**Ask your agent.** If your machine can already reach the forge (you
have cloned from `forge.example.com` before, or `tea` is logged in), open
Claude Code in your project and paste this prompt.

```text
Clone https://forge.example.com/example/agent-setup into a temp folder.
Copy its .agent folder, CLAUDE.md, AGENTS.md, CONTRIBUTING.md and
CODEOWNERS into this repo. Append its .gitignore line to ours. Put my
handle in CODEOWNERS. Then do the two setup edits its README describes
and tell me what you did.
```

**Terminal.** Clone, then copy the files across.

```bash
git clone https://forge.example.com/example/agent-setup
cd your-project
cp -R ../agent-setup/.agent ../agent-setup/CLAUDE.md ../agent-setup/AGENTS.md \
      ../agent-setup/CONTRIBUTING.md ../agent-setup/CODEOWNERS .
cat ../agent-setup/.gitignore >> .gitignore
```

Adjust the `../agent-setup` path if you cloned somewhere else. The last
line appends to your `.gitignore` rather than replacing it, which is
what you want whether or not you already have one.

**Download.** Sign in to the forge, open
[example/agent-setup](https://forge.example.com/example/agent-setup), and
download the ZIP from the Code button. Unzip it and move `.agent`,
`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, and `CODEOWNERS` into your
project's root folder, then add the one line from its `.gitignore` to
yours. Two of those (`.agent` and `.gitignore`) are hidden files, so if
you are in Finder press `Cmd + Shift + .` to see them.

### Then two small edits

1. Open `CODEOWNERS` and replace `@ecstra` with your own handle.

2. Decide whether you need a `## 0. Project Rules` section. It goes at
   the very top of `CLAUDE.md`, above everything else, and gets copied
   into `AGENTS.md` too. It is for what the general rules cannot know
   about your project.
   - the gates: the exact test suites, analyzers, builds, and validators
     that must be green before a review starts
   - the tooling: how PRs are opened, how the app runs
   - anything else the general sections do not cover

   It is optional. A brand new project usually has nothing to put there
   yet, so skip it and add it when the first gate exists.

Commit, and start your first session. The agent reads `.agent/INDEX.md`
on its own, you do not need to point at anything.

From then on `.agent/` fills up as a side effect of the work. The agent
writes docs as it builds things, files todos and bugs as they come up,
records decisions when they are made, and keeps small facts it learns.
You will never sit down to "maintain" it.

## Bringing an existing project over

Most projects that adopt the kit already have a pile of docs, an old
`CLAUDE.md`, a TODO list somewhere, and notes nobody has opened in
weeks. None of that is lost. All of it gets filed into `.agent/`, and
the agent does the filing, because there is a lot of it and every file
needs the right header block and index line.

The port is a normal branch like any other work. The agent reads, then
files, then cleans up, and you review the branch before it merges.

### The flow

1. **Get the kit in.** Any of the three ways above. If you already have
   a `CLAUDE.md`, `AGENTS.md`, or `CONTRIBUTING.md`, keep yours aside,
   the copy overwrites them and step 3 folds them back in.

2. **The agent reads everything first.** The whole project, the code,
   every doc and note it can find, and then the specs in `.agent/spec/`
   so it knows the target format. No filing before the reading is done,
   and it shows you the plan before it moves anything.

3. **It files each thing where it belongs**, on its own branch, with the
   header block and index line each file needs. The map below says where
   each kind of thing goes. Your own wording is kept in todos, and
   nothing gets shortened on the way. Old `CLAUDE.md` or `AGENTS.md`
   content becomes `## 0. Project Rules`.

4. **It cleans up.** Once a doc lives in `.agent/`, the old copy is
   deleted. The one exception is anything a person wrote by hand, which
   stays where it is, untouched. The agent tells the two apart by the
   writing itself, since a human's notes do not read like generated
   docs, and it lists what it left alone so you can decide.

5. **You review the branch** and merge it. After that the root holds
   only `README.md`, `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, and
   `CODEOWNERS`. If you keep a small human `docs/` folder, it points
   into `.agent/docs/` rather than repeat it.

### Where things go

| What you have today | Where it goes |
|---|---|
| Your own `CLAUDE.md` or `AGENTS.md` | `## 0. Project Rules` at the top of the new `CLAUDE.md`, mirrored in `AGENTS.md`. Anything the general rules already cover is dropped. |
| A `docs/` folder, wiki pages, architecture or design notes | `.agent/docs/`, sorted into a category folder (`foundation/`, `systems/`, `ops/`, `research/`), one line each in `.agent/docs/INDEX.md`. |
| ADRs or a decisions log | `.agent/decisions/`, one file per decision. |
| A TODO list, roadmap, or backlog | `.agent/todos/`, one file per item, your wording kept as is. |
| Known bugs, issue notes | `.agent/bugs/`, one file per bug. |
| Gotchas, tribal knowledge, "remember that" notes | `.agent/memory/`, one fact per file. |
| Your `CONTRIBUTING.md` | Replaced by the kit's. Extra rules of yours go into `## 0. Project Rules`. |
| Your `README.md` | Stays at the root, trimmed to what the project is and how to run it, with links onward. Detail moves into `.agent/docs/`. |
| Changelogs, status reports, meeting notes | Not agent knowledge. Left where they are or dropped. |

### The prompt

Get the kit in, then paste this into your agent. It covers the whole
flow above.

```text
We are adopting the agent kit that now sits in this repo. Do the port
on a new branch. First read the whole project: the code, every doc and
note, our old CLAUDE.md or AGENTS.md if there is one, and every TODO
list. Then read .agent/INDEX.md and everything in .agent/spec/ so you
know the target format. Show me a plan of what goes where before you
move anything. Then file it all into .agent/ (docs, decisions, todos,
bugs, memory, everything) with correct frontmatter and index lines,
keeping my wording in todos. Old CLAUDE.md or AGENTS.md content becomes
section 0 Project Rules. When it is filed, delete the old copies of the
docs you moved, but leave anything a human wrote by hand where it is
and list those for me. Then tell me what you did and where.
```

## Keeping the kit current

When this repo's rulebook changes, copy the new `CLAUDE.md` over yours
and put your `## 0. Project Rules` back on top. Section 0 is the only
part that is yours. Copy the result to `AGENTS.md`. The files in
`.agent/spec/` update the same way, new over old, and nothing else in
`.agent/` is touched. Or, again, ask the agent to do it.

## What `.agent/` looks like

Here is how it ships, empty and ready.

```text
.agent/
├── INDEX.md              the spine, one line per file, read first
├── README.md             what the directory is and how an agent boots from it
├── house-rules.md        the branch contract and code review protocol
├── spec/                 the format rules, one per folder
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
.agent/
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

Every folder has an `INDEX.md` that lists what is inside, and
`.agent/INDEX.md` at the top lists everything. `handover/` is the one
folder that does not ship, it appears the first time a session hands
work over.

## Where to read next

- [`CLAUDE.md`](CLAUDE.md), the full rulebook.
- [`.agent/README.md`](.agent/README.md), how a cold agent boots.
- [`.agent/house-rules.md`](.agent/house-rules.md), the branch contract and review protocol.
- [`.agent/spec/conventions.md`](.agent/spec/conventions.md), the shared rules every file in `.agent/` obeys.
- [`CONTRIBUTING.md`](CONTRIBUTING.md), the absolutes on one page.
