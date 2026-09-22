"""Bringing a project to the kit: port when it has no brain, upgrade when it has one.

The kit is a checkout of agent-setup, by default the one this tool runs
from. The project is the folder the command runs in. Both commands
install the kit's own files, keep everything the project wrote, carry
its section 0 into AGENTS.md, and end with doctor --fix. Between the two
sits the migration table, one step per layout change the kit has made,
keyed by the version stamp the project carries.
"""

import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, TextIO

from . import doctor, frontmatter, schema, store

FOLDER = ".agents"
OLD_FOLDER = ".agent"
VERSION = "VERSION"
NO_VERSION = "0"

FRONT_DOORS = ("AGENTS.md", "CLAUDE.md", "GEMINI.md")
ROOT_FILES = (*FRONT_DOORS, "CONTRIBUTING.md")
AGENT_FOLDERS = (".claude", ".codex", ".gemini")

# The hook configs are merged into what the project has, so its own hooks
# stay beside the kit's. Everything else the kit ships is copied whole.
MERGED = ("settings.json", "hooks.json")
NOT_SHIPPED = ("settings.local.json",)
KIT_HOOK_MARK = "agent-brain/scripts/hooks.py"
IGNORE_FILE = ".gitignore"
IGNORE_HEADING = "# The agent kit's own ignores."

# The project's own section, whatever it was called before, takes the
# heading the rulebook names.
SECTION_ZERO = re.compile(r"^## 0\..*$", re.MULTILINE)
SECTION_ZERO_HEADING = "## 0. Project Rules"
NEXT_SECTION = re.compile(r"^## ", re.MULTILINE)


class UpgradeError(Exception):
    """The port or upgrade was refused, with the reason in the message."""


@dataclass
class Report:
    """What a port or upgrade did, one line each, in the order it happened.

    Given a stream, each line goes out the moment it is done, so a run
    that fails part way leaves the record of what it changed on screen.
    """

    out: Optional[TextIO] = None
    lines: list[str] = field(default_factory=list)
    findings: list[doctor.Finding] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)

    def done(
        self,
        text: str,
    ) -> None:
        self.lines.append(text)
        if self.out is not None:
            print(text, file=self.out)

    def tail(self) -> str:
        """The doctor's answer and what is left to file, after the lines."""
        parts: list[str] = []

        if self.findings:
            parts.append("")
            parts.append("Doctor still finds:")
            parts += [f"  {finding.line()}" for finding in self.findings]
        else:
            parts.append("")
            parts.append("Doctor is clean.")

        if self.candidates:
            parts.append("")
            parts.append("Left for the agent to file through brain new, never by hand:")
            parts += [f"  {candidate}" for candidate in self.candidates]

        return "\n".join(parts) + "\n"

    def render(self) -> str:
        return "\n".join(self.lines) + "\n" + self.tail()


@dataclass
class Kit:
    """A checkout of agent-setup, the source of everything the kit owns."""

    root: Path

    @property
    def brain(self) -> Path:
        return self.root / FOLDER

    def version(self) -> str:
        stamp = self.brain / VERSION
        if not store.readable_file(stamp):
            raise UpgradeError(f"{self.root} is not a kit checkout, it carries no {FOLDER}/{VERSION}")

        return read_version(stamp)

    def brain_files(self) -> list[Path]:
        """The kit's own files under .agents/, relative to it, the indexes left out since the tool builds those."""
        found = [Path(name) for name in schema.KIT_FILES if name != schema.INDEX]
        found += sorted(path.relative_to(self.brain) for path in (self.brain / "spec").glob("*.md"))
        found += sorted(
            path.relative_to(self.brain)
            for path in (self.brain / "skills").rglob("*")
            if ships(path)
        )
        found.append(Path(VERSION))

        return found

    def agent_files(self) -> list[Path]:
        """The hook configs and chat style files under the agent folders, relative to the kit root.

        A symlink is the doctor's to make, and a personal settings file
        never ships.
        """
        found: list[Path] = []

        for folder in AGENT_FOLDERS:
            for path in sorted((self.root / folder).rglob("*")):
                if ships(path) and path.name not in NOT_SHIPPED:
                    found.append(path.relative_to(self.root))

        return found

    def text(
        self,
        relative: Path,
    ) -> str:
        """A kit file the run composes with, read as text."""
        try:
            return (self.root / relative).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise UpgradeError(f"the kit's {relative} cannot be read: {error}") from error

    def data(
        self,
        relative: Path,
    ) -> tuple[bytes, int]:
        """A kit file copied whole, its bytes and its mode, whatever it holds."""
        path = self.root / relative
        try:
            return path.read_bytes(), os.stat(path).st_mode & 0o777
        except OSError as error:
            raise UpgradeError(f"the kit's {relative} cannot be read: {error}") from error


