"""A helper agent: the tools it may use and how one job is run."""

from __future__ import annotations

from collections.abc import Callable

from langchain_core.messages import HumanMessage

from harness.chat.prompt import build_helper_prompt
from harness.model.text import text_of
from harness.tools.permission import needs_approval


def helper_tools(tools: list) -> list:
    """The tools a helper may use: the ones nobody has to be asked about."""
    return [tool for tool in tools if not needs_approval(tool.name)]


def build_helper_runner(graph) -> Callable[[str], str]:
    """Build the call behind the tool: one job in, the helper's last message out."""

    def run(job: str) -> str:
        final = graph.invoke({"messages": [HumanMessage(content=build_helper_prompt(job))]})
        return text_of(final["messages"][-1])

    return run
