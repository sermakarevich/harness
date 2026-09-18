"""Keeps tool file paths inside the working directory."""

from __future__ import annotations

from pathlib import Path

OUTSIDE_MESSAGE = "path is outside the working directory: {path}"
MISSING_MESSAGE = "file not found: {path}"


def resolve_inside(root: Path, path: str) -> Path | None:
    """Resolve a path against the root, or return None when it lies outside."""
    candidate = Path(path)
    target = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if target != root and root not in target.parents:
        return None
    return target
