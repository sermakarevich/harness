from io import StringIO

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from rich.console import Console

from harness.tools.permission import Answer
from harness.tui.app import App
from harness.tui.ask import answer_of
from harness.tui.render import StreamState, render_event
from tests.conftest import FakeToolChatModel


def make_app(settings):
    model = FakeToolChatModel(
        messages=iter([AIMessage(content="pong"), AIMessage(content="again")])
    )
    buf = StringIO()
    app = App(
        settings,
        console=Console(file=buf, width=80, force_terminal=False),
        model=model,
    )
    return app, buf


def test_run_turn_streams_reply(settings):
    app, buf = make_app(settings)
    app.run_turn("ping")
    assert "pong" in buf.getvalue()


def test_new_command_changes_session(settings):
    app, buf = make_app(settings)
    before = app.session.session_id
    assert app.handle_command("/new") is True
    assert app.session.session_id != before
    assert "new session" in buf.getvalue()


def test_exit_and_unknown_commands(settings):
    app, buf = make_app(settings)
    assert app.handle_command("/exit") is False
    assert app.handle_command("/bogus") is True
    assert "unknown command" in buf.getvalue()


def test_help_lists_commands(settings):
    app, buf = make_app(settings)
    app.handle_command("/help")
    out = buf.getvalue()
    assert "/new" in out and "/exit" in out


def test_run_turn_prints_tool_call_before_answer(settings, tmp_path):
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
    buf = StringIO()
    app = App(
        settings,
        console=Console(file=buf, width=80, force_terminal=False),
        cwd=tmp_path,
        model=model,
    )
    app.run_turn("read it")
    out = buf.getvalue()
    assert "→ read_file path=" in out
    assert out.index("→ read_file path=") < out.index("done")


def test_run_turn_shortens_long_tool_arg(settings, tmp_path):
    model = FakeToolChatModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "write_file",
                            "args": {"path": "note.txt", "content": "x" * 200},
                            "id": "call-1",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="done"),
            ]
        )
    )
    buf = StringIO()
    app = App(
        settings,
        console=Console(file=buf, width=200, force_terminal=False),
        cwd=tmp_path,
        model=model,
    )
    app.read_line = lambda prompt_text: "y"
    app.run_turn("write it")
    line = next(line for line in buf.getvalue().splitlines() if "→ write_file" in line)
    assert len(line) < 120
    assert "…" in line


def test_run_turn_shows_every_tool_call_of_one_reply(settings, tmp_path):
    model = FakeToolChatModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "write_file",
                            "args": {"path": "a.txt", "content": "a"},
                            "id": "call-1",
                            "type": "tool_call",
                        },
                        {
                            "name": "write_file",
                            "args": {"path": "b.txt", "content": "b"},
                            "id": "call-2",
                            "type": "tool_call",
                        },
                    ],
                ),
                AIMessage(content="done"),
            ]
        )
    )
    buf = StringIO()
    app = App(
        settings,
        console=Console(file=buf, width=200, force_terminal=False),
        cwd=tmp_path,
        model=model,
    )
    app.read_line = lambda prompt_text: "y"
    app.run_turn("write both")
    out = buf.getvalue()
    assert "→ write_file path=a.txt" in out
    assert "→ write_file path=b.txt" in out
    assert out.index("→ write_file path=a.txt") < out.index("done")
    assert out.index("→ write_file path=b.txt") < out.index("done")


def write_call_app(settings, tmp_path, buf):
    model = FakeToolChatModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "write_file",
                            "args": {"path": "note.txt", "content": "hello"},
                            "id": "call-1",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="done"),
            ]
        )
    )
    return App(
        settings,
        console=Console(file=buf, width=200, force_terminal=False),
        cwd=tmp_path,
        model=model,
    )


def stub_read_line(app, buf, replies):
    seen = []

    def read(prompt_text):
        seen.append(prompt_text)
        buf.write(prompt_text + "\n")
        return replies.pop(0)

    app.read_line = read
    return seen


