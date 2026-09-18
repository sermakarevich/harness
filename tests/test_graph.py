from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage

from harness.chat.graph import build_graph
from harness.chat.prompt import build_system_prompt
from harness.chat.session import Session
from harness.chat.thread import new_session_id, thread_config
from harness.config import Settings


def fake_model():
    return GenericFakeChatModel(messages=iter([AIMessage(content="one"), AIMessage(content="two")]))


def test_two_turns_accumulate_in_one_thread():
    graph = build_graph(fake_model(), Settings(api_key="x"))
    cfg = thread_config(new_session_id())
    graph.invoke({"messages": [HumanMessage(content="a")]}, cfg)
    graph.invoke({"messages": [HumanMessage(content="b")]}, cfg)
    msgs = graph.get_state(cfg).values["messages"]
    assert [m.content for m in msgs] == ["a", "one", "b", "two"]


def test_threads_are_isolated():
    graph = build_graph(fake_model(), Settings(api_key="x"))
    cfg1, cfg2 = thread_config("s1"), thread_config("s2")
    graph.invoke({"messages": [HumanMessage(content="a")]}, cfg1)
    graph.invoke({"messages": [HumanMessage(content="b")]}, cfg2)
    assert len(graph.get_state(cfg1).values["messages"]) == 2
    assert len(graph.get_state(cfg2).values["messages"]) == 2


def test_system_prompt_mentions_cwd(tmp_path):
    assert str(tmp_path) in build_system_prompt(Settings(api_key="x"), cwd=tmp_path)


def test_stream_mode_messages_yields_ai_chunks():
    graph = build_graph(fake_model(), Settings(api_key="x"))
    cfg = thread_config("s")
    events = list(
        graph.stream({"messages": [HumanMessage(content="a")]}, cfg, stream_mode="messages")
    )
    assert events, "expected streamed message events"
    text = "".join(getattr(msg, "content", "") for msg, _meta in events)
    assert "one" in text


def test_session_start_injects_model():
    s = Session.start(Settings(api_key="x"), model=fake_model())
    assert s.session_id.startswith("harness-")
    assert s.config["configurable"]["thread_id"] == s.session_id
