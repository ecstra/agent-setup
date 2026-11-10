"""The session a command or a hook runs in.

Two agents may work in one project folder, each on its own line of
work. What tells them apart is the session each runs in, which the
agent itself names in the environment of every command and hook it
starts. The tool reads it there and nowhere else, so no command takes
a session's id and the agent never types one. Where no agent names a
session, as in a plain terminal, there is none, and the tool works on
the folder's own files as it did before 3.2.0.

Only a short hash of the id is ever kept or compared, so no file of
the brain holds the id itself.
"""

import hashlib
import os
from typing import Optional

# what Claude Code, Codex and Gemini CLI put into the environment of what they run, read in that order
SESSION_VARS: tuple[str, ...] = ("CLAUDE_CODE_SESSION_ID", "CODEX_THREAD_ID", "GEMINI_SESSION_ID")

# long enough that two sessions in one folder never share one, short enough for a file's name
HASH_LENGTH = 16


def session() -> Optional[str]:
    """The session this process runs in, as a short hash of the id its agent gives, or None where no agent names one."""
    for name in SESSION_VARS:
        given: str = os.environ.get(name, "").strip()
        if given:
            return hashlib.sha256(given.encode("utf-8")).hexdigest()[:HASH_LENGTH]

    return None
