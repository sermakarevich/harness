"""Reading back saved conversations."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import HumanMessage

NO_MESSAGE = "(empty)"
SHORT_ID_LENGTH = 8


def short_id(session_id: str) -> str:
    return session_id[-SHORT_ID_LENGTH:]


@dataclass(frozen=True)
class SavedSession:
    session_id: str
    started: str
    first_message: str


def first_user_text(messages: list) -> str:
    for message in messages:
        if isinstance(message, HumanMessage):
            content = message.content
            text = content if isinstance(content, str) else str(content)
            return text if text else NO_MESSAGE
    return NO_MESSAGE


def saved_sessions(checkpointer, limit: int) -> list[SavedSession]:
    """List recent saved conversations, newest first."""
    found: list[SavedSession] = []
    seen: set[str] = set()
    for item in checkpointer.list(None):
        session_id = item.config["configurable"]["thread_id"]
        if session_id in seen:
            continue
        seen.add(session_id)
        messages = item.checkpoint["channel_values"].get("messages", [])
        found.append(
            SavedSession(
                session_id=session_id,
                started=item.checkpoint["ts"],
                first_message=first_user_text(messages),
            )
        )
        if len(found) >= limit:
            break
    return found
