# Tutorial 0 — Setup
Git tag: `tut00`. Run: `just tut00`.

## What we are building

A harness is everything around the model that is not the model itself.
It holds the loop that calls the model, the tools the model can use, the memory of past turns, and the rules that keep it safe.
An LLM (large language model) is the text-generating model at the center: it reads text and writes the next piece of text.
LangGraph is a Python library that describes an agent as a graph of steps with shared state passed between them.
We build one harness piece by piece, one tutorial per piece, starting here with setup.

## What you need

- `uv` — the Python package and environment manager; it installs everything.
- `just` — the task runner; every tutorial runs as one short `just` command.
- An OpenCode Go key — the secret that lets our code call the model; it goes into `.env` below.

## One tool for the environment

One tool owns the environment, so every reader runs the same code.
That tool is `uv`: `just setup` runs `uv sync`.
`uv sync` reads `pyproject.toml` and `uv.lock` and installs the exact locked versions.
A locked file means no surprise upgrades between machines.
Run `just setup`.

You should see lines like these at the end:

```
Resolved 57 packages in 20ms
Checked 55 packages in 1ms
```

## The secret stays in .env

A secret pasted into code ends up in git history, where every clone keeps it.
So the key lives in `.env`, and `.env` is gitignored and never committed.
Copy the example file with `cp .env.example .env` (it prints nothing).
Then open `.env` and replace the placeholder with your real key.
The code reads the key from the environment at startup and hides it from debug output:

src/harness/config.py
```python
api_key: str = field(repr=False)
```

`repr=False` keeps the key out of `repr()`, the text Python prints when it shows an object.

## Tests run without network

The three tests use a fake key and a missing file path, so they never touch the network.
They prove the key loads from the environment, a missing key raises an error, and the key never appears in printed output.
One of them:

tests/test_config.py
```python
def test_repr_never_leaks_key():
    s = Settings(api_key="super-secret")
    assert "super-secret" not in repr(s)
    assert "super-secret" not in str(s)
```

Run `just test`.

You should see this last line:

```
3 passed in 0.01s
```

## The tree

```
.env.example — placeholder key; copy it to .env
.gitignore — keeps .env, caches, and virtualenvs out of git
.python-version — pins the Python version for uv
AGENTS.md — coding rules for this repo
CLAUDE.md — pointer to the shared harness instructions
README.md — what the project is and how to start
justfile — short commands: setup, test, tut00
pyproject.toml — package list and tool settings
uv.lock — exact locked versions of every package
docs/dev/GOAL.md — goal and plan of the tutorial
docs/dev/NOTES.md — verified notes from the live model spike
docs/dev/TUTORIAL_METHOD.md — how tutorials, tags, and diffs work
docs/dev/_TEMPLATE.md — shape of every tutorial document
docs/harnesses/OPERATIONS.md — the operations we are building toward
docs/harnesses/hermes.md — what the hermes harness does
docs/harnesses/opencode.md — what the opencode harness does
docs/harnesses/pi.md — what the pi harness does
docs/harnesses/_raw/hermes-inventory.md — raw notes on hermes
docs/harnesses/_raw/opencode-inventory.md — raw notes on opencode
docs/harnesses/_raw/pi-inventory.md — raw notes on pi
src/harness/__init__.py — package marker with a short description
src/harness/config.py — settings and key loading from .env
src/harness/py.typed — marks the package as typed
tests/__init__.py — marks the tests as a package
tests/test_config.py — the three offline tests
```

## Run it

```bash
git checkout tut00
just tut00
```

Last lines you should see:

```
3 passed in 0.00s
```

## What is still missing

Nothing here talks to a model yet.
Tutorial 1 makes one raw call and prints `pong`.
