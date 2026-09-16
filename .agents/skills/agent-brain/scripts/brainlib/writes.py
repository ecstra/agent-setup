"""Filing a new entry and changing one that is already filed.

Every field a kind carries is checked here before anything reaches disk,
so a file cannot arrive in the brain already breaking its spec. The
prose comes from the caller and is written through untouched.
"""

from datetime import date
from pathlib import Path
from typing import Optional

from . import frontmatter, schema, sections, store


class WriteError(Exception):
    """The change was refused, with the reason in the message."""


def today() -> str:
    return date.today().isoformat()


def create(
    brain: store.Brain,
    kind: schema.Kind,
    title: str,
    description: str,
    values: Optional[dict[str, str]] = None,
    body: str = "",
    category: str = "",
    links: Optional[list[str]] = None,
    stamp: str = "",
) -> store.Entry:
    stamp = stamp or today()

    taken = brain.with_slug(
        kind=kind,
        slug=schema.slugify(title),
    )
    if taken is not None:
        raise WriteError(f"{taken.name} already carries that title")

    path = brain.path_for(
        kind=kind,
        title=title,
        category=category,
    )
    if path.exists():
        raise WriteError(f"{path.name} is already filed")

    if body and sections.missing(body=body, kind=kind):
        wanted = ", ".join(sections.missing(body=body, kind=kind))
        raise WriteError(f"the body is missing the {wanted} heading")

    fields = opening_fields(
        kind=kind,
        name=entry_name(path=path, kind=kind),
        description=description,
        links=links or [],
        stamp=stamp,
    )
    fields.update(defaults(kind=kind, stamp=stamp))
    fields.update(values or {})

    check(kind=kind, fields=fields)

    document = frontmatter.Document(
        lines=render_lines(kind=kind, fields=fields),
        body=body or sections.skeleton(kind=kind, title=title),
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter.write(path=str(path), document=document)

    return brain.read(path=path, kind=kind)


def update(
    brain: store.Brain,
    key: str,
    changes: dict[str, str],
    stamp: str = "",
) -> store.Entry:
    entry = brain.find(key)
    if entry is None:
        raise WriteError(f"nothing in the brain answers to '{key}'")

    stamp = stamp or today()
    fields = entry.document.fields()
    fields.update(changes)

    check(kind=entry.kind, fields=fields)
    check_transition(
        entry=entry,
        changes=changes,
        fields=fields,
    )

    for name, value in changes.items():
        entry.document.set(key=name, value=value)

    entry.document.set(key="updated", value=stamp)
    frontmatter.write(path=str(entry.path), document=entry.document)

    return brain.read(path=entry.path, kind=entry.kind)


def entry_name(
    path: Path,
    kind: schema.Kind,
) -> str:
    if kind.name == "review":
        return path.parent.name

    return path.stem


def opening_fields(
    kind: schema.Kind,
    name: str,
    description: str,
    links: list[str],
    stamp: str,
) -> dict[str, str]:
    return {
        "name": name,
        "kind": kind.kind_value,
        "description": description,
        "updated": stamp,
        "links": frontmatter.render_list(links),
    }


def defaults(
    kind: schema.Kind,
    stamp: str,
) -> dict[str, str]:
    """The fields a new file of this kind can fill in for itself."""
    starting = {
        "bug": {"status": "open", "reported": stamp},
        "todo": {"status": "open", "born": stamp},
        "decision": {"status": "standing", "date": stamp},
        "review": {"status": "open"},
    }

    return dict(starting.get(kind.name, {}))


def render_lines(
    kind: schema.Kind,
    fields: dict[str, str],
) -> list[str]:
    """Frontmatter lines in the order the spec lists them."""
    return [
        f"{item.name}: {fields[item.name]}"
        for item in schema.fields_for(kind)
        if item.name in fields
    ]


def check(
    kind: schema.Kind,
    fields: dict[str, str],
) -> None:
    known = {item.name for item in schema.fields_for(kind)}

    for name in fields:
        if name not in known:
            raise WriteError(f"{kind.name} files carry no '{name}' field")

    for item in schema.fields_for(kind):
        value = fields.get(item.name, "")

        if item.required and not value:
            raise WriteError(f"a {kind.name} needs a {item.name}")

        if not value:
            continue

        if item.values and value not in item.values:
            allowed = " or ".join(item.values)
            raise WriteError(f"{item.name} is {allowed}, not '{value}'")

        if item.is_date and not schema.is_date(value):
            raise WriteError(f"{item.name} reads YYYY-MM-DD, not '{value}'")


def check_transition(
    entry: store.Entry,
    changes: dict[str, str],
    fields: dict[str, str],
) -> None:
    """The lifecycle rules a status change has to satisfy."""
    status = changes.get("status")
    if status is None:
        return

    body = entry.document.body

    if entry.kind.name == "bug" and status == "fixed":
        if not sections.is_filled(body=body, title="Fix"):
            raise WriteError(
                "a bug goes fixed once its Fix section names the cause and the commit"
            )

    if entry.kind.name == "bug" and status == "wontfix":
        if not sections.is_filled(body=body, title="Problem"):
            raise WriteError("a wontfix needs its reason written in the body")

    if entry.kind.name == "todo" and status == "done":
        if not fields.get("done"):
            raise WriteError("a todo goes done with the date it closed, done: YYYY-MM-DD")

        if not sections.is_filled(body=body, title="Done when"):
            raise WriteError("a todo goes done once Done when names what closed it")

    if entry.kind.name == "decision" and status == "superseded":
        if not fields.get("superseded-by"):
            raise WriteError("a superseded decision names the one that replaced it")
