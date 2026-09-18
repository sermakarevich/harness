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

# Pipes a request that writes a file and one that deletes it, allowing the first and refusing the second (uses your key; run sparingly)
smoke:
    printf 'Create a file hello.txt here containing the word hello. Do not run any other tool afterwards.\ny\nNow delete hello.txt with a shell command.\nn\n/exit\n' | uv run python -m harness
    rm -f hello.txt
