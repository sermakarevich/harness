# Tutorial 8 — Token accounting and cost

After this tutorial you see what every turn costs, and what the whole conversation has cost so far.

## In short

### The concepts

- **The numbers come back with the reply.** You do not count tokens yourself and you cannot:
  only the server knows how its tokeniser split your text. Every reply carries a usage record that
  rides on the message, so tutorial 7 has been saving it all along (knowledge base:
  HarnessEngineering). Usage per turn in opencode, per message in pi, queued in hermes-agent.
- **A bill is three numbers against three rates.** Output costs twice as much as input on this
  model, the thinking you never see is billed as output, and input the server has already seen
  costs one fiftieth of the input rate. The server sends counts, never money, so you carry the
  rates in settings. opencode prices with exact decimal maths and splits reasoning out, pi prices
  into a cost field for the terminal footer, hermes-agent prices per million in the background.
- **Every turn pays for the whole conversation again.** Tutorial 2 said the list is the memory
  and every turn resends it, so the input number on turn ten is the whole of turns one to nine.
  Caching keeps this survivable for you; compaction (tutorial 10) keeps it bounded. One study put
  the same task at about 1.1 million tokens under one harness, 1.3 under opencode and 2.2 under
  pi, so the harness decides most of the bill (knowledge base: NOOAObjectOrientedAgents). Raw
  spend explained about 1 percent of success, so paying more is not doing better (knowledge base:
  ScalingLawsAgentHarnesses). The DeepSeek Harness only measures pressure on the context window.

### Scope

1. You read the usage record off the replies the conversation already saved.
2. You put the three rates in settings, where you can change them.
3. You price full-rate input, cached input and output, each at its own rate.
4. You print one dim line after each turn with this turn and the total so far.
Left out: more models in the table, a budget or warning near a limit, and the window gauge.

### The problem

```text
harness · model muse-spark-1.3-contributor · session 2e7c433e · /help for
commands
> Say hello in exactly three words.
Hello dear friend
> Now say goodbye in exactly three words.
Goodbye dear friend
> /exit
```

The second turn quietly resent the first, and nothing on the screen says how much text went to
the server or what it cost.

### What changes

```text
src/harness/
  chat/
+   usage.py              prices three kinds of token against three rates
~   session.py            reads the saved messages back for totaling
  tui/
~   render.py             prints one dim cost line after each turn
~ config.py               carries the three price settings
~ settings and packaging  input, cached input, and output rates
~ tests/                  offline checks for totaling and pricing
```

## In detail

### How it works

1. The turn starts and you note how long the saved conversation is.
2. You send the whole list; the model answers and its reply carries the usage record.
3. The reply is appended and saved, so the record sits on disk with it.
4. You read the conversation back: new messages since the turn started are this turn.
5. Each set of counts is priced against the three rates, and one dim line prints both.

You keep no counter anywhere, so nothing can drift and a resumed conversation brings its own bill
back with it.

### Design decisions

- **The totals are read from the saved messages, not kept in a counter.** The counts already
  live on the replies, so a second copy would drift. Tutorial 7 took its ordering from the store
  for the same reason.
- **The rates live in settings, not in the code.** A provider changes prices without asking you,
  so you keep them where you can change them too. A wrong number that is quiet is worse than none.
- **Cached input is priced apart from fresh input, not folded in.** On this model the
  difference is fifty-fold. Some providers also charge to write the cache; this one reports
  only reads, so three rates are all you need here.

### Run it

```bash
git checkout tut08
just tutorial
```

`just smoke` runs the harness twice: the first run saves, the second resumes.

```text
harness · model muse-spark-1.3-contributor · session e47e52db · /help for
commands
> Remember the word banana. Reply with just: ok
ok
in 912 (cached 113) · out 149 (thinking 138) · turn $0.0001 · total $0.0001

> /exit
harness · model muse-spark-1.3-contributor · session 29beb369 · /help for
commands
> /resume 1
resumed session harness-f6a13a63-7a08-46a8-9643-8a58e47e52db
> Which word did I ask you to remember?
banana
in 1076 (cached 881) · out 209 (thinking 198) · turn $0.0001 · total $0.0002

> /exit
```

### Under the hood

Most of what you pay for on this model is thinking you never see: 138 of 149 output tokens on
the first turn above were reasoning, 198 of 209 on the second. They are billed as output, so you
pay for a model which thinks harder.

### Key takeaways

- Every reply carries its token counts, so you read the bill from saved messages, never a counter.
- A bill is full-rate input, cached input, and output, each against a rate you own in settings.
- Every turn resends the full history, so caching decides what you actually pay.

### What is still missing

One tool output can be bigger than the whole conversation around it, and it stays in the history,
so you pay for it on every turn that follows. Tutorial 9 keeps the big ones out of the context.
