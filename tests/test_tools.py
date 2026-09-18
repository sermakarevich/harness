"""The file-reading tool stays inside the working directory."""

from harness.tools.read_file import read_file_tool


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
