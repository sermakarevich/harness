"""The tools the model may use."""

from __future__ import annotations

from pathlib import Path

from harness.tools.edit_file import edit_file_tool
from harness.tools.read_file import read_file_tool
from harness.tools.read_skill import read_skill_tool
from harness.tools.shell import shell_tool
from harness.tools.write_file import write_file_tool


def build_tools(cwd: Path, shell_timeout_seconds: int, skills_dir: str) -> list:
    """List every tool the model may ask the harness to run."""
    return [
        read_file_tool(cwd),
        read_skill_tool(cwd, skills_dir),
        write_file_tool(cwd),
        edit_file_tool(cwd),
        shell_tool(cwd, shell_timeout_seconds),
    ]
