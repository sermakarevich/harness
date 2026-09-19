# Architecture: where each harness job lives

How the code in `src/harness/` maps to the 24 harness
operations in `docs/harnesses/OPERATIONS.md`. Read the intro, the at-a-glance
table, and the "Build order" section of that document first.

## 1. Module map

The real tree, layer by layer from the top down:

```text
src/harness/__init__.py       package root
src/harness/__main__.py       `just run` entry point: load settings, start the chat
src/harness/config.py         settings and key loading from `.env`; key hidden from `repr`
src/harness/tui/__init__.py   terminal layer: app, commands, render, ask, pick
src/harness/tui/app.py        terminal chat loop (App delegates to commands and render)
src/harness/tui/ask.py        the permission question and its yes / always / no answers
src/harness/tui/commands.py   slash commands (handle_command for /new, /resume, /help, /exit)
src/harness/tui/pick.py       the numbered list of saved conversations and the pick you type
src/harness/tui/render.py     one turn plus streamed reply rendering (run_turn, render_event)
src/harness/chat/__init__.py  conversation layer: graph, session, prompt, state, store, usage
src/harness/chat/compact.py   swaps older turns for one summary once the conversation grows big
src/harness/chat/graph.py     the agent loop as a graph (build_graph plus call_model)
src/harness/chat/prompt.py    system prompt assembly (build_system_prompt)
src/harness/chat/prompts/system.txt system prompt text with {today} and {cwd} slots
src/harness/chat/prompts/summary.txt what to keep when the older turns are summarised
src/harness/chat/run_tools.py the tools node: ask about every risky call, then run them
src/harness/chat/session.py   one conversation id bound to its model and graph (start, resume)
src/harness/chat/sessions.py  reads saved conversations back as a list you can recognise
src/harness/chat/state.py     conversation state (HarnessState); one field per harness job
src/harness/chat/store.py     opens the SQLite file the conversations are saved in (open_store)
src/harness/chat/thread.py    session ids (new_session_id) and thread config
src/harness/chat/usage.py     token counts of the saved replies and what they cost (dollars)
src/harness/tools/__init__.py tool layer: one file per tool plus the shared path and policy rules
src/harness/tools/edit_file.py  replaces one exact piece of text in a file
src/harness/tools/offload.py  spills an over-long tool result to a file and previews it
src/harness/tools/paths.py    resolves every path under the working directory
src/harness/tools/permission.py which tool names run without a question
src/harness/tools/read_file.py  reads one file
src/harness/tools/registry.py lists the tools the model may call
src/harness/tools/shell.py    runs one command with a timeout
src/harness/tools/write_file.py creates or overwrites one file
src/harness/model/__init__.py model layer: client plus text helper
src/harness/model/client.py   the single seam where a model object is built (make_model)
src/harness/model/text.py     plain-text reader for model replies (text_of)
```

Tutorial 1 wrote `model/client.py` as one raw HTTP call and tutorial 2 replaced it with the
LangChain adapter. Tutorial 2 kept the conversation as a plain list in `chat/loop.py`, which
tutorial 3 replaced with the graph. `just smoke` pipes a fixed exchange through `python -m harness`.

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
3. The checkpointer, a `SqliteSaver` opened by `src/harness/chat/store.py`, loads the conversation's
   history from disk by `thread_id` (`src/harness/chat/thread.py`).
4. Before the model is called, the edge out of `START` asks `src/harness/chat/compact.py`
   how many input tokens the model reported on its last reply. Over the budget the turn goes
   through the compaction node first, which summarises every turn but the newest few in one
   call and puts the recap in their place; under it the turn goes straight on.
5. `call_model` (`src/harness/chat/graph.py`) prepends the system prompt (`src/harness/chat/prompt.py`) and calls `model.invoke`.
6. The `ChatOpenAI` built by `make_model` (`src/harness/model/client.py`) sends one HTTPS request to OpenCode
   Go with the `x-opencode-session` header.
