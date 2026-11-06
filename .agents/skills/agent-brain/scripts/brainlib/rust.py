"""The kit's Rust rule, `rules/rust.md`, which stands in a project exactly while its root holds a Cargo.toml, and the reference configs written beside it once.

The rule's words and the configs come from templates the tool carries
beside its own code, so doctor writes them in any project, git or none,
and the rule is the kit's, written whole like AGENTS.md. A project's own
Rust rules go in a rule of its own. Doctor holds all of it on every run,
so Rust that arrives after the port gets the rule, and Rust that leaves
takes it away.
"""

import os
import re
from datetime import date
from pathlib import Path
from typing import Optional

from . import frontmatter, rules

MANIFEST = "Cargo.toml"
RULE = "rust.md"
NAME = "rust"
# the stamp the rule first ships with, before which a rule of that name was the project's own
SINCE = "3.1.0"
TOOLCHAIN = "rust-toolchain.toml"
# the configs written once where missing, then the project's, and the table a reader pastes into the root Cargo.toml
CONFIGS: tuple[str, ...] = ("rustfmt.toml", "clippy.toml", "deny.toml")
# the other names each tool reads its config under, which keep the reference copy from going beside the project's own, since the tool would read the copy first
ALTERNATES: dict[str, tuple[str, ...]] = {"rustfmt.toml": (".rustfmt.toml",), "clippy.toml": (".clippy.toml",), "deny.toml": (".deny.toml", ".cargo/deny.toml")}
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
# one step through a TOML array of strings, a string, a comment or a comma, which stops at the array's closing bracket
ARRAY_STEP = re.compile(r"\s*(?:\"((?:\\.|[^\"\\])*)\"|'([^']*)'|#[^\n]*|,)")
PATH_KEY = re.compile(r"\bpath\s*=\s*(?:\"((?:\\.|[^\"\\])*)\"|'([^']*)')")
# the tables whose path entries are dependencies, a table of one dependency and a target's among them, never a patch or the workspace's own
DEPENDENCY_TABLES = {"dependencies", "dev-dependencies", "build-dependencies"}
NOT_DEPENDENCIES = {"patch", "replace", "workspace"}


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
        if not any((project / name).exists() for name in (config, *ALTERNATES[config])):
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


def says_the_kits(
    text: str,
) -> bool:
    """Whether a rule's words below its header are the template's, as doctor compares them."""
    return body_of(text).strip() == template_body().strip()


def workspace_array(
    text: str,
    key: str,
) -> list[str]:
    """The strings of one array under the root manifest's `[workspace]` table, `members` or `exclude`, over as many lines as it spans, or none where it has no such key."""
    inside = False
    lines = text.splitlines()
    for number, line in enumerate(lines):
        table = TABLE.match(line)
        if table is not None:
            inside = table.group(1).strip() == "workspace"
            continue

        opening = re.match(rf"^\s*{key}\s*=\s*\[", line) if inside else None
        if opening is None:
            continue

        rest = "\n".join([line[opening.end() :], *lines[number + 1 :]])
        found: list[str] = []
        step = ARRAY_STEP.match(rest)
        while step is not None:
            value = step.group(1) if step.group(1) is not None else step.group(2)
            if value is not None:
                found.append(value)
            step = ARRAY_STEP.match(rest, step.end())

        return found

    return []


def path_dependencies(
    folder: Path,
    text: str,
) -> list[Path]:
    """The folders a manifest's dependency tables name by path, each from the manifest's own folder."""
    found: list[Path] = []
    inside = False
    for line in text.splitlines():
        table = TABLE.match(line)
        if table is not None:
            parts = [part.strip() for part in table.group(1).split(".")]
            inside = parts[0] not in NOT_DEPENDENCIES and any(part in DEPENDENCY_TABLES for part in parts)
            continue

        if inside:
            found += [folder / (match.group(1) if match.group(1) is not None else match.group(2)) for match in PATH_KEY.finditer(line)]

    return found


def is_under(
    folder: Path,
    above: Path,
) -> bool:
    return folder == above or above in folder.parents


def workspace_members(
    project: Path,
    root_text: str,
) -> list[Path]:
    """The manifests of the workspace's crates as cargo reads them, the root's own aside, in a steady order.

    They are those its members name, by glob, and every path dependency
    inside the root, of the root and of each crate in turn, less those
    under a path the workspace excludes.
    """
    root = Path(os.path.normpath(project))
    excluded = [Path(os.path.normpath(root / path)) for path in workspace_array(text=root_text, key="exclude")]
    waiting: list[Path] = []
    for pattern in workspace_array(text=root_text, key="members"):
        try:
            waiting += sorted(root.glob(pattern))
        except (ValueError, NotImplementedError):
            # an empty or an absolute pattern, which pathlib cannot glob and cargo reads as no crate below the root
            continue

    waiting += path_dependencies(folder=root, text=root_text)
    found: set[Path] = set()
    while waiting:
        folder = Path(os.path.normpath(waiting.pop(0)))
        manifest = folder / MANIFEST
        if manifest in found or folder == root or not is_under(folder=folder, above=root) or any(is_under(folder=folder, above=out) for out in excluded):
            continue

        if not manifest.is_file():
            continue

        found.add(manifest)
        waiting += path_dependencies(folder=folder, text=manifest.read_text(encoding="utf-8-sig"))

    return sorted(found)


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

    # a root that is a package as well is a crate of its own workspace
    if "package" in named and not opts_in(root):
        found.append((MANIFEST, NOT_OPTED_IN))

    root_folder = Path(os.path.normpath(project))
    for manifest in workspace_members(project=project, root_text=root):
        if not opts_in(manifest.read_text(encoding="utf-8-sig")):
            found.append((manifest.relative_to(root_folder).as_posix(), NOT_OPTED_IN))

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
