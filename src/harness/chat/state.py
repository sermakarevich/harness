"""Conversation memory for the harness.

It holds the messages so far. Later steps add one field at a time as the
harness grows.
"""

from langgraph.graph import MessagesState


class HarnessState(MessagesState):
    """Conversation state; currently only `messages`."""
