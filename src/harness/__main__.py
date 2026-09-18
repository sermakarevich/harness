"""Runs two prompts as two requests and prints both replies."""

from __future__ import annotations

import sys

from harness.config import ConfigError, load_settings
from harness.model.client import ask, new_session_id
from harness.model.text import output_types, text_of

PROMPTS = (
    "Remember this word: pelican",
    "Which word did I ask you to remember? Answer with the word only.",
)
ECHO_PREFIX = "> "
BLOCKS_LINE = "blocks: {kinds}"


def main() -> int:
    """Send both prompts and show the model keeps nothing between them."""
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2
    session_id = new_session_id()
    for prompt in PROMPTS:
        print(ECHO_PREFIX + prompt)
        reply = ask(settings, session_id, prompt)
        print(text_of(reply))
        print(BLOCKS_LINE.format(kinds=", ".join(output_types(reply))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
