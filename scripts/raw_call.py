"""One direct call to the model over plain web requests.

Shows what we send and what comes back. The answer arrives in nested lists,
so we join the text pieces.
"""

import uuid

import httpx

from harness.config import load_settings


def main() -> None:
    settings = load_settings()
    session_id = f"harness-raw-{uuid.uuid4()}"
    resp = httpx.post(
        f"{settings.base_url}/responses",
        headers={
            "Authorization": f"Bearer {settings.api_key}",
            "x-opencode-session": session_id,
            "User-Agent": settings.user_agent,
        },
        json={"model": settings.model, "input": "Reply with exactly one word: pong"},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    texts = [
        part["text"]
        for item in data.get("output", [])
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    ]
    print("".join(texts) or data)


if __name__ == "__main__":
    main()
