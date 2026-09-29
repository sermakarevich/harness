"""Plain text lines every front end prints."""

from __future__ import annotations

import re

from harness.chat.usage import Usage

TOOL_ARG_WIDTH = 60
PRICE_DECIMALS = 4
MEMORY_LINE = "memory: {names}"
SKILLS_LINE = "skills: {names}"
TOOL_ARROW = "→"
COMPACT_NOTICE = "Context over {budget} input tokens; older turns summarised."
ERROR_LINE = "error: {name}: {message}"


def shorten(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value))
    return text if len(text) <= TOOL_ARG_WIDTH else text[:TOOL_ARG_WIDTH] + "…"


def call_text(name: str, args: dict) -> str:
    """Text of one tool call for the terminal."""
    params = " ".join(f"{key}={shorten(value)}" for key, value in args.items())
    return f"{name} {params}".rstrip()


def tool_line(name: str, args: dict) -> str:
    """One tool call line for the terminal, with the leading arrow."""
    return f"{TOOL_ARROW} {call_text(name, args)}"


def cost_line(turn: Usage, total: Usage, turn_cost: float, total_cost: float) -> str:
    """Text of the token and cost line shown after each turn."""
    return (
        f"in {turn.input_tokens} (cached {turn.cached_input_tokens})"
        f" · out {turn.output_tokens} (thinking {turn.reasoning_tokens})"
        f" · turn ${turn_cost:.{PRICE_DECIMALS}f}"
        f" · total ${total_cost:.{PRICE_DECIMALS}f}"
    )
