"""Settings: where the model lives and the key that lets us in.

Reads the key from the environment so it never leaks into logs. We also send
our own app name with each request because the server blocks generic names.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ENV_API_KEY = "OPENCODE_API_KEY"
ENV_BASE_URL = "HARNESS_BASE_URL"
ENV_MODEL = "HARNESS_MODEL"
ENV_USER_AGENT = "HARNESS_USER_AGENT"


class ConfigError(RuntimeError):
    """Raised when a required setting is missing."""


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    base_url: str = "https://opencode.ai/zen/go/v1"
    model: str = "muse-spark-1.3-contributor"
    user_agent: str = "harness-dev/0.1"


def load_settings(env_file: str | Path | None = None) -> Settings:
    """Read settings from the environment and return them."""
    load_dotenv(env_file, override=False)
    api_key = os.environ.get(ENV_API_KEY, "").strip()
    if not api_key:
        raise ConfigError(
            "OPENCODE_API_KEY is not set. Copy .env.example to .env and add your OpenCode Go key."
        )
    return Settings(
        api_key=api_key,
        base_url=os.environ.get(ENV_BASE_URL, Settings.base_url),
        model=os.environ.get(ENV_MODEL, Settings.model),
        user_agent=os.environ.get(ENV_USER_AGENT, Settings.user_agent),
    )
