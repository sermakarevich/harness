import uuid

from langchain_core.messages import AIMessage

from harness.model.client import make_model
from harness.model.text import text_of


def test_make_model_carries_session_header(settings):
    sid = f"t-{uuid.uuid4()}"
    model = make_model(settings, session_id=sid)
    headers = dict(getattr(model, "default_headers", None) or {})
    assert headers.get("x-opencode-session") == sid
    assert headers.get("User-Agent")


def test_make_model_uses_go_endpoint_and_model(settings):
    model = make_model(settings, session_id="s")
    assert "opencode.ai/zen/go" in str(getattr(model, "openai_api_base", "") or model.__dict__)
    assert model.model_name == "muse-spark-1.3-contributor"


def test_text_of_string_and_blocks():
    assert text_of(AIMessage(content="hi")) == "hi"
    blocks = [{"type": "text", "text": "a"}, {"type": "output_text", "text": "b"}]
    assert text_of(AIMessage(content=blocks)) == "ab"
    assert text_of(AIMessage(content=[])) == ""
