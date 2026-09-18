# How this codebase becomes a tutorial

One codebase grows tutorial by tutorial. A reader at tutorial 3 must be able to run
tutorial 3's code, not the finished harness. This document says how we do that.

## The three rules

1. **Write the final vision first.** `docs/VISION.md` lists everything the finished
   harness does and shows its final folder tree. Every tutorial adds a file to that
   tree; no tutorial reshuffles it.
2. **One tutorial = one concept = one visible limitation fixed.** A tutorial starts
   with something the chat cannot do yet, adds the smallest code that fixes it, and
   ends with a command the reader can run and see.
3. **The git history is the tutorial.** Every tutorial ends in a git tag (`tut03`).
   The tutorial document walks through `git diff tut02..tut03`. The reader checks out
   the tag, runs `just tut03`, reads the diff.

## What this means for the code

- Tutorials are additive. Once a tag exists, the code under it is not refactored.
  A change that cuts across old tutorials becomes its own tutorial.
- Every tutorial has a `just tutNN` recipe that shows the new ability in the terminal.
- Every tutorial has tests that run without a network connection.
- The layout follows `AGENTS.md`: layers as folders, small files, imports point down.

## What every tutorial document contains

Use `docs/tutorials/_TEMPLATE.md`. The sections, in order:

1. **The limitation** — what the chat cannot do before this tutorial, shown as a
   short terminal exchange that fails or gives a poor answer.
2. **The concept** — the idea in plain words, three to eight sentences, no code.
   What the three harnesses we studied do about it (one line each, from
   `docs/harnesses/OPERATIONS.md`).
3. **The change** — the diff walked through file by file. Excerpts are copied from
   the real files. Each excerpt gets a short plain-English paragraph.
4. **Run it** — `git checkout tutNN`, `just tutNN`, expected output.
5. **Tests** — what the tests prove and how to run them.
6. **What is still missing** — the limitation the next tutorial fixes.

## The tutorial plan

The tutorials tell one story. Each tutorial ends with a limitation, and the next
tutorial's concept is the answer to it. The order below follows that story, not the
order the code was first written in. The number in brackets is the operation number
from `docs/harnesses/OPERATIONS.md`.

The **Explained** column lists the points the tutorial document must teach, a few
words each. It is the checklist for whoever writes the tutorial.

| # | Concept | Explained | What the reader sees at the end |
|---|---|---|---|
| 0 | Project setup | one tool for the environment (uv); secrets in `.env`, never in git; tests run offline | `just setup`, `just test` green |
| 1 | One raw model call [1] | a request is plain HTTP; the key travels in a header; the request is stateless: nothing is kept between calls; the reply is a list of typed blocks (reasoning, text) | `just tut01` prints `pong` |
| 2 | Messages stack into memory [2, 3, 4] | three roles: system, user, assistant; the list *is* the memory; every turn resends the whole list; so the context grows each turn; the system prompt sits first and shapes every answer; a new chat is an empty list | chat that remembers within a session, `/new` forgets |
| 3 | Adapter, graph, streaming [1, 5] | one adapter hides vendor quirks; one graph node is one turn; a checkpointer keeps the list per thread id; tokens arrive one by one, so print them as they come; the read-print loop of a terminal | `just smoke` streams tokens; `just run` opens the chat |
| 4 | Tools and the agent loop [7, 8] | a tool is a schema plus a function; the model asks, the harness runs; the result goes back as a tool message; loop until the model stops asking; first tool: read a file | model reads a file you name |
| 5 | File tools and the shell tool [10, 11] | edit as exact find-and-replace; shell with a timeout; working directory matters; stdout and stderr become text for the model | model edits a file and runs `pytest` |
| 6 | Permission gate [12] | read is safe, write and run are not; ask before a side effect; allow once versus always; a denial is a message back to the model, not a crash | terminal asks before a write or a command |
| 7 | Session persistence [13] | checkpoints move from memory to disk; thread id becomes a session name; list, pick, continue; state survives a restart | `/resume` after a restart |
| 8 | Token accounting and cost [15] | usage numbers come back with each reply; input versus output tokens; a price table per model; running total per session; growth from tutorial 2 now has a price | cost shown after each turn |
| 9 | Tool output offloading [17] | one big output can flood the context; save it to a file; show the first lines plus the path; the model reads more only if it needs to | huge outputs spill to disk with a preview |
| 10 | Context compaction [16] | the window has a hard limit; summarise old turns, keep recent ones; what gets lost and what must survive; when to trigger | a long chat keeps working |
| 11 | Memory files [18] | notes the model should always know; loaded into the system prompt at start; project notes versus personal notes; how notes accumulate over time | project notes land in the system prompt |
| 12 | Skills [19] | instructions the model needs sometimes, not always; a short index in the prompt, the full text on demand; saves context compared with memory files | instructions loaded on demand |
| 13 | Reliability and parallel tools [6, 9] | calls fail: retry with backoff; rate limits and timeouts; independent tool calls run at the same time; results return in the asked order | retries; independent tools run together |
| 14 | Planning and todos [21] | a plan the model writes and updates; plan as graph state, not chat text; visible progress on long tasks | a visible task list the model maintains |
| 15 | Sub-agents [20] | a child graph with a fresh, empty context; delegate one job, get back one summary; keeps the parent context small | delegation to a child graph |
| 16 | Outside tool servers, MCP [22] | tools that live in another process; discover them at start; the same loop from tutorial 4 runs them | tools from a Model Context Protocol server |
| 17 | Evaluation | a fixed set of tasks; a score before and after a change; catch regressions, not just wins | a number before and after a harness change |

Tutorials 0 to 3 already have code. Tutorials 2 and 3 swap places compared with the
current `docs/tutorials/` files and `just` recipes, so one small task renames those
before tagging. Tutorial 2 is taught with a plain message list first; the graph and
checkpointer arrive in tutorial 3 as the tidy way to keep that list.

Operations 14, 23 and 24 (snapshot and revert, hooks and plugins, background work)
are out of scope for the tutorial. They matter for a product, less for learning.
The plan may change; the rules above do not.

## How a tutorial gets built

1. The manager writes two fleet task specs: one for the code with tests, one for the
   tutorial document. Both point at `AGENTS.md` and this file.
2. Workers run in order on the shared tree; the code task commits first.
3. The manager reviews, runs the live check once, and tags the commit `tutNN`.
4. `docs/ARCHITECTURE.md` gets its operations table updated: the row moves from
   `planned` to `done`.
