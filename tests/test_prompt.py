from harness.chat.prompt import build_system_prompt


def test_system_prompt_mentions_cwd(tmp_path, settings):
    assert str(tmp_path) in build_system_prompt(settings, cwd=tmp_path)


def test_system_prompt_has_today_and_no_placeholders(tmp_path, settings):
    from datetime import date

    prompt = build_system_prompt(settings, cwd=tmp_path)
    assert date.today().isoformat() in prompt
    assert "{" not in prompt
