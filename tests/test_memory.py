"""Instruction files under throwaway directories, never the work tree."""

from harness.chat.memory import build_notes, memory_paths, short_path

NAMES = ("AGENTS.md", "CLAUDE.md")


def test_note_in_working_directory_is_found(tmp_path):
    (tmp_path / "AGENTS.md").write_text("work note")
    assert memory_paths(tmp_path, NAMES) == [tmp_path / "AGENTS.md"]


def test_first_name_wins_in_one_directory(tmp_path):
    (tmp_path / "AGENTS.md").write_text("first")
    (tmp_path / "CLAUDE.md").write_text("second")
    assert memory_paths(tmp_path, NAMES) == [tmp_path / "AGENTS.md"]


def test_parent_note_comes_before_nearer_one(tmp_path):
    child = tmp_path / "child"
    child.mkdir()
    (tmp_path / "AGENTS.md").write_text("parent note")
    (child / "AGENTS.md").write_text("child note")
    assert memory_paths(child, NAMES) == [tmp_path / "AGENTS.md", child / "AGENTS.md"]


def test_no_notes_gives_empty_list_and_empty_block(tmp_path):
    assert memory_paths(tmp_path, ("ONLY.md",)) == []
    assert build_notes(tmp_path, ("ONLY.md",)) == ""


def test_block_names_each_file_and_carries_its_text(tmp_path):
    child = tmp_path / "child"
    child.mkdir()
    (tmp_path / "AGENTS.md").write_text("parent note")
    (child / "CLAUDE.md").write_text("child note")
    notes = build_notes(child, NAMES)
    assert short_path(tmp_path / "AGENTS.md", child) in notes
    assert short_path(child / "CLAUDE.md", child) in notes
    assert "parent note" in notes
    assert "child note" in notes
    assert notes.index("parent note") < notes.index("child note")
