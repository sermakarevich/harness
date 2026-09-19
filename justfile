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

# Runs the harness twice: the second run resumes the first one's conversation (uses your key; run sparingly)
smoke:
    rm -rf .harness
    printf 'Remember the word banana. Reply with just: ok\n/exit\n' | uv run python -m harness
    printf '/resume 1\nWhich word did I ask you to remember?\n/exit\n' | uv run python -m harness
