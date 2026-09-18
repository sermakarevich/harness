# How this codebase becomes a tutorial

One codebase grows chapter by chapter. A reader at chapter 3 must be able to run
chapter 3's code, not the finished harness. This document says how we do that.

## The three rules

1. **Write the final vision first.** `docs/VISION.md` lists everything the finished
   harness does and shows its final folder tree. Every chapter adds a file to that
   tree; no chapter reshuffles it.
2. **One chapter = one concept = one visible limitation fixed.** A chapter starts
   with something the chat cannot do yet, adds the smallest code that fixes it, and
   ends with a command the reader can run and see.
3. **The git history is the tutorial.** Every chapter ends in a git tag (`ch03`).
   The chapter document walks through `git diff ch02..ch03`. The reader checks out
   the tag, runs `just ch03`, reads the diff.

## What this means for the code

- Chapters are additive. Once a tag exists, the code under it is not refactored.
  A change that cuts across old chapters becomes its own chapter.
- Every chapter has a `just chNN` recipe that shows the new ability in the terminal.
- Every chapter has tests that run without a network connection.
- The layout follows `AGENTS.md`: layers as folders, small files, imports point down.

## What every chapter document contains

Use `docs/chapters/_TEMPLATE.md`. The sections, in order:

1. **The limitation** — what the chat cannot do before this chapter, shown as a
   short terminal exchange that fails or gives a poor answer.
2. **The concept** — the idea in plain words, three to eight sentences, no code.
   What the three harnesses we studied do about it (one line each, from
   `docs/harnesses/OPERATIONS.md`).
3. **The change** — the diff walked through file by file. Excerpts are copied from
   the real files. Each excerpt gets a short plain-English paragraph.
4. **Run it** — `git checkout chNN`, `just chNN`, expected output.
5. **Tests** — what the tests prove and how to run them.
6. **What is still missing** — the limitation the next chapter fixes.

## The chapter plan

Chapters 0 to 3 exist. The rest follows the build order in
`docs/harnesses/OPERATIONS.md`, one operation per chapter unless two are
inseparable. The number in brackets is the operation number.

| Ch | Concept | What the reader sees at the end |
|---|---|---|
| 0 | Project setup | `just setup`, `just test` green |
| 1 | One raw model call [1] | `just ch01` prints `pong` |
| 2 | The LangChain adapter [1, 5] | `just smoke` streams tokens |
| 3 | Conversation loop with memory [2, 3, 4] | chat that remembers within a session |
| 4 | Tool definitions and the agent loop [7, 8] | model reads a file you name |
| 5 | File tools and the shell tool [10, 11] | model edits a file and runs `pytest` |
| 6 | Permission gate [12] | terminal asks before a write or a command |
| 7 | Session persistence [13] | `/resume` after a restart |
| 8 | Token accounting and cost [15] | cost shown after each turn |
| 9 | Tool output offloading [17] | huge outputs spill to disk with a preview |
| 10 | Context compaction [16] | a long chat keeps working |
| 11 | Memory files [18] | project notes land in the system prompt |
| 12 | Skills [19] | instructions loaded on demand |
| 13 | Reliability and parallel tools [6, 9] | retries; independent tools run together |
| 14 | Planning and todos [21] | a visible task list the model maintains |
| 15 | Sub-agents [20] | delegation to a child graph |
| 16 | Outside tool servers, MCP [22] | tools from a Model Context Protocol server |
| 17 | Evaluation | a number before and after a harness change |

Operations 14, 23 and 24 (snapshot and revert, hooks and plugins, background work)
are out of scope for the tutorial. They matter for a product, less for learning.
The plan may change; the rules above do not.

## How a chapter gets built

1. The manager writes two fleet task specs: one for the code with tests, one for the
   chapter document. Both point at `AGENTS.md` and this file.
2. Workers run in order on the shared tree; the code task commits first.
3. The manager reviews, runs the live check once, and tags the commit `chNN`.
4. `docs/ARCHITECTURE.md` gets its operations table updated: the row moves from
   `planned` to `done`.
