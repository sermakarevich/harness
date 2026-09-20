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

# Runs the harness once to show this tutorial (uses your key; run sparingly)
smoke:
    rm -rf .harness
    printf 'What is 2 plus 2? Reply with just the number.\nDo not run shell commands. Write the commit message for adding the skills loader. Reply with the message only.\n/exit\n' | uv run python -m harness
