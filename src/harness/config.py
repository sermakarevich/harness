"""Settings: where the model lives and how we authenticate.

Reads the OpenCode Go key from the environment (or a `.env` file in the
current directory). The key is deliberately excluded from `repr()` so it can
never leak into logs or error messages.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when a required setting is missing."""


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    base_url: str = "https://opencode.ai/zen/go/v1"
    model: str = "muse-spark-1.3-contributor"
    # OpenCode rejects generic library user agents; this identifies our client.
    user_agent: str = "harness-dev/0.1"


def load_settings(env_file: str | Path | None = None) -> Settings:
    """Load settings from `.env` (if present) and the process environment."""
    load_dotenv(env_file, override=False)
    api_key = os.environ.get("OPENCODE_API_KEY", "").strip()
    if not api_key:
        raise ConfigError(
            "OPENCODE_API_KEY is not set. Copy .env.example to .env and add your OpenCode Go key."
        )
    return Settings(
        api_key=api_key,
        base_url=os.environ.get("HARNESS_BASE_URL", Settings.base_url),
        model=os.environ.get("HARNESS_MODEL", Settings.model),
    )
