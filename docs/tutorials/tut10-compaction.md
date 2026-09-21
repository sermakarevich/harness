# Tutorial 10 — Context compaction

After this tutorial a long conversation keeps working, because the harness replaces its
older turns with a summary instead of carrying all of them for ever.

## In short

### The concepts

- **The list only grows, and the window has an end.** Every turn joins the list and the whole
  list is resent, so you pay for all of it on every call. Tutorial 9 bounds one result; this
  bounds the whole list.
- **Summarise the old, keep the recent, never cut a turn in half.** Over budget your older
  turns become one short recap while the newest stay untouched, cut only at a turn start.
  pi triggers at the window minus a reserve; opencode blanks old tool outputs instead.
- **What survives matters more than how much you cut.** You measure by the input count on the
  last reply, not a turn sum. The dropped cost stays carried beside the messages. Checking
  only that the agent finished hides the bill, because it pays that bill re-asking for what you
  threw away: compression raised retrieval calls in all six comparisons while completion never
  moved, fabricated content raised re-querying by 57 percent, and a fact-preserving summary
  stayed near-lossless where plain deletion tripled it (knowledge base:
  ContextCompressionInteractionCosts).

### Scope

1. You put the token budget and the number of turns to keep in settings.
2. You measure the conversation by what the model reported reading on its last call.
3. You cut at a turn boundary and replace everything older with one summary.
4. You carry the cost of the dropped turns so the running total never falls.
Left out: pruning results first, a second pass, recovery after a refusal, on-demand compacting.

### The problem

Three shell commands ran first, each printing two thousand lines. The conversation the model
read grew from 3069 to 5829 to 8600 input tokens, and then one trivial question, the last turn
of the run, still cost this much:

```text
> What is 2 plus 2? Reply with just the number.
4
in 5005 (cached 4849) · out 81 (thinking 70) · turn $0.0000 · total $0.0007
```

Tutorial 9 capped each single result, but three capped results still pile up and never leave.
The same question costs 2224 input tokens in a fresh session. A turn that runs a tool makes two
model calls, so its `in` sums both and only the last line measures the conversation.

### What changes

```text
src/harness/
  chat/
+   compact.py            swaps older turns for one summary
+   prompts/summary.txt   asks for facts and forbids guessing
~   graph.py              checks the budget before each turn
~   state.py              carries the cost of dropped turns
  tui/
~   render.py             prints the notice and keeps the total honest
~ config.py               carries the token budget and the kept turns
~ tests/                  offline checks for cutting and carrying cost
```

## In detail

### How it works

1. You type a line, and before anything is sent the harness looks at what the model said it
   read on its last call.
2. Under the budget your turn goes straight to the model, as in every tutorial so far; over
   it your turn goes through the compaction step first.
3. That step finds the start of the turn you must keep, sends everything older to the model once
   with the summary prompt and no tools bound, and swaps the history for summary plus kept turns.
4. The terminal says it happened and never prints the summary itself, then your turn runs as
   usual and the next call carries the short history.

The check sits at the entry to a turn and nowhere else, so you can never cut in the middle
of a tool round.

### Design decisions

- **The check runs at the entry to a turn and nowhere else.** The shape of the graph is what
  guarantees a tool call never loses its result. All four harnesses check before a step.
- **The size is the input count the model itself reported.** It is exact, free, and always
  agrees with what you are billed. pi prefers recent usage for the same estimate.
- **The summary and the dropped turns stay inside the running total.** The summary costs its
  reply, and the dropped turns are carried beside the messages. A total that forgets what you
  spent is worse than no total.

### Run it

```bash
git checkout tut10
just tutorial
```

`just smoke` runs those same three shell commands, the same question, and one more question
after it. Here are its last two turns:

```text
> What is 2 plus 2? Reply with just the number.
Context over 4000 input tokens; older turns summarised.
4
in 5817 (cached 1459) · out 707 (thinking 40) · turn $0.0007 · total $0.0013

> What is 3 plus 3? Reply with just the number.
6
in 3025 (cached 2929) · out 26 (thinking 15) · turn $0.0000 · total $0.0013
```

The fourth turn compacts, so it pays for the summary as well as the answer and its `in` is the
largest of the run. The fifth turn is the payoff: `in 3025` against the `5005` above, and the
notice prints once. The total never falls, because you carry what you spent.

### Under the hood

The honest measure is the last call's input count, not the sum of a turn, because a turn with
a tool calls the model twice and its `in` looks larger than it is; you read the newest reply.

### Key takeaways

- Every turn resends the whole list, so you replace older turns with a summary.
- You cut only at a turn boundary, so a tool call never loses its result.
- You keep names, paths, numbers and decisions, so the model never re-asks for them.

### What is still missing

The summary keeps your conversation alive, but it is written fresh every time and it dies
with the session, and nothing about your project survives into the next one. Tutorial 11 adds
memory files, notes loaded into the system prompt at the start of every session.
