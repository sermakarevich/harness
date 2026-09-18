"""Reads the block kinds and the plain text out of a reply."""

from __future__ import annotations

from enum import StrEnum


class BlockType(StrEnum):
    REASONING = "reasoning"
    MESSAGE = "message"
    OUTPUT_TEXT = "output_text"


def output_types(response: dict) -> list[str]:
    """List the kind of every block in a reply."""
    return [str(item.get("type", "")) for item in response.get("output", [])]


def text_of(response: dict) -> str:
    """Join the plain text pieces of a reply."""
    parts: list[str] = []
    for item in response.get("output", []):
        for part in item.get("content", []):
            if part.get("type") == BlockType.OUTPUT_TEXT:
                parts.append(part.get("text", ""))
    return "".join(parts)
