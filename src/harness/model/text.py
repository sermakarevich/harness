"""Reads plain text out of model replies.

Some replies arrive in pieces, so this joins the text pieces together.
"""

from __future__ import annotations

from enum import StrEnum

from langchain_core.messages import BaseMessage


class BlockType(StrEnum):
    TEXT = "text"
    OUTPUT_TEXT = "output_text"


TEXT_KEY = "text"
TYPE_KEY = "type"


def join_text(content) -> str:
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


def text_of(message: BaseMessage) -> str:
    """Join the text pieces of a reply together."""
    return join_text(message.content)
