"""Reads plain text out of model replies.

Some replies arrive in pieces, so this joins the text pieces together.
The client file next to it builds the model itself.
"""

from __future__ import annotations

from enum import StrEnum

from langchain_core.messages import BaseMessage


class BlockType(StrEnum):
    """Content block kinds that carry plain text."""

    TEXT = "text"
    OUTPUT_TEXT = "output_text"


TEXT_KEY = "text"
TYPE_KEY = "type"


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
        elif isinstance(block, dict) and block.get(TYPE_KEY) in (
            BlockType.TEXT,
            BlockType.OUTPUT_TEXT,
        ):
            parts.append(block.get(TEXT_KEY, ""))
    return "".join(parts)
