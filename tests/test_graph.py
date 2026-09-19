from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command

from harness.chat.graph import build_graph
from harness.chat.session import Session
from harness.chat.thread import thread_config
from harness.model.client import new_session_id
from harness.tools.permission import DENIED_MESSAGE, Answer
from harness.tools.write_file import WRITTEN_MESSAGE
from tests.conftest import FakeToolChatModel


def tool_call(name, args, call_id="call-1"):
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


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


def write_call_model(*replies):
    return FakeToolChatModel(messages=iter(list(replies)))


def test_write_file_pauses_before_running(tmp_path, settings):
    model = write_call_model(
        AIMessage(
            content="",
            tool_calls=[tool_call("write_file", {"path": "note.txt", "content": "hello"})],
        ),
        AIMessage(content="done"),
    )
    session = Session.start(settings, cwd=tmp_path, model=model)
    session.graph.invoke({"messages": [HumanMessage(content="write it")]}, session.config)
    target = tmp_path / "note.txt"
    assert not target.exists()
    pending = session.pending_request()
    assert pending["name"] == "write_file"
    assert pending["args"] == {"path": "note.txt", "content": "hello"}
    session.graph.invoke(Command(resume=Answer.YES), session.config)
    assert target.read_text() == "hello"
    msgs = session.graph.get_state(session.config).values["messages"]
    assert isinstance(msgs[-2], ToolMessage)
    assert msgs[-2].content == WRITTEN_MESSAGE.format(path="note.txt")


def test_write_file_denied_runs_nothing(tmp_path, settings):
    model = write_call_model(
        AIMessage(
            content="",
            tool_calls=[tool_call("write_file", {"path": "note.txt", "content": "hello"})],
        ),
        AIMessage(content="denied, stopping"),
    )
    graph = build_graph(model, settings, cwd=tmp_path)
    cfg = thread_config("gate-no")
    graph.invoke({"messages": [HumanMessage(content="write it")]}, cfg)
    assert not (tmp_path / "note.txt").exists()
    graph.invoke(Command(resume=Answer.NO), cfg)
    assert not (tmp_path / "note.txt").exists()
    msgs = graph.get_state(cfg).values["messages"]
    assert isinstance(msgs[-2], ToolMessage) and msgs[-2].content == DENIED_MESSAGE


def test_always_answer_skips_the_next_pause(tmp_path, settings):
    model = write_call_model(
        AIMessage(
            content="",
            tool_calls=[tool_call("write_file", {"path": "a.txt", "content": "a"})],
        ),
        AIMessage(content="one"),
        AIMessage(
            content="",
            tool_calls=[
                tool_call("write_file", {"path": "b.txt", "content": "b"}, call_id="call-2")
            ],
        ),
        AIMessage(content="two"),
    )
    graph = build_graph(model, settings, cwd=tmp_path)
    cfg = thread_config("gate-always")
    graph.invoke({"messages": [HumanMessage(content="first")]}, cfg)
    graph.invoke(Command(resume=Answer.ALWAYS), cfg)
    assert (tmp_path / "a.txt").read_text() == "a"
    graph.invoke({"messages": [HumanMessage(content="second")]}, cfg)
    assert graph.get_state(cfg).interrupts == ()
    assert (tmp_path / "b.txt").read_text() == "b"


def test_read_file_never_pauses(tmp_path, settings):
    target = tmp_path / "note.txt"
    target.write_text("hello")
    model = write_call_model(
        AIMessage(
            content="",
            tool_calls=[tool_call("read_file", {"path": "note.txt"})],
        ),
        AIMessage(content="done"),
    )
    graph = build_graph(model, settings, cwd=tmp_path)
    cfg = thread_config("gate-read")
    graph.invoke({"messages": [HumanMessage(content="read it")]}, cfg)
    assert graph.get_state(cfg).interrupts == ()
    msgs = graph.get_state(cfg).values["messages"]
    assert isinstance(msgs[-2], ToolMessage) and msgs[-2].content == "hello"


def test_long_tool_result_is_offloaded_to_file(tmp_path, settings):
    body = "x" * (settings.tool_output_limit_characters + 500)
    (tmp_path / "big.txt").write_text(body)
    model = write_call_model(
        AIMessage(
            content="",
            tool_calls=[tool_call("read_file", {"path": "big.txt"})],
        ),
        AIMessage(content="done"),
    )
    graph = build_graph(model, settings, cwd=tmp_path)
    cfg = thread_config("offload")
    graph.invoke({"messages": [HumanMessage(content="read it")]}, cfg)
    msgs = graph.get_state(cfg).values["messages"]
    tool_msg = next(m for m in msgs if isinstance(m, ToolMessage))
    assert len(tool_msg.content) < len(body)
    assert str(len(body)) in tool_msg.content
    spilled = list((tmp_path / settings.tool_output_dir).glob("*"))
    assert len(spilled) == 1
    assert spilled[0].read_text() == body
    assert spilled[0].relative_to(tmp_path).as_posix() in tool_msg.content
