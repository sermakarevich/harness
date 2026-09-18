"""The terminal chat at this point.

Read a line, print the reply and the size of the list, repeat.
"""

from __future__ import annotations

import sys

from harness.chat.loop import Chat
from harness.chat.prompt import build_system_prompt
from harness.config import Settings
from harness.model.client import make_model, new_session_id
from harness.tui.commands import COMMAND_PREFIX, Command

PROMPT = "> "
CONTEXT_LINE = "context: {count} messages"
NEW_NOTICE = "new conversation"
UNKNOWN_COMMAND = "unknown command {command}"


class App:
    def __init__(self, settings: Settings, model=None):
        model = model or make_model(settings, new_session_id())
        self.chat = Chat(model, build_system_prompt(settings))

    def handle_command(self, line: str) -> None:
        if line == Command.NEW:
            self.chat.reset()
            print(NEW_NOTICE)
        else:
            print(UNKNOWN_COMMAND.format(command=line))

    def run_turn(self, text: str) -> None:
        print(self.chat.ask(text))
        print(CONTEXT_LINE.format(count=self.chat.size()))

    def run(self) -> None:
        while True:
            try:
                line = input(PROMPT)
            except EOFError:
                break
            if not sys.stdin.isatty():
                print(line)
            if not line.strip():
                continue
            if line.startswith(COMMAND_PREFIX):
                self.handle_command(line)
            else:
                self.run_turn(line)
