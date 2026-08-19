# Example Agent Setup

The starting kit for a project's agent setup. Drop it into a repo and a
coding agent arrives with its rules and its brain already in place. All
of it is committed, so any agent on any machine resumes cold.

## What is in the box

| File | What it does |
|---|---|
| `CLAUDE.md` | The general rulebook. How the agent writes code, how it talks, where docs go, how the agent directory is kept, how a branch gets reviewed, the git rules. Read by Claude Code. |
| `AGENTS.md` | The same rulebook under the name other tools look for. Keep the two identical. |
| `.agent/` | The agent directory, the project's brain. Ships empty, with the specs that govern each folder. |
| `CONTRIBUTING.md` | The hard rules for humans and agents on one page. Points into `.agent/house-rules.md` for the full protocol. |
| `CODEOWNERS` | One rule handing the whole repo to one owner, written for Gitea (Go regex, so `.*`). Swap in your own handle. |
| `.gitignore` | One entry, `.agent/.worktrees/`, the only place a worktree may ever live. |

Everything here is generic on purpose. Project specifics belong in a
`## 0. Project Rules` section at the top of the project's `CLAUDE.md`
and in the files the project grows inside `.agent/`.

## How it fits together

Two things travel with the kit.

The rulebook (`CLAUDE.md`, mirrored as `AGENTS.md`) tells the agent how
to behave. It is general and reads the same in every project that
carries it.

The agent directory (`.agent/`) holds the project's own knowledge, one
folder per job (docs, memory, todos, bugs, decisions, reviews,
handovers), each with a spec in `.agent/spec/` that states its format
and lifecycle. An agent boots by reading `.agent/INDEX.md`, obeys
`.agent/house-rules.md` for branches, commits, and reviews, and follows
the spec for every file it writes there. [`.agent/README.md`](.agent/README.md)
has the map.

Two rules hold across the whole directory. Nothing secret ever enters
it, since it is committed. And nothing in it points at any machine's
local state.

## Setting up a new project

1. Get the kit.

   ```bash
   git clone https://forge.example.com/example/agent-setup
   ```

2. Copy it into your repo root.

   ```bash
   cp -R agent-setup/.agent agent-setup/CLAUDE.md agent-setup/AGENTS.md \
         agent-setup/CONTRIBUTING.md agent-setup/CODEOWNERS agent-setup/.gitignore \
         your-project/
   ```

3. Open `CODEOWNERS` and put your own handle in place of `@ecstra`.

4. Add a `## 0. Project Rules` section at the very top of `CLAUDE.md`,
   above everything else, and mirror it into `AGENTS.md`. It holds what
   the general rules cannot know about your project.
   - the gates: the exact suites, analyzers, builds, and validators that
     must be green before a review starts
   - the tooling: how PRs are opened, how the app runs
   - anything else the general sections do not cover

   The section is optional. Skip it until the project has something to
   put there.

5. Commit and start the first agent session. The agent reads
   `.agent/INDEX.md` first, nothing else needs pointing out.

The directory starts empty and fills in the same motion as the work.
The agent writes docs as systems get built, files todos and bugs on
intake, records decisions as they are taken, and stores the facts it
learns in memory. Nobody maintains it as a separate chore.

## Porting an existing project

Same install, with a merge step for the files you already have.

1. Get the kit and copy it in. The copy overwrites any `CLAUDE.md`,
   `AGENTS.md`, or `CONTRIBUTING.md` you already have, so keep yours
   aside to fold in at step 2. Append the `.gitignore` instead of
   replacing it.

   ```bash
   cp -R agent-setup/.agent agent-setup/CLAUDE.md agent-setup/AGENTS.md \
         agent-setup/CONTRIBUTING.md agent-setup/CODEOWNERS your-project/
   cat agent-setup/.gitignore >> your-project/.gitignore
   ```

2. Move what you already have into its one home.

   | You have | Where it goes |
   |---|---|
   | Your own `CLAUDE.md` or `AGENTS.md` | Its content becomes `## 0. Project Rules` at the top of the new `CLAUDE.md`, mirrored in `AGENTS.md`. Drop anything the general sections already say. |
   | A `docs/` folder, wiki pages, architecture or design notes | `.agent/docs/` under a category folder (`foundation/`, `systems/`, `ops/`, `research/`), one line each in `.agent/docs/INDEX.md`. Format in [`.agent/spec/docs.md`](.agent/spec/docs.md). |
   | ADRs or a decisions log | `.agent/decisions/`, one file per decision with a `DEC-###` id. Format in [`.agent/spec/decisions.md`](.agent/spec/decisions.md). |
   | A TODO list, roadmap, or backlog | `.agent/todos/`, one item per file with a `TODO-###` id, your wording preserved. Format in [`.agent/spec/todos.md`](.agent/spec/todos.md). |
   | Known bugs, issue notes | `.agent/bugs/`, one per file with a `BUG-###` id. Format in [`.agent/spec/bugs.md`](.agent/spec/bugs.md). |
   | Gotchas, tribal knowledge, "remember that" notes | `.agent/memory/`, one fact per file. Format in [`.agent/spec/memory.md`](.agent/spec/memory.md). |
   | Your `CONTRIBUTING.md` | Replace it with the kit's, or fold your extra rules into `## 0. Project Rules`. |
   | Your `README.md` | Stays at the root. Trim it to the front door, what the project is and how to run it, and link onward for the rest. Detail moves into `.agent/docs/`. |
   | Changelogs, status reports, meeting notes | Not agent knowledge. Leave them where they are or drop them. `decisions/` is not a changelog. |

3. Every file that lands in `.agent/` gets the frontmatter from
   [`.agent/spec/conventions.md`](.agent/spec/conventions.md) and a line
   in its folder's `INDEX.md`. An index that disagrees with its folder is
   a bug, so move both together.

4. Keep the root clear. After the port the only docs at the root are
   `README.md`, `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, and
   `CODEOWNERS`. If you keep a human `docs/` folder, keep it small and
   have it point into `.agent/docs/` rather than repeat it.

The port is a good first job for the agent itself. Point it at this
README and your old docs and tell it to file each thing where the map
says, then review the result. Filing with the right frontmatter and
index line is exactly what the specs describe.

## Keeping the kit current

When this repo's rulebook changes, copy the new `CLAUDE.md` into your
project and put your `## 0. Project Rules` back on top. Section 0 is
the only part that is yours, everything below it is the kit's. Mirror
the result into `AGENTS.md`. The files in `.agent/spec/` update the
same way, new spec over old, and nothing else inside `.agent/` is
touched.

## Where to read next

- [`CLAUDE.md`](CLAUDE.md), the full rulebook.
- [`.agent/README.md`](.agent/README.md), how a cold agent boots.
- [`.agent/house-rules.md`](.agent/house-rules.md), the branch contract and review protocol.
- [`.agent/spec/conventions.md`](.agent/spec/conventions.md), the shared rules every file in `.agent/` obeys.
- [`CONTRIBUTING.md`](CONTRIBUTING.md), the absolutes on one page.
