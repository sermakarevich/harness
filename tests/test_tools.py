"""The file-reading tool stays inside the working directory."""

from harness.tools.edit_file import edit_file_tool
from harness.tools.read_file import read_file_tool
from harness.tools.shell import shell_tool
from harness.tools.write_file import write_file_tool


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
