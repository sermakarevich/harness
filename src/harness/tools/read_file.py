"""Reads a text file for the model."""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool

from harness.tools.paths import MISSING_MESSAGE, OUTSIDE_MESSAGE, resolve_inside

TOOL_NAME = "read_file"


def read_file_tool(cwd: Path):
    """Build the file-reading tool for one working directory."""
    root = cwd.resolve()

    @tool(TOOL_NAME)
    def read_file(path: str) -> str:
        """Read a text file under the working directory. Paths are relative to it."""
        target = resolve_inside(root, path)
        if target is None:
            return OUTSIDE_MESSAGE.format(path=path)
        if not target.is_file():
            return MISSING_MESSAGE.format(path=path)
        return target.read_text()

    return read_file
