# Example Agent Instructions

The starting kit for any new project's agent setup. Copy these into a
fresh repo and the agent arrives with its rules and its brain:

- `CLAUDE.md` and `Agents.md`: the general rulebook (coding guideline,
  style, rigor, docs, chat, the agent directory, code review, git). A
  project adds its own `## 0. Project Rules` section at the top of its
  copy for anything the general rules do not cover.
- `.agent/`: the committed agent directory, empty and ready. The spec
  inside governs its own folders (knowledge docs, memory, bugs, todos,
  decisions, review ledgers, handovers). An agent boots from
  `.agent/INDEX.md` and obeys `.agent/house-rules.md` for branches,
  commits, and code review.
- `.gitignore`: the one line the directory needs (worktrees never enter
  git).

Everything in `.agent/` is generic on purpose: project specifics belong
to the project's own section 0 and to the files the project grows inside
the directory.
