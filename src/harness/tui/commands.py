"""Commands for the terminal chat."""

from __future__ import annotations

from enum import StrEnum

COMMAND_PREFIX = "/"


class Command(StrEnum):
    NEW = f"{COMMAND_PREFIX}new"