def ships(
    path: Path,
) -> bool:
    """Whether a file in the kit's tree is one the kit ships: a real file, not bytecode, not a dotfile."""
    if path.is_symlink() or not path.is_file():
        return False

    return "__pycache__" not in path.parts and path.suffix != ".pyc" and not path.name.startswith(".")


@dataclass
class Project:
    """The folder being brought to the kit."""

    root: Path

    @property
    def brain(self) -> Path:
        return self.root / FOLDER

    def state(self) -> str:
        """`none` with no brain at all, `old` with the .agent/ layout, `current` with .agents/."""
        if store.quietly(self.brain.is_dir):
            return "current"

        if store.quietly((self.root / OLD_FOLDER).is_dir):
            return "old"

        return "none"

    def version(self) -> str:
        stamp = self.brain / VERSION
        if not store.readable_file(stamp):
            return NO_VERSION

        return read_version(stamp)


@dataclass
class Migration:
    """One layout change, applied to a project stamped below `to`."""

    to: str
    says: str
    apply: Callable[[Project, Report], None]


def read_version(
    stamp: Path,
) -> str:
    try:
        text = stamp.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError) as error:
        raise UpgradeError(f"{stamp.name} cannot be read: {error}") from error

    if as_tuple(text) is None:
        raise UpgradeError(f"{stamp.name} says '{text}', not a version like 1.0.0")

    return text


def as_tuple(
    version: str,
) -> Optional[tuple[int, ...]]:
    parts = version.split(".")
    if not parts or not all(part.isdigit() for part in parts):
        return None

    return tuple(int(part) for part in parts)


def default_kit() -> Kit:
    """The kit this tool runs from, five folders above this file."""
    return Kit(root=Path(__file__).resolve().parents[5])


def port(
    kit: Kit,
    project: Project,
    out: Optional[TextIO] = None,
) -> Report:
    """Install the kit into a project that has no brain yet, and say what is left to file."""
    state = project.state()
    if state != "none":
        raise UpgradeError(f"{project.root} already carries a brain, run brain upgrade instead")

    prepared = prepare(kit=kit, project=project)
    report = Report(out=out)
    refuse_when_dirty(project=project, paths=guarded_paths(kit=kit, project=project), report=report)
    install(kit=kit, project=project, prepared=prepared, report=report)
    report.candidates = candidates(project)
    report.findings = check(project)

    return report


def upgrade(
    kit: Kit,
    project: Project,
    out: Optional[TextIO] = None,
) -> Report:
    """Bring a project that has a brain up to the kit, migrations first, then the kit's files."""
    state = project.state()
    if state == "none":
        raise UpgradeError(f"{project.root} carries no brain, run brain port instead")

    if kit.root.resolve() == project.root.resolve():
        raise UpgradeError("the kit is the project, there is nothing to install")

    prepared = prepare(kit=kit, project=project)
    report = Report(out=out)
    refuse_when_dirty(project=project, paths=guarded_paths(kit=kit, project=project), report=report)
    have = as_tuple(project.version())
    want = as_tuple(prepared.stamp)
    if have is not None and want is not None and have > want:
        raise UpgradeError(f"the project is on {project.version()} and this kit is {prepared.stamp}, use a kit at least that new")

    for migration in MIGRATIONS:
        target = as_tuple(migration.to)
        if have is not None and want is not None and have < target <= want:
            migration.apply(project, report)
            report.done(f"migrated to {migration.to}: {migration.says}")

    install(kit=kit, project=project, prepared=prepared, report=report)
    report.findings = check(project)

    return report


@dataclass
class Prepared:
    """What a run composes from the kit and the project's own configs, read and checked before any write."""

    stamp: str
    front_doors: dict[str, str]
    configs: dict[Path, str]


