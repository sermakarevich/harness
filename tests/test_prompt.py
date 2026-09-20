from harness.chat.prompt import build_system_prompt


def test_system_prompt_mentions_cwd(tmp_path, settings):
    assert str(tmp_path) in build_system_prompt(settings, cwd=tmp_path)


def test_system_prompt_has_today_and_no_placeholders(tmp_path, settings):
    from datetime import date

    prompt = build_system_prompt(settings, cwd=tmp_path)
    assert date.today().isoformat() in prompt
    assert "{" not in prompt


def test_note_in_working_directory_reaches_system_prompt(tmp_path, settings):
    (tmp_path / "AGENTS.md").write_text("Always greet with hello.")
    prompt = build_system_prompt(settings, cwd=tmp_path)
    assert "Always greet with hello." in prompt
    assert "AGENTS.md" in prompt


def test_note_with_braces_reaches_prompt_unchanged(tmp_path, settings):
    (tmp_path / "AGENTS.md").write_text("Use {cwd} for paths.")
    prompt = build_system_prompt(settings, cwd=tmp_path)
    assert "Use {cwd} for paths." in prompt


def test_skill_index_reaches_prompt_without_body(tmp_path, settings):
    skill = tmp_path / "skills" / "commit-message"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\ndescription: The house format for a commit message.\n---\n\n# Commit messages\n"
    )
    prompt = build_system_prompt(settings, cwd=tmp_path)
    assert "commit-message" in prompt
    assert "The house format for a commit message." in prompt
    assert "# Commit messages" not in prompt


def test_skill_description_with_braces_reaches_prompt_unchanged(tmp_path, settings):
    skill = tmp_path / "skills" / "paths"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\ndescription: Use {cwd} for paths.\n---\n\nBody\n")
    prompt = build_system_prompt(settings, cwd=tmp_path)
    assert "Use {cwd} for paths." in prompt
