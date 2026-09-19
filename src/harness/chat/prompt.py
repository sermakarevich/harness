"""Builds the opening message for the model.

It says who the assistant is and what is true today. Later steps add tool
and memory details here.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from harness.config import Settings

PROMPTS_DIR = Path(__file__).parent / "prompts"
SYSTEM_PROMPT_FILE = "system.txt"
SUMMARY_PROMPT_FILE = "summary.txt"


def build_system_prompt(settings: Settings, cwd: Path | None = None) -> str:
    template = (PROMPTS_DIR / SYSTEM_PROMPT_FILE).read_text().strip()
    return template.format(today=date.today().isoformat(), cwd=cwd or Path.cwd())


def build_summary_prompt() -> str:
    return (PROMPTS_DIR / SUMMARY_PROMPT_FILE).read_text().strip()
