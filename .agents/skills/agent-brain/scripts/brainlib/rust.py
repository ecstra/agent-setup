"""The kit's Rust rule, `rules/rust.md`, which stands in a project exactly while its root holds a Cargo.toml, and the reference configs written beside it once.

The rule's words and the configs come from templates the tool carries
beside its own code, so doctor writes them in any project, git or none,
and the rule is the kit's, written whole like AGENTS.md. A project's own
Rust rules go in a rule of its own. Doctor holds all of it on every run,
so Rust that arrives after the port gets the rule, and Rust that leaves
takes it away.
"""

import re
from datetime import date
from pathlib import Path
from typing import Optional

from . import frontmatter, rules

MANIFEST = "Cargo.toml"
RULE = "rust.md"
NAME = "rust"
TOOLCHAIN = "rust-toolchain.toml"
# the configs written once where missing, then the project's, and the table a reader pastes into the root Cargo.toml
CONFIGS: tuple[str, ...] = ("rustfmt.toml", "clippy.toml", "deny.toml")
LINTS_TABLE = "workspace-lints.toml"
TEMPLATES = Path(__file__).resolve().parents[2] / "templates" / "rust"
TEMPLATE_PATH = f".agents/skills/agent-brain/templates/rust/{LINTS_TABLE}"

HEADER = """---
name: rust
kind: rule
description: the kit's Rust rules, which every agent loads in a project whose root holds a Cargo.toml
updated: {date}
links: []
---

"""

RELOAD = "and the rule loads once the session is reloaded"
MISSING = f"the project's root holds a {MANIFEST} and the brain no rust.md, so the kit's Rust rules never load, and the fix writes them with their import and the missing configs, {RELOAD}"
CHANGED = "says other than the kit's Rust rules, which the kit writes whole, so the fix writes them back, and the project's own Rust rules go in a rule of its own"
NO_RUST = f"stands with no {MANIFEST} at the project's root, so the fix retires it with its import, and doctor writes it again once one is back"
NO_RUST_CHANGED = f"stands with no {MANIFEST} at the project's root and says other than the kit's words, so move what is the project's into a rule of its own and delete it"
NAME_TAKEN = "is the kit's Rust rule, and {path} is named rust already, so retitle it with brain refile and the fix writes the rule"
NO_TOOLCHAIN = "is missing, so no toolchain is pinned, and the Rust rule asks for the latest stable one pinned here"
NO_WORKSPACE_LINTS = f"names a workspace and no [workspace.lints] table, so paste the one in {TEMPLATE_PATH}"
NO_CRATE_LINTS = f"names no [lints] table, so paste the one in {TEMPLATE_PATH} as [lints]"
NOT_OPTED_IN = "is a crate of the workspace that never sets [lints] workspace = true, so the workspace's lints never reach it"
NAME_IS_THE_KITS = "rust is the name of the kit's Rust rule, which doctor writes in a project with a Cargo.toml, so the project's own Rust rules go in project.md or a rule of another name"

TABLE = re.compile(r"^\s*\[([^\]]+)\]\s*(?:#.*)?$")
UPDATED = re.compile(r"^updated:.*$", re.MULTILINE)
WORKSPACE_TRUE = re.compile(r"^\s*workspace\s*=\s*true\b")
# the folders a crate's manifest is never looked for in, a build's output and the dotted ones among them
SKIPPED = {"target", "node_modules"}


def is_rust(
    project: Path,
) -> bool:
    """Whether the project's root holds a Cargo.toml, which is what makes it a Rust project to the kit."""
    return (project / MANIFEST).is_file()


def template(
    name: str,
) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def template_body() -> str:
    return template(RULE)


def rule_text(
    body: str,
    date: str,
) -> str:
    return HEADER.format(date=date) + body


def body_of(
    text: str,
) -> str:
    """A rule's words below its header block and the blank line after it, compared with the template, since doctor fills the header's people and dates."""
    return rules.body_of(text).lstrip("\n")


def write_rule(
    brain_root: Path,
) -> None:
    """Write the rule from the template and import it, the configs the project lacks with it."""
    path = brain_root / rules.FOLDER / RULE
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter.write_text(path=str(path), text=rule_text(body=template_body(), date=date.today().isoformat()))
    rules.write_imports(brain_root)
    project = brain_root.parent
    for config in CONFIGS:
        if not (project / config).exists():
            frontmatter.write_text(path=str(project / config), text=template(config))


def rewrite_body(
    brain_root: Path,
) -> None:
    """Write the template's words back below the rule's header, which keeps its people and its date."""
    path = brain_root / rules.FOLDER / RULE
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    fence = f"{frontmatter.FENCE}\n"
    closing = text.find(f"\n{fence}", len(fence)) if text.startswith(fence) else -1
    today = date.today().isoformat()
    head = text[: closing + len(fence) + 1] if closing != -1 else HEADER.format(date=today).rstrip("\n") + "\n"
    # the words changed, so the header's date says so, as every write in the brain does
    head = UPDATED.sub(f"updated: {today}", head, count=1)
    frontmatter.write_text(path=str(path), text=f"{head}\n{template_body()}")


def retire(
    brain_root: Path,
) -> None:
    (brain_root / rules.FOLDER / RULE).unlink()
    rules.write_imports(brain_root)


def manifests_below(
    project: Path,
) -> list[Path]:
    """Every Cargo.toml below the root, a build's output and the dotted folders left out, in a steady order."""
    found: list[Path] = []
    for folder in sorted(path for path in project.iterdir() if path.is_dir() and path.name not in SKIPPED and not path.name.startswith(".")):
        for path in sorted(folder.rglob(MANIFEST)):
            if not any(part in SKIPPED or part.startswith(".") for part in path.relative_to(project).parts[:-1]):
                found.append(path)

    return found


def tables(
    text: str,
) -> list[str]:
    """The names of the tables a TOML text opens, `[lints]` and `[lints.clippy]` among them, outside its comments."""
    return [match.group(1).strip() for match in (TABLE.match(line) for line in text.splitlines()) if match is not None]


def opts_in(
    text: str,
) -> bool:
    """Whether a crate's manifest sets `workspace = true` under its `[lints]` table."""
    inside = False
    for line in text.splitlines():
        table = TABLE.match(line)
        if table is not None:
            inside = table.group(1).strip() == "lints"
            continue

        if inside and WORKSPACE_TRUE.match(line):
            return True

    return False


def lint_trouble(
    project: Path,
) -> list[tuple[str, str]]:
    """What the project's manifests lack of the lints the Rust rule asks for, each as the file's path and the words for it."""
    root = (project / MANIFEST).read_text(encoding="utf-8-sig")
    named = tables(root)
    if "workspace" not in named:
        return [] if any(name == "lints" or name.startswith("lints.") for name in named) else [(MANIFEST, NO_CRATE_LINTS)]

    found: list[tuple[str, str]] = []
    if not any(name == "workspace.lints" or name.startswith("workspace.lints.") for name in named):
        found.append((MANIFEST, NO_WORKSPACE_LINTS))

    for manifest in manifests_below(project):
        if not opts_in(manifest.read_text(encoding="utf-8-sig")):
            found.append((manifest.relative_to(project).as_posix(), NOT_OPTED_IN))

    return found


def holder_of_the_name(
    entries: list,
    rule: Path,
) -> Optional[str]:
    """The entry other than the rule itself that is named rust already, by its path in the brain, or None."""
    for entry in entries:
        if entry.path != rule and entry.document.get("name") == NAME:
            return entry.relative

    return None
