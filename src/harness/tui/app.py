"""Terminal chat: read a line, show the reply, repeat."""

import sys
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

from harness.chat.session import Session
from harness.config import Settings
from harness.tui import commands, render
from harness.tui.commands import Command

PROMPT = "> "


class App:
    def __init__(self, settings: Settings, console=None, cwd=None, model=None):
        self.settings = settings
        self.console = console or Console()
        self.cwd = cwd or Path.cwd()
        self._model = model
        self.checkpointer = InMemorySaver()
        self.session = self._new_session()

    def _new_session(self) -> Session:
        return Session.start(self.settings, self.checkpointer, self.cwd, model=self._model)

    def handle_command(self, line: str) -> bool:
        return commands.handle_command(self, line)

    def run_turn(self, text: str) -> None:
        """Send one user message and show the reply as it arrives."""
        render.run_turn(self, text)

    def banner(self) -> None:
        self.console.print(
            f"[bold]harness[/bold] · model [cyan]{self.settings.model}[/cyan] · "
            f"session [dim]{self.session.session_id[-8:]}[/dim] · {Command.HELP} for commands"
        )

    def run(self) -> None:
        self.banner()
        interactive = sys.stdin.isatty()
        prompt = PromptSession(history=InMemoryHistory()) if interactive else None
        while True:
            try:
                line = prompt.prompt(PROMPT) if prompt else input(PROMPT)
            except (EOFError, KeyboardInterrupt):
                self.console.print()
                break
            if not interactive:
                self.console.print(line, markup=False, highlight=False)
            if not line.strip():
                continue
            if line.startswith(commands.COMMAND_PREFIX):
                if not self.handle_command(line):
                    break
                continue
            self.run_turn(line)
