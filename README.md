<p align="center">
  <img
    alt="Agent Setup"
    src="assets/header.png" />
</p>

<p align="center">
  <br>
  <img alt="Works with Claude Code, Codex and Gemini CLI" src="https://img.shields.io/badge/agents-Claude_Code_%7C_Codex_%7C_Gemini_CLI-D97757.svg">
  <img alt="macOS, Linux and Windows" src="https://img.shields.io/badge/platform-macOS_%7C_Linux_%7C_Windows-0078D6.svg">
  <img alt="Python 3.9 or later" src="https://img.shields.io/badge/python-3.9%2B-3776AB.svg">
  <img alt="No dependencies" src="https://img.shields.io/badge/dependencies-none-brightgreen.svg">
  <br><br>
</p>

## Overview

Agent Setup gives your coding agents a shared rulebook and a memory that lives in your repo. You run one command in your project and that's it. It copies plain files into your repo, and nothing runs in the background.

Claude Code, Codex and Gemini CLI then load the same rules when a session starts. They file what they learn as plain markdown under `.agents/`, committed with your code, so a new session on any machine starts from what the last one knew.

Made on macOS and tested on native Windows 11. It needs Python 3.9 or later and git.

## What it does

- **One rulebook for every agent:** how to write and test code, keep docs, use git, review a branch and reply to you. Your project's own rules load after it.
- **A memory in your repo:** docs, decisions, plans, build specs, bugs, todos and short notes, each a markdown file in `.agents/`.
- **Handover between sessions:** a session that stops partway through a task writes a note and gets it back first when it starts again. A new session picks up the note that is waiting.
- **Several agents in one folder:** each agent keeps its own work in hand, its own approvals and its own handover note, so two of them working side by side never mix.
- **Linting as it writes:** every file the agent writes goes through your project's linters right away, and the results go back to the agent to fix.
- **A guard on your tests:** an edit that changes or removes an assertion in an existing test is blocked until you approve that file.
- **Code review when you ask:** sub agents read the whole branch, two more verify each finding, and the agent fixes what was confirmed.
- **Rust projects:** a project with a `Cargo.toml` gets a Rust rule, and gates for formatting, clippy, tests, mutation testing and a dependency audit.
- **Screen recordings and screenshots:** an agent that reads images but not video can step through a recording frame by frame and measure a screenshot in pixels.

What changed in each version is on this repo's releases page.

## Install

Clone this repo next to your project, then run this from your project's root with your work committed.

```bash
python3 ../agent-setup/.agents/brain port
```

The installer copies `.agents/` and a few files into your project's own root. The clone stays outside your project and is only where the install runs from.

The full steps are in [INSTALL.md](INSTALL.md), along with how to bring in the docs and notes you already have, and how to upgrade.

## How it works

- **Rules:** `AGENTS.md` at your repo's root points every agent at the rulebook, `.agents/SYSTEM.md`, and at your own rules in `.agents/rules/`. Claude Code and Gemini CLI load them on their own. Codex gets them from a hook.
- **Memory:** every bug, todo, plan, decision and note is one markdown file with a small header. The agent never types those headers. A command line tool called `brain` creates, lists, edits and checks every entry, and keeps the indexes.
- **Hooks:** each agent runs a few hooks from its own config folder. They put the time and the work in hand in front of the agent, run your linters on what it writes, and refuse a write that breaks the memory's format or changes what a test expects.
- **Review:** the review is a skill the agent runs when you ask. Every finding is voted on before it counts, and each one ends in a ledger as fixed, refuted, left as it is or deferred.
- **Upgrades:** the installer copies files into your repo. An upgrade replaces Agent Setup's own files and leaves yours.

## Day to day

You talk to your agent as usual, and it runs the `brain` tool for you. A few things worth knowing.

- A review starts only when you ask for one. A PR and a merge wait for your explicit ask too.
- You can approve upcoming steps in advance, until a set time or until a task is done, and the agent stops asking in between.
- You can give the agent a time to stop. It winds down, commits what passed its checks and writes the handover.
- `python3 .agents/brain status` shows the work in hand and what each tracker holds.

## Known limits

- The hooks see the agent's edit tools. A write the agent makes through a shell command goes unseen, and there the rulebook alone tells it not to.
- Claude Code's sandbox refuses the installer's writes, so the install runs from a plain terminal.
- Where an agent has no sub agents, the review runs in one session and takes longer.
- The see skill needs ffmpeg.

## Read next

- [`INSTALL.md`](INSTALL.md): install, bring in what you have, upgrade.
- [`.agents/SYSTEM.md`](.agents/SYSTEM.md): the full rulebook.
- [`.agents/house-rules.md`](.agents/house-rules.md): the branch contract and the review protocol.
- [`.agents/skills/agent-brain/SKILL.md`](.agents/skills/agent-brain/SKILL.md): the `brain` tool as the agent uses it, and the format of every file in `.agents/`.
- [`.agents/skills/agent-brain/references/commands.md`](.agents/skills/agent-brain/references/commands.md): every command, with its flags and refusals.
- [`.agents/skills/branch-review/SKILL.md`](.agents/skills/branch-review/SKILL.md): the review, step by step.
- [`.agents/skills/see/SKILL.md`](.agents/skills/see/SKILL.md): the see skill.

## Credits

Everything is by **ecstra**.
