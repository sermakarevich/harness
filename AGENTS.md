# Coding rules for this repository

These rules apply to every file in this repo: code, tests, scripts, and docs.
They bind humans, Claude Code, and fleet workers alike.

## Values, in priority order

1. **Simplicity** — the smallest thing that works. No layers "for later".
2. **Readability** — code reads top to bottom like a short story.
3. **Evolvability** — one module per harness job, so the next step adds a file instead of rewriting one.
4. **Maintainability** — every behaviour has a test that runs without network.

## No comments unless absolutely necessary

- Do not write `#` comments. If code needs a comment to be understood, rename or split it instead.
- The only exception is a fact the code cannot show, such as a vendor quirk or a workaround for a bug. Then one short comment, with the reason.
- One short docstring per module and per public function is allowed. It says what the thing does, in one to three plain sentences.

## Plain English

- Use simple, everyday words in names, docstrings, docs, and commit messages.
- Spell out every abbreviation the first time it appears in a document (for example: LLM, large language model).
- Short sentences. One idea per sentence.

## Hierarchy: high calls low, folders show the layers

- Code is organised top-down. A higher-level function calls lower-level functions, never the other way round. Imports point down the hierarchy only; no cycles.
- Folders mirror the layers. The entry point sits at the top, then the user interface, then the conversation logic, then model transport, then settings at the bottom.
- Each file is small and does one thing. A file that needs a second job gets a sibling file, not a second class.
- A file name says what the file does in one or two plain words (`prompt.py`, `render.py`), never `utils.py`, `helpers.py`, `common.py`.
- Each folder has a short `__init__.py` docstring saying what layer it is and what lives below it.

## Prompts live in text files

- Every prompt sent to the model is a `.txt` file next to the code that uses it, for example `src/harness/chat/prompts/system.txt`.
- Python loads the file and fills named placeholders such as `{cwd}`. No prompt text inside Python strings.
- One prompt per file. The file name says what the prompt is for.

## No hardcoded values

- A literal that carries meaning gets a name. Compare against the name, never the raw value.
  Write `if cmd == Command.NEW:`, not `if cmd == "/new":`.
- Group related names in one place: a `StrEnum` for a fixed set of choices (slash commands, content block types), a small frozen dataclass or module-level constants for the rest (header names, id prefixes, file names).
- Anything a user might want to change (model name, base URL, user agent, timeouts) is a field in `Settings` with an environment override, not a literal in the code that uses it.
- Framework-required keys such as LangGraph's `"messages"` state key are the one exception; they are part of the library's contract, not our choice.

## Project conventions

- Python 3.12+, managed by `uv`; run everything through `uv run` or `just`.
- The model is constructed only in `src/harness/model/client.py`.
- Secrets live in `.env` and are never printed, logged, or committed.
