"""The tools the model may use."""

from __future__ import annotations

from pathlib import Path

from harness.tools.read_file import read_file_tool


def build_tools(cwd: Path) -> list:
    """List every tool the model may ask the harness to run."""
    return [read_file_tool(cwd)]
