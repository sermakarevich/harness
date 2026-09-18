from io import StringIO

from langchain_core.messages import AIMessage
from rich.console import Console

from harness.tui.app import App
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
