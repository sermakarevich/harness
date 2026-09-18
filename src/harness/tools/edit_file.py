"""Replaces one piece of text inside a file for the model."""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool

from harness.tools.paths import MISSING_MESSAGE, OUTSIDE_MESSAGE, resolve_inside

NOT_FOUND_MESSAGE = "old_text not found in {path}"
AMBIGUOUS_MESSAGE = "old_text appears {count} times in {path}; include more surrounding text"
EDITED_MESSAGE = "edited {path}"


def edit_file_tool(cwd: Path):
    """Build the file-editing tool for one working directory."""
    root = cwd.resolve()

    @tool
    def edit_file(path: str, old_text: str, new_text: str) -> str:
        """Replace one exact occurrence of `old_text` with `new_text` in a file.

        The file must live under the working directory; `old_text` must appear
        exactly once, so include enough surrounding lines to make it unique.
        """
        target = resolve_inside(root, path)
        if target is None:
            return OUTSIDE_MESSAGE.format(path=path)
        if not target.is_file():
            return MISSING_MESSAGE.format(path=path)
        content = target.read_text()
        count = content.count(old_text)
        if count == 0:
            return NOT_FOUND_MESSAGE.format(path=path)
        if count > 1:
            return AMBIGUOUS_MESSAGE.format(count=count, path=path)
        target.write_text(content.replace(old_text, new_text, 1))
        return EDITED_MESSAGE.format(path=path)

    return edit_file
