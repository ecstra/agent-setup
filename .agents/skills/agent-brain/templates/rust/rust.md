# Rust rules

The kit writes this rule into every project whose root holds a `Cargo.toml`, and keeps it whole, so it is never edited by hand. The project's own Rust rules go in `.agents/rules/project.md` or a rule of their own, in addition to these. A rule a tool can hold is held by the lints, the configs and the gates below, and this file says what no tool can check.

## Toolchain and versions

- Use the latest stable toolchain and the latest edition, checked online when the project starts, never from memory. Pin the exact toolchain in `rust-toolchain.toml` and give every crate of the workspace that edition.
- Use the latest version of every crate, checked on crates.io when the project starts or the crate is added, never from memory.
- Commit `Cargo.lock` and run every build and test with `--locked`, so no run changes the lock unseen.
- Update one crate at a time with `cargo update --precise`, after reading its changelog.

## Dependencies

- Check a crate on crates.io before adding it, that it exists under that exact name, is maintained and has real use. Never add a half remembered name, since models invent about one crate name in five.
- Each new crate waits for the owner's ok, then goes on the approved list under `[bans] allow` in `deny.toml` with every crate it pulls in. An empty list lets every crate through, so the first crate approved starts it with every crate already in `Cargo.lock`.
- Before using a crate's API, read its docs for the exact version `Cargo.lock` holds, since the API you remember may be older.
- Each of the project's own crates sets `publish = false` until it is published, or names its license, since `cargo deny` fails a crate with neither.

## Errors and panics

- A library crate defines its own error enum with `thiserror`. `anyhow` is only for a binary's `main` and for tools.
- No `unwrap`, `expect`, `panic!`, `todo!`, `unimplemented!` or unchecked indexing outside tests. Return an error instead.
- A true invariant takes `#[expect(clippy::expect_used, reason = "...")]` with the reason it cannot fail, and the owner reviews each one.
- Every suppression is `#[expect(lint, reason = "...")]`, never `#[allow]`, so one that stops firing fails the gates.
- Never drop a `Result` with `let _ =` or `.ok()`. Handle it, pass it up with `?`, or log it.
- Panics unwind, so a panic ends one task and not the whole process. Never set `panic = "abort"`.

## Numbers

- Overflow checks stay on in release, `overflow-checks = true` under `[profile.release]` in the root `Cargo.toml`.
- Arithmetic on outside input uses `checked_`, `saturating_` or `wrapping_` on purpose.
- Convert numbers with `try_from`, and use `as` only where no value can be lost or flip its sign.

## Unsafe and FFI

- `unsafe` lives only in named FFI crates, a `-sys` crate for the raw bindings and a wrapper crate with a safe API, each root opting in with `#![expect(unsafe_code, reason = "FFI")]`. Raw bindings never leave them.
- Every `unsafe` block does one operation under a `// SAFETY:` comment that says why it holds, and every `unsafe fn` has a `# Safety` doc section.
- C++ goes through `cxx` where it can, a C API through `bindgen`.
- A callback from foreign code is `extern "C"`, runs its body inside `catch_unwind`, only hands its data to a channel with `try_send` and returns, and is unregistered before its context is freed.
- A foreign object lives on one owner thread behind a type that is not `Send`, and other code talks to it through a handle over a bounded channel.
- Pure Rust unsafe code passes Miri.

## Async and concurrency

- One async runtime per project, tokio unless the project's rules name another.
- Nothing blocks inside async code. Blocking I/O goes in `spawn_blocking`, heavy CPU work to its own pool with the result sent back on a oneshot, and a loop that never ends gets its own thread.
- No lock guard or `RefCell` borrow is held across `.await`. Use `std::sync::Mutex` for plain data, and `tokio::sync::Mutex` only where the lock must be held across `.await`.
- Hold one lock at a time, never across a foreign call or a channel send. Where two are unavoidable, write their order beside the type.
- Channels are bounded and never form a loop.
- Every task has an owner, a stored handle, a `JoinSet` or a `TaskTracker`, and shutdown cancels through a `CancellationToken`, then waits for the tracker.
- Every network and database call runs under a deadline.
- Only cancel safe branches go inside `select!`, as tokio's docs list them.

