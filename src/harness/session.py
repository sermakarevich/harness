"""A session holds one conversation with its model and answer loop."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from harness.config import Settings
from harness.graph import build_graph, new_session_id, thread_config
from harness.model import make_model


@dataclass
class Session:
    settings: Settings
    session_id: str
    graph: object
    config: dict

    @classmethod
    def start(
        cls,
        settings: Settings,
        checkpointer: BaseCheckpointSaver | None = None,
        cwd: Path | None = None,
        model=None,
    ) -> Session:
        """Start a fresh conversation. Tests may pass in their own model."""
        session_id = new_session_id()
        model = model or make_model(settings, session_id)
        graph = build_graph(model, settings, checkpointer or InMemorySaver(), cwd)
        return cls(settings, session_id, graph, thread_config(session_id))
