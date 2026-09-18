from harness.tui.app import NEW_NOTICE, App
from tests.conftest import RecordingModel


def test_turn_prints_reply_and_context(settings, capsys):
    app = App(settings, model=RecordingModel())
    app.run_turn("hi")
    out = capsys.readouterr().out
    assert "reply 1" in out
    assert "context: 3 messages" in out


def test_new_command_resets(settings, capsys):
    app = App(settings, model=RecordingModel())
    app.run_turn("hi")
    capsys.readouterr()
    app.handle_command("/new")
    out = capsys.readouterr().out
    assert NEW_NOTICE in out
    assert app.chat.size() == 1
