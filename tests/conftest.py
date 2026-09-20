"""Shared fixtures for offline tests."""

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk

from harness.config import load_settings


class FakeToolChatModel(GenericFakeChatModel):
    """A scripted model whose replies may carry tool calls."""

    def bind_tools(self, tools, **kwargs):
        return self

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        message = next(self.messages)
        reply = message if isinstance(message, AIMessage) else AIMessage(content=message)
        extra = {"usage_metadata": reply.usage_metadata} if reply.usage_metadata else {}
        chunk = ChatGenerationChunk(
            message=AIMessageChunk(content=reply.content, tool_calls=reply.tool_calls, **extra)
        )
        if run_manager:
            run_manager.on_llm_new_token(reply.content, chunk=chunk)
        yield chunk


@pytest.fixture
def settings(monkeypatch, tmp_path):
    monkeypatch.setenv("HARNESS_API_KEY", "x")
    monkeypatch.setenv("HARNESS_SESSIONS_DB", str(tmp_path / "sessions.db"))
    monkeypatch.setenv("DOTENV_PATH_FOR_DYNACONF", "/nonexistent/.env")
    monkeypatch.delenv("HARNESS_MODEL", raising=False)
    monkeypatch.delenv("HARNESS_BASE_URL", raising=False)
    monkeypatch.delenv("HARNESS_USER_AGENT", raising=False)
    monkeypatch.delenv("HARNESS_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("HARNESS_SHELL_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("HARNESS_INPUT_PRICE_PER_MILLION", raising=False)
    monkeypatch.delenv("HARNESS_CACHED_INPUT_PRICE_PER_MILLION", raising=False)
    monkeypatch.delenv("HARNESS_OUTPUT_PRICE_PER_MILLION", raising=False)
    monkeypatch.delenv("HARNESS_TOOL_OUTPUT_LIMIT_CHARACTERS", raising=False)
    monkeypatch.delenv("HARNESS_TOOL_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("HARNESS_COMPACT_AT_TOKENS", raising=False)
    monkeypatch.delenv("HARNESS_KEEP_RECENT_TURNS", raising=False)
    monkeypatch.delenv("HARNESS_MEMORY_FILE_NAMES", raising=False)
    monkeypatch.delenv("HARNESS_SKILLS_DIR", raising=False)
    monkeypatch.delenv("HARNESS_RETRY_ATTEMPTS", raising=False)
    monkeypatch.delenv("HARNESS_RETRY_INITIAL_SECONDS", raising=False)
    monkeypatch.delenv("HARNESS_RETRY_BACKOFF_FACTOR", raising=False)
    monkeypatch.delenv("HARNESS_MAX_PARALLEL_TOOLS", raising=False)
    return load_settings(env_file="/nonexistent/.env")
