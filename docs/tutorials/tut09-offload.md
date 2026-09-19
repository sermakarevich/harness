# Tutorial 9 — Tool output offloading

After this tutorial big tool outputs stay out of the conversation but within reach.

## In short

### The concepts

- **One tool call can flood the context.** A command prints what it wants; every character
  stays in the conversation. The terminal shows the call, never the output, so only the cost
  line from tutorial 8 reveals it. The OsmaniHarness note lists offloading among four defences
  against context rot: compaction, skills with progressive disclosure, and full resets. All four
  cap inline text and spill the rest to a file; hermes-agent budgets the whole turn on top.
- **Save it, then point at it.** The whole text lands in a file; the model keeps the first part
  plus the path, so nothing is lost and most stays out of context. Work leaves context for
  storage it reads on demand, a harness job (knowledge base: ExternalizationInLLMAgents). opencode
  previews the head and drops week-old spills, pi caps lines and bytes, and the DeepSeek Harness
  previews both ends, spills images down a second path, and stays inline with nowhere to spill.
- **Caching buys money back, never space.** Below, the second turn is almost entirely cached
  input, so the flood cost almost nothing and still filled the window. Tutorial 8 could not
  fix this half of the bill, which is why a cap is a separate job from a price.

### Scope

1. You put the character limit and the spill folder in settings.
2. You write the whole result to a file when it goes over the limit.
3. You hand the model the first part plus the path and the full size.
4. You move the exit code to the front of a shell result so the cap can never cut it.
Left out: a per-turn budget, a both-ends preview, and a way to fetch the middle of a file.

### The problem

```text
> Run the shell command "seq 1 2000" and then reply with just: done
→ shell command=seq 1 2000
done
in 7004 (cached 994) · out 209 (thinking 129) · turn $0.0006 · total $0.0006

> What is 2 plus 2? Reply with just the number.
4
in 6179 (cached 6001) · out 41 (thinking 30) · turn $0.0000 · total $0.0007
```

`seq 1 2000` prints 8893 characters, worth roughly 4700 tokens against about 2280 input tokens
for a turn with no tool output. The second turn asks something unrelated and pays for them again.

### What changes

```text
src/harness/
  chat/
~   graph.py              wires the spill function into the tools node
~   run_tools.py          passes every tool result through the spill
  tools/
+   offload.py            writes long results to disk, returns a preview plus a path
~   shell.py              reports the exit code before the output
~ config.py               carries the limit and the folder settings
~ settings and packaging  the 2000-character limit and the spill folder
~ tests/                  offline checks for spilling and previewing
```

## In detail

### How it works

1. The model asks for a tool, and the gate from tutorial 6 asks you when the policy says so.
2. The tool runs and hands back text that passes the one place where a result becomes a message.
3. Under the limit the text goes through untouched; over it the whole text goes to a file.
4. The message keeps the first part plus a notice with the size and the path.
5. That message is what is saved and what every later turn resends.
6. The model reads the notice and decides whether it wants the file.

The cap sits on the road every result travels, so a later tool is bounded for free.

### Design decisions

- **The cap sits in the tools node.** Keeping the context small is your job, and a tool written
  next month gets it for free. opencode and pi also cap where a tool run ends, and hermes-agent
  puts a whole-turn budget above that.
- **The spill file is named after its text, not its call.** The same output never lands on
  disk twice, and nothing the model chose ends up in a file name, as in tutorial 5's paths.
- **The exit code moves to the front.** The end of a long output is what gets cut, and whether
  the command worked is the one thing you can never let the model lose.

### Run it

```bash
git checkout tut09
just tutorial
```

`just smoke` runs the same two turns as the problem above.

```text
harness · model muse-spark-1.3-contributor · session 2e7c91eb · /help for
commands
> Run the shell command "seq 1 2000" and then reply with just: done
I'll run seq 1 2000 now.
allow shell command=seq 1 2000? [y]es/[a]lways/[n]o y
→ shell command=seq 1 2000
done
in 3132 (cached 994) · out 251 (thinking 166) · turn $0.0003 · total $0.0003

> What is 2 plus 2? Reply with just the number.
4
in 2301 (cached 2161) · out 36 (thinking 25) · turn $0.0000 · total $0.0003

> /exit
ls .harness/outputs
44a39ad06c524a5f.txt
```

### Under the hood

The flood never reaches your screen: the terminal prints the call line, never the output, so
at tutorial 8 the only sign of the flood was the cost line. Caching made the
second turn nearly free without giving the window back: cached tokens are cheap, not absent.

### Key takeaways

- One tool call can flood the context, so you spill long results to disk.
- The model gets the first part plus the path and the size, so nothing is lost.
- Cached tokens are cheap but still fill the window, so a cap is a separate job from a price.

### What is still missing

No single call floods the context now, but the conversation still only grows and every
turn resends all of it. Tutorial 10 summarises the old turns and keeps the recent ones.
