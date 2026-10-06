<!-- Claude Code reads this file. The rules live in AGENTS.md, which the
     line below pulls in. Below the marker line, the same one AGENTS.md
     carries, sit the kit's compaction instructions, which Claude Code
     reads from this file alone when it compacts a session. -->

@AGENTS.md

<!-- The kit's words start here. Section 0 goes above this line. -->

# Compact instructions

Keep, in the words they were given, every rule the user gave in chat,
the work chain and the review's batch as the last hook line printed
them, the uncommitted files and what each holds, the step in hand and
the next one, and the traps met. The handover the session wrote with
`brain handover` beats this summary. The session start hook puts it in
front of you after the compaction, and you read it before anything else.
