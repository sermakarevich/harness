"""Instruction files found in the working directory and above it.

Turns the small set of standing notes into one block of text for the prompt.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

NOTE_MARKER = "--- {path} ---"


def memory_paths(cwd: Path, file_names: Sequence[str]) -> list[Path]:
    """Instruction files from the working directory up, farthest first."""
    found: list[Path] = []
    for directory in [cwd, *cwd.parents]:
        for name in file_names:
            candidate = directory / name
            if candidate.is_file():
                found.append(candidate)
                break
    return list(reversed(found))


def short_path(path: Path, cwd: Path) -> str:
    """Path relative to the work tree when inside it, plain path otherwise."""
    try:
        return str(path.relative_to(cwd))
    except ValueError:
        return str(path)


def build_notes(cwd: Path, file_names: Sequence[str]) -> str:
    """All instruction files joined under lines naming them."""
    blocks = []
    for path in memory_paths(cwd, file_names):
        blocks.append(f"{NOTE_MARKER.format(path=short_path(path, cwd))}\n{path.read_text()}")
    return "\n\n".join(blocks)
