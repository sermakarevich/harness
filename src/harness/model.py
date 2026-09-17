"""Turns the model server into a chat model we can use.

This is the only place that knows the server details. To use another
provider, change only this file.
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from harness.config import Settings


def make_model(settings: Settings, session_id: str) -> BaseChatModel:
    """Build a chat model tied to one conversation.

    The session id travels with each request so replies stay in the same
    conversation.
    """
    return ChatOpenAI(
        model=settings.model,
        api_key=settings.api_key,
        base_url=settings.base_url,
        use_responses_api=True,
        default_headers={
            "x-opencode-session": session_id,
            "User-Agent": settings.user_agent,
        },
    )


def text_of(message: BaseMessage) -> str:
    """Return the plain text of a message.

    Some replies arrive in pieces, so we join the text pieces together.
    """
    content = message.content
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") in ("text", "output_text"):
            parts.append(block.get("text", ""))
    return "".join(parts)
