from io import StringIO

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from rich.console import Console

from harness.config import Settings
from harness.tui.app import App


def make_app():
    model = GenericFakeChatModel(
        messages=iter([AIMessage(content="pong"), AIMessage(content="again")])
    )
    buf = StringIO()
    app = App(
        Settings(api_key="x"),
        console=Console(file=buf, width=80, force_terminal=False),
        model=model,
    )
    return app, buf


def test_run_turn_streams_reply():
    app, buf = make_app()
    app.run_turn("ping")
    assert "pong" in buf.getvalue()


def test_new_command_changes_session():
    app, buf = make_app()
    before = app.session.session_id
    assert app.handle_command("/new") is True
    assert app.session.session_id != before
    assert "new session" in buf.getvalue()


def test_exit_and_unknown_commands():
    app, buf = make_app()
    assert app.handle_command("/exit") is False
    assert app.handle_command("/bogus") is True
    assert "unknown command" in buf.getvalue()


def test_help_lists_commands():
    app, buf = make_app()
    app.handle_command("/help")
    out = buf.getvalue()
    assert "/new" in out and "/exit" in out
