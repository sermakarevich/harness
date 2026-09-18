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

# Pipes a file-reading request into the chat (uses your key; run sparingly)
smoke:
    printf 'Read the file README.md and tell me its first heading. Answer with the heading only.\n/exit\n' | uv run python -m harness
