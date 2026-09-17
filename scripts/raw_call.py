"""Chapter 1: one pure LLM call with plain HTTP, no framework.

Shows exactly what goes over the wire to OpenCode Go: the Responses API body
and the two mandatory headers. Everything later in the harness is built on
this one request/response pair.
"""

import uuid

import httpx

from harness.config import load_settings


def main() -> None:
    s = load_settings()
    session_id = f"harness-raw-{uuid.uuid4()}"
    resp = httpx.post(
        f"{s.base_url}/responses",
        headers={
            "Authorization": f"Bearer {s.api_key}",
            "x-opencode-session": session_id,
            "User-Agent": s.user_agent,
        },
        json={"model": s.model, "input": "Reply with exactly one word: pong"},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    # Responses API: output is a list of items; text lives in output[i].content[j].text
    texts = [
        part["text"]
        for item in data.get("output", [])
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    ]
    print("".join(texts) or data)


if __name__ == "__main__":
    main()
