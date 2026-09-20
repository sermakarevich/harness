"""Loads one skill for the model."""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool

from harness.tools.skills import UNKNOWN_SKILL_MESSAGE, skill_body

TOOL_NAME = "read_skill"


def read_skill_tool(cwd: Path, skills_dir: str):
    """Build the skill-loading tool for one working directory."""
    root = cwd.resolve()

    @tool(TOOL_NAME)
    def read_skill(name: str) -> str:
        """Load the full instructions of one skill listed in the system prompt, by name."""
        body = skill_body(root, skills_dir, name)
        if body is None:
            return UNKNOWN_SKILL_MESSAGE.format(name=name)
        return body

    return read_skill
