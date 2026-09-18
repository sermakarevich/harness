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

### How it works

Running just tut00 starts with the recipes defined in justfile. Before any recipe runs, just
loads the variables from the environment file into the process, so every step sees them. The
setup recipe then runs uv sync, which builds the locked environment from pyproject.toml and
uv.lock so every reader gets the same packages. Finally pytest runs the suite in tests with the slow marker excluded by the
configuration in pyproject.toml, so no network or key is needed.

When Python code needs settings it calls load_settings from the config module in
src/harness/config.py. That function reads the environment file without overriding real
environment variables, so deploys win over local files. It then looks for the key and fails
fast with ConfigError when the key is missing or blank instead of failing later at request
time. Every other field falls back to its default in Settings, so base URL, model, and user
agent work with no extra setup. The call returns a frozen Settings object that carries the
resolved values together. That object hides the key from printed forms, so repr and str never
leak it into logs.

### Design decisions

- A frozen dataclass with plain defaults keeps settings in one readable place with few moving
  parts, and the price is no validation beyond the key. A settings library was rejected because
  it would add concepts and config layers for four fields.
- Environment variable names live in `ENV_*` constants next to the settings they feed, so a
  rename is one edit in one file. String literals at each call site were rejected because the
  same name would drift across copies.
- Live-model tests carry the `slow` marker and stay excluded by default, so `just test` runs
  offline with no key and no network. Mocking the vendor API in every test was rejected because
  it would freeze fake request shapes instead of testing real settings behavior.
- Only the key is required and every other field ships with a default that works, so a new
  reader runs with one line in the environment file. Requiring every field up front was rejected
  because it would force setup work before the first run teaches anything.

### The excerpt that carries the idea

**New file `src/harness/config.py`**

```python
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

The `override=False` argument keeps real environment variables ahead of the file, so a local
file never wins on a deploy by accident. The empty-key branch raises `ConfigError` at once, so
a missing key stops at startup with a fix instead of a late network error.

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
