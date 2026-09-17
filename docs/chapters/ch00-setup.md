# Chapter 0 — Setup: your workbench before the first model call

A **harness** is everything around the model that is not the model itself:
the loop that calls it, the tools it can use, the memory it keeps, and the
rules that keep it safe and on budget. The common shorthand is
`agent = model + harness`.

Over the whole tutorial we will build such a harness piece by piece in
Python, using LangGraph (a Python library for describing an agent as a graph
of steps with explicit state passed between them). Each chapter fixes one
limitation of a bare model call; the full list of the 24 harness operations
we are working toward lives in `docs/harnesses/OPERATIONS.md` — skim its
intro, the at-a-glance table, and the "Build order" section now, and treat it
as the map for the entire journey. This chapter only sets up the workbench.

## Prerequisites

- `uv` — the Python package and environment manager used by this project.
- `just` — the task runner; every chapter runs as `just chNN`.
- An OpenCode Go subscription key — the secret that authenticates our model
  calls (a Large Language Model, LLM for short, is the text-generating
  Artificial Intelligence model behind every chapter).

## Hands-on

Copy the example environment file and put your key in it:

```bash
cp .env.example .env   # then replace the placeholder with your real key
```

The placeholder line inside looks like this:

```bash
OPENCODE_API_KEY=your-opencode-go-key-here
```

Then install the locked environment and run the test suite:

```bash
just setup
just test
```

Both must finish green before you continue. `just setup` runs `uv sync`;
`just test` runs `pytest` (a Python test runner) over `tests/`.

## Project layout

```text
src/harness/config.py    settings and key loading from `.env`
src/harness/model.py     LangChain adapter for OpenCode Go (chapter 2)
src/harness/state.py     conversation state for the graph (chapter 3)
src/harness/prompt.py    system prompt assembly (chapter 3)
src/harness/graph.py     the LangGraph conversation loop (chapter 3)
src/harness/session.py   one conversation id plus its model and graph
src/harness/tui/app.py   terminal chat: read a line, stream a reply (TUI,
                         a Terminal User Interface you interact with by typing)
src/harness/__main__.py  `just run` entry point: starts the terminal chat
scripts/raw_call.py      chapter 1: one raw HTTP call, no framework
docs/NOTES.md            verified transport notes from the live spike
docs/harnesses/OPERATIONS.md  the 24 operations we are building toward
```

## Why the key lives in `.env` and never in code

A secret pasted into source code ends up in git history forever, where every
clone carries it. `.env` is gitignored, so it stays on your machine only, and
`load_settings()` in `src/harness/config.py` reads it at startup. As a second
lock, the `Settings` dataclass marks the field with `field(repr=False)`:

```python
api_key: str = field(repr=False)
```

That one flag excludes the key from `repr()` (the debug representation
Python prints for objects), so the key can never leak into logs or error
messages. Run `just setup` and `just test` once more if you changed anything —
chapter 1 makes the first live call.
