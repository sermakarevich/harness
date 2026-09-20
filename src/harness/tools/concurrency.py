"""Group tool calls into batches that may run beside each other."""

from harness.tools.edit_file import TOOL_NAME as EDIT_FILE
from harness.tools.write_file import TOOL_NAME as WRITE_FILE

EXCLUSIVE_TOOLS = frozenset({WRITE_FILE, EDIT_FILE})


def runs_alone(name: str) -> bool:
    """True when a tool call must run with no other call beside it."""
    return name in EXCLUSIVE_TOOLS


def batch_calls(calls: list) -> list[list]:
    """Split the calls into batches that may run together, in order."""
    batches: list[list] = []
    current: list = []
    for call in calls:
        if runs_alone(call["name"]):
            if current:
                batches.append(current)
                current = []
            batches.append([call])
        else:
            current.append(call)
    if current:
        batches.append(current)
    return batches
