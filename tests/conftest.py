"""Load tutorial scripts so tests can call them without the network."""

import importlib.util
from pathlib import Path

import pytest

from harness.config import load_settings

SCRIPTS_DIR = Path(__file__).parents[1] / "scripts"


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def raw_call():
    return load_script("raw_call")


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv("HARNESS_API_KEY", "x")
    monkeypatch.setenv("DOTENV_PATH_FOR_DYNACONF", "/nonexistent/.env")
    monkeypatch.delenv("HARNESS_MODEL", raising=False)
    monkeypatch.delenv("HARNESS_BASE_URL", raising=False)
    monkeypatch.delenv("HARNESS_USER_AGENT", raising=False)
    monkeypatch.delenv("HARNESS_TIMEOUT_SECONDS", raising=False)
    return load_settings(env_file="/nonexistent/.env")


@pytest.fixture
def chat_list():
    return load_script("chat_list")
