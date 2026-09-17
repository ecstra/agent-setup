"""Filing a new entry and changing one that is already filed.

Every field a kind carries is checked here before anything reaches disk,
so a file cannot arrive in the brain already breaking its spec. The
prose comes from the caller and is written through untouched.
"""

from datetime import date
from pathlib import Path
from typing import Optional

from . import frontmatter, links, schema, sections, store


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

    slug = schema.slugify(title)
    if kind.name == "review" and not schema.is_review_folder(slug):
        raise WriteError(f"a review folder is named <yyyy-mm>-<branch-slug>, and '{slug}' is not")

    taken = brain.with_slug(
        kind=kind,
        slug=slug,
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
        links=path_links(brain=brain, references=links or []),
        stamp=stamp,
    )
    fields.update(defaults(kind=kind, stamp=stamp))
    fields.update(values or {})

    check(kind=kind, fields=fields)

    document = frontmatter.Document(
        lines=render_lines(kind=kind, fields=fields),
        body=framed(body) if body else sections.skeleton(kind=kind, title=title),
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter.write(path=str(path), document=document)
    brain.refresh()

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
    changes = dict(changes)
    if "links" in changes:
        wanted = path_links(brain=brain, references=frontmatter.parse_list(changes["links"]))
        changes["links"] = frontmatter.render_list(wanted)

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
    brain.refresh()

    return brain.read(path=entry.path, kind=entry.kind)


def retitle(
    brain: store.Brain,
    key: str,
    title: str,
    stamp: str = "",
) -> store.Entry:
    """Rename a file for a new title. The id stays, every link follows."""
    entry = brain.find(key)
    if entry is None:
        raise WriteError(f"nothing in the brain answers to '{key}'")

    if entry.kind.name == "review":
        raise WriteError("a review keeps the name of its branch")

    slug = schema.slugify(title)
    if not slug:
        raise WriteError(f"'{title}' leaves nothing to name a file with")

    taken = brain.with_slug(kind=entry.kind, slug=slug)
    if taken is not None and taken.path != entry.path:
        raise WriteError(f"{taken.name} already carries that title")

    stem = f"{entry.identifier}-{slug}" if entry.identifier else slug
    target = entry.path.with_name(f"{stem}.md")
    if occupied(target=target, by=entry.path):
        raise WriteError(f"{target.relative_to(brain.root)} is already on disk, the brain does not write over it")

    stamp = stamp or today()
    before = frontmatter.load(str(entry.path))
    moved = links.move_links(
        brain=brain,
        old=entry.relative,
        new=str(target.relative_to(brain.root)),
        stamp=stamp,
    )

    entry.document.set(key="name", value=stem)
    entry.document.set(key="updated", value=stamp)
    try:
        frontmatter.write(path=str(entry.path), document=entry.document)
        entry.path.rename(target)
    except OSError as error:
        undo_retitle(path=entry.path, before=before, moved=moved, error=error)
        raise
    finally:
        brain.refresh()

    return brain.read(path=target, kind=entry.kind)


def undo_retitle(
    path: Path,
    before: str,
    moved: list[links.Planned],
    error: OSError,
) -> None:
    """Put the file and every link that followed it back, or say which would not go.

    The file goes back only if it changed. A write refused up front
    left it as it was, and a refused file cannot take the restore either.
    What could not go back is named beside the failure that started it.
    """
    stuck: list[Path] = []

    try:
        if frontmatter.load(str(path)) != before:
            frontmatter.write_text(path=str(path), text=before)
    except (OSError, frontmatter.FrontmatterError):
        stuck.append(path)

    stuck += links.put_back_all(moved)
    if stuck:
        raise OSError(f"{store.explain(error)}, and {links.names_of(stuck)} could not be put back") from error


def occupied(
    target: Path,
    by: Path,
) -> bool:
    """Whether something other than the file being renamed already sits at `target`.

    On a file system that folds case, a rename that changes only the
    case sees itself at the target, and that is not an occupant.
    """
    if store.quietly(target.is_symlink):
        return True

    if not store.quietly(target.exists):
        return False

    try:
        return not target.samefile(by)
    except OSError:
        return True


def convert(
    brain: store.Brain,
    key: str,
    kind: schema.Kind,
    description: str,
    values: Optional[dict[str, str]] = None,
    body: str = "",
    stamp: str = "",
) -> store.Entry:
    """File a todo as a bug, or the reverse, keeping the id trail in links.

    The old file stays, closed, and the two point at each other. An id
    is never reused, so the old one is not deleted.
    """
    source = brain.find(key)
    if source is None:
        raise WriteError(f"nothing in the brain answers to '{key}'")

    if source.kind.name == kind.name:
        raise WriteError(f"{source.name} is already a {kind.name}")

    if source.kind.name not in ("todo", "bug") or kind.name not in ("todo", "bug"):
        raise WriteError("only a todo and a bug convert into each other")

    stamp = stamp or today()
    created = create(
        brain=brain,
        kind=kind,
        title=source.slug.replace("-", " "),
        description=description,
        values=values,
        body=body,
        links=[source.relative],
        stamp=stamp,
    )

    closing = {"todo": {"status": "dropped", "done": stamp}, "bug": {"status": "wontfix"}}
    source = brain.find(key)
    if source is None:
        raise WriteError(f"{key} vanished while converting it")

    for name, value in closing[source.kind.name].items():
        source.document.set(key=name, value=value)

    trail = [link for link in source.document.get_list("links") if link != created.relative]
    source.document.set_list(key="links", values=[*trail, created.relative])
    source.document.set(key="updated", value=stamp)
    try:
        frontmatter.write(path=str(source.path), document=source.document)
    except OSError:
        created.path.unlink()
        raise
    finally:
        brain.refresh()

    return created


def framed(
    body: str,
) -> str:
    """The prose as given, with a blank line before it and a newline after.

    The text itself is untouched. This only settles where the body sits
    against the closing fence, which the caller should not have to think
    about.
    """
    opening = "" if body.startswith("\n") else "\n"
    closing = "" if body.endswith("\n") else "\n"

    return f"{opening}{body}{closing}"


def entry_name(
    path: Path,
    kind: schema.Kind,
) -> str:
    if kind.name == "review":
        return path.parent.name

    return path.stem


def path_links(
    brain: store.Brain,
    references: list[str],
) -> list[str]:
    """Every link in path form, refused when one reaches nothing in the brain."""
    found: list[str] = []

    for reference in references:
        path = links.canonical(brain=brain, reference=reference)
        if path is None:
            raise WriteError(f"link '{reference}' reaches nothing inside .agents/")

        found.append(path)

    return found


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
    """Every field against the spec, the common ones and the kind's own."""
    check_against(kind=kind, fields=fields, items=schema.fields_for(kind))


def check_own(
    kind: schema.Kind,
    fields: dict[str, str],
) -> None:
    """The kind's own fields only, for a caller that checks the common ones itself."""
    check_against(kind=kind, fields=fields, items=kind.fields)


def check_against(
    kind: schema.Kind,
    fields: dict[str, str],
    items: tuple[schema.Field, ...],
) -> None:
    known = {item.name for item in schema.fields_for(kind)}

    for name in fields:
        if name not in known:
            raise WriteError(f"{kind.name} files carry no '{name}' field")

    for item in items:
        value = fields.get(item.name, "")

        if item.required and not value:
            raise WriteError(f"a {kind.name} needs {item.name} filled in")

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
            raise WriteError("a todo goes done with its closing date, done=YYYY-MM-DD")

        if not sections.is_filled(body=body, title="Done when"):
            raise WriteError("a todo goes done once Done when names what closed it")

    if entry.kind.name == "decision" and status == "superseded":
        if not fields.get("superseded-by"):
            raise WriteError("a superseded decision names the one that replaced it")
