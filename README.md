# Harness

A hands-on tutorial that builds an *agent harness* (everything around a language
model that is not the model: the loop, tools, memory and safety rules) step by
step in Python with LangGraph, using an OpenCode Go model.

## Quick start

```bash
cp .env.example .env   # then add your OpenCode Go key
just setup
just test
just run               # terminal chat arrives in a later step
```

See `docs/GOAL.md` for the tutorial plan and `docs/harnesses/OPERATIONS.md` for
background on how harnesses run agents.

## Tutorial

- [Tutorial 0 — Setup](docs/tutorials/tut00-setup.md): workbench, layout, secrets.
- [Tutorial 1 — One raw call](docs/tutorials/tut01-raw-call.md): plain HTTP, no framework.
- [Tutorial 2 — The LangChain adapter](docs/tutorials/tut02-langchain-adapter.md): one interface for any model.
- [Tutorial 3 — The conversation loop](docs/tutorials/tut03-conversation-loop.md): memory within a session.

Run them as `just tut00`, `just tut01`, `just tut02`, `just tut03`.
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the code maps to the
24 harness operations.
