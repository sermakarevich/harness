"""Token use and cost; cached input is part of the input, not an extra."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import AIMessage

from harness.config import Settings

TOKENS_PER_MILLION = 1_000_000


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0


def usage_of(messages: list) -> Usage:
    found = Usage()
    for message in messages:
        if not isinstance(message, AIMessage):
            continue
        meta = message.usage_metadata or {}
        if not meta:
            continue
        details_in = meta.get("input_token_details") or {}
        details_out = meta.get("output_token_details") or {}
        found = Usage(
            input_tokens=found.input_tokens + meta.get("input_tokens", 0),
            cached_input_tokens=found.cached_input_tokens + details_in.get("cache_read", 0),
            output_tokens=found.output_tokens + meta.get("output_tokens", 0),
            reasoning_tokens=found.reasoning_tokens + details_out.get("reasoning", 0),
        )
    return found


def dollars(usage: Usage, settings: Settings) -> float:
    full_rate = usage.input_tokens - usage.cached_input_tokens
    return (
        full_rate * settings.input_price_per_million
        + usage.cached_input_tokens * settings.cached_input_price_per_million
        + usage.output_tokens * settings.output_price_per_million
    ) / TOKENS_PER_MILLION
