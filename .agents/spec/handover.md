---
name: spec-handover
kind: doc
description: the one note a session leaves for the next in .agents/handover, which brain handover writes and the session start hook reads once and removes
updated: 2026-10-27
links: [spec/conventions.md]
---

# Spec for handover/

The note one session leaves for the next, so a session that starts
after a compaction or any other stop picks up without reconstructing a
head. The folder holds one note, `handover.md`, which a session start
renames `handover.md.reading` while it holds it. Git ignores the
folder, since the note belongs to one machine and one stretch of work,
like `.ack` and `.task` beside it, so no note reaches another machine
or another person. The store never lists it, and doctor reads no file
in it and reports only the leftover of an interrupted write there,
which `--fix` removes.

## Who writes it

`brain handover`, and nothing else. The tool writes the header, the
branch, the head and the moment, then the record it reads off the
machine, the branch at its head, the uncommitted files, the first fifty
each with its state and the rest counted in one line, the standing word
as it stood at the note's moment, and the current work chain with the
review's batch, read as the note is written since a chain has no clock.
Under that it passes the prose from standard input through, less the
blank lines before and after it. The prose says what the tool cannot
read, which is what is verified against what is merely written, the
step in hand and the next one, the traps met, and the rules the owner
gave in chat. A note with no words is refused, and a write by hand
anywhere in the folder is refused by the hook.

A second `brain handover` on the same branch replaces the note, and a
claimed one a session start could not remove with it, so the note is
always the latest. A checkout holds one note, so one left for another
branch blocks the write until `--replace` writes over it on the owner's
word. A note that names no branch, or whose branch reads `no git` or
`git could not answer`, is replaced like this branch's, while a session
whose own branch reads `detached`, `no commits yet`, `no git` or
`git could not answer` is refused over a note that names a branch. A
folder at `handover.md` or at `handover.md.reading`, or a file where
the folder goes, refuses the write in words that say what to move
away, and whatever stands at `handover.md`, or at `handover.md.reading`
while nothing stands at `handover.md`, that the tool never wrote or
cannot read as a file refuses it too. `--replace` writes over none of
them.

## Who reads it

The session start hook, in every agent that runs one, on every session
start but a fork, which carries the context it came from, a compaction
included in Claude Code and Codex. The hook renames the note aside and
reads it there, puts it whole into the session's context ahead of the
status and the rules, and removes the file once the context is out, so
a note is read once and a note written meanwhile is never the one
removed.

A note is for a session on the branch it names, and one written on a
detached head or before the first commit for a session that stands the
same way. Two branch names compare as written, or without regard to
case where git's `core.ignorecase` takes both spellings for one ref. A
note that names no branch, or whose branch reads `no git` or
`git could not answer`, is for any session, and any note is for a
session whose own branch reads either, so a git hiccup never strands
one. A note written on another branch is left where it is and named in
one line, which lets sessions on different branches share a checkout.
An agent that runs no hook reads the file itself once `brain status`
shows a note that is for it by these rules, `handover.md`, or
`handover.md.reading` where the status says it was read before, and
deletes it once read, the one change the hook lets through in the
folder.

A note the hook cannot rename aside is read where it is, the context
saying why, and stays for the next session. A file that lands at
`handover.md` between the hook's first read and its rename is judged
again once aside, and where it is not this session's note it goes back
to `handover.md` and is named in one line, as a file found there is.
Where it cannot go back it stays under the claimed name, said with the
reason, and is taken from then on for a claimed file read before. A
claimed file the hook cannot remove is the note still waiting, which
`brain status` counts as read before and the next start reads again,
saying so, as long as no newer note sits at `handover.md`.

A note holds as things stood at its moment, so it beats a compaction's
summary on the time before that moment, and what the summary keeps of
the work after it beats the note.

## When

A session writes the note whenever its work stops mid task or passes
to another session, and a compaction it sees coming as the context
nears its limit is such a stop. A compaction the owner runs by hand
starts at once, with no turn for the agent to write it, so a note
reaches the session after it only where the owner asked for one first.
A session that resumed from a note and pauses again writes a new one,
carrying forward whatever of the old note still holds, the traps and
the rules from chat above all, since the old note is gone once read.

## What it never is

Documentation. What a note knows that outlives the session goes into
the brain through `brain new`, and the note dies with its reading.
Notes filed in this folder before this rule, any markdown file there,
nested too, that is not the tool's note, are the project's to move or
delete. The upgrade names them on every run while they remain, and the
session start and `brain handover` leave one at the note's own path
where it is and say so. Nothing in the tool moves or removes one
outside the race the limits below name.

## Limits

A checkout holds one note and the note stays on this machine, both by
the owner's design, so sessions on two branches of one checkout leave a
note one at a time, and what has to reach another machine or another
person goes into the brain through `brain new`. A second session opened
on the note's branch while the session that wrote it still runs, a
headless run included, takes the note like any other start, so open
none while a note waits for the session meant to read it.

Gemini CLI fires no hook after a compression, so there a note reaches
the next session that starts, resumes or is cleared, never the session
that goes on past the compression.

Neither the session start nor `brain handover` takes a lock on the
folder, so two sessions that act on the note at the same moment can
meet inside each other's steps. Two session starts at once in one
checkout give the note to at least one of them, since a start removes
the file only once its context is out, but the second can get none, or
get it under a heading that does not hold, read before by a session
that could not remove it or left for the next session, so start one
session at a time while a note waits. Where a file lands at
`handover.md` while a session start claims the note, and a newer note
lands in the moment that start puts the file back, one of the two can
be lost, a note or a file of the project's own. Writing a handover
while no other session starts in the same checkout keeps clear of this,
and a lock across the claim and the write is planned.

The tool's git calls keep the environment they are given, so one run
from inside a git hook reads that hook's `GIT_DIR`. Run from inside a
brain that is a symlink, the tool finds the brain at the link's target,
so the note and the git its record reads are the target's. On Windows a
git that starts a child process holding its output can run past the
10 second limit, since the tool stops only the git it started.

Branch names and paths compare as git's `core.ignorecase` says, so a
flag set wrong for the disk takes two spellings for one where the disk
keeps them apart, or for two where it folds them, and setting the flag
right is the owner's to do. Where the flag is true, branch names fold
by Unicode's case folding, which takes a few pairs NTFS keeps apart for
one, ß and ss among them, so two branches that differ only by such a
pair share a note there. A branch whose name ends in a character
Unicode counts as white space, a no break space among them, is named
without it, the way every header value is read, so two branches that
differ only by such an ending share a note too.
