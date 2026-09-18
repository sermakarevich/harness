"""Turns the model server into a chat model we can use.

This is the only place that knows the server details. To use another
provider, change only this file.
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
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