def prepare(
    kit: Kit,
    project: Project,
) -> Prepared:
    """Read the kit's stamp and front doors and merge the hook configs, so a refusal comes before the first write."""
    if (project.brain / "skills" / "agent-brain").is_symlink():
        raise UpgradeError(f"{FOLDER}/skills/agent-brain is a symlink, replace it with a real folder first")

    stamp = kit.version()
    front_doors = {name: kit.text(Path(name)) for name in ROOT_FILES}
    configs: dict[Path, str] = {}

    for relative in kit.agent_files():
        target = project.root / relative
        if relative.name in MERGED and store.readable_file(target):
            configs[relative] = merged_config(existing=read(target), kit=kit.text(relative), where=str(relative))

    return Prepared(stamp=stamp, front_doors=front_doors, configs=configs)


def install(
    kit: Kit,
    project: Project,
    prepared: Prepared,
    report: Report,
) -> None:
    """Copy the kit's own files in, leaving the project's alone, the version stamp last.

    The kit's texts and the merged configs were read and checked by
    `prepare` before anything was touched. Section 0 is read here, after
    the migration has pointed it at the new folder name.
    """
    stamp = prepared.stamp
    configs = prepared.configs
    front_doors = dict(prepared.front_doors)
    zero = section_zero_of(project=project, kit_text=front_doors["AGENTS.md"])
    if zero is not None:
        front_doors["AGENTS.md"] = with_section_zero(text=front_doors["AGENTS.md"], zero=zero[1])
        report.done(f"kept section 0 from {zero[0]}")

    for name in ROOT_FILES:
        settle_case(project=project, name=name, report=report)
        put(project=project, relative=Path(name), text=front_doors[name], report=report)

    skill_home = project.brain / "skills" / "agent-brain"
    shipped = [Path(FOLDER) / relative for relative in kit.brain_files() if relative.name != VERSION]
    written = sum(copy(kit=kit, project=project, relative=relative) for relative in shipped)
    retired = retire(project=project, folder=skill_home, keep=set(shipped))
    report.done(f"the kit's {len(shipped)} files under {FOLDER}/, {written} written, {len(retired)} retired")

    for kind in schema.KINDS.values():
        (project.brain / kind.folder).mkdir(parents=True, exist_ok=True)

    for relative in kit.agent_files():
        if relative in configs:
            put(project=project, relative=relative, text=configs[relative], report=report)
            continue

        if copy(kit=kit, project=project, relative=relative):
            report.done(f"wrote {relative}")

    ignore(project=project, kit=kit, report=report)

    put(project=project, relative=Path(FOLDER) / VERSION, text=stamp + "\n", report=report, quiet=True)
    report.done(f"stamped {FOLDER}/{VERSION} {stamp}")


def check(
    project: Project,
) -> list[doctor.Finding]:
    """Doctor with --fix over the brain as installed, and what it could not clear."""
    brain = store.Brain(root=project.brain)

    return doctor.run(brain=brain, fix=True)


def candidates(
    project: Project,
) -> list[str]:
    """What an unported project usually holds that belongs in the brain, for the agent to file."""
    found: list[str] = []
    kept = {*ROOT_FILES, "README.md", "CODEOWNERS", "LICENSE.md", "CHANGELOG.md"}

    for path in sorted(project.root.glob("*.md")):
        if path.name not in kept and path.name.lower() not in {name.lower() for name in kept}:
            found.append(path.name)

    for folder in ("docs", "doc", "notes", "adr", "decisions"):
        if store.quietly((project.root / folder).is_dir):
            found.append(f"{folder}/")

    return found


def to_agents_folder(
    project: Project,
    report: Report,
) -> None:
    """The layout before 1.0.0 kept the brain in .agent/ and the rules in CLAUDE.md."""
    old = project.root / OLD_FOLDER
    if store.quietly(old.is_dir):
        if store.quietly(project.brain.exists):
            raise UpgradeError(f"both {OLD_FOLDER}/ and {FOLDER}/ exist, fold one into the other by hand first")

        move(project=project, old=old, new=project.brain)
        report.done(f"renamed {OLD_FOLDER}/ to {FOLDER}/")

    changed = 0
    for path in sorted(project.root.glob("*.md")) + [project.root / IGNORE_FILE]:
        if rewrite_folder_name(path):
            changed += 1

    for path in sorted(project.brain.rglob("*.md")):
        if "skills" in path.relative_to(project.brain).parts:
            continue

        if rewrite_folder_name(path):
            changed += 1

    if changed:
        report.done(f"pointed {changed} files at {FOLDER}/ instead of {OLD_FOLDER}/")


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        to="1.0.0",
        says=f"the brain lives in {FOLDER}/, the rules in the kit's own files, and section 0 in AGENTS.md",
        apply=to_agents_folder,
    ),
)


