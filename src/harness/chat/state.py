"""Conversation memory for the harness."""

from operator import add
from typing import Annotated

from langgraph.graph import MessagesState


class HarnessState(MessagesState):
    always_allowed: Annotated[list[str], add]
