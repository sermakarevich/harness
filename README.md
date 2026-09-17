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
