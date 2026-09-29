"""Full-screen front end, driven by a scripted model."""

import asyncio

from langchain_core.messages import AIMessage
from textual.widgets import RichLog, Static

from harness.chat.lines import call_text, cost_line, shorten
from harness.chat.usage import Usage
from harness.screen.app import INPUT_ID, LOG_ID, STATUS_ID, ScreenApp
from harness.screen.keys import EXIT
from harness.screen.permission import PermissionScreen
from tests.conftest import FakeToolChatModel

POLL_ROUNDS = 200


def log_text(app: ScreenApp) -> str:
    log = app.query_one(f"#{LOG_ID}", RichLog)
    return "\n".join(line.text for line in log.lines)


def status_text(app: ScreenApp) -> str:
    return str(app.query_one(f"#{STATUS_ID}", Static).render())


async def type_line(pilot, text: str) -> None:
    await pilot.click(f"#{INPUT_ID}")
    await pilot.press(*text, "enter")


async def run_plain(app: ScreenApp):
    async with app.run_test() as pilot:
        await type_line(pilot, "ping")
        for _ in range(POLL_ROUNDS):
            await pilot.pause()
            if "pong" in log_text(app):
                break
        await pilot.pause()
        return log_text(app), status_text(app)


def test_plain_turn_shows_reply_and_cost(settings, tmp_path):
    model = FakeToolChatModel(messages=iter([AIMessage(content="pong")]))
    app = ScreenApp(settings, cwd=tmp_path, model=model)
    log, status = asyncio.run(run_plain(app))
    assert "pong" in log
    assert status.startswith("in ")


def write_model():
    return FakeToolChatModel(
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


async def answer_permission(app: ScreenApp, key: str):
    async with app.run_test() as pilot:
        await type_line(pilot, "write it")
        for _ in range(POLL_ROUNDS):
            await pilot.pause()
            if isinstance(app.screen, PermissionScreen):
                break
        assert isinstance(app.screen, PermissionScreen)
        await pilot.press(key)
        for _ in range(POLL_ROUNDS):
            await pilot.pause()
            if "done" in log_text(app):
                break
        await pilot.pause()
        return log_text(app)


def test_allow_runs_tool_and_shows_arrow(settings, tmp_path):
    app = ScreenApp(settings, cwd=tmp_path, model=write_model())
    log = asyncio.run(answer_permission(app, "y"))
    assert (tmp_path / "note.txt").read_text() == "hello"
    assert "→ write_file path=note.txt" in log


def test_deny_skips_tool_and_hides_arrow(settings, tmp_path):
    app = ScreenApp(settings, cwd=tmp_path, model=write_model())
    log = asyncio.run(answer_permission(app, "n"))
    assert not (tmp_path / "note.txt").exists()
    assert "→ write_file" not in log


async def run_exit(app: ScreenApp):
    async with app.run_test() as pilot:
        await type_line(pilot, EXIT)
        await pilot.pause()
        return app.is_running


def test_exit_command_closes_app(settings, tmp_path):
    model = FakeToolChatModel(messages=iter([AIMessage(content="pong")]))
    app = ScreenApp(settings, cwd=tmp_path, model=model)
    assert asyncio.run(run_exit(app)) is False


def test_lines_share_shorten_call_and_cost():
    assert shorten("x" * 200).endswith("…")
    assert call_text("read_file", {"path": "note.txt"}) == "read_file path=note.txt"
    line = cost_line(Usage(input_tokens=10), Usage(), 0.0, 0.0)
    assert line.startswith("in 10")
