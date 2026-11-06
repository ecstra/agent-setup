---
name: project
kind: rule
description: the project's own rules, which every agent loads as a system instruction
updated: 2026-11-06
links: []
author: ecstra
editor: ecstra
---

# Project rules

<!-- This file is the project's own, and the upgrade never writes over it.
Every rule here loads as a system instruction in every session, so keep
it to durable instructions this project alone needs, written sparingly,
never a note, a todo or a doc. A Lint heading with fenced lines names
the linters the lint hook runs on each file written, and a Gates heading
with fenced blocks names the gates brain gates runs, as the brain tool's
commands.md says. A change here loads once the session is reloaded. -->
