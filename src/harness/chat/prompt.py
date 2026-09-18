"""Builds the opening message for the model.

It says who the assistant is and what is true today. Later steps add tool
and memory details here.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from harness.config import Settings


def build_system_prompt(settings: Settings, cwd: Path | None = None) -> str:
    cwd = cwd or Path.cwd()
    return (
        "You are a helpful assistant running inside a terminal chat harness.\n"
        f"Today is {date.today().isoformat()}. The user's working directory is {cwd}.\n"
        "Answer concisely in plain language; use Markdown only when it helps."
    )
