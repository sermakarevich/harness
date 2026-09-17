"""Terminal chat: read a line, stream the model's reply, repeat.

Rendering is split into three seams so later chapters can grow it without
rewriting: `handle_command` (slash commands such as /new), `run_turn`
(send one user message through the graph), and `render_event` (how each
streamed graph event is shown — tool calls and approvals arrive here later).
"""

from __future__ import annotations

import sys
from pathlib import Path

from langchain_core.messages import AIMessageChunk, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

from harness.config import Settings
from harness.model import text_of
from harness.session import Session

HELP = """Commands:
  /new    start a fresh conversation (new session id)
  /help   show this help
  /exit   quit (also Ctrl-D)"""


class App:
    def __init__(
        self,
        settings: Settings,
        console: Console | None = None,
        cwd: Path | None = None,
        model=None,
    ):
        self.settings = settings
        self.console = console or Console()
        self.cwd = cwd or Path.cwd()
        self._model = model  # injected in tests only
        # One checkpointer for the whole app: /new starts a new thread inside it,
        # so earlier conversations stay resumable later (persistence to disk is a later chapter).
        self.checkpointer = InMemorySaver()
        self.session = self._new_session()

    # --- seams -----------------------------------------------------------------

    def _new_session(self) -> Session:
        return Session.start(self.settings, self.checkpointer, self.cwd, model=self._model)

    def handle_command(self, line: str) -> bool:
        """Handle a /command. Returns False when the app should exit."""
        cmd = line.strip().split()[0].lower()
        if cmd in ("/exit", "/quit"):
            return False
        if cmd == "/new":
            self.session = self._new_session()
            self.console.print(f"[dim]new session {self.session.session_id}[/dim]")
        elif cmd == "/help":
            self.console.print(HELP)
        else:
            self.console.print(f"[red]unknown command {cmd}[/red] — try /help")
        return True

    def run_turn(self, text: str) -> None:
        """Send one user message through the graph and stream the reply."""
        events = self.session.graph.stream(
            {"messages": [HumanMessage(content=text)]},
            self.session.config,
            stream_mode="messages",
        )
        try:
            for message, meta in events:
                self.render_event(message, meta)
        except Exception as exc:  # network / API errors must not kill the chat
            self.console.print(f"\n[red]error:[/red] {type(exc).__name__}: {exc}")
        finally:
            self.console.print()  # end the streamed line

    def render_event(self, message, meta: dict) -> None:
        """Show one streamed event. Today: print assistant tokens as they arrive."""
        if isinstance(message, AIMessageChunk):
            self.console.print(
                text_of(message), end="", markup=False, highlight=False, soft_wrap=True
            )

    # --- main loop -------------------------------------------------------------

    def banner(self) -> None:
        self.console.print(
            f"[bold]harness[/bold] · model [cyan]{self.settings.model}[/cyan] · "
            f"session [dim]{self.session.session_id[-8:]}[/dim] · /help for commands"
        )

    def run(self) -> None:
        self.banner()
        interactive = sys.stdin.isatty()
        prompt = PromptSession(history=InMemoryHistory()) if interactive else None
        while True:
            try:
                line = prompt.prompt("> ") if prompt else input("> ")
            except (EOFError, KeyboardInterrupt):
                self.console.print()
                break
            if not line.strip():
                continue
            if line.startswith("/"):
                if not self.handle_command(line):
                    break
                continue
            self.run_turn(line)
