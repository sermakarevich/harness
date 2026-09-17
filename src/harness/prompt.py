"""System prompt assembly.

The system prompt is where the harness tells the model who it is and what
it may assume. Today it is three lines; later chapters append tool
descriptions, project memory and skill listings here, so keep it a
function, not a constant.
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
