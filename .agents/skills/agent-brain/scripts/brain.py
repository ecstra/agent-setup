"""The brain tool. Files, changes, counts and checks everything in .agents/.

Run from anywhere inside a project that carries the kit:

    python3 .agents/skills/agent-brain/scripts/brain.py status

Prose for a new file comes in on standard input, so a heredoc in single
quotes passes it through without the shell touching it. Exit codes: 0
when it did the thing, 1 when it refused and said why, 2 when doctor
still has findings.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from brainlib import doctor, frontmatter, index, ledger, reads, schema, store, writes

REFUSED = 1
FINDINGS_REMAIN = 2

FIELD_FLAGS = ("status", "severity", "area", "by", "type", "branch", "date")


def main(
    argv: Optional[list[str]] = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return REFUSED

    try:
        brain = store.find_brain(Path.cwd())
        return args.handler(brain=brain, args=args)
    except (
        store.StoreError,
        writes.WriteError,
        ledger.LedgerError,
        frontmatter.FrontmatterError,
        schema.UnknownKind,
        OSError,
        KeyError,
    ) as error:
        print(store.explain(error), file=sys.stderr)
        return REFUSED


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="brain",
        description="file, change, count and check what is in .agents/",
    )
    commands = parser.add_subparsers(dest="command")

    add_version(commands)
    add_status(commands)
    add_list(commands)
    add_show(commands)
    add_path(commands)
    add_links(commands)
    add_new(commands)
    add_set(commands)
    add_refile(commands)
    add_index(commands)
    add_doctor(commands)
    add_ledger(commands)

    return parser


def add_version(
    commands: argparse._SubParsersAction,
) -> None:
    command = commands.add_parser("version", help="the kit version this project carries")
    command.set_defaults(handler=run_version)


def run_version(
    brain: store.Brain,
    args: argparse.Namespace,
) -> int:
    print(reads.version(brain))
    return 0


def add_status(
    commands: argparse._SubParsersAction,
) -> None:
    command = commands.add_parser("status", help="the whole picture in a few lines")
    command.add_argument("--json", action="store_true")
    command.set_defaults(handler=run_status)


def run_status(
    brain: store.Brain,
    args: argparse.Namespace,
) -> int:
    data = reads.status(brain)
    print(json.dumps(data, indent=2) if args.json else reads.render_status(data))
    return 0


def add_list(
    commands: argparse._SubParsersAction,
) -> None:
    command = commands.add_parser("list", help="one line per entry of a kind, narrowed by field")
    command.add_argument("kind", choices=sorted(schema.KINDS))
    for flag in FIELD_FLAGS:
        command.add_argument(f"--{flag}")
    command.add_argument("--json", action="store_true")
    command.set_defaults(handler=run_list)


def run_list(
    brain: store.Brain,
    args: argparse.Namespace,
) -> int:
    kind = schema.kind_named(args.kind)
    filters = {flag: getattr(args, flag) for flag in FIELD_FLAGS if getattr(args, flag)}
    found = reads.rows(brain=brain, kind=kind, filters=filters)
    print(json.dumps(found, indent=2) if args.json else reads.render_rows(kind=kind, found=found))
    return 0


def add_show(
    commands: argparse._SubParsersAction,
) -> None:
    command = commands.add_parser("show", help="print one entry, by id, name or path")
    command.add_argument("key")
    command.add_argument("--meta", action="store_true", help="the frontmatter only")
    command.set_defaults(handler=run_show)


def run_show(
    brain: store.Brain,
    args: argparse.Namespace,
) -> int:
    text = reads.show(brain=brain, key=args.key, meta_only=args.meta)
    if text is None:
        return missing(args.key)

    print(text, end="" if text.endswith("\n") else "\n")
    return 0


def add_path(
    commands: argparse._SubParsersAction,
) -> None:
    command = commands.add_parser("path", help="the file behind an id or a name")
    command.add_argument("key")
    command.set_defaults(handler=run_path)


def run_path(
    brain: store.Brain,
    args: argparse.Namespace,
) -> int:
    path = reads.path_of(brain=brain, key=args.key)
    if path is None:
        return missing(args.key)

    print(path)
    return 0


def add_links(
    commands: argparse._SubParsersAction,
) -> None:
    command = commands.add_parser("links", help="what an entry points at, and what points back")
    command.add_argument("key")
    command.add_argument("--json", action="store_true")
    command.set_defaults(handler=run_links)


def run_links(
    brain: store.Brain,
    args: argparse.Namespace,
) -> int:
    data = reads.links_of(brain=brain, key=args.key)
    if data is None:
        return missing(args.key)

    print(json.dumps(data, indent=2) if args.json else reads.render_links(data))
    return 0


def add_new(
    commands: argparse._SubParsersAction,
) -> None:
    command = commands.add_parser("new", help="file a new entry, prose on standard input")
    command.add_argument("kind", choices=sorted(schema.KINDS))
    command.add_argument("--title", required=True)
    command.add_argument("--description", required=True, help="the one line the index shows")
    command.add_argument("--category", default="", help="for a doc, its category folder")
    command.add_argument("--link", action="append", default=[], help="a related file, repeatable")
    for flag in FIELD_FLAGS:
        command.add_argument(f"--{flag}")
    command.set_defaults(handler=run_new)


def run_new(
    brain: store.Brain,
    args: argparse.Namespace,
) -> int:
    kind = schema.kind_named(args.kind)
    entry = writes.create(
        brain=brain,
        kind=kind,
        title=args.title,
        description=args.description,
        values=field_values(args),
        body=stdin_text(),
        category=args.category,
        links=args.link,
    )
    index.write(brain)
    print(entry.relative)
    return 0


def add_set(
    commands: argparse._SubParsersAction,
) -> None:
    command = commands.add_parser("set", help="change fields on an entry, as field=value")
    command.add_argument("key")
    command.add_argument("changes", nargs="+", metavar="field=value")
    command.set_defaults(handler=run_set)


def run_set(
    brain: store.Brain,
    args: argparse.Namespace,
) -> int:
    entry = writes.update(
        brain=brain,
        key=args.key,
        changes=pairs(args.changes),
    )
    index.write(brain)
    print(entry.relative)
    return 0


def add_refile(
    commands: argparse._SubParsersAction,
) -> None:
    command = commands.add_parser("refile", help="retitle an entry, or turn a todo into a bug")
    command.add_argument("key")
    command.add_argument("--title", help="the new title, the id stays")
    command.add_argument("--kind", choices=("todo", "bug"), help="the kind it becomes")
    command.add_argument("--description", default="", help="with --kind, the new one line")
    for flag in FIELD_FLAGS:
        command.add_argument(f"--{flag}")
    command.set_defaults(handler=run_refile)


def run_refile(
    brain: store.Brain,
    args: argparse.Namespace,
) -> int:
    if bool(args.title) == bool(args.kind):
        print("refile takes --title or --kind, one of the two", file=sys.stderr)
        return REFUSED

    if args.title:
        entry = writes.retitle(brain=brain, key=args.key, title=args.title)
    else:
        entry = writes.convert(
            brain=brain,
            key=args.key,
            kind=schema.kind_named(args.kind),
            description=args.description,
            values=field_values(args),
            body=stdin_text(),
        )

    index.write(brain)
    print(entry.relative)
    return 0


def add_index(
    commands: argparse._SubParsersAction,
) -> None:
    command = commands.add_parser("index", help="rebuild every INDEX.md from its folder")
    command.set_defaults(handler=run_index)


def run_index(
    brain: store.Brain,
    args: argparse.Namespace,
) -> int:
    for path in index.write(brain):
        print(path.relative_to(brain.root))
    return 0


def add_doctor(
    commands: argparse._SubParsersAction,
) -> None:
    command = commands.add_parser("doctor", help="check the whole brain, fix what is mechanical")
    command.add_argument("--fix", action="store_true")
    command.add_argument("--json", action="store_true")
    command.set_defaults(handler=run_doctor)


def run_doctor(
    brain: store.Brain,
    args: argparse.Namespace,
) -> int:
    found = doctor.run(brain=brain, fix=args.fix)
    if args.json:
        print(json.dumps([finding.as_dict() for finding in found], indent=2))
    else:
        for finding in found:
            print(finding.line())
        print("clean" if not found else f"{len(found)} findings")

    return FINDINGS_REMAIN if found else 0


def add_ledger(
    commands: argparse._SubParsersAction,
) -> None:
    command = commands.add_parser("ledger", help="review ledgers: open, batch, add, set, close")
    actions = command.add_subparsers(dest="action")

    opening = actions.add_parser("open", help="start the ledger for a branch")
    opening.add_argument("branch")
    opening.add_argument("--summary", required=True)
    opening.set_defaults(handler=run_ledger_open)

    batch = actions.add_parser("batch", help="add a batch, or set one's status, ack or theme")
    batch.add_argument("key")
    batch.add_argument("number", nargs="?", type=int)
    batch.add_argument("--theme")
    batch.add_argument("--status")
    batch.add_argument("--ack")
    batch.set_defaults(handler=run_ledger_batch)

    adding = actions.add_parser("add", help="record a finding")
    adding.add_argument("key")
    adding.add_argument("claim")
    adding.add_argument("--severity", required=True, choices=schema.SEVERITIES)
    adding.add_argument("--found-by", default="review", choices=ledger.FOUND_BY)
    adding.add_argument("--batch", type=int, default=0)
    adding.set_defaults(handler=run_ledger_add)

    setting = actions.add_parser("set", help="change a finding's status or fix")
    setting.add_argument("key")
    setting.add_argument("finding")
    setting.add_argument("changes", nargs="+", metavar="field=value")
    setting.set_defaults(handler=run_ledger_set)

    closing = actions.add_parser("close", help="close the ledger once every finding landed")
    closing.add_argument("key")
    closing.set_defaults(handler=run_ledger_close)


def run_ledger_open(
    brain: store.Brain,
    args: argparse.Namespace,
) -> int:
    entry = ledger.open_ledger(brain=brain, branch=args.branch, summary=args.summary)
    index.write(brain)
    print(entry.relative)
    return 0


def run_ledger_batch(
    brain: store.Brain,
    args: argparse.Namespace,
) -> int:
    if args.number is None:
        if args.status or args.ack:
            print("give the batch's number to set its status or ack", file=sys.stderr)
            return REFUSED

        if not args.theme:
            print("a new batch needs --theme", file=sys.stderr)
            return REFUSED

        print(ledger.add_batch(brain=brain, key=args.key, theme=args.theme))
        return 0

    ledger.set_batch(
        brain=brain,
        key=args.key,
        number=args.number,
        status=args.status or "",
        ack=args.ack or "",
        theme=args.theme or "",
    )
    return 0


def run_ledger_add(
    brain: store.Brain,
    args: argparse.Namespace,
) -> int:
    print(
        ledger.add_finding(
            brain=brain,
            key=args.key,
            claim=args.claim,
            severity=args.severity,
            found_by=args.found_by,
            batch=args.batch,
        )
    )
    return 0


def run_ledger_set(
    brain: store.Brain,
    args: argparse.Namespace,
) -> int:
    ledger.set_finding(
        brain=brain,
        key=args.key,
        identifier=args.finding,
        changes=pairs(args.changes),
    )
    return 0


def run_ledger_close(
    brain: store.Brain,
    args: argparse.Namespace,
) -> int:
    ledger.close(brain=brain, key=args.key)
    index.write(brain)
    return 0


def field_values(
    args: argparse.Namespace,
) -> dict[str, str]:
    return {flag: getattr(args, flag) for flag in FIELD_FLAGS if getattr(args, flag, None)}


def pairs(
    items: list[str],
) -> dict[str, str]:
    found: dict[str, str] = {}

    for item in items:
        if "=" not in item:
            raise writes.WriteError(f"'{item}' is not field=value")

        field, _, value = item.partition("=")
        found[field.strip()] = value.strip()

    return found


def stdin_text() -> str:
    """The prose on standard input, or nothing when there is no input at all.

    A closed standard input leaves `sys.stdin` as None, and a terminal
    means nobody piped anything, so both read as an empty body.
    """
    if sys.stdin is None or sys.stdin.isatty():
        return ""

    return sys.stdin.read()


def missing(
    key: str,
) -> int:
    print(f"nothing in the brain answers to '{key}'", file=sys.stderr)
    return REFUSED


if __name__ == "__main__":
    sys.exit(main())
