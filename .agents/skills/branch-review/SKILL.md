---
name: branch-review
description: The kit's code review of one branch, run on the owner's word. A few finder sub agents read the whole branch at once, verifiers vote on what they found, the main agent fixes the confirmed findings in one go, a recheck reads the fix, and one docs agent brings the docs up to the code. Use it when the owner asks for a review, and never start one on your own.
argument-hint: [quick|standard|deep] [<base>...<head>]
---

# The review

The review finds what will break for a user and fixes it. It does not
look for style, which the project's linters fix as each file is
written, and it does not look at docs, which one docs agent brings up
to the code at the end. It runs in one pass and a short recheck, and
it never loops until nothing is left to find.

## What counts as a finding

A finding is a defect with concrete harm, one of these.

- behaviour that breaks for a user, or differs from the build spec
- data lost, leaked or written wrong
- a security hole
- an edge case a real input reaches
- code that does more than the spec asks, dead code, or a test that
  can never fail

Each finding names the file and line, the input, what happens and what
should happen. A finding with no scenario is not filed.

A case outside the functions the range changed and the code the change
made reachable, which behaves the same on the base, is older than the
branch, and every other case is the branch's.

These are never findings.

- style, wording, naming or layout, since the linters own them
- docs, since the docs agent owns them
- a case no real input reaches
- a rule that adds a restriction with no harm behind it
- an older case, which goes straight to `.agents/bugs/` through
  `brain new bug`, its link to the ledger
- in a project, a defect in a file the kit writes whole, which is the
  kit's to fix, its skills, `SYSTEM.md`, the brain's `README.md` and
  `house-rules.md`, `.agents/VERSION`, the definitions under
  `.claude/agents/`, the skill links under `.claude/skills/`, the chat
  style `plain-and-short.md` under `.claude/output-styles/` and its
  copies in `.codex/` and `.gemini/`, `CLAUDE.md`, `GEMINI.md` and
  `CONTRIBUTING.md`

## Levels

| Level | Finders | Verifiers | Rounds |
|---|---|---|---|
| quick | 1, angle 1 alone | none for the vote, the main agent reads each finding | 3 at most |
| standard | 4, one per angle | 2 | 3 at most |
| deep | 8, two per angle, then a fresh read | 2 | 3 at most |

Standard is the usual level. Quick fits a small change, never one to a
public interface, stored data, auth or security, which takes standard
at least. Deep fits a release, or code that handles money, sign in or
data, and costs about twice standard. Its two finders of an angle read
apart, since two runs miss different things, and once the last round's
recheck is done one fresh finder per angle reads the finished branch
once, with the ledger's findings as found already, its findings taking
one more round with no fresh read after it. The level sets how many
finders run and never how hard the model thinks, which is the session's
effort and the owner's to set.

## The angles

1. **Spec and logic.** Does the code do what the build spec's Behaviour
   and Edge cases say, and does it hold for real inputs? Is the code
   only fitted to its tests? What did the change take away, a guard
   removed or a caller it broke?
2. **The user and the data.** What breaks for the person using it, what
   is lost, leaked or left half written, what fails without a word?
3. **Overbuilding.** Code the spec never asked for, abstractions with
   one caller, dead code, and tests that would pass whatever the code
   did.
4. **Security.** Input crossing a boundary, secrets, auth,
   permissions, and commands built from strings.

## The steps

The range is `main...HEAD` unless the owner gave one, written
`<base>...<head>` below.

1. **Gates.** `brain gates` is green and the working tree is clean,
   since a review reads committed work. If not, say which and stop.
2. **Open the ledger** with the level and a one line summary, and
   commit it with the indexes the tool rebuilt. Where the build spec
   is the work the agent is on, the review goes under it on the work
   chain, and the tool says when the chain keeps it off.

   ```bash
   brain ledger open 'feat/billing' --level standard --summary - <<'EOF'
   what the branch did, one line
   EOF
   ```

