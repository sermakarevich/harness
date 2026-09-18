# Architecture: where each harness job lives

How the code in `src/harness/` and `scripts/` maps to the 24 harness
operations in `docs/harnesses/OPERATIONS.md`. Read the intro, the at-a-glance
table, and the "Build order" section of that document first.

## 1. Module map

The real layered tree (`find src -name '*.py' | sort`):

```text
src/harness/__init__.py       package root
src/harness/__main__.py       `just run` entry point: load settings, start the chat
src/harness/chat/__init__.py  conversation layer: graph, session, thread, prompt, state
src/harness/chat/graph.py     the agent loop as a graph (build_graph plus call_model)
src/harness/chat/prompt.py    system prompt assembly (build_system_prompt)
src/harness/chat/session.py   one conversation id bound to its model and graph
src/harness/chat/state.py     conversation state (HarnessState); one field per harness job
src/harness/chat/thread.py    session ids (new_session_id) and thread config
src/harness/config.py         settings and key loading from `.env`; key hidden from `repr`
src/harness/model/__init__.py model layer: client plus text helper
src/harness/model/client.py   the single seam where a model object is built (make_model)
src/harness/model/text.py     plain-text reader for model replies (text_of)
src/harness/tui/__init__.py   terminal layer: app plus commands plus render
src/harness/tui/app.py        terminal chat loop (App delegates to commands and render)
src/harness/tui/commands.py   slash commands (handle_command for /new, /help, /exit)
src/harness/tui/render.py     one turn plus streamed reply rendering (run_turn, render_event)
```

`scripts/raw_call.py` is chapter 1: one raw HTTP call, no framework.
`scripts/smoke_model.py` is the live check of the LangChain adapter (`just smoke`).

## Layers

The folders are the layers, top down: entry point, then the terminal
(Terminal User Interface, TUI for short) layer, then the conversation (chat)
layer, then the model layer, then settings at the bottom. A higher layer
calls the one below it, never the other way round. Imports point down only;
a lower file never imports from a file above it.

## 2. Data flow of one turn

1. Keypress — the user types a line and the main loop in `App.run` (`src/harness/tui/app.py`) reads it.
2. `run_turn` (`src/harness/tui/render.py`, via `App.run_turn`) wraps the text in a `HumanMessage` and calls `graph.stream`
   with the session config and `stream_mode="messages"`.
3. The checkpointer loads the conversation's history by `thread_id` (`src/harness/chat/thread.py`).
4. `call_model` (`src/harness/chat/graph.py`) prepends the system prompt (`src/harness/chat/prompt.py`) and calls `model.invoke`.
5. The `ChatOpenAI` built by `make_model` (`src/harness/model/client.py`) sends one HTTPS request to OpenCode
   Go with the `x-opencode-session` header.
6. Token chunks stream back through `stream_mode="messages"` events.
7. `render_event` (`src/harness/tui/render.py`) prints each assistant chunk as it arrives via `text_of` (`src/harness/model/text.py`).
8. The final message is appended to state (`src/harness/chat/state.py`) and saved under the `thread_id`.
9. If the call fails, `run_turn` prints the error and the loop continues.

## 3. Operations map

Status is `done` (works today), `partial` (a seam exists, the job is small),
or `planned` (a named future node or helper, per the "In LangGraph / Python"
hints in OPERATIONS.md).

| # | Operation | Tier | Status | Where it lives / will plug in |
|---|---|---|---|---|
| 1 | Pure LLM call | 1 | done | `scripts/raw_call.py`, `model/client.py` |
| 2 | Streaming | 1 | done | `tui/render.py run_turn` + `stream_mode="messages"` |
| 3 | Conversation state | 2 | done | `chat/state.py` + `InMemorySaver` in `chat/graph.py` |
| 4 | System prompt assembly | 2 | partial | `chat/prompt.py` (static three lines today; tools and memory append here) |
| 5 | Provider & model abstraction | 3 | partial | `make_model` in `model/client.py` is the single seam; no catalog yet |
| 6 | Reliability | 4 | planned | `RetryPolicy` on `call_model` in `chat/graph.py` + `with_retry`/`with_fallbacks` on the model |
| 7 | Tool definitions | 2 | planned | `@tool` functions bound via `bind_tools`, run by a `tools` node in `chat/graph.py` |
| 8 | Agent loop | 2 | planned | `tools` node + conditional edge (`tools_condition`) in `chat/graph.py` |
| 9 | Parallel tool calls | 4 | planned | `ToolNode` runs siblings concurrently; `Send` fan-out for custom work |
| 10 | File tools | 2 | planned | `@tool` read/write/edit/search functions with path checks and output caps |
| 11 | Shell execution | 2 | planned | `@tool` around `subprocess` with timeout, exit code, trimmed output |
| 12 | Permission / approval gate | 4 | planned | `interrupt()` in the tools node in `chat/graph.py`, rendered in `tui/render.py` |
| 13 | Session persistence | 3 | partial | In-memory only in `chat/graph.py`; swap `InMemorySaver` for `SqliteSaver` |
| 14 | Snapshot & revert | 5 | planned | `get_state_history`/`update_state` on `chat/graph.py` + per-turn working-directory Snapshot |
| 15 | Token accounting & cost | 3 | planned | `usage_metadata` + rate table against the model catalog |
| 16 | Context overflow & compaction | 4 | planned | `trim_messages` + `RemoveMessage` compact node off `call_model` in `chat/graph.py` |
| 17 | Tool output offloading | 3 | planned | Cap, spill to disk, and return preview plus path inside tool functions |
| 18 | Memory files | 3 | planned | `pathlib` loader feeding `build_system_prompt` in `chat/prompt.py` |
| 19 | Skills / progressive disclosure | 3 | planned | `list_skills`/`read_skill` tools plus skill-directory scan |
| 20 | Sub-agents / delegation | 5 | planned | Child subgraph with own thread id (`chat/thread.py`), fanned out with `Send` |
| 21 | Planning & todo tracking | 4 | planned | Extra state field in `chat/state.py` plus `interrupt()` plan gate |
| 22 | MCP / dynamic external tools | 4 | planned | `MultiServerMCPClient` adapted into the `tools` node in `chat/graph.py` |
| 23 | Hooks, plugins & events | 5 | planned | Wrapper nodes around `call_model` in `chat/graph.py` first; a bus only when plugins need it |
| 24 | Background & concurrency | 5 | planned | One thread per job with its own `thread_id` (`chat/thread.py`); ids already run in parallel |

## 4. Rules of growth

Three conventions keep the codebase small as operations turn from planned to
done. Follow them in every contribution:

1. One module per harness job — a new operation starts as a new function in
   the module that owns its job, or a new module when no owner fits.
2. Every new node gets a fake-model test — tests inject a stub model via
   `Session.start(..., model=...)` and never call the live API.
3. The model is only ever constructed in `model/client.py` — graph, session, and
   terminal code receive a model object; they never import vendor details.
