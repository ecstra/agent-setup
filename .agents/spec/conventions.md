---
name: conventions
kind: doc
description: the shared rules every file in .agents obeys, frontmatter, naming, links, indexes
updated: 2026-09-23
links: [README.md]
---

# Conventions

The shared law. Each folder's own spec adds to this, never contradicts it.

## Frontmatter

Every markdown file in .agents opens with:

```
---
name: <unique-kebab-slug>
kind: doc | memory | bug | todo | decision | review
description: <one line, what this file holds>
updated: <YYYY-MM-DD, the last content change>
links: [<paths of related files, relative to .agents/>]
---
```

Kinds add their own fields (status, severity, area, by, date, parent),
defined in that kind's spec. `name` is unique across the whole directory
and normally equals the filename without extension.

The header is the kit's own shape, not general YAML. One key per line
at the margin, `key: value`, each key once, nothing blank or indented
between the fences. A value is plain text taken as written, so a colon
inside it is fine and nothing is ever quoted. A list sits on its key's
line as `[a, b]`. The brain tool writes headers this way and refuses to
read one written any other way, naming the line and the fix.

Two places sit outside this rule. `SYSTEM.md` carries no frontmatter at
all, since it is the rulebook and an agent takes it exactly as it
stands. `skills/` holds the kit's skills, and its files follow the
Agent Skills standard rather than this spec, so doctor holds them to
the prose and boundary rules below and to nothing in this section. A
project may keep skills of its own there too, each a folder with a
SKILL.md that doctor links for Claude Code, under any name but the
kit's own, `agent-brain` and `branch-review`, which the upgrade
replaces whole.

## Naming and ids

Files are kebab case. Tracked kinds carry ids: `BUG-###`, `TODO-###`,
`DEC-###`, zero padded, assigned as the next free number in that folder,
never reused. The filename is `<ID>-<short-slug>.md`.

## Links

Two forms, each with its job:

- Frontmatter `links:` lists paths relative to `.agents/`, such as
  `bugs/BUG-004-token-loop.md`, so an agent opens the file without
  searching for it. Each file is listed once. The brain tool rewrites
  every one when a file moves, and doctor turns a link written as a
  name into its path and drops a repeat.
- Body links are real markdown relative links that actually resolve, to
  files in .agents and to project files both. A link that does not
  resolve is a bug.

Every frontmatter link reaches a file that exists. Something worth
writing is a todo, not a dangling link.

## Indexes

`.agents/INDEX.md` is the spine: one line per file, grouped by folder.
The trackers, the docs library, and memory carry their own INDEX.md too,
however few files they hold, and the spine may summarize those groups
with counts plus the open items. `spec/` and `handover/` carry none, the
spine names them directly. An index line is `- [name](path), hook` where
the hook is the description or a shorter cut of it.

The upkeep rule: any change to a file updates its `updated:` date in the
same commit, and the indexes are rebuilt by the brain tool, never edited
by hand. The tool owns an index whole, its frontmatter as much as its
body, and an index that differs from what it builds is a bug that
doctor rebuilds.

A brain written before the tool existed reads these rules as its
target. `brain upgrade` brings it to the current layout first. Then
doctor names every way it falls short, `--fix` repairs the mechanical
part (indexes, names, links, dates, the style copies and the skill
link), and what is left is fixed by hand through the tool, one finding
at a time.

## Prose

House style: no em-dashes, no semicolons, plain words, colons only as
list labels. Terse beats complete. A claim about the code names the file
it is true in, so a sync round can verify it mechanically. Never leave a
line broken mid sentence or cut mid word: wrap prose naturally or not at
all.

## Boundaries

- No secrets, ever. This directory is committed.
- No machine paths, no user personal facts. Project truth only.
