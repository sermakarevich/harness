# Tutorial 14 — Planning and todos

After this tutorial the model keeps a short task list you can see, the harness holds it, and
summarising the conversation no longer throws the plan away.

## In short

### The concepts

- **Planning here is one short list the harness holds.** Not a document and not a design: a few
  steps, each marked waiting, in progress or done. The model decides the steps and rewrites them
  as it works; the harness keeps the list, prints it for you, and puts it back in front of the
  model on every call. A plan that lives only in the reply is not a plan: nothing outside the
  words holds it, the summary from tutorial 10 can drop it, and long-running agents stop early
  and overestimate how much is done (knowledge base: AutonomousLongRunningCodingAgents).
- **One writer, and the whole list every time.** opencode and the DeepSeek Harness replace the
  list whole on every call: no patch language, no identifiers to drift. hermes-agent numbers each
  revision and refuses a stale update; pi has neither and calls both extension work.
- **A short list steers a model that has forgotten everything else.** On SWE-Bench Pro a cheap
  model that inherited an exploration trail plus a todo list reached 92 to 97 percent of the
  frontier model's pass rate at 39 to 53 percent lower cost, while handing over a written plan
  instead cost 14 percent more than not splitting the task at all (knowledge base: Prewalk).
- **You start after tut13 with retries and parallel calls but no memory of the job shape.** This
  chapter adds a `todos` field in graph state plus a whole-replace write tool.
- **The list lives in state, not messages, with one `doing` task at most.** The harness demotes
  extras under the one-doing rule.

### Scope

1. You add one list to the state of the graph and one tool that replaces the whole list.
2. You let the harness keep the only rule that matters: one item in progress at a time.
3. You put the current list under the system prompt on every call, so a summary cannot lose it.
4. You show the list in the terminal every time it changes.
Left out: plan mode, an approval gate, editing one item, identifiers, and any copy on disk.

### The problem

The last lines of a real run at tutorial 13, where you asked for a plan first:

```text
> Create notes.txt with the three lines alpha, beta and gamma, then read it back and tell me how many lines it has. Plan the work first.
allow write_file content=alpha beta gamma  path=notes.txt? [y]es/[a]lways/[n]o a
→ write_file content=alpha beta gamma  path=notes.txt
→ read_file path=notes.txt
Plan was to write the file, then read it back and count.

Done. notes.txt has 3 lines.
in 7373 (cached 4691) · out 597 (thinking 397) · turn $0.0004 · total $0.0004
```

The model did plan, but it said so in prose, in the past tense, once the work was over.

### What changes

```text
src/harness/
  chat/
+   prompts/todos.txt  how to keep the list, and the list as it stands
~   graph.py           puts the current list under the system prompt on every call
~   prompt.py          fills the list into that prompt
~   run_tools.py       hands the new list on as state
~   state.py           one more field beside the messages
  tools/
+   todos.py           the list, its one rule, and the tool that replaces it whole
~   registry.py        the model sees the new tool, and no question is asked about it
  tui/
~   render.py          prints the list instead of a one-line tool arrow
~ tests/               offline checks for cleaning, replacing and surviving a summary
```

## In detail

### How it works

1. Before every model call the harness writes the list it holds under the system prompt.
2. The model replaces the whole list with one tool call, one item per line, a status and a step.
3. The harness keeps the order and moves every in-progress item after the first back to waiting.
4. The new list replaces the one in state, and the terminal prints what the tool hands back.

The list is not a message, so the summary node never sees it. That is why it lives in state.

### Design decisions

- **The list is state, not chat text.** Everything in the conversation is a candidate for the
  summary, and nothing in the conversation can be printed as a list.
- **The model replaces the whole list every time.** That costs a few more tokens than patching
  one item and removes every way for an index or an identifier to drift.
- **One rule, and no more.** Only one item may be in progress; the rest is the model's judgement.

### The excerpt that carries the idea

How to plan is not in the code. It is five sentences the harness puts under the system prompt
on every call, in `chat/prompts/todos.txt`.

```text
Keep one short task list for any job of more than one step. Write the whole list every
time with the write_todos tool, one item per line, as status: what the step is, where
status is todo, doing or done. Only one item may be doing. Move an item to doing when
you start it and to done the moment it is finished. Do not write the list into your
reply, because the list below is what the harness holds right now.

{todos}
```

`{todos}` is replaced by the list as the harness holds it, so the model reads its own plan
back before every decision. That is the whole method: write a list when the job has more than
one step, rewrite it whole to change anything, keep exactly one item in progress, and let the
harness rather than the reply hold it.

### Run it

```bash
git checkout tut14
just tutorial
```

`just smoke` asks that same question, word for word. It took 12 seconds at tutorial 13 and 30
seconds here, because the model stopped four times to rewrite the list. From the first list on:

```text
☐ Create notes.txt with alpha, beta and gamma
☐ Read notes.txt back and count lines
◐ Create notes.txt with alpha, beta and gamma
☐ Read notes.txt back and count lines
allow write_file content=alpha beta gamma  path=notes.txt? [y]es/[a]lways/[n]o a
→ write_file content=alpha beta gamma  path=notes.txt
☑ Create notes.txt with alpha, beta and gamma
◐ Read notes.txt back and count lines
Created the file. Now I'll read it back to count the lines.
→ read_file path=notes.txt
☑ Create notes.txt with alpha, beta and gamma
☑ Read notes.txt back and count lines
Created notes.txt. It has 3 lines.
in 20397 (cached 14615) · out 805 (thinking 330) · turn $0.0008 · total $0.0008
```

The answer is the same; what is new is that you can watch the shape of the job while it runs.

### Under the hood

The same question read 7373 input tokens and cost $0.0004 at tutorial 13, and 20397 tokens and
$0.0008 here: each list update ends one model call and starts another that re-reads the
conversation. The tool hands back the cleaned list rather than an acknowledgement, so a model that
marked two items in progress sees at once which one was kept.

### Key takeaways

- A plan you can see is state, not prose.
- The whole list is rewritten every time, so nothing can drift.
- The harness keeps one rule and leaves the rest of the judgement to the model.

### What is still missing

The harness does whatever the list says the moment the model writes it. There is no mode that
stops the work until you have read the plan and agreed to it, as three of the four harnesses do.
Tutorial 15 adds sub-agents, a child graph that takes one job and gives back one summary.
