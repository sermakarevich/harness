"""Policy naming which tool calls need a question first."""

from enum import StrEnum

from harness.tools.read_file import TOOL_NAME as READ_FILE
from harness.tools.read_skill import TOOL_NAME as READ_SKILL


class Answer(StrEnum):
    YES = "yes"
    ALWAYS = "always"
    NO = "no"


SAFE_TOOLS = frozenset({READ_FILE, READ_SKILL})

DENIED_MESSAGE = "denied by the user"


def needs_approval(name: str) -> bool:
    """True when a tool call must wait for a yes first."""
    return name not in SAFE_TOOLS
