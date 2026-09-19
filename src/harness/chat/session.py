"""A session holds one conversation with its model and answer loop."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from harness.chat.graph import build_graph
from harness.chat.thread import thread_config
from harness.config import Settings
from harness.model.client import make_model, new_session_id


@dataclass
class Session:
    settings: Settings
    session_id: str
    graph: object
    config: dict

    @classmethod
    def resume(
        cls,
        settings: Settings,
        session_id: str,
        checkpointer: BaseCheckpointSaver | None = None,
        cwd: Path | None = None,
        model=None,
    ) -> Session:
        """Continue a saved conversation."""
        chosen = model or make_model(settings, session_id)
        graph = build_graph(chosen, settings, checkpointer or InMemorySaver(), cwd)
        return cls(settings, session_id, graph, thread_config(session_id))

    @classmethod
    def start(
        cls,
        settings: Settings,
        checkpointer: BaseCheckpointSaver | None = None,
        cwd: Path | None = None,
        model=None,
    ) -> Session:
        """Start a fresh conversation."""
        return cls.resume(settings, new_session_id(), checkpointer, cwd, model)

    def saved_messages(self) -> list:
        """Messages the checkpointer holds for this conversation, if any."""
        return list(self.graph.get_state(self.config).values.get("messages", []))

    def pending_request(self) -> dict | None:
        """Payload of the first waiting permission question, if any."""
        interrupts = self.graph.get_state(self.config).interrupts
        return interrupts[0].value if interrupts else None
