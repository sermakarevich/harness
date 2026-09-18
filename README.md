# Harness

A hands-on tutorial that builds an *agent harness* (everything around a language
model that is not the model: the loop, tools, memory and safety rules) step by
step in Python with LangGraph, using an OpenCode Go model.

## Quick start

```bash
cp .env.example .env   # then add your OpenCode Go key
just setup
just test
```

`docs/harnesses/` holds background on how three existing harnesses run agents,
cited from the tutorials.

## Tutorial

- [Tutorial 0 — Setup](docs/tutorials/tut00-setup.md)


## For contributors

Everything about how this repo is built lives in `docs/dev/`: the tutorial method
and plan (`TUTORIAL_METHOD.md`), the tutorial template, the goal and the verified
transport notes. Coding rules are in `AGENTS.md`.
