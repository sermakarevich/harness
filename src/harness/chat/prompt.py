"""Builds the opening message for the model.

It says who the assistant is and what is true today. Later steps add tool
and memory details here.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from harness.chat.memory import build_notes
from harness.config import Settings
from harness.tools.skills import skill_index
from harness.tools.todos import EMPTY_TODOS, Todo, todo_lines

PROMPTS_DIR = Path(__file__).parent / "prompts"
SYSTEM_PROMPT_FILE = "system.txt"
SUMMARY_PROMPT_FILE = "summary.txt"
MEMORY_PROMPT_FILE = "memory.txt"
SKILLS_PROMPT_FILE = "skills.txt"
TODOS_PROMPT_FILE = "todos.txt"
HELPER_PROMPT_FILE = "helper.txt"


def build_system_prompt(settings: Settings, cwd: Path | None = None) -> str:
    template = (PROMPTS_DIR / SYSTEM_PROMPT_FILE).read_text().strip()
    root = cwd or Path.cwd()
    base = template.format(today=date.today().isoformat(), cwd=root)
    prompt = base
    notes = build_notes(root, settings.memory_file_names)
    if notes:
        framing = (PROMPTS_DIR / MEMORY_PROMPT_FILE).read_text().strip()
        prompt = f"{prompt}\n\n{framing.format(notes=notes)}"
    index = skill_index(root, settings.skills_dir)
    if index:
        framing = (PROMPTS_DIR / SKILLS_PROMPT_FILE).read_text().strip()
        prompt = f"{prompt}\n\n{framing.format(skills=index)}"
    return prompt


def build_summary_prompt() -> str:
    return (PROMPTS_DIR / SUMMARY_PROMPT_FILE).read_text().strip()


def build_todos_prompt(todos: list[Todo]) -> str:
    """Frame the stored task list for the model."""
    framing = (PROMPTS_DIR / TODOS_PROMPT_FILE).read_text().strip()
    return framing.format(todos=todo_lines(todos) or EMPTY_TODOS)


def build_helper_prompt(job: str) -> str:
    """Frame one job as the first message a helper sees."""
    framing = (PROMPTS_DIR / HELPER_PROMPT_FILE).read_text().strip()
    return framing.format(job=job)
