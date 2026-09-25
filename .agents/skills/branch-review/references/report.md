# The reports

Every report follows SYSTEM.md section 7.6. The state lines come from
`brain ledger report`, never from memory, and the only counts in prose
are the refuted and hunter counts the shapes below carry. Never a tip
line.

A finding, a bug, a todo or a decision is named by what it is, in
plain words, "the dirty guard skips ignored files" and never "F-03".
The id may follow the words in brackets where the owner would need it
to look the thing up, and it never stands in their place, since the
owner does not hold the ledger in their head. The same holds in every
reply outside the reports.

While the owner's standing word holds, a line below that puts the next
step on the owner's word or asks for the ack, "Batch 1 starts on your
word." and "Your call: ack batch 2, which starts it." alike, says
instead that the step started on the standing word and what is left of
it, "Batch 2 started on your standing word, 2 h left." A batch that
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

<n> candidates were refuted and not filed.
Cut short: <the angle>, after three runs, <the files it never reached, or that candidates past its cap remained>.
Batch <n> starts on your word.
```

The batch named last is 1 after the finding pass and the closing pass
batch after that pass. The cut short line appears only when an angle
ran three times and still ended with (more remain), and it goes into
every shape below the same way.

## When nothing survived

```text
<the lines brain ledger report prints>

Nothing survived verification, <n> candidates refuted. No batch, no
closing pass.
Cut short: <the angle>, after three runs, <the files it never reached, or that candidates past its cap remained>.
The ledger is closed, and the branch is ready to merge on your ask.
```

## After a batch

```text
<the lines brain ledger report prints>

Fixed:
- <file>, <what changed, in plain words>
The hunter found <n> more, fixed above. (or: The hunter found nothing.)

Deferred: <the finding, in plain words> (F-nn), filed as <the bug's title> (BUG-nnn), <why it cannot be fixed here>.
Cut short: the hunter, after three runs, <the files it never reached, or that candidates past its cap remained>.
Your call: ack batch <n+1>, which starts it.
```

The deferred line appears only when there is one, and the cut short
line only when the hunter ran three times and still ended with (more
remain). When the batch was the last, there is no next batch to ack,
and the closing line says instead what comes, the closing pass where
house rule 7 owes one. Where none is owed, the ledger closes with no
word and the line reads "The ledger is closed, and the branch is ready
to merge on your ask."

## After the closing pass

```text
<the lines brain ledger report prints>

The closing pass found nothing. (or: The closing pass's findings are acked and fixed above.)
Cut short: <the angle>, after three runs, <the files it never reached, or that candidates past its cap remained>.
The ledger is closed, and the branch is ready to merge on your ask.
```

A closing pass that found something is reported first with the finding
pass shape, its batch starting on the owner's word, then goes through
the batch shape, once per batch when it was split by theme, and this
shape follows once the last of those batches is done.

## Without sub agents

The same shapes, with one line right after the state lines saying that
this review ran without sub agents, every angle in one context.
