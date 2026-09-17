# Task runner for the harness tutorial. `just` alone lists recipes.
set dotenv-load := true

default:
    @just --list

# Install the exact locked environment
setup:
    uv sync

# Start the terminal chat (added in a later step)
run:
    uv run python -m harness

fmt:
    uv run ruff format .
    uv run ruff check --fix .

lint:
    uv run ruff check .
    uv run ruff format --check .

test:
    uv run pytest -q

# Chapter 0 has no code to run; it is `just setup` + `just test`
ch00: setup test

# Chapter 1: one raw HTTP call to the model, no framework
ch01:
    uv run python scripts/raw_call.py

# Chapter 2: the LangChain adapter live check
ch02: smoke

# Chapter 3: the conversation loop in the terminal
ch03: run

# Live check of the LangChain adapter (uses your key; run sparingly)
smoke:
    uv run python scripts/smoke_model.py

# Non-interactive smoke of the chat: pipes two lines in (uses your key; run sparingly)
smoke-tui:
    printf 'Reply with exactly one word: pong\n/exit\n' | uv run python -m harness
