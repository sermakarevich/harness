"""Skill folders under throwaway directories, never the work tree."""

from harness.tools.skills import skill_body, skill_index, skill_names, split_skill

SKILL_TEXT = """---
description: A short note.
---

# Body here
"""


def write_skill(root, name, text=SKILL_TEXT):
    folder = root / "skills" / name
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(text)
    return folder


def test_split_skill_returns_description_and_body():
    description, body = split_skill(SKILL_TEXT)
    assert description == "A short note."
    assert "# Body here" in body
    assert "description" not in body


def test_split_skill_without_front_matter_has_no_description():
    description, body = split_skill("# Just a body\n")
    assert description == ""
    assert body == "# Just a body\n"


def test_skill_names_finds_skills_sorted_and_skips_gaps(tmp_path):
    write_skill(tmp_path, "second")
    write_skill(tmp_path, "first")
    empty = tmp_path / "skills" / "empty"
    empty.mkdir()
    undescribed = tmp_path / "skills" / "undescribed"
    undescribed.mkdir()
    (undescribed / "SKILL.md").write_text("# No front matter\n")
    assert skill_names(tmp_path, "skills") == ["first", "second"]


def test_skill_index_lists_one_line_per_skill(tmp_path):
    write_skill(tmp_path, "commit-message", SKILL_TEXT)
    index = skill_index(tmp_path, "skills")
    assert index == "- commit-message: A short note."


def test_skill_index_is_empty_without_skills_folder(tmp_path):
    assert skill_index(tmp_path, "skills") == ""


def test_skill_body_returns_body_without_front_matter(tmp_path):
    write_skill(tmp_path, "commit-message", SKILL_TEXT)
    body = skill_body(tmp_path, "skills", "commit-message")
    assert body is not None
    assert "# Body here" in body
    assert "description" not in body


def test_skill_body_is_none_for_missing_skill(tmp_path):
    write_skill(tmp_path, "commit-message", SKILL_TEXT)
    assert skill_body(tmp_path, "skills", "no-such-skill") is None


def test_skill_body_is_none_for_path_leaving_the_tree(tmp_path):
    write_skill(tmp_path, "commit-message", SKILL_TEXT)
    assert skill_body(tmp_path, "skills", "../..") is None
    assert skill_body(tmp_path, "skills", "../../etc") is None
