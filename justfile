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
    printf 'Use the shell tool three times in this one turn, as three separate calls: sleep 5, sleep 5, sleep 5. Do not combine them into one command. Then reply done.\na\n/exit\n' | uv run python -m harness

# Shows the retry path against a closed port (no server, no cost)
retries:
    printf 'What is 2 plus 2? Reply with just the number.\n/exit\n' | HARNESS_BASE_URL=http://127.0.0.1:1 uv run python -m harness
