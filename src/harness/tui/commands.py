"""Slash commands for the terminal chat.

Each line starting with a slash runs here. The app passes itself in
so commands can read settings and swap the current conversation.
"""

from __future__ import annotations

HELP = """Commands:
  /new    start a fresh conversation (new session id)
  /help   show this help
  /exit   quit (also Ctrl-D)"""


def handle_command(app, line: str) -> bool:
    """Run a slash command. Returns False when the app should quit."""
    cmd = line.strip().split()[0].lower()
    if cmd in ("/exit", "/quit"):
        return False
    if cmd == "/new":
        app.session = app._new_session()
        app.console.print(f"[dim]new session {app.session.session_id}[/dim]")
    elif cmd == "/help":
        app.console.print(HELP)
    else:
        app.console.print(f"[red]unknown command {cmd}[/red] — try /help")
    return True
