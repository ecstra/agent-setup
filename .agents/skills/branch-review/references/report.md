# The reports

Every report follows SYSTEM.md section 7.6. The state lines come from
`brain ledger report`, never from memory. Never a tip line.

A report speaks of the review's own run in four lines only, the one
exception 7.6 names, since the owner measures the review by them. The
hunts line gives the count of what the hunts found. The cut short line
names a sub agent the [skill sheet](../SKILL.md) counts as cut short,
with what it left undone. The time line gives the time the review
took, from the commit that opened the ledger to the close. The line of
the last section says that the review ran without sub agents, where it
did. No other line counts the review's work or tells how it went.

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

Refuted: <the claim, in plain words> (F-nn), <why it is wrong, with the page of the product's docs that says so>.
Cut short: <the finder, its angle and its slice or the whole range, or the second look of a slice>, <that candidates past its cap remained, or that it stopped twice at its turn cap and reported nothing>.
The batches start on your word, all at once or the first few in number order.
```

The refuted line appears only for a claim about another product that
the product's docs refuted before it was filed, a line each. After the
closing pass the last line names its one batch, "The closing pass
batch starts on your word." The cut short line appears only when there
is one, a line each, in this shape and every shape below.

## When nothing was found

```text
<the lines brain ledger report prints>

The finders found nothing. No batch, no closing pass.
Cut short: <the finder, its angle and its slice or the whole range, or the second look of a slice>, <that candidates past its cap remained, or that it stopped twice at its turn cap and reported nothing>.
The review took <the time, such as 1 h 40 min>.
The ledger is closed, and the branch is ready to merge on your ask.
```

## After the rounds

The round shape, one report once the last pass is done, for every
batch the word covered, and once more after the owner's word on a
finding that cannot be fixed here, as the end of this section says.

```text
<the lines brain ledger report prints>

Fixed, batch 1, <theme>:
- <file>, <what changed, in plain words>
Fixed, batch 2, <theme>:
- ...
The hunts found <n> more, fixed above. (or: The hunts found nothing.)

Refuted: <the claim, in plain words> (F-nn), <why it is wrong>.
Left as it is: <the finding, in plain words> (F-nn), <the reason>.
Cannot be fixed here: <the finding, in plain words> (F-nn), <why>, yours to send to the bugs or not.
Sent to the bugs: <the finding, in plain words> (F-nn), filed as <the bug, in plain words> (BUG-nnn), on your word.
Older than the branch: <the defect, in plain words> (BUG-nnn), filed as a bug.
Cut short: <the sub agent and its slice or group>, <that candidates past its cap remained, or that it stopped twice at its turn cap and answered nothing>.
Your call: ack batches <n> to <m>, which starts them, all at once or the first few in number order.
```

The refuted, left, cannot, sent and older lines appear only when there
is one, a line each. While a batch stays open for a finding that
cannot be fixed here, the closing line asks the owner's word on that
finding first, which a standing word does not give, "Your call: your
word on the finding that cannot be fixed here, which keeps batch 3
open." Otherwise it asks for the pending batches, and names one left
alone as in "Your call: ack batch 4, which starts it." With none
pending it asks for the closing pass where house rule 7 owes one.
Where none is owed, the ledger closes with no word and the report
ends with the two lines that close every review, "The review took
1 h 40 min." and "The ledger is closed, and the branch is ready to
merge on your ask."

A word that sends the finding to the bugs or leaves it as it is starts
no round. The report then comes again in this shape with nothing fixed
and no hunts line, the finding on its sent or left line, and its
closing line asks for what comes next or ends the review, as the
paragraph above says. A word that names how to fix the finding starts
a round, which reports like any other.

## After the closing pass

```text
<the lines brain ledger report prints>

The closing pass found nothing. (or: The closing pass's findings are acked and fixed above.)
Cut short: <the finder, its angle and its slice or the whole range>, <that candidates past its cap remained, or that it stopped twice at its turn cap and reported nothing>.
The review took <the time, such as 1 h 40 min>.
The ledger is closed, and the branch is ready to merge on your ask.
```

A closing pass that found something is reported first with the finding
pass shape, its batch starting on the owner's word, then goes through
the round shape, and this shape follows once that batch is done.

## Without sub agents

The same shapes, with one line right after the state lines saying that
this review ran without sub agents, every slice and angle in one
context.
