# Tutorial 16 — Outside tool servers

After this tutorial the harness can use tools it did not write, borrowed at
start-up from a program running beside it.

## In short

### The concepts

- **An outside tool server is a second program that offers tools.** Not a library and not a
  plugin: a separate program the harness starts, talks to through the pipes of a child
  child process, and asks one question before anything else: what tools do you have?
  Each answer becomes a tool in the same list the loop from tutorial 4 already runs.
  The Model Context Protocol (MCP) is the agreement both sides follow, so the harness
  needs no code written for that server (knowledge base: AI_Harness_Engineering).
- **You pay for a borrowed tool on every turn, whether you use it or not.** Its
  description and its arguments travel with every model call. Measured on a 120-tool,
  six-server setup, tool definitions alone took 47.3 thousand tokens per turn; loading
  the full description only for the tools that match the request cut that to 2.4
  thousand, and raised the share of the context window doing useful work from 24 to 91
  percent (knowledge base: ToolAttentionIsAllYouNeed).
- **A borrowed tool is someone else's code holding your permissions.** An unattended
  tool with a free hand was talked into deleting a database table, and a breach needs
  three things together: private data, text from outside, and a way to send something
  back out. So every borrowed tool stays off the no-question list from tutorial 6, and
  the harness asks you before each call. (knowledge base: BuildTimeVsRuntimeDevTools)

### Scope

1. You name the servers you want in the settings file, each with the command that starts it.
2. You connect to each one at start-up and ask it for its tools.
3. You rename each tool after its server, so two servers never collide.
4. You wrap it so the loop you already have runs it with no change.
Left out: servers reached over HyperText Transfer Protocol (HTTP), keeping one connection alive
between calls, retries and cooldowns for a server that dies mid-run, a line in the banner naming
the servers that answered, and any way for a helper from tutorial 15 to use a borrowed tool.

### The problem

```text
> What time is it in Tokyo right now?
I'll check the current time in Tokyo for you.
allow shell command=TZ='Asia/Tokyo' date; date -u? [y]es/[a]lways/[n]o a
→ shell command=TZ='Asia/Tokyo' date; date -u
It is 4:41 PM in Tokyo right now, Monday September 21.
in 5081 (cached 2402) · out 392 (thinking 285) · turn $0.0004 · total $0.0004
```

The harness has no tool for this, so the model reaches for the shell, the one tool that
can do anything. You are asked to approve a command line you have to read and judge. A
narrow tool made for the job would be both safer to allow and easier for the model to get
right.

### What changes

```text
src/harness/
  tools/
+   servers.py         connects to each server and adapts its tools into local ones
  chat/
~   graph.py           adds the borrowed tools to the parent's list
  model/
~   text.py            the text-joining part is now reusable
~ settings.toml        the servers to start, and the command for each
~ tests/               offline checks with a tiny server of our own
```
