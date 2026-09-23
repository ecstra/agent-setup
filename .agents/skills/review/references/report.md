# The reports

Every report to the owner opens with the state, then says what changed,
what is left and what the owner has to do, in plain words a reader who
has not opened the code, the ledger or the brain can follow. A file is
named once, with what it does. Nothing about the agent's own process,
effort, passes or reasoning. No counts in prose beyond the state lines,
and the state lines come from `brain ledger report`, never from memory.
No closing summary, no tip line, and never a pointer at the ledger as
the answer.

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
last, the last line says the closing pass runs next, or, at low or on
a sweep branch, that the branch is ready to merge on the owner's word.

## After the closing pass

```text
<the lines brain ledger report prints>

The closing pass found nothing. (or the batch shape above)
The branch is ready to merge on your word.
```

## Without sub agents

The same shapes, opened with one line: "This review ran without sub
agents, every angle in one context."
