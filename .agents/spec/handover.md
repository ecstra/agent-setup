---
name: spec-handover
kind: doc
description: the one note a session leaves for the next in .agents/handover, written by the tool, read once by the session start hook, never in git
updated: 2026-10-06
links: [spec/conventions.md]
---

# Spec: handover/

The note one session leaves for the next, so a session that starts after
a compaction, a restart or a pause picks up without reconstructing a
head. The folder holds one file, `handover.md`, and git ignores the
folder, since the note belongs to one machine and one stretch of work,
like `.ack` and `.task` beside it. The store never lists it and doctor
never reads it.

## Who writes it

`brain handover`, and nothing else. The tool writes the header, the
branch, the head and the moment, then the record it can read off the
machine, the branch at its head, the uncommitted files each with its
state, the standing word and the current work chain with the review's
batch, and passes the prose from standard input through under that. The
prose says what the tool cannot read: what is verified against what is
merely written, the step in hand and the next one, the traps met, and
the rules the owner gave in chat. A note with no words is refused, and a
write by hand anywhere in the folder is refused by the hook.

A second `brain handover` on the same branch replaces the note, so the
note is always the latest. One left by a session on another branch is
kept, and `--replace` writes over it on the owner's word.

## Who reads it

The session start hook, in every agent that runs one, on a start, a
resume, a clear and a compaction. It puts the note whole into the
session's context and removes the file, so a note is read once. A fork
leaves it, since a fork carries the context it came from. A note
written on another branch is left where it is and named in one line,
which lets two sessions work on one repository. The note's facts beat a
compaction's summary.

## When

Before a compaction the agent runs by hand or sees coming, before a
session ends mid task, and when work passes to another session. A
session that resumed from a note and pauses again writes a new one.

## What it never is

Documentation. What a note knows that outlives the session goes into
docs/, memory/ or a todo through the tool, and the note dies with its
reading. Notes filed in this folder before this rule, as docs with a
header block, are the project's to move or delete, and the upgrade
names them once.
