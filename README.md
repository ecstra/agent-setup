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

## Getting the kit into your project

Three ways, easiest first. All of them end with the kit's files sitting
in your repo root next to your code.

### Ask your agent

If your machine can already reach the forge (you have cloned from
`forge.example.com` before, or `tea` is logged in), open Claude Code in
your project and paste this prompt.

```text
Clone https://forge.example.com/example/agent-setup into a temp folder.
Copy its .agent folder, CLAUDE.md, AGENTS.md, CONTRIBUTING.md and
CODEOWNERS into this repo. Append its .gitignore line to ours. Put my
handle in CODEOWNERS. Then follow the setup steps in its README and
tell me what you did.
```

The agent does the copying and the first setup pass. Read the result,
adjust, commit.

### Terminal

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

### Download

Sign in to the forge, open
[example/agent-setup](https://forge.example.com/example/agent-setup), and
download the ZIP from the Code button. Unzip it and move `.agent`,
`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, and `CODEOWNERS` into your
project's root folder, then add the one line from its `.gitignore` to
yours. Two of those (`.agent` and `.gitignore`) are hidden files, so if
you are in Finder press `Cmd + Shift + .` to see them.

## Setting up a new project

Once the files are in place there are only two things to do.

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

If your project already has docs, a CLAUDE.md, a TODO list, or years of
notes, they all still have a home. The kit's rule is that each piece of
knowledge lives in exactly one place. Here is where each thing goes.

| What you have today | Where it goes |
|---|---|
| Your own `CLAUDE.md` or `AGENTS.md` | Its content becomes `## 0. Project Rules` at the top of the new `CLAUDE.md`, mirrored in `AGENTS.md`. Drop anything the general rules already cover. |
| A `docs/` folder, wiki pages, architecture or design notes | `.agent/docs/`, sorted into a category folder (`foundation/`, `systems/`, `ops/`, `research/`), one line each in `.agent/docs/INDEX.md`. |
| ADRs or a decisions log | `.agent/decisions/`, one file per decision. |
| A TODO list, roadmap, or backlog | `.agent/todos/`, one file per item, your wording kept as is. |
| Known bugs, issue notes | `.agent/bugs/`, one file per bug. |
| Gotchas, tribal knowledge, "remember that" notes | `.agent/memory/`, one fact per file. |
| Your `CONTRIBUTING.md` | Replace it with the kit's, or fold your extra rules into `## 0. Project Rules`. |
| Your `README.md` | Stays at the root. Trim it to what the project is and how to run it, and link onward for the rest. Detail moves into `.agent/docs/`. |
| Changelogs, status reports, meeting notes | Not agent knowledge. Leave them where they are or drop them. |

Every file that lands in `.agent/` gets a small header block (the
frontmatter, described in
[`.agent/spec/conventions.md`](.agent/spec/conventions.md)) and a line
in its folder's `INDEX.md`. That is fiddly by hand, so do not do it by
hand. Get the kit in first, then paste this prompt into your agent.

```text
Read .agent/INDEX.md and .agent/spec/conventions.md. Then go through
our existing docs, notes, todo lists and any old CLAUDE.md or
AGENTS.md, and file each piece where the README's "Bringing an
existing project over" table says it goes, with the right frontmatter
and index lines. Keep my wording in todos. Show me the plan before you
move anything.
```

Review the plan, let it run, then check that the root only holds
`README.md`, `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, and
`CODEOWNERS`. If you keep a human `docs/` folder, keep it small and
have it point into `.agent/docs/` rather than repeat it.

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

And here is the same directory a few months into a real project.

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
