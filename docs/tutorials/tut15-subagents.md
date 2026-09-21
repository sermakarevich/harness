# Tutorial 15 — Sub-agents

After this tutorial the model can hand one job to a helper that starts with an
empty conversation, and everything the helper reads stays out of yours.

## In short

### The concepts

- **A helper buys context, not cleverness.** With the thinking-token budget held equal, a single
  agent matched or beat every multi-agent arrangement tested on multi-hop reasoning, and the
  multi-agent versions only pulled ahead when the single agent's context was deliberately
  damaged with masking, deletion or distractors (knowledge base:
  SingleAgentLlmsOutperformMultiAgentSystemsOnMultiHopReasoning).
- **A helper knows only what the job says.** When agents each hold part of a specification,
  integration success fell by 30 to 35 percentage points against one agent doing the whole
  thing, at every level of detail tested, and restoring the full specification was both
  necessary and sufficient to repair it (knowledge base: TheSpecificationGap).
- **One rule gives the whole policy.** The tools that need no permission question are exactly
  the tools a helper may use. That keeps a helper read-only, and because asking for a helper
  needs a question, a helper cannot ask for one, with no counter anywhere. opencode reaches
  the same limit of one by walking the parent chain on every call.

### Scope

1. You add one tool that hands over one job and brings back one answer.
2. You build the helper out of the same graph, with a smaller tool list and nothing saved.
3. You frame the job so the helper knows that only its last message comes back.
4. You keep the parent's conversation free of everything the helper read.
Left out: helpers running in parallel or in the background, named helper types, a depth counter,
and any accounting of what a helper spent.

### The problem

A real run at tutorial 14 that took 9 seconds shows where the cost lands:

```text
> Read src/harness/tools/permission.py and src/harness/tools/registry.py and tell me in one sentence which tool calls never need a permission question.
Reading the two files to check which tools skip permission.
→ read_file path=src/harness/tools/permission.py
→ read_file path=src/harness/tools/registry.py
Read file, read skill, and write todos never need a permission question.
in 5081 (cached 2402) · out 439 (thinking 285) · turn $0.0004 · total $0.0004
```

The model answered correctly, but both files now sit in the conversation for good and every
later turn pays for them again. The only tool the harness has for that is the summary from
tutorial 10, which throws the detail away instead of putting it somewhere cheaper.

### What changes

```text
src/harness/
  chat/
+   helper.py          the tools a helper may use and how one job is run
+   prompts/helper.txt what a helper is told before it starts, and the job
~   graph.py           builds the helper from the same code and adds the tool
~   prompt.py          frames one job as the helper's first message
  tools/
+   ask_helper.py      hands one job over and brings back one answer
~ tests/               offline checks that the helper's work stays out of your conversation
```

## In detail

### How it works

1. The model calls one tool with one job, written in its own words.
2. The harness asks you first, because that tool is not on the no-question list.
3. The same code builds a second graph with only the tools that need no question.
4. That graph runs its own loop with no saved conversation, reads what it needs, and stops.
5. Its last message comes back as the tool result.
6. Nothing else it did reaches your conversation.

The helper is the same graph built a second time, so every later tutorial improves both at once.

### Design decisions

- **Same graph, smaller tool list.** A second engine would be a second thing
  to keep working. hermes-agent does the same: a child gets the parent's tool
  groups minus the blocked ones.
- **Only tools that need no question.** That keeps the helper read-only.
  It cannot ask for a helper of its own,
  so the depth limit needs no counter.
- **Nothing saved but the answer.** No thread, no checkpoint,
  no conversation to resume. The only thing worth keeping is the answer.

### Run it

```bash
git checkout tut15
just tutorial
```

`just smoke` asks for the same answer as above, through a helper. It took 18 seconds.

```text
> Ask a helper to read src/harness/tools/permission.py and src/harness/tools/registry.py and tell me in one sentence which tool calls never need a permission question.
I'll ask a helper to read those tool files and identify which calls skip permission checks.
allow ask_helper job=Read src/harness/tools/permission.py and src/harness/tools/r…? [y]es/[a]lways/[n]o a
→ ask_helper job=Read src/harness/tools/permission.py and src/harness/tools/r…
Read-only tools `read_file`, `read_skill`, and `write_todos` never need a permission question.
in 5016 (cached 2402) · out 314 (thinking 163) · turn $0.0003 · total $0.0003
```

The answer matches, and neither file entered the conversation, so the next turn stays small.

### Under the hood

The parent's own turn barely moved: 5081 input tokens without a helper, 5016 with one.
Delegation never makes that turn cheaper: the job costs about what the question cost.
What changes is what the conversation carries afterwards. The same follow-up after each answer
read 3133 input tokens without a helper and 2864 with one. 2673 of them were cached in both,
so the fresh text fell from 460 tokens to 191. The two files are 1347 characters between them,
and that is the whole saving: the size of what the helper read. Its own model calls are counted
nowhere, so the cost line under a delegated turn reads lower than the turn really cost. More
tokens were spent in total, across two conversations instead of one. Only the parent's got smaller.

### Key takeaways

- A helper spends a second conversation's context; it does not give a better answer.
- The helper starts empty, so the job text is all it knows.
- The permission rule you already have is the whole delegation policy.

### What is still missing

One helper runs at a time and the harness waits for it, so there is no parallel and no background
work, which two of the four harnesses have, and nothing counts what a helper spends. Tutorial 16
adds outside tool servers, so the harness can use tools it did not write itself.
