# Tutorial 3 — Graph, streaming, terminal

After this tutorial you have a terminal chat that remembers within a session,
streams its answers and survives a failed call.

## In short

### The concepts

- **One graph node is one turn.** Tutorial 2 wrote the turn as plain code.
  Now it is a node in a graph, so you grow the harness by adding nodes.
  - opencode runs each turn as streaming steps inside a turn loop.
  - pi runs each turn through its prompt loop with hooks around it.
  - hermes-agent runs a bounded loop of model calls and tool rounds.
- **A checkpointer keeps the list under a thread id.** You name a thread and
  the checkpointer loads and saves the list around every turn. An LLM (large
  language model) keeps nothing between calls, so state across turns lives in
  an outside state manager (knowledge base: HarnessEngineering). Sessions save
  after every turn (knowledge base: HarnessEngineeringCourse), in memory here;
  tutorial 7 moves them to disk.
  - opencode keeps history in a local database and rebuilds the list each turn.
  - pi keeps a branchable session tree and walks the active path each turn.
  - hermes-agent copies stored history into a working list each turn.
- **Tokens arrive one by one, so you print them as they come.** Streaming is
  your choice to show work in progress. The terminal assembles the pieces as
  they arrive (knowledge base: HarnessEngineeringCourse).
  - opencode consumes one typed event stream piece by piece.
  - pi re-emits arriving tokens as display events.
  - hermes-agent fans text fragments out to display callbacks.

### Scope

1. You move the turn into a one-node graph.
2. You let a checkpointer keep the list under a thread id.
3. You stream the answer token by token.
4. You wrap it all in a terminal with three commands:
   - `/new` starts a fresh session.
   - `/help` lists the commands.
   - `/exit` quits.

Left out on purpose: tools (tutorial 4) and saving sessions to disk (tutorial 7).

### The problem

Tutorial 2 answers in one block after a pause, and forgets everything when you quit. The
exchange looks like this:

```text
> Remember this word: pelican
[pause] Got it, I'll remember: pelican.
> (you quit and start again) Which word did I ask you to remember?
I do not know; I see only this one question.
```

### What changes

```text
+ src/harness/chat/graph.py      one turn as one graph node
+ src/harness/chat/state.py      the message list the node reads
+ src/harness/chat/thread.py     fresh session ids and thread configs
+ src/harness/chat/session.py    one conversation with its own thread
+ src/harness/tui/               the read-print loop with three commands
+ src/harness/__main__.py        start the chat
+ tests/                         graph and terminal checks, no network
```

## In detail

### How it works

1. You type a line and the terminal reads it.
2. Lines starting with `/` go to the command table; the rest is chat.
3. Your line becomes a HumanMessage for `graph.stream` with the thread config.
4. The checkpointer loads the list saved under that thread id.
5. The node puts the system prompt first and calls the model.
6. Answer chunks stream back through the graph.
7. The terminal prints each chunk as it arrives.
8. The checkpointer saves the longer list under the same thread id.

A failed call prints one error line and returns to the prompt, so the chat
goes on.

### Design decisions

- **The checkpointer owns the list, so your code never touches it.** The graph
  loads and saves around every turn. Tutorial 7 swaps memory for disk.
- **A new session is a new thread id, not a cleared list.** Old threads stay
  readable; forgetting is naming, not deleting.
- **A failed call is a printed line, not a crash.** One network error never
  costs you the conversation. You see the error and keep talking.

### The excerpt that carries the idea

**src/harness/chat/graph.py** is the whole turn in one node:

```python
def call_model(state: HarnessState) -> dict:
    messages = [SystemMessage(content=system_prompt), *state["messages"]]
    response = model.invoke(messages)
    return {"messages": [response]}
```

### Run it

```bash
git checkout tut03
just tutorial
```

```text
harness · model muse-spark-1.3-contributor · session bc9ee37b · /help for commands
> Reply with exactly one word: pong
pong
```

You leave with `/exit` or Ctrl-D.

### Under the hood

The session header from tutorial 1 and the thread id are the same value, so
the server's routing and cache follow your notion of a conversation.

### Key takeaways

- One graph node is one turn: tutorial 2's loop is now a graph you grow.
- You name a thread and the checkpointer keeps the list.
- Tokens print as they arrive, and a failed call returns you to the prompt.

### What is still missing

The model can only talk. Tutorial 4 gives it a first tool and the loop that
runs tools until the model stops asking.
