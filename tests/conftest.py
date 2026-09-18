"""Shared fixtures for offline tests."""

import pytest
from langchain_core.messages import AIMessage

from harness.config import load_settings


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("HARNESS_API_KEY", "x")
    monkeypatch.setenv("DOTENV_PATH_FOR_DYNACONF", "/nonexistent/.env")
    monkeypatch.delenv("HARNESS_MODEL", raising=False)
    monkeypatch.delenv("HARNESS_BASE_URL", raising=False)
    monkeypatch.delenv("HARNESS_USER_AGENT", raising=False)
    monkeypatch.delenv("HARNESS_TIMEOUT_SECONDS", raising=False)
    return load_settings(env_file="/nonexistent/.env")


class RecordingModel:
    def __init__(self):
        self.seen: list[int] = []
        self.first: list = []

    def invoke(self, messages):
        self.seen.append(len(messages))
        self.first.append(messages[0])
        return AIMessage(content=f"reply {len(self.seen)}")
