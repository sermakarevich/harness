"""Thread helpers for the answer loop.

They make a fresh id for each conversation and tell the saved
store which conversation to continue. Small helpers live here
so the graph file stays about one job.
"""

from __future__ import annotations

import uuid

SESSION_ID_PREFIX = "harness-"


def new_session_id() -> str:
    """Make a fresh id for a new conversation."""
    return f"{SESSION_ID_PREFIX}{uuid.uuid4()}"


def thread_config(session_id: str) -> dict:
    """Tell the harness which saved conversation to continue."""
    return {"configurable": {"thread_id": session_id}}
