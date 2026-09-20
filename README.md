# Harness

A hands-on tutorial that builds an *agent harness* (everything around a language
model that is not the model: the loop, tools, memory and safety rules) step by
step in Python with LangGraph, using an OpenCode Go model.

## Quick start

```bash
cp .env.example .env   # then add your OpenCode Go key
just setup
just test
just run               # terminal chat
```

`docs/harnesses/` holds background on how four existing harnesses run agents,
cited from the tutorials. The notes the tutorials cite as "knowledge base" live in the
[agent harness topic](https://github.com/sermakarevich/knowlegde_base/tree/main/knowledge/structured_papers/agent_harness)
of the author's knowledge base.

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

Each tutorial adds one concept. A concept arrives in its simplest form and a later tutorial
replaces it with the real one, so the diff between two neighbouring tags is one concept and
nothing stays in the tree that the finished harness does not use. `git tag --list 'tut*'` shows how
far the series goes. `git checkout main` returns to the latest code.

You need `uv`, `just` and an OpenCode Go key in `.env` (see `.env.example`). Tutorials
that call the model say so; everything else runs offline.

## Tutorials

| Tutorial | Tag | Document |
|---|---|---|
| 0 — Setup | `tut00` | [tut00-setup.md](docs/tutorials/tut00-setup.md) |
| 1 — One raw model call | `tut01` | [tut01-raw-call.md](docs/tutorials/tut01-raw-call.md) |
| 2 — Messages stack into memory | `tut02` | [tut02-messages.md](docs/tutorials/tut02-messages.md) |
| 3 — Graph, streaming, terminal | `tut03` | [tut03-graph.md](docs/tutorials/tut03-graph.md) |
| 4 — Tools and the agent loop | `tut04` | [tut04-tools.md](docs/tutorials/tut04-tools.md) |
| 5 — File tools and the shell tool | `tut05` | [tut05-file-shell.md](docs/tutorials/tut05-file-shell.md) |
| 6 — Permission gate | `tut06` | [tut06-permission.md](docs/tutorials/tut06-permission.md) |
| 7 — Session persistence | `tut07` | [tut07-persistence.md](docs/tutorials/tut07-persistence.md) |
| 8 — Token accounting and cost | `tut08` | [tut08-cost.md](docs/tutorials/tut08-cost.md) |
| 9 — Tool output offloading | `tut09` | [tut09-offload.md](docs/tutorials/tut09-offload.md) |
| 10 — Context compaction | `tut10` | [tut10-compaction.md](docs/tutorials/tut10-compaction.md) |
| 11 — Memory files | `tut11` | [tut11-memory.md](docs/tutorials/tut11-memory.md) |
| 12 — Skills | `tut12` | [tut12-skills.md](docs/tutorials/tut12-skills.md) |
| 13 — Reliability and parallel tools | `tut13` | planned |
| 14 — Planning and todos | `tut14` | planned |
| 15 — Sub-agents | `tut15` | planned |
| 16 — Outside tool servers, MCP | `tut16` | planned |
| 17 — Evaluation | `tut17` | planned |

A row says `planned` until its tag is published. The concept behind each row and the
order of the story are in `docs/dev/TUTORIAL_METHOD.md`.

## For contributors

Everything about how this repo is built lives in `docs/dev/`: the tutorial method
and plan (`TUTORIAL_METHOD.md`), the tutorial template, the goal and the verified
transport notes. Coding rules are in `AGENTS.md`.
