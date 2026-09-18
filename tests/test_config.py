import pytest

from harness.config import ConfigError, Settings, load_settings


def test_load_settings_reads_key(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test-key-123")
    s = load_settings(env_file="/nonexistent/.env")
    assert s.api_key == "test-key-123"
    assert s.model == "muse-spark-1.3-contributor"
    assert s.base_url.startswith("https://opencode.ai/zen/go")


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        load_settings(env_file="/nonexistent/.env")


def test_repr_never_leaks_key():
    s = Settings(api_key="super-secret")
    assert "super-secret" not in repr(s)
    assert "super-secret" not in str(s)
