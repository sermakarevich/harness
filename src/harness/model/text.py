"""Reads plain text out of model replies.

Some replies arrive in pieces, so this joins the text pieces together.
The client file next to it builds the model itself.
"""

from __future__ import annotations

from langchain_core.messages import BaseMessage


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
