"""The only place that knows the model server.

To use another vendor, change only this file.
"""

from __future__ import annotations

import uuid

import httpx

from harness.config import Settings

RESPONSES_PATH = "/responses"
AUTHORIZATION_HEADER = "Authorization"
SESSION_HEADER = "x-opencode-session"
USER_AGENT_HEADER = "User-Agent"
BEARER_PREFIX = "Bearer"
SESSION_ID_PREFIX = "harness-"


def new_session_id() -> str:
    """Make a fresh session id for one run."""
    return f"{SESSION_ID_PREFIX}{uuid.uuid4()}"


def headers(settings: Settings, session_id: str) -> dict[str, str]:
    """Build the headers every model request must carry."""
    return {
        AUTHORIZATION_HEADER: f"{BEARER_PREFIX} {settings.api_key}",
        SESSION_HEADER: session_id,
        USER_AGENT_HEADER: settings.user_agent,
    }


def ask(settings: Settings, session_id: str, prompt: str) -> dict:
    """Send one prompt to the model and return the parsed reply."""
    response = httpx.post(
        f"{settings.base_url}{RESPONSES_PATH}",
        headers=headers(settings, session_id),
        json={"model": settings.model, "input": prompt},
        timeout=settings.timeout_seconds,
    )
    response.raise_for_status()
    return response.json()
