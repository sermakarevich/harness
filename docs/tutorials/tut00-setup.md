# Tutorial 0 — Setup

After this tutorial you have a runnable, tested workbench and know what the series builds.

## In short

### The concepts

An agent is a model plus a harness. The model is an LLM (large language model) that reads text and
writes the next piece of text. The harness is everything around it:

- the loop that calls the model
- the tools the model can run
- the context the model sees
- the rules the model must follow

The harness decides most of the result. One team rose from Top 30 to Top 5 on Terminal-Bench 2.0
by changing only the harness around the same model (knowledge base: TheAnatomyOfAnAgentHarness).
A second study measured a 6x swing from the harness alone (knowledge base: MetaHarness). The rule
this series follows comes from a third source: "Put rules in code, not wishes in prompts"
(knowledge base: HowToBuildACustomAgentHarness). The cause is plain: the model sees only what the
harness puts in its context and acts only through what the harness runs for it.

### Scope

This tutorial does two things:

1. You get an OpenCode Go key. The Go subscription costs 10 USD a month and is enough for the
   whole series. The key goes into a local `.env` file and nowhere else.
2. You set up the codebase scaffold: a `harness` package, settings loaded from the environment,
   offline tests, and a `just` task runner.

No model call happens yet. Tutorial 1 makes the first one.

Every later tutorial grows this scaffold by one concept. The finished harness has:

- a tool-using loop with a permission gate
- saved sessions and cost tracking
- compaction and memory files
- skills and sub-agents
- an evaluation suite

Each tutorial is one git tag with a `just tutorial` recipe and offline tests. Code runs at the
tag; documents are read on `main`.

### The problem

```text
$ uv run python -m harness
.venv/bin/python3: No module named harness.__main__; 'harness' is a package and cannot be directly executed
```

### What changes

```text
+ .env.example              key placeholder
+ AGENTS.md                 coding rules
+ justfile                  task runner
+ pyproject.toml, uv.lock   packages, locked versions
+ src/harness/config.py     settings
+ src/harness/settings.toml  defaults
+ tests/test_config.py      three offline tests
+ docs/                     tutorials, background on other harnesses, method
```

## In detail

### How it works

Settings are the first harness job: the model name, the endpoint, and the key all come from the
environment, never from code. That is what lets the same harness talk to another model later by
changing one line in `.env`. The key is required and the harness fails at startup when it is
missing, so a broken setup surfaces before the first model call, not during it.

Tests never touch the network. Anything that calls the live model is marked `slow` and excluded by
default, so `just test` is free and fast from tutorial 0 to the end of the series.

### Design decisions

- **Model as a setting, not a constant.** The series is about the harness, so the model must be
  swappable without touching harness code.
- **Offline tests by default.** A harness has many moving parts; a test suite that costs money and
  minutes per run would not be run.

### Run it

```bash
git checkout tut00
cp .env.example .env    # paste your OpenCode Go key
just tutorial
```

```text
3 passed
```

### Under the hood

The OpenCode server rejects generic `User-Agent` values, so the harness sends a named one. It is
the first example of a rule the harness enforces in code rather than hopes for.

### Key takeaways

- An agent is a model plus a harness, and the harness decides most of the result.
- The harness controls two things: what the model sees and what it can do.
- The model is a setting; the harness must outlive any single model.

### What is still missing

Nothing here talks to a model. Tutorial 1 makes one raw HTTP call with no framework and shows the
request is stateless: everything the model knows must travel inside that single call.
