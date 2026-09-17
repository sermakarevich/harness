"""The agent loop as a LangGraph graph.

Right now the graph is one node: `call_model`, which prepends the system
prompt and asks the model for the next message. A checkpointer stores the
messages per `thread_id`, so the same session id yields the same
conversation. Tools, approval gates and compaction become extra nodes here.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from harness.config import Settings
from harness.prompt import build_system_prompt
from harness.state import HarnessState


def new_session_id() -> str:
    """One id per conversation; doubles as LangGraph thread_id and OpenCode session header."""
    return f"harness-{uuid.uuid4()}"


def thread_config(session_id: str) -> dict:
    """The `config` LangGraph needs to find this conversation's checkpoint."""
    return {"configurable": {"thread_id": session_id}}


def build_graph(
    model: BaseChatModel,
    settings: Settings,
    checkpointer: BaseCheckpointSaver | None = None,
    cwd: Path | None = None,
):
    system_prompt = build_system_prompt(settings, cwd)

    def call_model(state: HarnessState) -> dict:
        messages = [SystemMessage(content=system_prompt), *state["messages"]]
        response = model.invoke(messages)
        return {"messages": [response]}

    builder = StateGraph(HarnessState)
    builder.add_node("call_model", call_model)
    builder.add_edge(START, "call_model")
    builder.add_edge("call_model", END)
    return builder.compile(checkpointer=checkpointer or InMemorySaver())
