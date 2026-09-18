"""Reads a text file for the model."""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool

OUTSIDE_MESSAGE = "path is outside the working directory: {path}"
MISSING_MESSAGE = "file not found: {path}"


def read_file_tool(cwd: Path):
    """Build the file-reading tool for one working directory."""
    root = cwd.resolve()

    @tool
    def read_file(path: str) -> str:
        """Read a text file under the working directory. Paths are relative to it."""
        candidate = Path(path)
        target = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
        if target != root and root not in target.parents:
            return OUTSIDE_MESSAGE.format(path=path)
        if not target.is_file():
            return MISSING_MESSAGE.format(path=path)
        return target.read_text()

    return read_file