def rewrite_folder_name(
    path: Path,
) -> bool:
    """Point one text file at .agents/ where it named .agent/, and say whether it changed.

    The file's own line endings are kept, so the change is the folder
    name and nothing else.
    """
    if not store.readable_file(path):
        return False

    try:
        text = read_as_is(path)
    except UpgradeError:
        return False

    wanted = text.replace(f"{OLD_FOLDER}/", f"{FOLDER}/")
    if wanted == text:
        return False

    frontmatter.write_text(path=str(path), text=wanted)

    return True


def read_as_is(
    path: Path,
) -> str:
    """The file's text with its line endings as written, not folded to newlines."""
    try:
        with open(path, encoding="utf-8", newline="") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError) as error:
        raise UpgradeError(f"{path.name} cannot be read: {error}") from error


def move(
    project: Project,
    old: Path,
    new: Path,
) -> None:
    """Rename a file or folder, through git when git tracks it, so the rename is recorded as one.

    A case only rename, `Agents.md` to `AGENTS.md`, goes through a
    passing name, since a case folding file system would otherwise call
    it no change at all.
    """
    result = git(project=project, arguments=["ls-files", "--error-unmatch", str(old.relative_to(project.root))])
    if result is not None and result.returncode == 0:
        moved = git(project=project, arguments=["mv", "-f", str(old.relative_to(project.root)), str(new.relative_to(project.root))])
        if moved is not None and moved.returncode == 0:
            return

    if old.name.lower() == new.name.lower() and old.parent == new.parent:
        passing = old.parent / f".{new.name}.renaming"
        old.rename(passing)
        old = passing

    old.rename(new)


