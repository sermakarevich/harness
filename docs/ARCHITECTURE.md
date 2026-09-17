# Architecture: where each harness job lives

How the code in `src/harness/` and `scripts/` maps to the 24 harness
operations in `docs/harnesses/OPERATIONS.md`. Read the intro, the at-a-glance
table, and the "Build order" section of that document first.

## 1. Module map

| File | Harness job |
|---|---|
| `src/harness/config.py` | Settings and key loading from `.env`; key hidden from `repr` |
| `src/harness/model.py` | The single seam where a model object is constructed (`make_model`, `text_of`) |
| `src/harness/state.py` | Conversation state (`HarnessState`); one field per harness job |
| `src/harness/prompt.py` | System prompt assembly (`build_system_prompt`) |
| `src/harness/graph.py` | The agent loop as a graph; session ids and thread config |
| `src/harness/session.py` | One conversation id bound to its model and graph |
| `src/harness/tui/app.py` | Terminal chat: commands, turns, and streamed rendering |
| `src/harness/__main__.py` | `just run` entry point: load settings, start the chat |
| `scripts/raw_call.py` | Chapter 1: one raw HTTP call, no framework |
| `scripts/smoke_model.py` | Live check of the LangChain adapter (`just smoke`) |

Every file owns exactly one harness job; new operations extend these files
instead of adding layers around them.

## 2. Data flow of one turn

1. Keypress — the user types a line and the main loop in `App.run` reads it.
2. `App.run_turn` wraps the text in a `HumanMessage` and calls `graph.stream`
   with the session config and `stream_mode="messages"`.
3. The checkpointer loads the conversation's history by `thread_id`.
4. `call_model` prepends the system prompt and calls `model.invoke`.
5. The `ChatOpenAI` built by `make_model` sends one HTTPS request to OpenCode
   Go with the `x-opencode-session` header.
6. Token chunks stream back through `stream_mode="messages"` events.
7. `render_event` prints each assistant chunk as it arrives via `text_of`.
8. The final message is appended to state and saved under the `thread_id`.
9. If the call fails, `run_turn` prints the error and the loop continues.

## 3. Operations map

Status is `done` (works today), `partial` (a seam exists, the job is small),
or `planned` (a named future node or helper, per the "In LangGraph / Python"
hints in OPERATIONS.md).

| # | Operation | Tier | Status | Where it lives / will plug in |
|---|---|---|---|---|
| 1 | Pure LLM call | 1 | done | `scripts/raw_call.py`, `model.py` |
| 2 | Streaming | 1 | done | `App.run_turn` + `stream_mode="messages"` |
| 3 | Conversation state | 2 | done | `state.py` + `InMemorySaver` in `graph.py` |
| 4 | System prompt assembly | 2 | partial | `prompt.py` (static three lines today; tools and memory append here) |
| 5 | Provider & model abstraction | 3 | partial | `make_model` is the single seam; no catalog yet |
| 6 | Reliability | 4 | planned | `RetryPolicy` on `call_model` + `with_retry`/`with_fallbacks` on the model |
| 7 | Tool definitions | 2 | planned | `@tool` functions bound via `bind_tools`, run by a `tools` node in `graph.py` |
| 8 | Agent loop | 2 | planned | `tools` node + conditional edge (`tools_condition`) in `graph.py` |
| 9 | Parallel tool calls | 4 | planned | `ToolNode` runs siblings concurrently; `Send` fan-out for custom work |
| 10 | File tools | 2 | planned | `@tool` read/write/edit/search functions with path checks and output caps |
| 11 | Shell execution | 2 | planned | `@tool` around `subprocess` with timeout, exit code, trimmed output |
| 12 | Permission / approval gate | 4 | planned | `interrupt()` in the tools node, rendered in `render_event` |
| 13 | Session persistence | 3 | partial | In-memory only; swap `InMemorySaver` for `SqliteSaver` |
| 14 | Snapshot & revert | 5 | planned | `get_state_history`/`update_state` + per-turn working-directory Snapshot |
| 15 | Token accounting & cost | 3 | planned | `usage_metadata` + rate table against the model catalog |
| 16 | Context overflow & compaction | 4 | planned | `trim_messages` + `RemoveMessage` compact node off `call_model` |
| 17 | Tool output offloading | 3 | planned | Cap, spill to disk, and return preview plus path inside tool functions |
| 18 | Memory files | 3 | planned | `pathlib` loader feeding `build_system_prompt` |
| 19 | Skills / progressive disclosure | 3 | planned | `list_skills`/`read_skill` tools plus skill-directory scan |
| 20 | Sub-agents / delegation | 5 | planned | Child subgraph with own thread id, fanned out with `Send` |
| 21 | Planning & todo tracking | 4 | planned | Extra state field plus `interrupt()` plan gate |
| 22 | MCP / dynamic external tools | 4 | planned | `MultiServerMCPClient` adapted into the `tools` node |
| 23 | Hooks, plugins & events | 5 | planned | Wrapper nodes around `call_model` first; a bus only when plugins need it |
| 24 | Background & concurrency | 5 | planned | One thread per job with its own `thread_id`; ids already run in parallel |

## 4. Rules of growth

Three conventions keep the codebase small as operations turn from planned to
done. Follow them in every contribution:

1. One module per harness job — a new operation starts as a new function in
   the module that owns its job, or a new module when no owner fits.
2. Every new node gets a fake-model test — tests inject a stub model via
   `Session.start(..., model=...)` and never call the live API.
3. The model is only ever constructed in `model.py` — graph, session, and
   terminal code receive a model object; they never import vendor details.
