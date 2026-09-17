# Chapter 3 — The conversation loop: memory within a session

Chapters 1 and 2 can ask the model things; this chapter gives it a memory.
The result is a real terminal chat: run it with:

```bash
just run
```

A sample exchange:

```text
> Hello, what can you do?
I am a terminal chat assistant. How can I help?
> /new
new session harness-3f9a…
> /exit
```

`/new` starts a fresh conversation; `/exit` (or Ctrl-D) quits. The heart of
it is a LangGraph graph — one node today, with room for tools, approval gates
and compaction later.

## State: what the harness remembers

```python
class HarnessState(MessagesState):
    """Conversation state; currently only `messages`."""
```

`MessagesState` is a LangGraph helper that gives us a `messages` list with an
append-style **reducer** — a small merge function that decides how new values
combine with old ones. Here the reducer appends: every node returns new
messages and LangGraph adds them to the list instead of replacing it. That is
the whole memory mechanism at this stage — history accumulates, and each turn
sends the full history back to the model. Later chapters add one field per
harness job (token usage, todo list) to this same class.

## The single node: `call_model`

```python
def call_model(state: HarnessState) -> dict:
    messages = [SystemMessage(content=system_prompt), *state["messages"]]
    response = model.invoke(messages)
    return {"messages": [response]}
```

Each turn, the node prepends the system prompt (a SystemMessage is a
LangChain message carrying background instructions for the model, built by
`build_system_prompt` in `prompt.py`) to the stored history, calls the model
once with `invoke` (a single blocking call that waits for the full answer),
and returns the reply as a one-element message list — which the reducer
appends. The graph wiring is two edges:

```python
builder = StateGraph(HarnessState)
builder.add_node("call_model", call_model)
builder.add_edge(START, "call_model")
builder.add_edge("call_model", END)
```

`START` marks where a turn begins, `END` where it finishes. Tools will later
appear as a second node with a conditional edge between them.

## The checkpointer and `thread_id`: one id, one conversation

```python
def new_session_id() -> str:
    """One id per conversation; doubles as LangGraph thread_id and OpenCode session header."""
    return f"harness-{uuid.uuid4()}"


def thread_config(session_id: str) -> dict:
    """The `config` LangGraph needs to find this conversation's checkpoint."""
    return {"configurable": {"thread_id": session_id}}
```

A **checkpointer** is the LangGraph object that saves graph state after every
turn; ours is an `InMemorySaver` (a checkpointer that keeps everything in
process memory). The `thread_id` inside `config` selects which conversation to
load and save — pass the same id and history resumes; pass a new id and you
get a blank slate. Notice the same id also travels as the `x-opencode-session`
HTTP header (see `make_model`), so the LangGraph checkpoint and OpenCode's
server-side caching agree on what "one conversation" means.

## `stream_mode="messages"`: tokens stream even though the node calls `invoke`

The node uses `invoke`, which waits for the complete reply — yet the terminal
fills in word by word. The trick is in `App.run_turn`:

```python
events = self.session.graph.stream(
    {"messages": [HumanMessage(content=text)]},
    self.session.config,
    stream_mode="messages",
)
```

`graph.stream` with `stream_mode="messages"` replays the model's token chunks
as events while the node runs, even though the node itself only sees the
final message. LangGraph fans the tokens out to us; each event is a
`(message, metadata)` pair handed to `render_event` below.

## The terminal: three seams in `App`

`src/harness/tui/app.py` splits rendering into three methods so later
chapters can grow the chat without rewriting it:

- `handle_command` — slash commands (`/new` starts a fresh session inside the
  same checkpointer, `/help` prints help, `/exit` quits, unknown input gets an
  error). Returns False only when the app should exit.
- `run_turn` — sends one user message through the graph and streams the
  reply, catching network errors so a failed call never kills the chat.
- `render_event` — shows one streamed event; today it prints assistant token
  chunks as they arrive:

```python
def render_event(self, message, meta: dict) -> None:
    """Show one streamed event. Today: print assistant tokens as they arrive."""
    if isinstance(message, AIMessageChunk):
        self.console.print(text_of(message), end="", markup=False, highlight=False, soft_wrap=True)
```

## Limitation fixed — and what is left

Fixed: the model now has a memory within a session. Ask a follow-up question
and it sees the earlier turns, because the checkpointer reloads them every
time. Still missing, and the hook to the next chapters: no tools (the model
cannot act on the world), memory dies with the process, no cost tracking,
and no safety gate before dangerous calls.
