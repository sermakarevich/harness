"""The answer loop of the harness.

The loop runs tools until the model stops asking.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition
from langgraph.types import RetryPolicy

from harness.chat.compact import build_compact, over_budget
from harness.chat.prompt import build_summary_prompt, build_system_prompt, build_todos_prompt
from harness.chat.run_tools import build_run_tools
from harness.chat.state import HarnessState
from harness.config import Settings
from harness.model.retry import should_retry
from harness.tools.offload import build_offload
from harness.tools.registry import build_tools

MODEL_NODE = "call_model"
TOOLS_NODE = "tools"
COMPACT_NODE = "compact"


def build_graph(
    model: BaseChatModel,
    settings: Settings,
    checkpointer: BaseCheckpointSaver | None = None,
    cwd: Path | None = None,
):
    root = cwd or Path.cwd()
    system_prompt = build_system_prompt(settings, root)
    tools = build_tools(root, settings.shell_timeout_seconds, settings.skills_dir)
    bound = model.bind_tools(tools)
    offload = build_offload(root, settings.tool_output_limit_characters, settings.tool_output_dir)

    def call_model(state: HarnessState) -> dict:
        todos_prompt = build_todos_prompt(state.get("todos") or [])
        messages = [
            SystemMessage(content=f"{system_prompt}\n\n{todos_prompt}"),
            *state["messages"],
        ]
        response = bound.invoke(messages)
        return {"messages": [response]}

    def route_start(state: HarnessState) -> str:
        if over_budget(state["messages"], settings.compact_at_tokens):
            return COMPACT_NODE
        return MODEL_NODE

    builder = StateGraph(HarnessState)
    retry = RetryPolicy(
        initial_interval=settings.retry_initial_seconds,
        backoff_factor=settings.retry_backoff_factor,
        max_attempts=settings.retry_attempts,
        jitter=True,
        retry_on=should_retry,
    )
    builder.add_node(MODEL_NODE, call_model, retry_policy=retry)
    builder.add_node(TOOLS_NODE, build_run_tools(tools, offload, settings.max_parallel_tools))
    builder.add_node(
        COMPACT_NODE, build_compact(model, build_summary_prompt(), settings), retry_policy=retry
    )
    builder.add_conditional_edges(START, route_start)
    builder.add_edge(COMPACT_NODE, MODEL_NODE)
    builder.add_conditional_edges(MODEL_NODE, tools_condition, {TOOLS_NODE: TOOLS_NODE, END: END})
    builder.add_edge(TOOLS_NODE, MODEL_NODE)
    return builder.compile(checkpointer=checkpointer or InMemorySaver())
