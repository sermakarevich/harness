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

# Pipes a write, test, fix exchange into the chat, then removes the scratch files (uses your key; run sparingly)
smoke:
    printf 'Write scratch_math.py with a function add(a, b) that on purpose returns a - b, and test_scratch_math.py with one test that add(2, 3) == 5. Then run pytest -q test_scratch_math.py and tell me the result in one line.\nNow fix the bug in scratch_math.py with the smallest possible edit, run the same pytest command again and tell me the result in one line.\n/exit\n' | uv run python -m harness
    rm -f scratch_math.py test_scratch_math.py
