"""Model transport: turn OpenCode Go into a LangChain chat model.

LangGraph does not care which vendor is behind the model as long as it gets
a LangChain `BaseChatModel`. This module is the single place that knows
about OpenCode Go's quirks (Responses API + mandatory session header), so
swapping providers later means changing only this file.
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from harness.config import Settings


def make_model(settings: Settings, session_id: str) -> BaseChatModel:
    """Build a chat model bound to one conversation.

    `session_id` becomes the `x-opencode-session` header: OpenCode uses it for
    routing and prompt caching, so one conversation must keep one id.
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

    Responses-API models may return `content` as a list of typed blocks
    instead of a string; the rest of the harness should not care.
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
