"""Builds the opening message for the model.

It says who the assistant is and what is true today. Later steps add tool
and memory details here.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from harness.config import Settings


def build_system_prompt(settings: Settings, cwd: Path | None = None) -> str:
    """Build the opening message from the text file on disk."""
    template = (Path(__file__).parent / "prompts" / "system.txt").read_text().strip()
    return template.format(today=date.today().isoformat(), cwd=cwd or Path.cwd())
