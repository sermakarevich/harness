"""Turns the model server into a chat model we can use.

This is the only place that knows the server details. To use another
provider, change only this file.
"""

from __future__ import annotations

import uuid

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from harness.config import Settings

SESSION_HEADER = "x-opencode-session"
USER_AGENT_HEADER = "User-Agent"
SESSION_ID_PREFIX = "harness-"


def new_session_id() -> str:
    """Make a fresh session id for one run."""
    return f"{SESSION_ID_PREFIX}{uuid.uuid4()}"


def make_model(settings: Settings, session_id: str) -> BaseChatModel:
    """Build a chat model tied to one conversation."""
    return ChatOpenAI(
        model=settings.model,
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=settings.timeout_seconds,
        use_responses_api=True,
        default_headers={
            SESSION_HEADER: session_id,
            USER_AGENT_HEADER: settings.user_agent,
        },
    )
