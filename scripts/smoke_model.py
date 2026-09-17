"""Live smoke test for model.py: one invoke, one stream. Run via `just smoke`."""

import uuid

from harness.config import load_settings
from harness.model import make_model, text_of


def main() -> None:
    settings = load_settings()
    model = make_model(settings, session_id=f"harness-smoke-{uuid.uuid4()}")

    reply = model.invoke("Reply with exactly one word: pong")
    print("invoke  :", text_of(reply))

    print("stream  : ", end="", flush=True)
    for chunk in model.stream("Count from 1 to 5, separated by spaces."):
        print(text_of(chunk), end="", flush=True)
    print()
    print("OK")


if __name__ == "__main__":
    main()
