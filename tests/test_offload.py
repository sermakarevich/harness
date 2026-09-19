"""Long tool results spill to disk; short ones pass through."""

from pathlib import Path

from harness.tools.offload import build_offload

LIMIT = 20
OUTPUT_DIR = ".harness/outputs"


def spill(root: Path):
    return build_offload(root, LIMIT, OUTPUT_DIR)


def test_short_text_returns_unchanged_and_writes_nothing(tmp_path):
    assert spill(tmp_path)("hello") == "hello"
    assert not (tmp_path / OUTPUT_DIR).exists()


def test_text_at_limit_returns_unchanged(tmp_path):
    text = "x" * LIMIT
    assert spill(tmp_path)(text) == text
    assert not (tmp_path / OUTPUT_DIR).exists()


def test_long_text_returns_prefix_with_notice(tmp_path):
    text = "y" * (LIMIT + 5)
    result = spill(tmp_path)(text)
    assert result.startswith(text[:LIMIT])
    assert str(len(text)) in result
    assert str(tmp_path) not in result


def test_long_text_file_holds_whole_text(tmp_path):
    text = "z" * (LIMIT + 50)
    result = spill(tmp_path)(text)
    spilled = list((tmp_path / OUTPUT_DIR).glob("*"))
    assert len(spilled) == 1
    assert spilled[0].read_text() == text
    assert spilled[0].relative_to(tmp_path).as_posix() in result


def test_same_text_twice_leaves_one_file(tmp_path):
    text = "w" * (LIMIT + 50)
    offload = spill(tmp_path)
    assert offload(text) == offload(text)
    assert len(list((tmp_path / OUTPUT_DIR).glob("*"))) == 1
