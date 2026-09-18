import pytest

from harness.config import ConfigError, Settings, load_settings

# Dynaconf auto-discovers .env files, so tests point that lookup at a missing file.


def test_load_settings_reads_key(monkeypatch):
    monkeypatch.setenv("DOTENV_PATH_FOR_DYNACONF", "/nonexistent/.env")
    monkeypatch.setenv("HARNESS_API_KEY", "test-key-123")
    monkeypatch.delenv("HARNESS_BASE_URL", raising=False)
    monkeypatch.delenv("HARNESS_MODEL", raising=False)
    monkeypatch.delenv("HARNESS_USER_AGENT", raising=False)
    s = load_settings(env_file="/nonexistent/.env")
    assert s.api_key == "test-key-123"
    assert s.model == "muse-spark-1.3-contributor"
    assert s.base_url.startswith("https://opencode.ai/zen/go")


def test_missing_key_raises(monkeypatch):
    monkeypatch.setenv("DOTENV_PATH_FOR_DYNACONF", "/nonexistent/.env")
    monkeypatch.delenv("HARNESS_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        load_settings(env_file="/nonexistent/.env")


def test_repr_never_leaks_key():
    s = Settings(
        api_key="super-secret",
        base_url="https://example.com",
        model="example-model",
        user_agent="example-agent",
        timeout_seconds=60,
        shell_timeout_seconds=120,
    )
    assert "super-secret" not in repr(s)
    assert "super-secret" not in str(s)


def test_env_overrides_default(monkeypatch):
    monkeypatch.setenv("DOTENV_PATH_FOR_DYNACONF", "/nonexistent/.env")
    monkeypatch.setenv("HARNESS_API_KEY", "test-key-123")
    monkeypatch.setenv("HARNESS_MODEL", "other-model")
    monkeypatch.delenv("HARNESS_BASE_URL", raising=False)
    monkeypatch.delenv("HARNESS_USER_AGENT", raising=False)
    s = load_settings(env_file="/nonexistent/.env")
    assert s.model == "other-model"
