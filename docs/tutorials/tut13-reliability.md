# Tutorial 13 — Reliability and parallel tools

After this tutorial one failed call no longer ends your turn, and three things you asked for at
once take about as long as the slowest one.

## In short

### The concepts

- **Sort, retry, and batch.** You sort model-call errors, retry the kinds that may pass next time
  with a growing wait, and run independent calls together while calls that write stay on their own.
- **Tutorial 12 stopped at the first failure.** There one failed call ended the turn and every
  tool call ran one after another.
- **Calls fail, and whose fault it is decides what to do.** A rate limit, an overloaded server,
  a dropped connection and a refused key all arrive as one exception, and only some pass on the
  next try. The catalogue counts 41 ways a run breaks, 36 the model's and 5 not, and judges
  still blame the model when the tool is at fault (knowledge base: ModelOrHarnessFailureTaxonomy).
- **Sort the error first, wait second, and let only one layer do it.** All four harnesses sort
  before they retry: a wrong key retried three times is three waits and the same error. opencode
  retries server and rate-limit errors up to five attempts, pi retries a turn three times from a
  two-second base, and hermes-agent classifies each failure once.
- **Independent calls run together, conflicting ones cannot, and the win is bounded.** All four
  harnesses run siblings at once and show results in the model's order. Amdahl's law bounds the
  gain by the serial share, and concurrent writes are one of three consistency violations
  (knowledge base: LLMTeamsAsDistributedSystems). Fanning out to 100 calls drove tool calling to
  0 percent while one script held 100 percent (knowledge base: BitterLessonOfToolCalling).

### Scope

1. You put the tries, the first wait, how fast it grows and the parallel limit into settings.
2. You sort each failure and try again only the kinds that often pass next time.
3. You turn off the retrying hidden inside the vendor client, so one policy is in charge.
4. You group a turn's calls into batches and give a call that writes a file a batch of its own.
Left out: a backup model, a second provider, per-file conflict rules, retrying tool calls.

### The problem

```text
> Use the shell tool three times in this one turn, as three separate calls: sleep 5, sleep 5, sleep 5. Do not combine them into one command. Then reply done.
I'll fire off three separate sleep calls at once.
allow shell command=sleep 5? [y]es/[a]lways/[n]o a
→ shell command=sleep 5
→ shell command=sleep 5
→ shell command=sleep 5
done
in 4772 (cached 2146) · out 432 (thinking 252) · turn $0.0004 · total $0.0004
```

The model asked for all three calls in one message and the harness ran them one after another,
so fifteen of those 23 seconds were spent sleeping. A call to a dead port ends the turn at once.

### What changes

```text
src/harness/
  chat/
~   graph.py          retries the model call and passes the parallel limit down
~   run_tools.py      asks first, then runs each batch at once in model order
  model/
+   retry.py          sorts a failure into worth another try or not
~   client.py         turns off the retrying hidden inside the vendor client
  tools/
+   concurrency.py    groups a turn's calls into batches that may share a run
~ config.py           carries the tries, the waits and the parallel limit
~ tests/              offline checks for sorting, waiting and batching
```

## In detail

### How it works

1. A failure goes to one question: is this the kind that often passes next time? If it is not,
   the error reaches the terminal at once, as before.
2. If it is, the harness waits a second, tries again, and doubles the wait, up to three tries.
3. When a reply asks for tools, every permission question is asked first, in the model's order,
   because a question cannot be asked from inside a thread.
4. Calls are grouped so neighbours that cannot collide share a batch and a writing call is alone.
5. Each batch runs at once, and its results go back in the model's order.

A tool call may already have changed a file, so the tools node has no retry policy of its own.

### Design decisions

- **The retry sits above the client, and only one layer retries.** A policy you cannot see is a
  policy you did not choose.
- **Sorting the error comes before waiting.** A rate limit or a dropped connection usually
  passes and a wrong key never does.
- **A call that writes a file runs alone.** Cruder than the harnesses that serialise per path,
  but it costs nothing while the model asks for one write at a time.

### Run it

```bash
git checkout tut13
just tutorial
```

`just smoke` asks the same question as the problem above, word for word. It took 23 seconds at
tutorial 12 and 11 seconds here, because the three sleeps now overlap. `just retries` points the
harness at a port where nothing listens, so it spends no money.

```text
> What is 2 plus 2? Reply with just the number.

error: OpenAIConnectionError: Connection error.
```

The error is the same one, but the turn takes 5 seconds instead of 3 because the harness waited
between tries, and the chat carried on afterwards.

### Under the hood

By default the client made three connection attempts in 1.49 seconds and said nothing; turned
off, it makes one attempt and returns at once. The harness then waits about a second, then about
two, and gives up after three tries, adding a random fraction of a second so that two harnesses
failing together do not come back together. Nothing is printed while it waits: "is this worth
another try?" is asked before the harness checks whether any tries are left, so an answer there
would promise a retry that may never happen. Only the clock and the tests show it.

### Key takeaways

- You sort a failure before you wait on it.
- One layer retries, and it is the one you chose.
- Calls that cannot collide run together, and the model still sees them in the order it asked.

### What is still missing

This harness has one model and one provider. When the provider stays down longer than the waits,
or the key is refused, there is nothing to fall back to. It also has no idea what it is doing
over a long task: every turn starts from the messages and nothing holds the shape of the work.
Tutorial 14 adds planning and todos, a plan the model writes and updates as it goes.