3. **Find.** Spawn the finders at once, each with
   [the finder prompt](references/prompts.md#the-finder) and its angle.
   Each reads the whole diff less the review's own paper,
   `git diff '<base>...<head>' -- ':!.agents/reviews'` with a
   `':!<path>'` for each other path a commit of the paper named, and
   any file it needs, with no slices, and reports ten findings at most.
4. **Vote.** Spawn the two verifiers at once with
   [the verifier prompt](references/prompts.md#the-verifier). Each
   reads every finding and votes REAL or NOT REAL with the line that
   decides it. A finding both call real is filed. A split vote is
   decided by the main agent from the scenario. The same defect found
   twice is filed once. A finding left out is named in the report with
   the line that refuted it.
5. **File** the findings in one batch, then start it. The owner's word
   to review is the first round's ack.

   ```bash
   brain ledger batch 2026-11-feat-billing --theme 'round 1'
   brain ledger add 2026-11-feat-billing - --severity bug --batch 1 <<'EOF'
   billing/invoice.py:412 a credit note is counted twice when ...
   EOF
   brain ledger batch 2026-11-feat-billing 1 --status fixing --ack 2026-11-02
   ```

6. **Fix.** The main agent fixes every confirmed finding itself, in one
   go. It fixes the cause and every place the same cause reaches, never
   only the line named, and brings the docstrings, comments and help
   strings of the code it changes up to date, since the docs agent
   edits docs only. A finding a user would see gets a test that fails
   without the fix and passes with it. Nothing else gets a test. A
   confirmed finding it finds wrong is set refuted only with the line
   of code that shows it, and one left as it is, wontfix, only with the
   reason it is on purpose, and the report names both. One that cannot
   be fixed inside the branch is deferred into a bug on the owner's
   word. The main agent runs the round's own tests, those of the files
   it changed, commits the fix, pushes it and sets the ledger.

   ```bash
   brain ledger set 2026-11-feat-billing F-01 F-02 status=fixed fix=abc1234
   brain ledger set 2026-11-feat-billing F-03 status=refuted reason='line 212 already guards it'
   brain ledger set 2026-11-feat-billing F-04 status=wontfix reason='the retry is on purpose'
   ```

7. **Recheck.** One fresh verifier reads only the diff of that commit,
   with [the recheck prompt](references/prompts.md#the-recheck), and
   names any finding still there, any new break the fix brought in and
   any fix that hid its symptom, at every level, quick included. What
   it finds is filed with `--found-by recheck` into the next round's
   batch, which starts on the owner's word or
   their standing word, `brain ack`. A recheck that reopens a fix, a
   case the fix missed or one it broke, sends the main agent back to
   the cause. It lists every input the mechanism takes before it writes
   the next fix, and where the cases keep coming it picks a simpler
   mechanism or names the rest as a limit, rather than patch the case
   named. After three rounds the review stops and tells the owner what
   is left, and why the approach may need a rethink. A round past the
   third runs only on the owner's own word, since the cap is a stop the
   standing word does not lift.
8. **Docs.** One docs agent, with
   [the docs prompt](references/prompts.md#the-docs-agent), brings every
   doc the branch made false up to the code, and states what the build
   spec's Changes record. The main agent reads its diff once.
9. **Gates.** The docs are one commit, pushed. `brain gates` runs
   before the close. A red gate is filed as a finding of a new round,
   fixed, rechecked and gated again like any round, so the ledger
   closes on green. Once three rounds have run, that round is one past
   the third, as step 7 says.
10. **Close.** Each batch goes verified then done, the ledger closes,
    and the build spec's review step settles. The paper is committed.

    ```bash
    brain ledger batch 2026-11-feat-billing 1 --status verified
    brain ledger batch 2026-11-feat-billing 1 --status done
    brain ledger close 2026-11-feat-billing
    ```

## Sub agents

The finder and the verifier read and report, never run the project's
whole test suite, and write only their answer file. The docs agent
edits docs only. Each runs on Opus in Claude Code, from the definitions
under `.claude/agents/`. A session with no definitions spawns a general
purpose sub agent with the definition's text at the top of its prompt.
Outside Claude Code the agent runs them on the strongest model it has.
No sub agent has the web, so where a finding turns on how another
product behaves, the main agent fetches that product's page and hands
it over as a file.

Every sub agent writes its answer to a file in the session's scratch
folder, outside the repository, and replies with one line per item.
One that returns with no answer file runs again once, fresh, with an
answer file of its own, and what follows a second failure is the main
agent's call. The scratch files may be gone by a later session, which
resumes from the ledger's claims. The main agent alone edits code,
commits and writes the ledger, and its writes through git and the brain
tool go one at a time, since none holds a lock.

## Without sub agents

The main agent runs each angle itself, one after another, then reads
its own findings once more as the verifier before it fixes them. It
rereads its own fix diff as the recheck and does the docs pass itself,
and the report says the review ran without sub agents.

## The report

Lead with where the review stands and when it ends. Give the count of
findings, the part of the code they touch and the time the fixes take,
"3 small leftovers in the lint hook, 10 minutes", and the detail of
each only when the owner asks, since a finding means little without
the code in front of the reader. Count the same way the bugs the review
filed and the calls the main agent made on split votes and refutations.
Say what the owner has to do, if anything, and whether a round started
on the owner's ack or their standing word, and what is left of that
word. At the close, say the time the review took, from the author date
of the commit that opened the ledger to the close, the findings fixed,
refuted and left, and that the branch is ready to merge on the owner's
ask.
