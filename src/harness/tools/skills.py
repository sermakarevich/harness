"""Skill folders on disk and what each one says it is for.

One directory per skill holds a file describing it. The prompt carries only
each skill's name and one-line description; the full text loads on demand.
"""

from __future__ import annotations

from pathlib import Path

from harness.tools.paths import resolve_inside

SKILL_FILE_NAME = "SKILL.md"
FRONT_MATTER_FENCE = "---"
DESCRIPTION_KEY = "description"
INDEX_LINE = "- {name}: {description}"
UNKNOWN_SKILL_MESSAGE = "unknown skill: {name}"


def split_skill(text: str) -> tuple[str, str]:
    """Description from the front matter and the text after it."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONT_MATTER_FENCE:
        return "", text
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == FRONT_MATTER_FENCE:
            end = i
            break
    if end is None:
        return "", text
    description = ""
    for line in lines[1:end]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip() == DESCRIPTION_KEY:
            description = value.strip()
    return description, "\n".join(lines[end + 1 :])


def skill_descriptions(root: Path, skills_dir: str) -> dict[str, str]:
    """Each skill's name and the one line it describes itself with, sorted by name."""
    base = root / skills_dir
    if not base.is_dir():
        return {}
    found = {}
    for child in sorted(base.iterdir()):
        skill_file = child / SKILL_FILE_NAME
        if not skill_file.is_file():
            continue
        description, _ = split_skill(skill_file.read_text())
        if description:
            found[child.name] = description
    return found


def skill_names(root: Path, skills_dir: str) -> list[str]:
    """Names of the skills the model may load."""
    return list(skill_descriptions(root, skills_dir))


def skill_index(root: Path, skills_dir: str) -> str:
    """One index line per skill, or the empty string when there are none."""
    found = skill_descriptions(root, skills_dir)
    return "\n".join(INDEX_LINE.format(name=name, description=d) for name, d in found.items())


def skill_body(root: Path, skills_dir: str, name: str) -> str | None:
    """Text after the front matter, or None when that skill does not exist."""
    target = resolve_inside(root, str(Path(skills_dir) / name / SKILL_FILE_NAME))
    if target is None or not target.is_file():
        return None
    _, body = split_skill(target.read_text())
    return body
