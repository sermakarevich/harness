from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from harness.chat.graph import build_graph
from harness.chat.session import Session
from harness.chat.thread import thread_config
from harness.model.client import new_session_id
from tests.conftest import FakeToolChatModel


def fake_model():
    return FakeToolChatModel(messages=iter([AIMessage(content="one"), AIMessage(content="two")]))


def test_two_turns_accumulate_in_one_thread(settings):
    graph = build_graph(fake_model(), settings)
    cfg = thread_config(new_session_id())
    graph.invoke({"messages": [HumanMessage(content="a")]}, cfg)
    graph.invoke({"messages": [HumanMessage(content="b")]}, cfg)
    msgs = graph.get_state(cfg).values["messages"]
    assert [m.content for m in msgs] == ["a", "one", "b", "two"]


def test_threads_are_isolated(settings):
    graph = build_graph(fake_model(), settings)
    cfg1, cfg2 = thread_config("s1"), thread_config("s2")
    graph.invoke({"messages": [HumanMessage(content="a")]}, cfg1)
    graph.invoke({"messages": [HumanMessage(content="b")]}, cfg2)
    assert len(graph.get_state(cfg1).values["messages"]) == 2
    assert len(graph.get_state(cfg2).values["messages"]) == 2


def test_stream_mode_messages_yields_ai_chunks(settings):
    graph = build_graph(fake_model(), settings)
    cfg = thread_config("s")
    events = list(
        graph.stream({"messages": [HumanMessage(content="a")]}, cfg, stream_mode="messages")
    )
    assert events, "expected streamed message events"
    text = "".join(getattr(msg, "content", "") for msg, _meta in events)
    assert "one" in text


def test_session_start_injects_model(settings):
    s = Session.start(settings, model=fake_model())
    assert s.session_id.startswith("harness-")
    assert s.config["configurable"]["thread_id"] == s.session_id


def test_tool_loop_reads_file_and_answers(tmp_path, settings):
    target = tmp_path / "note.txt"
    target.write_text("hello")
    model = FakeToolChatModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "read_file",
                            "args": {"path": "note.txt"},
                            "id": "call-1",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="done"),
            ]
        )
    )
    graph = build_graph(model, settings, cwd=tmp_path)
    cfg = thread_config("tools")
    graph.invoke({"messages": [HumanMessage(content="read it")]}, cfg)
    msgs = graph.get_state(cfg).values["messages"]
    assert isinstance(msgs[0], HumanMessage)
    assert isinstance(msgs[1], AIMessage) and msgs[1].tool_calls
    assert isinstance(msgs[2], ToolMessage) and msgs[2].content == "hello"
    assert isinstance(msgs[3], AIMessage) and msgs[3].content == "done"
