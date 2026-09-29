# The reports

Every report follows SYSTEM.md section 7.6. The state lines come from
`brain ledger report`, never from memory, the clock line among them,
and the only counts in prose are the hunt counts the shapes below
carry. Never a tip line.

While the owner's standing word holds, a line below that puts the next
step on the owner's word or asks for the ack, "The batches start on
your word." and "Your call: ack batch 4, which starts it." alike, says
instead that the step started on the standing word and what is left of
it, "The batches started on your standing word, 2 h left." A batch that
already carried the owner's dated ack started on that ack, and the
line says so instead, "Batch 2 started on your ack of 2026-09-22."
The same holds with the standing word off. When `brain ledger report`
says the next batch has the word, the owner having acked it ahead,
the closing line says it starts on that ack rather than asking for
one, "Batch 3 starts on your ack of 2026-09-23." The close and the
merge lines stay as written, since the close follows the last batch
with no word and the PR and the merge wait for the owner's ask either
way.

## After the finding pass

```text
<the lines brain ledger report prints>

Batch 1, <theme>:
- <file>:<line>, <what is wrong, in plain words>
Batch 2, <theme>:
- ...

Cut short: <the angle and its slice>, after three runs, <the files it never reached, or that candidates past its cap remained>.
The batches start on your word, all at once or the ones you name.
```

After the closing pass the last line names its one batch, "The closing
pass batch starts on your word." The cut short line appears only when
a finder ran three times and still ended with (more remain), or the
second look still returned candidates at its third run, and it goes
into every shape below the same way.

## When nothing was found

```text
<the lines brain ledger report prints>

The finders found nothing. No batch, no closing pass.
Cut short: <the angle and its slice>, after three runs, <the files it never reached, or that candidates past its cap remained>.
The ledger is closed, and the branch is ready to merge on your ask.
```

## After a round

One report for the round, whatever the count of batches in it.

```text
<the lines brain ledger report prints>

Fixed, batch 1, <theme>:
- <file>, <what changed, in plain words>
Fixed, batch 2, <theme>:
- ...
The hunts found <n> more, fixed above. (or: The hunts found nothing.)

Refuted: <the claim, in plain words> (F-nn), <why it is wrong>.
Left as it is: <the finding, in plain words> (F-nn), <the reason>.
Taken over: <the group's files>, after three rounds, <the model in one line and what it leaves out>.
Cannot be fixed here: <the finding, in plain words> (F-nn), <why>, yours to send to the bugs or not.
Cut short: a hunter, after three runs, <the files it never reached, or that candidates past its cap remained>.
Your call: ack batch <n>, which starts it.
```

The refuted, left, taken over and cannot lines appear only when there
is one, a line each, and the cut short line only when a hunter ran
three times and still ended with (more remain). When no batch is left
pending, there is none to ack, and the closing line says instead what
comes, the closing pass where house rule 7 owes one. Where none is
owed, the ledger closes with no word and the line reads "The ledger is
closed, and the branch is ready to merge on your ask."

## After the closing pass

```text
<the lines brain ledger report prints>

The closing pass found nothing. (or: The closing pass's findings are acked and fixed above.)
Cut short: <the angle and its slice>, after three runs, <the files it never reached, or that candidates past its cap remained>.
The ledger is closed, and the branch is ready to merge on your ask.
```

A closing pass that found something is reported first with the finding
pass shape, its batch starting on the owner's word, then goes through
the round shape, and this shape follows once that batch is done.

## Without sub agents

The same shapes, with one line right after the state lines saying that
this review ran without sub agents, every slice and angle in one
context.
