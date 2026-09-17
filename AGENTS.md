# Coding rules for this repository

These rules apply to every file in this repo: code, tests, scripts, and docs.
They bind humans, Claude Code, and fleet workers alike.

## Values, in priority order

1. **Simplicity** — the smallest thing that works. No layers "for later".
2. **Readability** — code reads top to bottom like a short story.
3. **Evolvability** — one module per harness job, so the next step adds a file instead of rewriting one.
4. **Maintainability** — every behaviour has a test that runs without network.

## No comments

- Do not write `#` comments. If code needs a comment to be understood, rename or split it instead.
- One short docstring per module and per public function is allowed. It says what the thing does, in one to three plain sentences.

## Plain English

- Use simple, everyday words in names, docstrings, docs, and commit messages.
- Spell out every abbreviation the first time it appears in a document (for example: LLM, large language model).
- Short sentences. One idea per sentence.

## Project conventions

- Python 3.12+, managed by `uv`; run everything through `uv run` or `just`.
- The model is constructed only in `src/harness/model.py`.
- Secrets live in `.env` and are never printed, logged, or committed.
