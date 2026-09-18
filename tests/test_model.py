"""Offline tests for the raw model call and reply reading."""

from harness.model.client import (
    AUTHORIZATION_HEADER,
    BEARER_PREFIX,
    SESSION_HEADER,
    SESSION_ID_PREFIX,
    USER_AGENT_HEADER,
    headers,
    new_session_id,
)
from harness.model.text import output_types, text_of

REPLY = {
    "output": [
        {"type": "reasoning"},
        {
            "type": "message",
            "content": [
                {"type": "output_text", "text": "po"},
                {"type": "output_text", "text": "ng"},
                {"type": "other", "text": "!"},
            ],
        },
    ]
}


def test_output_types_lists_every_block():
    assert output_types(REPLY) == ["reasoning", "message"]


def test_text_of_joins_only_output_text():
    assert text_of(REPLY) == "pong"


def test_headers_carry_key_session_and_agent(settings):
    sent = headers(settings, "session-123")
    assert sent[SESSION_HEADER] == "session-123"
    assert sent[AUTHORIZATION_HEADER].startswith(BEARER_PREFIX)
    assert sent[AUTHORIZATION_HEADER].endswith(settings.api_key)
    assert sent[USER_AGENT_HEADER] == settings.user_agent


def test_new_session_id_has_prefix_and_differs():
    first = new_session_id()
    second = new_session_id()
    assert first.startswith(SESSION_ID_PREFIX)
    assert second.startswith(SESSION_ID_PREFIX)
    assert first != second
