"""Creates or overwrites a text file for the model."""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool

from harness.tools.paths import OUTSIDE_MESSAGE, resolve_inside

WRITTEN_MESSAGE = "wrote {path}"
TOOL_NAME = "write_file"


def write_file_tool(cwd: Path):
    """Build the file-writing tool for one working directory."""
    root = cwd.resolve()

    @tool(TOOL_NAME)
    def write_file(path: str, content: str) -> str:
        """Create or overwrite a text file with the given content.

        The file must live under the working directory; paths are relative to it.
        """
        target = resolve_inside(root, path)
        if target is None:
            return OUTSIDE_MESSAGE.format(path=path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return WRITTEN_MESSAGE.format(path=path)

    return write_file
