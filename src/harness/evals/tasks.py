"""The fixed tasks the suite runs and scores."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

TASKS_FILENAME = "tasks.toml"
TASKS_KEY = "tasks"


@dataclass(frozen=True)
class Task:
    name: str
    prompt: str
    expect: str
    files: dict[str, str] = field(default_factory=dict)


def load_tasks(path: Path | None = None) -> tuple[Task, ...]:
    """Read the task list from its TOML file."""
    source = path or Path(__file__).with_name(TASKS_FILENAME)
    with open(source, "rb") as handle:
        data = tomllib.load(handle)
    return tuple(
        Task(
            name=entry["name"],
            prompt=entry["prompt"],
            expect=entry["expect"],
            files=dict(entry.get("files", {})),
        )
        for entry in data[TASKS_KEY]
    )
