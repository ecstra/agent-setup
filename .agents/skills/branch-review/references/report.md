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
Batch 1 starts on your word.
```

## After a batch

```text
<the lines brain ledger report prints>

Fixed:
- <file>, <what changed, in plain words>
The hunter found <n> more, fixed above. (or: The hunter found nothing.)

Deferred: <F-nn> as <BUG-nnn>, <why it cannot be fixed here>.
Your call: ack batch <n> to start batch <n+1>.
```

The deferred line appears only when there is one. When the batch was the
last, the ack line stays, and after it one line says what the ack
opens, the closing pass, or, at low or on a sweep branch, the close of
the ledger and then the merge on the owner's word.

## After the closing pass

```text
<the lines brain ledger report prints>

The closing pass found nothing, and the ledger is closed.
The branch is ready to merge on your word.
```

A closing pass that found something reports with the batch shape
instead, and this shape follows once that batch is done.

## Without sub agents

The same shapes, with one line right after the state lines: "This
review ran without sub agents, every angle in one context."
