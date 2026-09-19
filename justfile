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

# Runs the harness once through compaction (uses your key; run sparingly)
smoke:
    rm -rf .harness
    printf 'Run the shell command \"seq 1 2000\" and then reply with just: done\na\nRun the shell command \"seq 2001 4000\" and then reply with just: done\nRun the shell command \"seq 4001 6000\" and then reply with just: done\nWhat is 2 plus 2? Reply with just the number.\nWhat is 3 plus 3? Reply with just the number.\n/exit\n' | uv run python -m harness
