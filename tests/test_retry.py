"""Failed model calls worth trying again."""

import dataclasses

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)
from pydantic import PrivateAttr

from harness.chat.graph import build_graph
from harness.chat.thread import thread_config
from harness.model.retry import should_retry
from tests.conftest import FakeToolChatModel

REQUEST_URL = "https://example.com/v1"


def request() -> httpx.Request:
    return httpx.Request("POST", REQUEST_URL)


def status_error(kind, status_code: int):
    return kind("failed", response=httpx.Response(status_code, request=request()), body=None)


def test_connection_error_is_retried():
    assert should_retry(APIConnectionError(request=request())) is True


def test_timeout_is_retried():
    assert should_retry(APITimeoutError(request=request())) is True


def test_rate_limit_is_retried():
    assert should_retry(status_error(RateLimitError, 429)) is True


def test_server_error_is_retried():
    assert should_retry(status_error(InternalServerError, 500)) is True


def test_wrong_key_is_not_retried():
    assert should_retry(status_error(AuthenticationError, 401)) is False


def test_own_mistake_is_not_retried():
    assert should_retry(ValueError("bad")) is False


class FlakyModel(FakeToolChatModel):
    """Fails the first call with a dropped connection, then answers."""

    _calls: int = PrivateAttr(default=0)

    def invoke(self, messages, config=None, **kwargs):
        self._calls += 1
        if self._calls == 1:
            raise APIConnectionError(request=request())
        return AIMessage(content="four")


class WrongKeyModel(FakeToolChatModel):
    """Fails every call because the key is wrong."""

    _calls: int = PrivateAttr(default=0)

    def invoke(self, messages, config=None, **kwargs):
        self._calls += 1
        raise status_error(AuthenticationError, 401)


def test_dropped_connection_gets_through_on_second_try(settings):
    fast = dataclasses.replace(settings, retry_initial_seconds=0.0)
    model = FlakyModel(messages=iter([]))
    graph = build_graph(model, fast)
    cfg = thread_config("retry-yes")
    graph.invoke({"messages": [HumanMessage(content="two plus two")]}, cfg)
    contents = [m.content for m in graph.get_state(cfg).values["messages"]]
    assert "four" in contents
    assert model._calls == 2


def test_wrong_key_is_not_tried_again(settings):
    model = WrongKeyModel(messages=iter([]))
    graph = build_graph(model, settings)
    with pytest.raises(AuthenticationError):
        graph.invoke(
            {"messages": [HumanMessage(content="two plus two")]}, thread_config("retry-no")
        )
    assert model._calls == 1
