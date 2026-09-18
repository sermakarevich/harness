"""Send one plain web request to the model and print the reply."""

import uuid

import httpx

from harness.config import load_settings

PROMPT = "Reply with exactly one word: pong"
RESPONSES_PATH = "/responses"
HEADER_AUTHORIZATION = "Authorization"
HEADER_SESSION = "x-opencode-session"
HEADER_USER_AGENT = "User-Agent"
SESSION_ID_PREFIX = "harness-raw-"
PART_OUTPUT_TEXT = "output_text"


def output_types(response: dict) -> list[str]:
    """List the kind of every block in the reply."""
    return [item["type"] for item in response.get("output", [])]


def text_of(response: dict) -> str:
    """Join every text piece of the reply into one answer."""
    return "".join(
        part["text"]
        for item in response.get("output", [])
        for part in item.get("content", [])
        if part.get("type") == PART_OUTPUT_TEXT
    )


def main() -> None:
    """Send the prompt and print the reply blocks and text."""
    settings = load_settings()
    session_id = f"{SESSION_ID_PREFIX}{uuid.uuid4()}"
    reply = httpx.post(
        f"{settings.base_url}{RESPONSES_PATH}",
        headers={
            HEADER_AUTHORIZATION: f"Bearer {settings.api_key}",
            HEADER_SESSION: session_id,
            HEADER_USER_AGENT: settings.user_agent,
        },
        json={"model": settings.model, "input": PROMPT},
        timeout=settings.timeout_seconds,
    )
    reply.raise_for_status()
    data = reply.json()
    print(f"blocks: {', '.join(output_types(data))}")
    print(text_of(data))


if __name__ == "__main__":
    main()
