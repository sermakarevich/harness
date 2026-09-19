"""Saved conversations live in a SQLite file on disk."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver


def open_store(path: str | Path) -> SqliteSaver:
    """Open the saved conversation store, creating its folder if needed."""
    target = Path(path)
    if target.parent != Path():
        target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(target), check_same_thread=False)
    return SqliteSaver(connection)
