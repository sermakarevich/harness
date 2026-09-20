"""The file-reading tool stays inside the working directory."""

import threading
import time

from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from harness.chat.run_tools import build_run_tools
from harness.tools.edit_file import edit_file_tool
from harness.tools.read_file import read_file_tool
from harness.tools.shell import shell_tool
from harness.tools.write_file import write_file_tool


def tool_state(*calls):
    return {
        "messages": [AIMessage(content="", tool_calls=list(calls))],
        "always_allowed": [],
    }


def named_call(name, args, call_id):
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


def test_reads_file_inside_cwd(tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("hello")
    assert read_file_tool(tmp_path).invoke({"path": "note.txt"}) == "hello"


def test_missing_file_returns_not_found(tmp_path):
    assert read_file_tool(tmp_path).invoke({"path": "gone.txt"}) == "file not found: gone.txt"


def test_path_outside_cwd_returns_outside(tmp_path):
    assert read_file_tool(tmp_path).invoke({"path": ".."}) == (
        "path is outside the working directory: .."
    )


def test_write_creates_file(tmp_path):
    assert write_file_tool(tmp_path).invoke({"path": "note.txt", "content": "hello"}) == (
        "wrote note.txt"
    )
    assert (tmp_path / "note.txt").read_text() == "hello"


def test_write_creates_missing_folders(tmp_path):
    assert (
        write_file_tool(tmp_path).invoke({"path": "sub/note.txt", "content": "hello"})
        == "wrote sub/note.txt"
    )
    assert (tmp_path / "sub" / "note.txt").read_text() == "hello"


def test_write_outside_cwd_returns_outside(tmp_path):
    assert write_file_tool(tmp_path).invoke({"path": "../note.txt", "content": "hi"}) == (
        "path is outside the working directory: ../note.txt"
    )


def test_edit_replaces_one_occurrence(tmp_path):
    (tmp_path / "note.txt").write_text("hello world")
    assert (
        edit_file_tool(tmp_path).invoke(
            {"path": "note.txt", "old_text": "world", "new_text": "there"}
        )
        == "edited note.txt"
    )
    assert (tmp_path / "note.txt").read_text() == "hello there"


def test_edit_missing_text_returns_not_found(tmp_path):
    (tmp_path / "note.txt").write_text("hello")
    assert (
        edit_file_tool(tmp_path).invoke({"path": "note.txt", "old_text": "bye", "new_text": "hi"})
        == "old_text not found in note.txt"
    )


def test_edit_repeated_text_returns_count(tmp_path):
    (tmp_path / "note.txt").write_text("hi hi")
    assert (
        edit_file_tool(tmp_path).invoke({"path": "note.txt", "old_text": "hi", "new_text": "yo"})
        == "old_text appears 2 times in note.txt; include more surrounding text"
    )


def test_edit_missing_file_returns_not_found(tmp_path):
    assert (
        edit_file_tool(tmp_path).invoke({"path": "gone.txt", "old_text": "a", "new_text": "b"})
        == "file not found: gone.txt"
    )


def test_shell_echo_returns_output_and_exit_code(tmp_path):
    out = shell_tool(tmp_path, 60).invoke({"command": "echo hi"})
    assert "hi" in out
    assert "exit code: 0" in out


def test_shell_stderr_and_nonzero_exit(tmp_path):
    out = shell_tool(tmp_path, 60).invoke({"command": "echo bad >&2; exit 3"})
    assert "bad" in out
    assert "exit code: 3" in out


def test_shell_runs_in_working_directory(tmp_path):
    out = shell_tool(tmp_path, 60).invoke({"command": "pwd"})
    assert str(tmp_path.resolve()) in out


def test_shell_timeout_returns_timeout_message(tmp_path):
    assert shell_tool(tmp_path, 1).invoke({"command": "sleep 5"}) == (
        "command timed out after 1 seconds"
    )


def test_three_calls_run_together(settings):
    barrier = threading.Barrier(3)

    @tool("read_file")
    def gated() -> str:
        """Wait until all three calls have started."""
        barrier.wait(timeout=5)
        return "ok"

    node = build_run_tools([gated], lambda text: text, settings.max_parallel_tools)
    state = tool_state(
        named_call("read_file", {}, "call-1"),
        named_call("read_file", {}, "call-2"),
        named_call("read_file", {}, "call-3"),
    )
    result = node(state)
    assert [message.content for message in result["messages"]] == ["ok", "ok", "ok"]


def test_messages_come_back_in_model_order(settings):
    @tool("read_file")
    def delayed(pause: float) -> str:
        """Reply after a pause."""
        time.sleep(pause)
        return f"waited {pause}"

    node = build_run_tools([delayed], lambda text: text, settings.max_parallel_tools)
    state = tool_state(
        named_call("read_file", {"pause": 0.3}, "call-1"),
        named_call("read_file", {"pause": 0.0}, "call-2"),
        named_call("read_file", {"pause": 0.1}, "call-3"),
    )
    result = node(state)
    assert [message.tool_call_id for message in result["messages"]] == [
        "call-1",
        "call-2",
        "call-3",
    ]
    assert [message.content for message in result["messages"]] == [
        "waited 0.3",
        "waited 0.0",
        "waited 0.1",
    ]
