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

from harness.chat.prompt import build_system_prompt
from harness.chat.run_tools import build_run_tools
from harness.chat.state import HarnessState
from harness.config import Settings
from harness.tools.offload import build_offload
from harness.tools.registry import build_tools

MODEL_NODE = "call_model"
TOOLS_NODE = "tools"


def build_graph(
    model: BaseChatModel,
    settings: Settings,
    checkpointer: BaseCheckpointSaver | None = None,
    cwd: Path | None = None,
):
    root = cwd or Path.cwd()
    system_prompt = build_system_prompt(settings, root)
    tools = build_tools(root, settings.shell_timeout_seconds)
    bound = model.bind_tools(tools)
    offload = build_offload(root, settings.tool_output_limit_characters, settings.tool_output_dir)

    def call_model(state: HarnessState) -> dict:
        messages = [SystemMessage(content=system_prompt), *state["messages"]]
        response = bound.invoke(messages)
        return {"messages": [response]}

    builder = StateGraph(HarnessState)
    builder.add_node(MODEL_NODE, call_model)
    builder.add_node(TOOLS_NODE, build_run_tools(tools, offload))
    builder.add_edge(START, MODEL_NODE)
    builder.add_conditional_edges(MODEL_NODE, tools_condition, {TOOLS_NODE: TOOLS_NODE, END: END})
    builder.add_edge(TOOLS_NODE, MODEL_NODE)
    return builder.compile(checkpointer=checkpointer or InMemorySaver())