def test_run_turn_denied_hides_tool_call(settings, tmp_path):
    buf = StringIO()
    app = write_call_app(settings, tmp_path, buf)
    stub_read_line(app, buf, ["n"])
    app.run_turn("write it")
    out = buf.getvalue()
    assert "allow write_file" in out
    assert "→ write_file" not in out
    assert not (tmp_path / "note.txt").exists()


def test_run_turn_allowed_shows_tool_call(settings, tmp_path):
    buf = StringIO()
    app = write_call_app(settings, tmp_path, buf)
    seen = stub_read_line(app, buf, ["y"])
    app.run_turn("write it")
    out = buf.getvalue()
    assert "allow write_file" in seen[0]
    assert "→ write_file" in out
    assert (tmp_path / "note.txt").read_text() == "hello"


def test_answer_of_reads_first_letter():
    assert answer_of("y") is Answer.YES
    assert answer_of("always") is Answer.ALWAYS
    assert answer_of("N") is Answer.NO
    assert answer_of("") is Answer.NO
    assert answer_of("maybe") is Answer.NO


def test_denied_call_keeps_turn_alive():
    buf = StringIO()
    console = Console(file=buf, width=80, force_terminal=False)
    state = StreamState()
    first = AIMessageChunk(
        content="",
        tool_calls=[
            {
                "name": "shell",
                "args": {"command": "rm hello.txt"},
                "id": "call-1",
                "type": "tool_call",
            }
        ],
        additional_kwargs={"created_at": 1.5},
    )
    render_event(console, first, {}, state)
    state.denied.add("call-1")
    render_event(
        console,
        ToolMessage(content="denied", name="shell", tool_call_id="call-1"),
        {},
        state,
    )
    second = AIMessageChunk(content="sorry", additional_kwargs={"created_at": 2.5})
    render_event(console, second, {}, state)
    assert "sorry" in buf.getvalue()


def test_question_starts_on_fresh_line(settings, tmp_path):
    buf = StringIO()
    model = FakeToolChatModel(
        messages=iter(
            [
                AIMessage(
                    content="Creating your file.",
                    tool_calls=[
                        {
                            "name": "write_file",
                            "args": {"path": "note.txt", "content": "hello"},
                            "id": "call-1",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="done"),
            ]
        )
    )
    app = App(
        settings,
        console=Console(file=buf, width=200, force_terminal=False),
        cwd=tmp_path,
        model=model,
    )
    held = []
    replies = ["y"]

    def read(prompt_text):
        held.append(buf.getvalue())
        buf.write(prompt_text + "\n")
        return replies.pop(0)

    app.read_line = read
    app.run_turn("write it")
    assert held and held[0].endswith("\n")


def test_resume_with_nothing_saved(settings):
    from harness.tui.pick import NOTHING_SAVED

    app, buf = make_app(settings)
    assert app.handle_command("/resume") is True
    assert NOTHING_SAVED in buf.getvalue()


def test_resume_lists_saved_conversation(settings):
    app, buf = make_app(settings)
    app.run_turn("hello there")
    buf.truncate(0)
    buf.seek(0)
    assert app.handle_command("/resume") is True
    out = buf.getvalue()
    assert "hello there" in out


def test_resume_one_keeps_messages(settings):
    from langchain_core.messages import HumanMessage

    app, buf = make_app(settings)
    app.run_turn("first hello")
    first_id = app.session.session_id
    app.handle_command("/new")
    assert app.session.session_id != first_id
    assert app.handle_command("/resume 1") is True
    assert app.session.session_id == first_id
    state = app.session.graph.get_state(app.session.config)
    texts = [m.content for m in state.values["messages"] if isinstance(m, HumanMessage)]
    assert "first hello" in texts


def test_resume_unknown_number_changes_nothing(settings):
    app, buf = make_app(settings)
    app.run_turn("hello there")
    before = app.session.session_id
    assert app.handle_command("/resume 99") is True
    assert app.session.session_id == before
