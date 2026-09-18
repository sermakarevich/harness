"""A chat whose memory is a plain list of messages, kept by hand."""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterable, Iterator

from langchain_core.messages import HumanMessage, SystemMessage

from harness.chat.prompt import build_system_prompt
from harness.config import load_settings
from harness.model.client import make_model
from harness.model.text import text_of

NEW_COMMAND = "/new"
SESSION_ID_PREFIX = "harness-list-"
ECHO_PREFIX = "> "
CONTEXT_LINE = "context: {count} messages"
NEW_NOTICE = "new conversation"


def chat(model, system_prompt: str, lines: Iterable[str]) -> Iterator[tuple[str, int]]:
    """Run one chat, resending the whole message list every turn."""
    messages = [SystemMessage(content=system_prompt)]
    for line in lines:
        if not line:
            continue
        if line == NEW_COMMAND:
            messages = [SystemMessage(content=system_prompt)]
            yield NEW_NOTICE, len(messages)
            continue
        messages.append(HumanMessage(content=line))
        reply = model.invoke(messages)
        messages.append(reply)
        yield text_of(reply), len(messages)


def main() -> None:
    """Read stdin lines, echo each, and print every reply with its size."""

    def echoed(lines: Iterable[str]) -> Iterator[str]:
        for line in lines:
            print(f"{ECHO_PREFIX}{line}")
            yield line

    settings = load_settings()
    model = make_model(settings, f"{SESSION_ID_PREFIX}{uuid.uuid4()}")
    system_prompt = build_system_prompt(settings)
    lines = (line.strip() for line in sys.stdin)
    for text, count in chat(model, system_prompt, echoed(lines)):
        print(text)
        print(CONTEXT_LINE.format(count=count))


if __name__ == "__main__":
    main()
