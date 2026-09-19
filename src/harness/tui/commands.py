"""Commands for the terminal chat."""

from __future__ import annotations

from enum import StrEnum

from harness.tui.pick import pick_session, show_sessions

COMMAND_PREFIX = "/"

RESUME_LIST_LIMIT = 10


class Command(StrEnum):
    NEW = f"{COMMAND_PREFIX}new"
    RESUME = f"{COMMAND_PREFIX}resume"
    HELP = f"{COMMAND_PREFIX}help"
    EXIT = f"{COMMAND_PREFIX}exit"
    QUIT = f"{COMMAND_PREFIX}quit"


COMMAND_HELP = {
    Command.NEW: "start a fresh conversation (new session id)",
    Command.RESUME: "list saved conversations and continue one by number",
    Command.HELP: "show this help",
    Command.EXIT: "quit (also Ctrl-D)",
}


def help_text() -> str:
    lines = [f"  {cmd:<8}{text}" for cmd, text in COMMAND_HELP.items()]
    return "Commands:\n" + "\n".join(lines)


def handle_command(app, line: str) -> bool:
    parts = line.strip().split(None, 1)
    cmd = parts[0].lower()
    rest = parts[1].strip() if len(parts) > 1 else ""
    if cmd in (Command.EXIT, Command.QUIT):
        return False
    if cmd == Command.NEW:
        app.session = app._new_session()
        app.console.print(f"[dim]new session {app.session.session_id}[/dim]")
    elif cmd == Command.RESUME:
        sessions = app.saved(RESUME_LIST_LIMIT)
        if not rest:
            show_sessions(app.console, sessions)
        else:
            chosen = pick_session(sessions, rest)
            if chosen is None:
                app.console.print(f"[red]no saved session {rest}[/red]")
            else:
                app.resume_session(chosen.session_id)
                app.console.print(f"[dim]resumed session {chosen.session_id}[/dim]")
    elif cmd == Command.HELP:
        app.console.print(help_text())
    else:
        app.console.print(f"[red]unknown command {cmd}[/red] — try {Command.HELP}")
    return True
