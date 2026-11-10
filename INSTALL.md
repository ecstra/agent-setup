# Install

Agent Setup installs into a project with one command. It needs Python
3.9 or later and git. The see skill also needs ffmpeg.

The clone of this repo is only where the installer runs from. It stays
outside your project, and the installer copies the files into your
project's own root.

```text
projects/
├── agent-setup/      the clone, the source of the install
└── your-project/     where you run the installer
    ├── .agents/      the rulebook, the skills and the memory
    ├── .claude/      hooks, sub agents and chat style, the same for .codex/ and .gemini/
    ├── AGENTS.md     with CLAUDE.md, GEMINI.md and CONTRIBUTING.md
    └── ...           your own files, untouched
```

## Install

1. Commit your work. The installer refuses while a file it would
   replace has uncommitted changes.
2. Clone this repo next to your project, never inside it.
   ```bash
   git clone <repo URL> ../agent-setup
   ```
   `<repo URL>` is this repo's clone URL, from the top of its page.
3. From your project's root, run the installer.
   ```bash
   python3 ../agent-setup/.agents/brain port
   ```
4. Copy the owners file in, and put your own handle in it.
   ```bash
   cp ../agent-setup/CODEOWNERS .
   ```
5. Commit, and start a session. The agent reads `.agents/INDEX.md` on
   its own.

Run the installer from a plain terminal. Claude Code's sandbox refuses
writes under `.claude/agents`, where the review's sub agents go.

A second run refuses, since the project is already set up.

### Let your agent do it

Paste this into your agent, with the clone URL in place of
`<repo URL>`.

```text
Clone <repo URL> into a folder beside this repo, then run its installer
from our root:
python3 <that folder>/.agents/brain port
It refuses while a file it would replace has uncommitted changes, so
commit first. Copy its CODEOWNERS in with my handle in place of the one
it names. If this project already has test, build or lint commands,
name them in .agents/rules/project.md as the gates and the lint lines,
the way <that folder>/INSTALL.md shows. Read what the installer
printed, and tell me what you did and what it listed as left to file.
```

### What the installer changes

- **Added:** the rulebook, the house rules and the skills under
  `.agents/`, the files `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` and
  `CONTRIBUTING.md` at the root, and the hooks, sub agents and chat
  style in `.claude/`, `.codex/` and `.gemini/`.
- **Kept:** your own hooks and settings in those folders, and every
  line of your `.gitignore`. Agent Setup's ignore lines go in a block
  at the top.
- **Moved:** project rules you already had under a `## 0.` heading in
  `AGENTS.md`, `CLAUDE.md` or `GEMINI.md` go into
  `.agents/rules/project.md`. Everything else those files said is
  quoted in `.agents/docs/front-door-words.md` for your agent to sort.
- **Reported:** each root file it replaced, with where git keeps the
  old one, and a list of what it found that belongs in the memory.
  Keep that output. Nothing prints it again.

## Tell it about your project

`.agents/rules/project.md` holds what the general rules cannot know
about your project. Every session loads it. Name your gates there, the
commands that must pass before a review and a merge, and your linters.

````markdown
### Gates

```bash
npm test
```

### Lint

```text
*.ts npx eslint --fix {file}
```
````

Each fenced block under Gates is one gate. Each line under Lint is a
file pattern and a command, with `{file}` where the file goes. The
linters run on every file the agent writes, and the gates run before
each review and merge. A project with neither yet can leave the file
as it is.

The prose check reads every markdown file git lists. To leave out text
your project did not write, such as a vendored library, a fork or
generated docs, mark its folder in `.gitattributes`, as in
`vendor/** linguist-vendored` or `docs/api/** linguist-generated`.

Any other instruction your project needs is a rule of its own. Ask the
agent to add one and it files it beside `project.md`.

## Bring in what you already have

Most projects already have docs, an old `CLAUDE.md`, a TODO list and
notes. None of it is lost. Your agent files all of it into `.agents/`.

| What you have today | Where it goes |
|---|---|
| Your own `AGENTS.md`, `CLAUDE.md` or `GEMINI.md` | Read against the new rulebook. What the general rules already cover is dropped, and what is specific to your project becomes rules. |
| A `docs/` folder, wiki pages, architecture or design notes | `.agents/docs/`, sorted by category. What a person wrote by hand stays where it is. |
| ADRs or a decisions log | `.agents/decisions/`, one file per decision. |
| A TODO list, roadmap or backlog | `.agents/todos/`, one file per item in your wording. A roadmap becomes plans in `.agents/plans/`. |
| Known bugs and issue notes | `.agents/bugs/`, one file per bug. |
| Gotchas and "remember that" notes | `.agents/memory/`, one fact per file. |
| Your `README.md` | Stays at the root. |
| Changelogs, status reports, meeting notes | Left where they are. |

Paste this into your agent once the install is done.

```text
We are adopting Agent Setup, which now sits in this repo. Do the port
on a new branch. Before anything else, read the new AGENTS.md and the
rules it points at, and work by them from here on: prose edited with
the proper edit tools, no scripts or heredocs, the header blocks and
indexes inside .agents/ left to the brain tool, house style throughout.
Then read the whole project: the code, every doc and note, and every
TODO list, and the list the installer printed of what is left to file,
which I will paste if you did not run it. Then read .agents/INDEX.md
and the agent-brain skill, its section on the brain's files above all,
so you know the target format and the tool that writes it. Show me a
plan of what goes where before you move anything. Then file it all
into .agents/ (docs, decisions, todos, bugs, memory, everything) one
file at a time through brain new with the prose on standard input,
never by hand, keeping my wording in todos. .agents/rules/project.md
holds the section 0 the installer moved from our old rules, and
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

## Upgrade

1. Pull your clone of this repo.
   ```bash
   git -C ../agent-setup pull
   ```
2. From your project's root, on a branch of its own, run the upgrade.
   ```bash
   python3 ../agent-setup/.agents/brain upgrade
   ```
3. Read the diff and commit.

- **Replaced:** the rulebook, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
  `CONTRIBUTING.md`, the house rules, the skills, the hooks, the
  review's sub agents and the chat style.
- **Yours:** your rules in `.agents/rules/`, every entry your project
  filed, your own hooks and settings, and your `.gitignore` lines.
- **Rebuilt:** the indexes, by the health check that runs at the end.
- **Removed:** files an older release wrote that are no longer part of
  Agent Setup. The report names each one.

The upgrade works from any older release. It stops before it writes
anything when something needs you first, and says what. Each release
page lists what changed in that release and what to do when you come
from an older one.

## Remove

There is no uninstaller. The install is a set of file changes in your
repo, so if you committed it on its own, reverting that commit takes
Agent Setup out again.
