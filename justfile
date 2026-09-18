# Task runner for the harness tutorial. `just` alone lists recipes.
set dotenv-load := true

default:
    @just --list

# Install the exact locked environment
setup:
    uv sync

# Start the harness
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

# Shows what this tutorial built
tutorial: run

# Pipes a fixed exchange into the chat (uses your key; run sparingly)
smoke:
    printf 'Remember this word: pelican\nWhich word did I ask you to remember? Answer with the word only.\n/exit\n' | uv run python -m harness
