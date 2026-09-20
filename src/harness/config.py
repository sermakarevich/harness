"""Settings: where the model lives and the key that lets us in.

Reads the key from the environment so it never leaks into logs. We also send
our own app name with each request because the server blocks generic names.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from dynaconf import Dynaconf, ValidationError, Validator

SETTINGS_FILENAME = "settings.toml"
ENV_PREFIX = "HARNESS"
MISSING_KEY_MESSAGE = (
    "HARNESS_API_KEY is not set. Copy .env.example to .env and add your OpenCode Go key."
)


class ConfigError(RuntimeError):
    """Raised when a required setting is missing."""


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    base_url: str
    model: str
    user_agent: str
    timeout_seconds: int
    shell_timeout_seconds: int
    sessions_db: str = ".harness/sessions.db"
    input_price_per_million: float = 0.1
    cached_input_price_per_million: float = 0.002
    output_price_per_million: float = 0.2
    tool_output_limit_characters: int = 2000
    tool_output_dir: str = ".harness/outputs"
    compact_at_tokens: int = 4000
    keep_recent_turns: int = 2
    memory_file_names: tuple[str, ...] = ("AGENTS.md", "CLAUDE.md")
    skills_dir: str = "skills"
    retry_attempts: int = 3
    retry_initial_seconds: float = 1.0
    retry_backoff_factor: float = 2.0
    max_parallel_tools: int = 4


def load_settings(env_file: str | Path | None = None) -> Settings:
    options: dict[str, object] = {
        "envvar_prefix": ENV_PREFIX,
        "settings_files": [Path(__file__).with_name(SETTINGS_FILENAME)],
        "environments": False,
        "load_dotenv": True,
        "dotenv_override": False,
    }
    if env_file is not None:
        options["dotenv_path"] = env_file
    settings = Dynaconf(**options)
    settings.validators.register(Validator("API_KEY", must_exist=True, ne=""))
    try:
        settings.validators.validate()
    except ValidationError as exc:
        raise ConfigError(MISSING_KEY_MESSAGE) from exc
    api_key = str(settings.api_key).strip()
    if not api_key:
        raise ConfigError(MISSING_KEY_MESSAGE)
    return Settings(
        api_key=api_key,
        base_url=settings.base_url,
        model=settings.model,
        user_agent=settings.user_agent,
        timeout_seconds=settings.timeout_seconds,
        shell_timeout_seconds=settings.shell_timeout_seconds,
        sessions_db=settings.sessions_db,
        input_price_per_million=settings.input_price_per_million,
        cached_input_price_per_million=settings.cached_input_price_per_million,
        output_price_per_million=settings.output_price_per_million,
        tool_output_limit_characters=settings.tool_output_limit_characters,
        tool_output_dir=settings.tool_output_dir,
        compact_at_tokens=settings.compact_at_tokens,
        keep_recent_turns=settings.keep_recent_turns,
        memory_file_names=tuple(settings.memory_file_names),
        skills_dir=settings.skills_dir,
        retry_attempts=settings.retry_attempts,
        retry_initial_seconds=settings.retry_initial_seconds,
        retry_backoff_factor=settings.retry_backoff_factor,
        max_parallel_tools=settings.max_parallel_tools,
    )
