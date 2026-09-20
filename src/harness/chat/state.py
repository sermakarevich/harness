"""Conversation memory for the harness."""

from operator import add
from typing import Annotated

from langgraph.graph import MessagesState

from harness.tools.todos import Todo


class HarnessState(MessagesState):
    always_allowed: Annotated[list[str], add]
    carried_cost: Annotated[float, add]
    todos: list[Todo]
