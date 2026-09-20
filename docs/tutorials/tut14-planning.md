# Tutorial 14 — Planning and todos

After this tutorial the model keeps a short task list you can see, the harness holds it, and
summarising the conversation no longer throws the plan away.

## In short

### The concepts

- **A plan that lives in the reply is not a plan.** Nothing outside the words holds it, and the
  summary from tutorial 10 can drop it. Long-running agents stop early, overestimate how much is
  done, and write confident but weak plans (knowledge base: AutonomousLongRunningCodingAgents).
- **One writer, and the whole list every time.** opencode and the DeepSeek Harness replace the
  list whole on every call: no patch language, no identifiers to drift. hermes-agent numbers each
  revision and refuses a stale update; pi has neither and calls both extension work.
- **A short list steers a model that has forgotten everything else.** On SWE-Bench Pro a cheap
  model that inherited an exploration trail plus a todo list reached 92 to 97 percent of the
  frontier model's pass rate at 39 to 53 percent lower cost, while handing over a written plan
  instead cost 14 percent more than not splitting the task at all (knowledge base: Prewalk).

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
