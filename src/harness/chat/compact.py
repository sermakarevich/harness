"""Replaces older turns with one summary once the conversation grows too big."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES, RemoveMessage

from harness.chat.state import HarnessState
from harness.chat.usage import dollars, usage_of
from harness.config import Settings


def context_tokens(messages: list) -> int:
    """Size of the conversation as the model last saw it."""
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.usage_metadata:
            return message.usage_metadata.get("input_tokens", 0)
    return 0


def over_budget(messages: list, limit_tokens: int) -> bool:
    """Whether the conversation has grown past its token budget."""
    return context_tokens(messages) > limit_tokens


def split_at_turn(messages: list, keep_turns: int) -> tuple[list, list]:
    """Split the conversation into the part to summarise and the part to keep."""
    starts = [index for index, message in enumerate(messages) if isinstance(message, HumanMessage)]
    if len(starts) <= keep_turns:
        return [], list(messages)
    cut = starts[-keep_turns] if keep_turns > 0 else len(messages)
    return list(messages[:cut]), list(messages[cut:])


def build_compact(model, prompt: str, settings: Settings):
    """Build the node that swaps older turns for one summary."""

    def compact(state: HarnessState) -> dict:
        head, tail = split_at_turn(state["messages"], settings.keep_recent_turns)
        if not head:
            return {}
        reply = model.invoke([SystemMessage(content=prompt), *head])
        return {
            "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), reply, *tail],
            "carried_cost": dollars(usage_of(head), settings),
        }

    return compact