7. Token chunks stream back through `stream_mode="messages"` events.
8. `render_event` (`src/harness/tui/render.py`) prints each assistant chunk as it arrives via `text_of` (`src/harness/model/text.py`).
9. If the reply asks for a tool, the graph routes to `run_tools` (`src/harness/chat/run_tools.py`),
   which pauses the turn with `interrupt()` for every call that `src/harness/tools/permission.py`
   does not list as safe. `run_turn` reads the waiting question from the saved state, asks it with
   `src/harness/tui/ask.py`, and resumes the graph with your answer. Allowed calls run and their
   results pass `src/harness/tools/offload.py`, which spills anything over the limit to a file and
   keeps a preview plus its path. Denied calls come back as a tool message saying so, and the
   model is called again from step 5.
10. The final message is appended to state (`src/harness/chat/state.py`) and saved under the `thread_id`.
   Every step saves, so the conversation is on disk before the turn ends and `/resume` finds it
   through `src/harness/chat/sessions.py` in the next run. The reply carries its token counts, so
   `run_turn` prices this turn and the whole conversation with `src/harness/chat/usage.py` and
   prints one dim line.
11. If the call fails, `run_turn` prints the error and the loop continues.

## 3. Operations map

Status is `done` (works today), `partial` (a seam exists, the job is small),
or `planned` (a named future node or helper, per the "In LangGraph / Python"
hints in OPERATIONS.md).

| # | Operation | Tier | Status | Where it lives / will plug in |
|---|---|---|---|---|
| 1 | Pure LLM call | 1 | done | `model/client.py` (raw `httpx` at `tut01`, LangChain since `tut02`) |
| 2 | Streaming | 1 | done | `tui/render.py run_turn` + `stream_mode="messages"` |
| 3 | Conversation state | 2 | done | `chat/state.py` + the checkpointer attached in `chat/graph.py` (in memory until `tut07`, on disk since) |
| 4 | System prompt assembly | 2 | partial | `chat/prompt.py` (four static lines, one names the tools; memory appends here) |
| 5 | Provider & model abstraction | 3 | partial | `make_model` in `model/client.py` is the single seam; no catalog yet |
| 6 | Reliability | 4 | planned | `RetryPolicy` on `call_model` in `chat/graph.py` + `with_retry`/`with_fallbacks` on the model |
| 7 | Tool definitions | 2 | done | `@tool` functions in `tools/`, listed in `tools/registry.py`, bound via `bind_tools` (`tut04`) |
| 8 | Agent loop | 2 | done | `tools` node + conditional edge (`tools_condition`) in `chat/graph.py` (`tut04`) |
| 9 | Parallel tool calls | 4 | planned | `ToolNode` runs siblings concurrently; `Send` fan-out for custom work |
| 10 | File tools | 2 | partial | `tools/read_file.py`, `write_file.py`, `edit_file.py` with path checks in `tools/paths.py` (`tut05`); no search, no output caps yet |
| 11 | Shell execution | 2 | partial | `tools/shell.py` around `subprocess` with timeout and exit code (`tut05`); output not trimmed yet |
| 12 | Permission / approval gate | 4 | done | `tools/permission.py` names the safe tools, `chat/run_tools.py` pauses with `interrupt()`, `tui/ask.py` asks (`tut06`) |
| 13 | Session persistence | 3 | done | `SqliteSaver` from `chat/store.py`, listed by `chat/sessions.py`, picked in `tui/pick.py` via `/resume` (`tut07`) |
| 14 | Snapshot & revert | 5 | planned | `get_state_history`/`update_state` on `chat/graph.py` + per-turn working-directory Snapshot |
| 15 | Token accounting & cost | 3 | done | `chat/usage.py` adds up the `usage_metadata` of the saved replies and prices it with the rates in `settings.toml`; `tui/render.py` prints it (`tut08`) |
| 16 | Context overflow & compaction | 4 | done | `chat/compact.py` reads the last reply's input count; a conditional edge out of `START` in `chat/graph.py` sends the turn through a summary node that swaps every older turn for one recap (`tut10`) |
| 17 | Tool output offloading | 3 | done | `tools/offload.py` caps every result where `chat/run_tools.py` turns it into a message, spills the rest to a file and hands back a preview plus the path (`tut09`) |
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
