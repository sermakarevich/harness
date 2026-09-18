# Tutorial 0 — Setup

After this tutorial the reader has a runnable, tested workbench and knows what the series builds.

## In short

### The concepts

An agent is a model plus a harness. The model is an LLM (large language model) that reads text and
writes the next piece of text. The harness is everything around it: the loop that calls it, the
tools it can run, the context it sees, and the rules it must follow. The harness decides most of the
result: one team rose from Top 30 to Top 5 on Terminal-Bench 2.0 by changing only the harness around
the same model, though that is one benchmark and a vendor-reported number (knowledge base:
TheAnatomyOfAnAgentHarness). A second study measured a 6x swing on one benchmark from the harness
alone (knowledge base: MetaHarness). One explainer calls the model "only half the story" and sets
the rule this series follows: "Put rules in code, not wishes in prompts" (knowledge base:
HowToBuildACustomAgentHarness). The cause is plain: the model sees only what the harness puts in its
context and acts only through what the harness runs for it.

### Scope

The finished harness grows into a tool-using loop with a permission gate, saved sessions, cost
tracking, compaction, memory files, skills, sub-agents, and an evaluation suite. This tutorial
builds only the workbench under all of that: settings, offline tests, the task runner, and the
coding rules. No model call happens yet. Tutorial 1 makes one raw HTTP call with no framework and
shows the request is stateless. The series works the same way throughout: one git tag and one `just
tutNN` recipe per tutorial, offline tests, additive code, and one visible limitation fixed at a
time. Read "In short" for the story and "In detail" to build it.

### The problem

```text
$ uv run python -m harness
.venv/bin/python3: No module named harness.__main__; 'harness' is a package and cannot be directly executed
```

### What changes

```text
+ .env.example              key placeholder
+ .gitignore                skipped files
+ .python-version           Python pin
+ AGENTS.md                 coding rules
+ CLAUDE.md                 shared instructions
+ README.md                 project start
+ docs/dev/                 goal, notes, method, template
+ docs/harnesses/           operations, harness notes, raw material
+ docs/tutorials/tut00-setup.md   this document
+ justfile                  task runner
+ pyproject.toml            packages and tool settings
+ uv.lock                   locked versions
+ src/harness/__init__.py   package marker
+ src/harness/py.typed      typing marker
+ src/harness/config.py     settings
+ tests/__init__.py         package marker
+ tests/test_config.py      three offline tests
```

## In detail

### The change, file by file

**New file `src/harness/config.py`**

Settings holds the defaults for the base URL, the model name, and the user agent, while `ENV_*`
constants name the variables that override each field. Loading works in layers from weakest to
strongest: code defaults, then a `.env` file loaded with `override=False`, then real variables in
the surroundings. A real variable beats the file because deploys must win over local files without
anyone editing them. The key is required, so an empty key fails fast with `ConfigError` instead of a
late network error. The key field uses `repr=False`, which keeps it out of every printed object.

```python
"""Settings: where the model lives and the key that lets us in.

Reads the key from the environment so it never leaks into logs. We also send
our own app name with each request because the server blocks generic names.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ENV_API_KEY = "OPENCODE_API_KEY"
ENV_BASE_URL = "HARNESS_BASE_URL"
ENV_MODEL = "HARNESS_MODEL"
ENV_USER_AGENT = "HARNESS_USER_AGENT"


class ConfigError(RuntimeError):
    """Raised when a required setting is missing."""


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    base_url: str = "https://opencode.ai/zen/go/v1"
    model: str = "muse-spark-1.3-contributor"
    user_agent: str = "harness-dev/0.1"


def load_settings(env_file: str | Path | None = None) -> Settings:
    load_dotenv(env_file, override=False)
    api_key = os.environ.get(ENV_API_KEY, "").strip()
    if not api_key:
        raise ConfigError(
            "OPENCODE_API_KEY is not set. Copy .env.example to .env and add your OpenCode Go key."
        )
    return Settings(
        api_key=api_key,
        base_url=os.environ.get(ENV_BASE_URL, Settings.base_url),
        model=os.environ.get(ENV_MODEL, Settings.model),
        user_agent=os.environ.get(ENV_USER_AGENT, Settings.user_agent),
    )
```

**New file `tests/test_config.py`**

`test_load_settings_reads_key` proves the key loads from the environment while model and URL fall
back to defaults. `test_missing_key_raises` proves an empty key fails fast with `ConfigError`.
`test_repr_never_leaks_key` proves the key stays out of printed output.

```python
import pytest

from harness.config import ConfigError, Settings, load_settings


def test_load_settings_reads_key(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test-key-123")
    s = load_settings(env_file="/nonexistent/.env")
    assert s.api_key == "test-key-123"
    assert s.model == "muse-spark-1.3-contributor"
    assert s.base_url.startswith("https://opencode.ai/zen/go")


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("OPENCODE_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        load_settings(env_file="/nonexistent/.env")


def test_repr_never_leaks_key():
    s = Settings(api_key="super-secret")
    assert "super-secret" not in repr(s)
    assert "super-secret" not in str(s)
```

**New file `pyproject.toml`**

Only the pytest block matters here. The `slow` marker names the tests that need a network or a live
model, and `addopts` excludes them, so later tutorials can add live-model tests while `just test`
still runs offline with no key.

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m 'not slow'"
markers = ["slow: needs network or a live model; excluded by default"]
```

**New file `justfile`**

Tutorial 0 has no program to run, so its recipe chains the two checks: install the locked setup,
then run the offline tests.

```just
tut00: setup test
```

### Run it

```bash
git checkout tut00
just tut00
```

```text
uv run pytest -q
...                                                                      [100%]
3 passed
```

### Tests

- `test_load_settings_reads_key`: proves the key loads from the environment while model and URL use
  defaults.
- `test_missing_key_raises`: proves an empty key fails fast with `ConfigError`.
- `test_repr_never_leaks_key`: proves the key never appears in printed output.

### Under the hood

The server rejects generic `User-Agent` values, so sending a named agent string is a transport
requirement rather than decoration. That is why `Settings.user_agent` exists, as the `config.py`
docstring notes.

### Key takeaways

- Agent plus harness: an agent is a model plus a harness, and the harness decides most of the
  result.
- Series arc: the finished harness is a tool-using loop with a permission gate, saved sessions, cost
  tracking, compaction, memory, skills, sub-agents, and evaluation.
- Series mechanics: each tutorial is one tag, one recipe, and offline tests, and each fixes one
  visible limitation; "In short" tells the story and "In detail" builds it.
- Settings layering: defaults live in `Settings`, a `.env` file overrides them, and real variables
  override the file, while the key stays required and hidden from printed output.

### What is still missing

Nothing here talks to a model. Tutorial 1 makes one raw HTTP call with no framework and shows the
request is stateless: everything the model knows must travel inside that single call.
