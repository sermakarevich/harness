"""Offer saved conversations as a numbered choice."""

from __future__ import annotations

import re

NOTHING_SAVED = "nothing saved yet"
PREVIEW_WIDTH = 60


def shorten_preview(text: str) -> str:
    single = re.sub(r"\s+", " ", text)
    return single if len(single) <= PREVIEW_WIDTH else single[:PREVIEW_WIDTH] + "…"


def show_sessions(console, sessions) -> None:
    """Print saved conversations newest first so one can be picked."""
    if not sessions:
        console.print(NOTHING_SAVED)
        return
    for number, saved in enumerate(sessions, start=1):
        console.print(
            f"  {number} {saved.session_id[-8:]} {saved.started} "
            f"{shorten_preview(saved.first_message)}",
            markup=False,
            highlight=False,
        )


def pick_session(sessions, argument: str):
    """Turn the typed number into one of the listed conversations."""
    if not argument or not argument.strip().isdigit():
        return None
    number = int(argument.strip())
    if number < 1 or number > len(sessions):
        return None
    return sessions[number - 1]
