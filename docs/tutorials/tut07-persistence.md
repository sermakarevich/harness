# Tutorial 7 — Session persistence

After this tutorial, closing the terminal no longer loses the conversation.

## In short

### The concepts

- **Checkpoints move from memory to disk.** Tutorial 3 keyed the conversation by
  thread id, but the checkpointer died with it. Swapping in SQLite is small: the
  graph never knew where its state was kept (knowledge base:
  TheAnatomyOfAnAgentHarness). opencode and hermes-agent keep sessions in a local
  database, while pi and the DeepSeek Harness keep them in line-delimited JSON files.
- **The thread id becomes a session name.** The id that loads the conversation
  is the one the banner prints and the one you type after `/resume`. opencode
  re-reads its rows, pi walks a branchable tree, hermes-agent builds views.
- **List, pick, continue.** You see recent conversations with the time and the
  first thing you said, which you recognise (knowledge base: BuildingLongRunningAgenticAISystems).
  Each step saves, as in all four harnesses, so a mid-turn kill still resumes. The
  DeepSeek Harness repairs a kill-cut tail by appending the missing closers, not by truncating it.

### Scope

1. You open a SQLite store on disk and hand it to the graph.
2. You read back the recent conversations with a label you recognise.
3. You run `/resume` to list them and `/resume 2` to continue one.
4. You check that a second process really sees the first one's memory.
Left out: branching a conversation, renaming or deleting one, and any cap on size.

### The problem

```text
$ just tutorial
> Remember the word banana. Reply with just: ok
ok
> /exit

$ just tutorial
> Which word did I ask you to remember? Answer in one line and do not use any
tools.
You didn't ask me to remember any word.
> /exit
```

The second process starts from nothing, and the two session ids in the banners
are the reason: each run invented a new one and nothing on disk connected them.

### What changes

```text
src/harness/
  chat/
+   store.py              opens the on-disk session store
+   sessions.py           lists saved conversations with a label
~   session.py            resumes a saved id instead of starting fresh
  tui/
+   pick.py               prints the numbered list and reads your pick
~   app.py                opens one store for the whole run
~   commands.py           answers /resume with a list or a switch
~ config.py               carries the store path setting
~ settings and packaging  default path, locked deps, ignored store file
~ tests/                  offline checks for listing, picking, and resuming
```

## In detail

### How it works

1. The terminal opens the SQLite store at the configured path.
2. You type `/resume`.
3. The harness lists recent conversations newest first, numbered by what you said.
4. You type `/resume 1`.
5. The harness builds a session around that existing id, not a new one.
6. Your next line enters the graph with that thread id, and the saved past loads.
7. It answers from history with no tool call.

The graph, the loop, and the gate are untouched, because none of them ever knew
where the state was kept.

### Design decisions

- **One store opens for the whole run and every session shares it.** Switching
  with `/resume` is then only a change of thread id, and the file never opens twice.
- **Ordering comes from the store, not from a field you maintain.**
  Continuing a conversation already moves it to the front, so a "last used"
  column is a second copy of a fact the checkpointer already has.
- **`/new` keeps its meaning and no longer loses anything.** The old conversation
  stays on disk and can be resumed; before, the same command threw it away.

### Run it

```bash
git checkout tut07
just tutorial
```

`just smoke` runs the harness twice: the first run saves, the second resumes.

```text
harness · model muse-spark-1.3-contributor · session e487b9e6 · /help for
commands
> Remember the word banana. Reply with just: ok
ok
> /exit
harness · model muse-spark-1.3-contributor · session 35e4d791 · /help for
commands
> /resume 1
resumed session harness-413d5f01-3ed4-4d40-a834-d7dde487b9e6
> Which word did I ask you to remember?
banana
> /exit
```

### Under the hood

A waiting permission question survives a restart, and answering it finishes
the old tool call. Nothing arranges this: the pause is state, so it saves
with the rest. Tutorials 6 and 7 give you this together.

### Key takeaways

- The graph compiles against a SQLite saver, so conversations survive restarts.
- The thread id is the session name: the banner shows it, `/resume` takes it.
- All state saves together, so always answers and open questions come back too.

### What is still missing

Every turn resends the whole saved conversation, and chats that live for days
only grow it, with nothing counting the cost. Tutorial 8 puts a number on it.
