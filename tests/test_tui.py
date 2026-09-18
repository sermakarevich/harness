from io import StringIO

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from rich.console import Console

from harness.tui.app import App


def make_app(settings):
    model = GenericFakeChatModel(
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
