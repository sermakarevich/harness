# Tutorial 3 — Graph, streaming, terminal

After this tutorial you have a terminal chat that remembers within a session,
streams its answers and survives a failed call.

## In short
### The concepts
- **One graph node is one turn.** You send a message; one node prefixes the
  system prompt and answers. The reply joins the thread.
  - opencode rebuilds model messages from stored parts on every turn.
  - pi walks its session tree from leaf to root and converts the path.
  - hermes-agent copies stored history into a working turn context.
- **A checkpointer keeps the list per thread id.** You name a thread and it loads
  the list for the turn. The model is a stateless compute unit; its memory is
  this external list (knowledge base: HarnessEngineering).
  - opencode keeps messages and parts in a local file database.
  - pi saves sessions as line-delimited files linked into a tree.
  - hermes-agent flushes messages append-only during the turn.
- **Tokens arrive one by one, so you print them as they come.** You stream each
  token instead of waiting for the whole answer (knowledge base:
  HarnessEngineeringCourse).
  - opencode converts both runtimes into one typed event stream.
  - pi re-emits arriving tokens as display events with text pieces.
  - hermes-agent fans fragments out through a single writer.
### Scope
1. You move the turn into a LangGraph graph with a single node.
2. You let a checkpointer keep the list under a thread id instead of a variable.
3. You stream the answer token by token as it arrives.
4. You wrap it in a terminal with three commands:
   - `/new` starts a fresh thread id.
   - `/help` lists the commands.
   - `/exit` leaves the chat.
Left out for now: tools (tutorial 4) and saving sessions to disk (tutorial 7).
### The problem

```text
> Remember this word: pelican
Got it, I'll remember pelican.
context: 3 messages
> Which word did I ask you to remember? Answer with the word only.
pelican
context: 5 messages
> /new
new conversation
> Which word did I ask you to remember? Answer with the word only.
You haven't asked me to remember a word.
context: 3 messages
```

Each answer arrived in one block after a pause — the list was one variable that died with the run.
### What changes

```text
src/harness/
+   chat/graph.py             the turn as one graph node
+   chat/state.py             the message list the graph carries
+   chat/thread.py            the thread id naming one conversation
+   chat/session.py           one conversation with its graph and config
-   chat/loop.py              the Chat class and its hand-held list are gone
~   tui/app.py                read-print loop with banner and history
~   tui/commands.py           three commands with help text
+   tui/render.py             prints each token as it arrives
tests/                       offline tests for the graph and terminal
```
## In detail

### How it works
1. You type a line and the terminal reads it.
2. The terminal checks for a leading slash and routes commands.
3. A plain message enters `graph.stream` as a HumanMessage with the thread config.
4. The checkpointer loads the list stored under that thread id.
5. The node puts the system prompt first and calls the model.
6. Answer chunks stream back while the model is still writing.
7. The terminal prints each chunk as it arrives and assembles the reply.
8. The checkpointer saves the grown list under the same thread id.

### Design decisions
- **The checkpointer owns the list.** It saves after every turn, because
  nothing survives unless written (knowledge base: HarnessEngineeringCourse).
  Your code never touches the list, so Tutorial 7 swaps memory for disk.
- **A new session is a new thread id, not a cleared list.** Old threads stay
  readable because nothing is erased. You start over without destroying a thing.
- **A failed call is a printed line, not a crash.** You keep everything said so
  far and return to the prompt. One network error never costs you the chat.

### The excerpt that carries the idea

**`src/harness/chat/graph.py` — the whole turn in four lines:**
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
harness · model muse-spark-1.3-contributor · session 060ca639 · /help for
commands
> Remember this word: pelican
Got it — I'll remember pelican.
> Which word did I ask you to remember? Answer with the word only.
pelican
> /exit
```

You leave the chat with `/exit` or Ctrl-D.

### Under the hood

The session header from tutorial 1 and the thread id are the same value, so
the server's routing and cache follow your notion of a conversation.

### Key takeaways

- One graph node answers one turn, and you can grow the graph from here.
- The checkpointer owns the list, so you name a thread instead of holding it.
- Tokens print as they arrive, and a failed call costs you one line.

### What is still missing

The model can only talk back to you. Tutorial 4 gives it a first tool and the
loop that runs tools until the model stops asking.
