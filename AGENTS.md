# AGENTS.md

The rules for working in this repo are in @.agents/SYSTEM.md and every
agent works by them, and the project's own rules are the files imported
at the end of this one. Claude Code and Gemini CLI pull them all into
context on their own. Codex gets them from its session start hook.
Anything else that reads this file as plain text opens each of them
first.

This file is Agent Setup's and is written whole, so nothing here is edited
by hand. A project's own instruction is a rule, one file in
`.agents/rules/`, filed through `brain new rule`, which adds its line
below. A rule loads as a session starts, so a new one needs the session
reloaded, and rules are written sparingly.

<!-- The project's rules, one import per line below, are the brain tool's to write. A new rule goes in through brain new rule. -->
@.agents/rules/project.md
