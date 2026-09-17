"""The answer loop of the harness.

Today it asks the model once and returns the reply. Later steps add tools
and safety checks here.
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
    """Make a fresh id for a new conversation."""
    return f"harness-{uuid.uuid4()}"


def thread_config(session_id: str) -> dict:
    """Tell the harness which saved conversation to continue."""
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
