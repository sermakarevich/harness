"""Hands one job to a helper that starts with an empty conversation."""

from __future__ import annotations

from collections.abc import Callable

from langchain_core.tools import tool

TOOL_NAME = "ask_helper"


def ask_helper_tool(run_helper: Callable[[str], str]):
    """Build the tool that gives one job to a helper."""

    @tool(TOOL_NAME)
    def ask_helper(job: str) -> str:
        """Give one job to a helper that starts fresh and sends back one answer.

        Use it for reading or searching whose details you do not need to keep. The helper
        cannot change anything and cannot pass the job on.
        """
        return run_helper(job)

    return ask_helper
