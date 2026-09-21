# Tutorial 16 — Outside tool servers

After this tutorial the harness can use tools it did not write, borrowed at start-up from
a program running beside it.

## In short

### The concepts

- **You name the servers, the harness borrows their tools.** You name each outside server in the
  settings file, the harness starts each one and asks it for its tools, renames each tool after its
  server, and the loop you already have runs them like its own. Three of the four harnesses in
  `docs/harnesses/OPERATIONS.md` borrow tools this way: opencode puts the server name in front of
  every tool name, hermes-agent keeps one long-lived connection per server and gives a failing one
  a cooldown before trying again, and pi has none.
- **An outside tool server is a second program that offers tools.** Not a library and not a
  plugin: a separate program the harness starts, talks to through the pipes of a child process,
  and asks one question before anything else: what tools do you have? Each answer becomes a tool
  in the same list the loop from tutorial 4 already runs. The Model Context Protocol (MCP) is the
  agreement both sides follow, so the harness needs no code written for that server (knowledge
  base: AI_Harness_Engineering).
- **You pay for a borrowed tool on every turn, whether you use it or not.** Its description and
  its arguments travel with every model call. Measured on a 120-tool, six-server setup, tool
  definitions alone took 47.3 thousand tokens per turn; loading the full description only for the
  tools that match the request cut that to 2.4 thousand, and raised the share of the context
  window doing useful work from 24 to 91 percent (knowledge base: ToolAttentionIsAllYouNeed).
- **A borrowed tool is someone else's code holding your permissions.** An unattended tool with a
  free hand was talked into deleting a database table, and a breach needs three things together:
  private data, text from outside, and a way to send something back out. So every borrowed tool
  stays off the no-question list from tutorial 6, and the harness asks you before each call
  (knowledge base: BuildTimeVsRuntimeDevTools).
- **Tutorial 15 shared jobs, but every tool was written here.** Tutorial 15 let the model hand a job
  to a helper, but every tool either of them could call was one this project wrote; this chapter is
  the first time the harness runs a tool nobody here wrote.
- **Two traps the code guards against.** Two servers can offer a tool of the same name, and the
  dictionary the loop builds keeps only the later one: running one demo server under two names gave
  four tools called `add`, `shout`, `add`, `shout` and two surviving entries, so every tool is
  renamed after its server. One server whose command does not exist fails the whole listing in
  about 0.01 seconds and returns no tools at all, so each server gets its own connection and its
  own `try`.

### Scope

1. You name the servers you want in the settings file, each with the command that starts it.
2. You connect to each one at start-up and ask it for its tools.
3. You rename each tool after its server, so two servers never collide.
4. You wrap it so the loop you already have runs it with no change.
Left out: servers reached over HyperText Transfer Protocol (HTTP), keeping one connection alive
between calls, retries and cooldowns for a server that dies mid-run, a line in the banner naming
the servers that answered, and any way for a helper from tutorial 15 to use a borrowed tool.

### The problem

A real run at tutorial 15, before this chapter's code, shows what the model reaches for:

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

## In detail

### How it works

1. The settings file names each server and the command that starts it.
2. At start-up the harness starts each server as a child process and asks what tools it has.
3. Each remote tool gets its server's name in front of its own.
4. Each one is wrapped in an ordinary tool, so the loop makes the call it always made.
5. The model sees them beside `read_file` and asks for one by name.
6. The harness asks you first, because a borrowed tool is not on the no-question list, then runs
   it and puts the text it returns into the tool result.

Each server gets its own connection, so a server that is not there costs only its own tools;
and the borrowed tools go to your conversation only, never to a helper from tutorial 15,
because a helper may use only tools that need no question.

### Design decisions

- **One connection per server.** Measured: a list holding one working server and one whose
  command does not exist failed the whole listing in about 0.01 seconds and returned no tools at
  all. One `try` per server turns that into losing one server's tools. hermes-agent goes further,
  giving a failing server a growing cooldown so a dead one never stalls a turn.
- **Every tool is renamed after its server.** Remote names arrive raw. Running the same server
  under two names gave four tools whose names were `add`, `shout`, `add`, `shout`, and the
  dictionary the loop builds from them kept two: the second server quietly replaced the first.
  opencode namespaces every key as the server name plus the tool name for the same reason.
- **The remote tool is wrapped, not adopted.** It answers only to an asynchronous call, which the
  loop from tutorial 13 does not make; the wrapper makes that call and hands back plain text. That
  is why nothing else changed: not the permission rule, not the tool-running node, not the registry.

### The excerpt that carries the idea

Adapting one remote tool into a local one is the function `_local_tool` in `servers.py`:

```python
def _local_tool(server: ToolServer, remote) -> StructuredTool:
    def run(**kwargs):
        return join_text(asyncio.run(remote.ainvoke(kwargs)))

    return StructuredTool(
        name=f"{server.name}{NAME_SEPARATOR}{remote.name}",
        description=remote.description,
        args_schema=remote.args_schema,
        func=run,
    )
```

The name gains its server, and the wrapper makes the asynchronous call the loop cannot make;
the text of the reply becomes the tool result: a borrowed tool and `read_file` are the same.

### Run it

```bash
git checkout tut16
just tutorial
```

The first start downloads the outside server once, and with it downloaded a start took 1.4 seconds.

`just smoke` repeats the problem question with a tool made for it, and it took 7 seconds.

```text
> What time is it in Tokyo right now?
I'll check the current time in Tokyo.
allow time_get_current_time timezone=Asia/Tokyo? [y]es/[a]lways/[n]o a
→ time_get_current_time timezone=Asia/Tokyo
It's 4:44 PM on Monday in Tokyo.
in 5513 (cached 2658) · out 215 (thinking 120) · turn $0.0003 · total $0.0003
```

The model asked for one narrow tool by name, and you approved that tool rather than a command line.
The answer came from a program the harness did not write.

### Under the hood

The first turn read 5081 input tokens before this tutorial and 5513 after it, a difference of
432 tokens, and that difference rides on every call whether a borrowed tool is used or not. Every
call starts the server again. One round trip through a local server measured 254.9 milliseconds
and 250.4 milliseconds on two calls, and 234.6, 232.2, 236.1 and 234.0 in repeat runs. Nothing is
kept alive between calls, and nothing is left running afterwards. The harness pays that price for
correctness it did not have to write, which is the trade the protocol exists to make.

### Key takeaways

- A borrowed tool is a normal tool by the time the loop sees it, and everything interesting
  happens in the renaming and wrapping.
- A server you do not control gets the same permission question as the shell, and for the
  same reason.
- The tool list is not free: every borrowed tool is paid for on every turn.

### What is still missing

Nothing is printed when a server is skipped, there is no retry or cooldown for a server that dies
mid-run, only servers started as a child process are supported and not ones reached over
HyperText Transfer Protocol (HTTP), and a helper still cannot borrow. Tutorial 17 adds
evaluation, so a change to the harness can be measured instead of argued about.
