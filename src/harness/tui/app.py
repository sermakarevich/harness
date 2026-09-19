"""Terminal chat: read a line, show the reply, repeat."""

import sys
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

from harness.chat.session import Session
from harness.chat.sessions import saved_sessions, short_id
from harness.chat.store import open_store
from harness.config import Settings
from harness.tui import commands, render
from harness.tui.commands import Command

PROMPT = "> "


class App:
    def __init__(self, settings: Settings, console=None, cwd=None, model=None, checkpointer=None):
        self.settings = settings
        self.console = console or Console()
        self.cwd = cwd or Path.cwd()
        self._model = model
        self._prompt = None
        self.checkpointer = checkpointer or open_store(self.settings.sessions_db)
        self.session = self._new_session()

    def _new_session(self) -> Session:
        return Session.start(self.settings, self.checkpointer, self.cwd, model=self._model)

    def resume_session(self, session_id: str) -> None:
        self.session = Session.resume(
            self.settings, session_id, self.checkpointer, self.cwd, model=self._model
        )

    def saved(self, limit: int):
        """Return recent saved conversations, newest first."""
        return saved_sessions(self.checkpointer, limit)

    def handle_command(self, line: str) -> bool:
        return commands.handle_command(self, line)

    def run_turn(self, text: str) -> None:
        """Send one user message and show the reply as it arrives."""
        render.run_turn(self, text)

    def banner(self) -> None:
        self.console.print(
            f"[bold]harness[/bold] · model [cyan]{self.settings.model}[/cyan] · "
            f"session [dim]{short_id(self.session.session_id)}[/dim] · {Command.HELP} for commands"
        )

    def read_line(self, prompt_text: str) -> str:
        """Read one line, echoing it when the input is not a terminal."""
        if self._prompt is not None:
            return self._prompt.prompt(prompt_text)
        line = input(prompt_text)
        self.console.print(line, markup=False, highlight=False)
        return line

    def run(self) -> None:
        self.banner()
        interactive = sys.stdin.isatty()
        self._prompt = PromptSession(history=InMemoryHistory()) if interactive else None
        while True:
            try:
                line = self.read_line(PROMPT)
            except (EOFError, KeyboardInterrupt):
                self.console.print()
                break
            if not line.strip():
                continue
            if line.startswith(commands.COMMAND_PREFIX):
                if not self.handle_command(line):
                    break
                continue
            self.run_turn(line)
