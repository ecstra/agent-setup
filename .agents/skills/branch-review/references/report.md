# The reports

Every report follows SYSTEM.md section 7.6. The state lines come from
`brain ledger report`, never from memory, and the only counts in prose
are the refuted and hunter counts the shapes below carry. Never a tip
line.

## After the finding pass

```text
<the lines brain ledger report prints>

Batch 1, <theme>:
- <file>:<line>, <what is wrong, in plain words>
Batch 2, <theme>:
- ...

<n> candidates were refuted and not filed.
Batch <n> starts on your word.
```

The batch named last is 1 after the finding pass and the closing pass
batch after that pass.

## When nothing survived

```text
<the lines brain ledger report prints>

Nothing survived verification, <n> candidates refuted. No batch, no
closing pass. The ledger is closed, and the branch is ready to merge on
your word.
```

## After a batch

```text
<the lines brain ledger report prints>

Fixed:
- <file>, <what changed, in plain words>
The hunter found <n> more, fixed above. (or: The hunter found nothing.)

Deferred: <F-nn> as <BUG-nnn>, <why it cannot be fixed here>.
Your call: ack batch <n>.
The ack starts batch <n+1>.
```

The deferred line appears only when there is one. When the batch was
the last, the closing line says instead what the ack opens, the
closing pass where house rule 7 owes one, else the close of the ledger
and then the merge on the owner's word.

## After the closing pass

```text
<the lines brain ledger report prints>

The closing pass found nothing. (or: The closing pass's findings are fixed and acked above.)
The ledger is closed, and the branch is ready to merge on your word.
```

A closing pass that found something is reported first with the finding
pass shape, its batch starting on the owner's word, then goes through
the batch shape, and this shape follows once that batch is done.

## Without sub agents

The same shapes, with one line right after the state lines saying that
this review ran without sub agents, every angle in one context.