def git(
    project: Project,
    arguments: list[str],
) -> Optional["subprocess.CompletedProcess[str]"]:
    """Run git in the project, or None when git is not there to run."""
    try:
        return subprocess.run(
            ["git", "-C", str(project.root), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None


def section_zero_of(
    project: Project,
    kit_text: str,
) -> Optional[tuple[str, str]]:
    """The project's own rules, found in whichever front door carries a `## 0.` section.

    In an AGENTS.md the kit already wrote, the section ends where the
    kit's own words begin, so an upgrade run twice carries it once.
    """
    stop = kit_body(kit_text)

    for name in FRONT_DOORS:
        path = any_case(project.root, name)
        if path is None:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        zero = section_zero_in(text=text, stop=stop)
        if zero is not None:
            return path.name, zero

    return None


def kit_body(
    kit_text: str,
) -> str:
    """The first paragraph of the kit's AGENTS.md after its title, the mark where the kit's words start."""
    rest = kit_text.split("\n", 1)[1] if "\n" in kit_text else ""

    return rest.strip().split("\n\n", 1)[0]


def section_zero_in(
    text: str,
    stop: str = "",
) -> Optional[str]:
    """The `## 0.` section of a file, heading included, up to the next `## ` heading or the `stop` text."""
    match = SECTION_ZERO.search(text)
    if match is None:
        return None

    rest = text[match.start() :]
    ends = [len(rest)]
    following = NEXT_SECTION.search(rest, 1)
    if following:
        ends.append(following.start())

    if stop and stop in rest:
        ends.append(rest.index(stop))

    block = rest[: min(ends)].rstrip() + "\n"
    heading, body = block.split("\n", 1)

    return f"{SECTION_ZERO_HEADING}\n{body}"


def with_section_zero(
    text: str,
    zero: str,
) -> str:
    """The kit's AGENTS.md with the project's section 0 directly under the title."""
    title, rest = text.split("\n", 1)

    return f"{title}\n\n{zero.rstrip()}\n\n{rest.lstrip()}"


def merged_config(
    existing: str,
    kit: str,
    where: str,
) -> str:
    """The project's hook config with the kit's hooks in it, its own hooks kept.

    The kit's earlier hooks go, told apart by the tool's own script in
    their command, so a release that changes a command leaves no double.
    Any other key the kit sets is added only where the project has none.
    """
    try:
        have = json.loads(existing)
        want = json.loads(kit)
    except json.JSONDecodeError as error:
        raise UpgradeError(f"{where} is not valid JSON: {error}") from error

    if not isinstance(have, dict) or not isinstance(want, dict):
        raise UpgradeError(f"{where} is not a JSON object")

    hooks = have.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise UpgradeError(f"hooks in {where} is not a JSON object")

    for event, groups in want.get("hooks", {}).items():
        mine = hooks.get(event, [])
        if not isinstance(mine, list):
            raise UpgradeError(f"hooks.{event} in {where} is not a JSON list")

        kept = [group for group in mine if not is_kit_group(group)]
        hooks[event] = kept + groups

    for key, value in want.items():
        if key == "hooks":
            continue

        if isinstance(value, dict) and isinstance(have.get(key), dict):
            for inner, inner_value in value.items():
                have[key].setdefault(inner, inner_value)
            continue

        have.setdefault(key, value)

    return json.dumps(have, indent=2) + "\n"


def is_kit_group(
    group: object,
) -> bool:
    if not isinstance(group, dict):
        return False

    return any(KIT_HOOK_MARK in str(hook.get("command", "")) for hook in group.get("hooks", []) if isinstance(hook, dict))


def ignore(
    project: Project,
    kit: Kit,
    report: Report,
) -> None:
    """The kit's ignore patterns present in the project's .gitignore, added under one heading when missing."""
    wanted = [line for line in kit.text(Path(IGNORE_FILE)).splitlines() if line.strip() and not line.startswith("#")]
    target = project.root / IGNORE_FILE
    existing = read_as_is(target) if store.readable_file(target) else ""
    present = {line.strip() for line in existing.splitlines()}
    missing = [line for line in wanted if line not in present]
    if not missing:
        return

    ending = "\r\n" if "\r\n" in existing else "\n"
    tail = ending.join([IGNORE_HEADING, *missing]) + ending
    text = existing.rstrip("\r\n") + (ending * 2 if existing.strip() else "") + tail
    frontmatter.write_text(path=str(target), text=text)
    report.done(f"added {len(missing)} lines to {IGNORE_FILE}")


def guarded_paths(
    kit: Kit,
    project: Project,
) -> list[str]:
    """Every project path a port or upgrade writes over or removes, relative to the project.

    The front doors and CONTRIBUTING.md are replaced whole, so are the
    kit's files under .agents/ and the style files in the agent folders,
    the skill folder is cleared and rewritten, and the migration
    rewrites the root markdown and every file under the old folder.
    The ignore file and the hook configs keep what they hold, so an edit
    there is safe and not listed.
    """
    paths = [*ROOT_FILES]
    paths += [str(relative) for relative in kit.agent_files() if relative.name not in MERGED]
    paths += [str(Path(FOLDER) / relative) for relative in kit.brain_files()]
    paths += files_under(root=project.root, folder=project.brain / "skills" / "agent-brain")

    old = project.root / OLD_FOLDER
    if store.quietly(old.is_dir):
        paths += files_under(root=project.root, folder=old)
        paths += [path.name for path in list_names(project.root) if path.suffix == ".md"]

    return paths


def files_under(
    root: Path,
    folder: Path,
) -> list[str]:
    """Every file below the folder that a run would touch, relative to the root, bytecode and dotfiles left out."""
    if not store.quietly(folder.is_dir):
        return []

    return [str(path.relative_to(root)) for path in sorted(folder.rglob("*")) if ships(path)]


def refuse_when_dirty(
    project: Project,
    paths: list[str],
    report: Report,
) -> None:
    """Refuse while a file about to be written over or removed holds uncommitted work.

    Git is asked for the whole working tree once, ignored files
    included since a removed one is lost all the same, and the answer
    is matched against the paths without regard to case, so a front
    door spelled `Agents.md` is seen. Git names paths from the
    repository's root, so the project's place below it is put in front
    of each path first. A repository whose git fails is refused too,
    since nothing would be guarded. A project outside git gets no
    guard, and the report says so.
    """
    result = git(project=project, arguments=["status", "--porcelain", "--untracked-files=all", "--ignored=matching", "-z"])
    if result is None:
        report.done("git is not on this machine, so nothing is saved before a file is replaced")
        return

    if result.returncode != 0:
        if "not a git repository" in result.stderr:
            report.done("not a git repository, so nothing is saved before a file is replaced")
            return

        raise UpgradeError(f"git could not read the working tree, so nothing is guarded: {result.stderr.strip()}")

    prefix = git(project=project, arguments=["rev-parse", "--show-prefix"])
    if prefix is None or prefix.returncode != 0:
        raise UpgradeError(f"git could not place the project in its repository, so nothing is guarded: {(prefix.stderr if prefix else '').strip()}")

    base = prefix.stdout.strip().replace("\\", "/")
    wanted = {(base + path.replace("\\", "/")).lower() for path in paths}
    dirty = sorted(path[len(base) :] for path in changed_paths(result.stdout) if path.lower() in wanted)
    if dirty:
        raise UpgradeError("commit, stash or move these first, they would be written over or removed: " + ", ".join(dirty))


def changed_paths(
    porcelain: str,
) -> list[str]:
    """The paths in a NUL separated porcelain listing, a rename's old name included."""
    found: list[str] = []
    tokens = porcelain.split("\0")
    index = 0

    while index < len(tokens):
        entry = tokens[index]
        index += 1
        if len(entry) < 4:
            continue

        found.append(entry[3:])
        if entry[0] in "RC" and index < len(tokens):
            found.append(tokens[index])
            index += 1

    return found


def settle_case(
    project: Project,
    name: str,
    report: Report,
) -> None:
    """A front door spelled in another case, `Agents.md` for one, takes the kit's spelling first."""
    found = any_case(project.root, name)
    if found is None or found.name == name:
        return

    move(project=project, old=found, new=project.root / name)
    report.done(f"renamed {found.name} to {name}")


def any_case(
    folder: Path,
    name: str,
) -> Optional[Path]:
    """The file in the folder whose name matches in any case, the exact spelling first."""
    exact = folder / name
    if store.readable_file(exact) and exact.name == name and exact in list_names(folder):
        return exact

    for path in list_names(folder):
        if path.name.lower() == name.lower():
            return path

    return None


def list_names(
    folder: Path,
) -> list[Path]:
    try:
        return sorted(path for path in folder.iterdir() if path.is_file())
    except OSError:
        return []


def put(
    project: Project,
    relative: Path,
    text: str,
    report: Report,
    quiet: bool = False,
) -> None:
    """Write one file whole, and say whether it was new or replaced."""
    target = project.root / relative
    was_there = store.readable_file(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    frontmatter.write_text(path=str(target), text=text)

    if not quiet:
        report.done(f"{'replaced' if was_there else 'created'} {relative}")


def read(
    path: Path,
) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise UpgradeError(f"{path.name} cannot be read: {error}") from error


def copy(
    kit: Kit,
    project: Project,
    relative: Path,
) -> bool:
    """Copy one kit file whole, bytes and mode, and say whether anything was written.

    A target that already holds the same bytes is left alone, so a run
    that changes nothing touches nothing.
    """
    data, mode = kit.data(relative)
    target = project.root / relative
    if store.readable_file(target):
        try:
            if target.read_bytes() == data:
                return False
        except OSError:
            pass

    write_bytes(path=target, data=data, mode=mode)

    return True


def write_bytes(
    path: Path,
    data: bytes,
    mode: int,
) -> None:
    """Write a file whole or not at all, through a temporary file beside it, with the mode given.

    The temporary file takes the same shape as the tool's other writes,
    so one left beside a markdown file by an interrupted run is found
    and removed by doctor.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, passing = tempfile.mkstemp(prefix=f".{path.name}.", suffix=frontmatter.TEMP_SUFFIX, dir=str(path.parent))
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())

        os.chmod(passing, mode)
        os.replace(passing, path)
    except BaseException:
        try:
            os.unlink(passing)
        except OSError:
            pass

        raise


def retire(
    project: Project,
    folder: Path,
    keep: set[Path],
) -> list[str]:
    """Remove the files under the skill folder the kit no longer ships, and the folders that emptied.

    The kit's new files are written before this runs, so the tool is
    never half gone. The folder is the tool's own, so what the kit does
    not ship goes, named in the report, and the guard has already
    refused if any of it held uncommitted work. A dotfile is left.
    """
    if not store.quietly(folder.is_dir):
        return []

    retired: list[str] = []
    for path in sorted(folder.rglob("*"), reverse=True):
        relative = path.relative_to(project.root)
        if ships(path) and relative not in keep:
            path.unlink()
            retired.append(str(relative))
        elif path.is_dir() and not path.is_symlink() and not any(path.iterdir()):
            path.rmdir()

    return retired
