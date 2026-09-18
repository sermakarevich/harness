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

Start with the tutorials below. `docs/harnesses/` holds background on how three
existing harnesses run agents, cited from the tutorials.

## Tutorial

- [Tutorial 0 — Setup](docs/tutorials/tut00-setup.md): workbench, layout, secrets.
- [Tutorial 1 — One raw call](docs/tutorials/tut01-raw-call.md): plain HTTP, no framework.
- [Tutorial 2 — The LangChain adapter](docs/tutorials/tut02-langchain-adapter.md): one interface for any model.
- [Tutorial 3 — The conversation loop](docs/tutorials/tut03-conversation-loop.md): memory within a session.

Run them as `just tut00`, `just tut01`, `just tut02`, `just tut03`.


## For contributors

Everything about how this repo is built lives in `docs/dev/`: the tutorial method
and plan (`TUTORIAL_METHOD.md`), the tutorial template, the architecture map
(`ARCHITECTURE.md`), the goal and the verified transport notes. Coding rules are in
`AGENTS.md`.
