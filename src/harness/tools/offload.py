"""Moves over-long tool results to a file outside the conversation."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

DIGEST_LENGTH = 16
OUTPUT_SUFFIX = ".txt"
NOTICE = "\n[showing {shown} of {total} characters, full output in {path}]"


def build_offload(root: Path, limit_characters: int, output_dir: str) -> Callable[[str], str]:
    """Build the function that spills long tool results to disk."""
    base = root.resolve()

    def offload(text: str) -> str:
        if len(text) <= limit_characters:
            return text
        digest = hashlib.sha256(text.encode()).hexdigest()[:DIGEST_LENGTH]
        folder = base / output_dir
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (digest + OUTPUT_SUFFIX)).write_text(text)
        relative = (Path(output_dir) / (digest + OUTPUT_SUFFIX)).as_posix()
        return text[:limit_characters] + NOTICE.format(
            shown=limit_characters, total=len(text), path=relative
        )

    return offload
