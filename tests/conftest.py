"""Shared fixtures for offline tests."""

import pytest

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
