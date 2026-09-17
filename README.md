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

See `GOAL.md` for the tutorial plan and `docs/harnesses/OPERATIONS.md` for
background on how harnesses run agents.

## Tutorial

- [Chapter 0 — Setup](docs/chapters/ch00-setup.md): workbench, layout, secrets.
- [Chapter 1 — One raw call](docs/chapters/ch01-raw-call.md): plain HTTP, no framework.
- [Chapter 2 — The LangChain adapter](docs/chapters/ch02-langchain-adapter.md): one interface for any model.
- [Chapter 3 — The conversation loop](docs/chapters/ch03-conversation-loop.md): memory within a session.

Run them as `just ch00`, `just ch01`, `just ch02`, `just ch03`.
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the code maps to the
24 harness operations.
