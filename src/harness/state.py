"""Graph state: what the harness remembers while a conversation runs.

`MessagesState` already gives us a `messages` list with an append-style
reducer (new messages are added, not replaced). Later chapters add fields
here (token usage, todo list, working-directory facts) — one field per
harness job, never a grab bag.
"""

from langgraph.graph import MessagesState


class HarnessState(MessagesState):
    """Conversation state; currently only `messages`."""
