"""Commands for the terminal chat."""

from __future__ import annotations

from enum import StrEnum

COMMAND_PREFIX = "/"


class Command(StrEnum):
    NEW = f"{COMMAND_PREFIX}new"
    HELP = f"{COMMAND_PREFIX}help"
    EXIT = f"{COMMAND_PREFIX}exit"
    QUIT = f"{COMMAND_PREFIX}quit"


COMMAND_HELP = {
    Command.NEW: "start a fresh conversation (new session id)",
    Command.HELP: "show this help",
    Command.EXIT: "quit (also Ctrl-D)",
}


def help_text() -> str:
    lines = [f"  {cmd:<8}{text}" for cmd, text in COMMAND_HELP.items()]
    return "Commands:\n" + "\n".join(lines)


def handle_command(app, line: str) -> bool:
    cmd = line.strip().split()[0].lower()
    if cmd in (Command.EXIT, Command.QUIT):
        return False
    if cmd == Command.NEW:
        app.session = app._new_session()
        app.console.print(f"[dim]new session {app.session.session_id}[/dim]")
    elif cmd == Command.HELP:
        app.console.print(help_text())
    else:
        app.console.print(f"[red]unknown command {cmd}[/red] — try {Command.HELP}")
    return True
