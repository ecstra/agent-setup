---
name: branch-review
description: Agent Setup's code review of one branch, run on the owner's word. A few finder sub agents read the whole branch at once, verifiers vote on what they found, the main agent fixes the confirmed findings in one go, a recheck reads the fix, and one docs agent brings the docs up to the code. Use it when the owner asks for a review, and never start one on your own.
argument-hint: [quick|standard|deep] [<base>...<head>]
---

<!-- The brain tool writes this file from .agents/skills/branch-review/SKILL.md, and brain doctor --fix keeps it in step, so edit the sheet and never this file. -->

Read `.agents/skills/branch-review/SKILL.md` and follow it. Its links, such as `references/...`, count from that file's folder.
