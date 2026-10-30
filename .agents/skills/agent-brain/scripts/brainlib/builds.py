"""A build spec, what one branch builds and how it proves it, filed before the code.

The prose is the owner's and the agent's. The steps table is the tool's,
per `steps`, and lists the todos, bugs and review the branch takes on.
"""

from typing import Optional

from . import schema, steps, store, writes


class BuildError(Exception):
    """A build spec the tool cannot file as asked, with the reason in the message."""


def create(
    brain: store.Brain,
    title: str,
    description: str,
    body: str,
    values: Optional[dict[str, str]] = None,
    links: Optional[list[str]] = None,
    stamp: str = "",
) -> store.Entry:
    """File a draft build spec from its prose, its listed steps turned into the table."""
    if not body.strip():
        raise BuildError("a build spec needs its prose on standard input, the Goal to the Steps")

    kind = schema.kind_named("build-spec")

    text = body
    if steps.span(text) is None:
        text = steps.with_table(
            body=text,
            rows=[],
            kind=kind,
        )

    return writes.create(
        brain=brain,
        kind=kind,
        title=title,
        description=description,
        values=dict(values or {}),
        body=text,
        links=links or [],
        stamp=stamp,
    )