## Tests

- A test asserts what the spec says the code must do, never what the code happens to do, since an assertion copied from the output writes the bug into the test.
- Mutation testing proves the tests, not a coverage bar. The gates run `cargo mutants --in-diff` over the branch's change, and a planted bug that every test survives fails them. Exclusions go in `.cargo/mutants.toml`, each with its reason.
- The gate runs only the mutated crate's own tests, so a workspace that tests one crate from another sets `test_workspace = true` in `.cargo/mutants.toml`.
- A weekly full `cargo mutants` run catches a weakened test, which `--in-diff` cannot, since a change to tests alone plants no mutants.
- An assertion already written, an `assert!`, an `assert_eq!` or a snapshot, is never changed or removed without the owner's word, and the brain's guard refuses the edit until that word is recorded with `brain ack tests <file>`. Never bless a snapshot with `cargo insta accept` to get green.
- Tests may unwrap, expect, panic and index, which `clippy.toml` allows inside tests only.
- Loom, Kani, sanitizers and fuzzing are nightly options a project may add in its own rules.

## Working as an agent

1. Reproduce a bug before fixing it.
2. Never add a clone, an `Arc`, an `Rc<RefCell<_>>` or a looser signature only to satisfy the borrow checker. Fix the ownership.
3. A match on the project's own enum lists every variant with no wildcard arm, so a new variant fails the build where it needs handling.
4. Each item has one public path, with no duplicate re-exports.
5. A port keeps the old behaviour first and redesigns second, with the old test suite as the judge, and an integer never quietly turns into a float.
6. Done means every gate below passed on the change.

## The configs

- `rustfmt.toml`, `clippy.toml` and `deny.toml` at the root start as the kit's reference copies and are the project's once written, so the project tunes them there.
- `.agents/skills/agent-brain/templates/rust/workspace-lints.toml`, beside this rule's template, holds the `[workspace.lints]` tables to paste into the root `Cargo.toml`, and every crate opts in with `[lints] workspace = true`. A single crate with no workspace takes them as its own `[lints]` tables.
- `clippy.toml` holds the values lints read and the banned calls, never lint levels, which live in those tables.

## Lint

On each Rust file written, the lint hook runs `cargo fmt`, which takes the edition from `Cargo.toml` and formats every crate of the workspace along the way.

```text
*.rs cargo fmt -- {file}
```

## Gates

A gate whose tool is missing fails with the line that says how to install it.

```bash
cargo fmt --all --check ||
  { code=$?; cargo fmt --version >/dev/null 2>&1 || echo "rustfmt is not installed, run rustup component add rustfmt" >&2; exit "$code"; }
```

```bash
cargo clippy --workspace --all-targets --all-features --locked -- -D warnings ||
  { code=$?; cargo clippy --version >/dev/null 2>&1 || echo "clippy is not installed, run rustup component add clippy" >&2; exit "$code"; }
```

```bash
cargo test --workspace --locked ||
  { code=$?; command -v cargo >/dev/null || echo "cargo is not installed, install Rust through rustup from https://rustup.rs" >&2; exit "$code"; }
```

The mutants gate tests the branch's change from main, edits not yet committed included and files git does not track yet left out. It passes where the change plants no mutant, on main among them, and caps rustc's lints so a denied lint never hides a mutant as unviable.

```bash
cargo mutants --version >/dev/null 2>&1 ||
  { echo "cargo-mutants is not installed, run cargo install --locked cargo-mutants" >&2; exit 1; }
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
git diff --no-color --no-ext-diff --src-prefix=a/ --dst-prefix=b/ "$(git merge-base main HEAD)" > "$work/branch.diff"
cargo mutants --workspace --in-diff "$work/branch.diff" --output "$work" --cap-lints=true --cargo-arg=--locked
```

The deny gate fetches the advisory database, so it needs the network.

```bash
cargo deny --locked check ||
  { code=$?; cargo deny --version >/dev/null 2>&1 || echo "cargo-deny is not installed, run cargo install --locked cargo-deny" >&2; exit "$code"; }
```
