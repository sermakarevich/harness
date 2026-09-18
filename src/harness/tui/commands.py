"""Slash commands for the terminal chat.

Each line starting with a slash runs here. The app passes itself in
so commands can read settings and swap the current conversation.
"""

from __future__ import annotations

from enum import StrEnum


class Command(StrEnum):
    """Slash commands the terminal chat accepts."""

    NEW = "/new"
    HELP = "/help"
    EXIT = "/exit"
    QUIT = "/quit"


COMMAND_PREFIX = "/"

HELP = (
    "Commands:\n"
    f"  {Command.NEW}    start a fresh conversation (new session id)\n"
    f"  {Command.HELP}   show this help\n"
    f"  {Command.EXIT}   quit (also Ctrl-D)"
)


def handle_command(app, line: str) -> bool:
    """Run a slash command. Returns False when the app should quit."""
    cmd = line.strip().split()[0].lower()
    if cmd in (Command.EXIT, Command.QUIT):
        return False
    if cmd == Command.NEW:
        app.session = app._new_session()
        app.console.print(f"[dim]new session {app.session.session_id}[/dim]")
    elif cmd == Command.HELP:
        app.console.print(HELP)
    else:
        app.console.print(f"[red]unknown command {cmd}[/red] — try {Command.HELP}")
    return True
