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

# Shows what the latest tutorial built
tutorial: run

# Live check of the LangChain adapter (uses your key; run sparingly)
smoke:
    uv run python scripts/smoke_model.py

# Non-interactive smoke of the chat: pipes two lines in (uses your key; run sparingly)
smoke-tui:
    printf 'Reply with exactly one word: pong\n/exit\n' | uv run python -m harness
