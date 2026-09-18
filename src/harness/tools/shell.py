"""Runs a shell command for the model."""

from __future__ import annotations

import subprocess
from pathlib import Path

from langchain_core.tools import tool

EXIT_LINE = "exit code: {code}"
TIMEOUT_MESSAGE = "command timed out after {seconds} seconds"


def shell_tool(cwd: Path, timeout_seconds: int):
    """Build the shell tool for one working directory."""
    root = cwd.resolve()

    @tool
    def shell(command: str) -> str:
        """Run a shell command in the working directory.

        Return its output followed by the exit code.
        """
        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return TIMEOUT_MESSAGE.format(seconds=timeout_seconds)
        parts = [
            completed.stdout.strip(),
            completed.stderr.strip(),
            EXIT_LINE.format(code=completed.returncode),
        ]
        return "\n".join(part for part in parts if part)

    return shell
