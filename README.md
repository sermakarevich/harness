# Harness

A hands-on tutorial that builds an *agent harness* (everything around a language
model that is not the model: the loop, tools, memory and safety rules) step by
step in Python with LangGraph, using an OpenCode Go model.

## Quick start

```bash
cp .env.example .env   # then add your OpenCode Go key
just setup
just test
just run               # terminal chat, arrives in tutorial 3
```

Start with the tutorials below. `docs/harnesses/` holds background on how three
existing harnesses run agents, cited from the tutorials.

## How to follow the tutorials

Each tutorial is a document in `docs/tutorials/` and a git tag (`tut00`, `tut01`, ...).
Read the documents here on `main`; run the code at the tag. `main` is the latest code and
is not kept runnable for older tutorials. The tag is frozen and always matches its document.

The document has two layers. **In short** gives the concepts, the scope and the problem
in plain language, no code. **In detail** explains how the code works and why it is built
that way. Read only the first layer of every tutorial for the story; read the second to
build it.

For each tutorial:

```bash
git checkout tut01              # the code exactly as the tutorial describes it
just setup                      # once per checkout, installs the locked environment
just tutorial                   # shows what this tutorial built
just test                       # the tests for this tutorial, no network needed
git diff tut00..tut01 --stat    # every file this tutorial added or changed
```

Tutorials are additive: nothing under an older tag is rewritten later, so the diff
between two neighbouring tags is exactly one concept. `git tag --list 'tut*'` shows how
far the series goes. `git checkout main` returns to the latest code.

You need `uv`, `just` and an OpenCode Go key in `.env` (see `.env.example`). Tutorials
that call the model say so; everything else runs offline.

## Tutorials

| Tutorial | Tag | Document |
|---|---|---|
| 0 — Setup | `tut00` | [tut00-setup.md](docs/tutorials/tut00-setup.md) |
| 1 — One raw model call | `tut01` | [tut01-raw-call.md](docs/tutorials/tut01-raw-call.md) |

More rows appear as tags are published. The full plan is in `docs/dev/TUTORIAL_METHOD.md`.

## For contributors

Everything about how this repo is built lives in `docs/dev/`: the tutorial method
and plan (`TUTORIAL_METHOD.md`), the tutorial template, the architecture map
(`ARCHITECTURE.md`), the goal and the verified transport notes. Coding rules are in
`AGENTS.md`.
