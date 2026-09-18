# Tutorial 2 — Messages stack into memory

After this tutorial the model remembers what you said earlier in the same run, and you know
exactly where that memory lives: in a list your harness keeps and resends every turn.

## In short

### The concepts

- The list is the memory: "Every call replays the entire conversation history. The harness
  fakes memory." You resend the list every turn (knowledge base: AGENTIC_ENGINEERING_PATTERS).
  - opencode rebuilds model messages from stored parts on every turn.
  - pi walks its session tree from leaf to root and converts the path for the provider.
  - hermes-agent copies stored history into a working turn context each turn.
- The system prompt is the standing order. It sits first and shapes every answer you get. The
  rulebook is the highest-leverage point in the harness (knowledge base: OsmaniHarness).
  - opencode assembles the prompt fresh every turn from a template plus environment facts.
  - pi renders its tool list plus guidelines with the date and working directory last.
  - hermes-agent builds the prompt once per session and freezes it for cache savings.
- The adapter is the vendor seam. One `chat()` entry point hides the address and the key,
  so swapping backends never touches your code (knowledge base: HarnessEngineeringCourse).
  - opencode maps each vendor to its models with per-model normalization.
  - pi keeps one model interface over four wire protocols.
  - hermes-agent keeps one global name-to-vendor map plus per-profile scoped maps.

### Scope

1. You keep a list of messages and resend the whole list every turn.
2. You put a system prompt first in that list.
3. You reach the model through one adapter instead of raw HTTP.
4. You ask the two tutorial 1 questions again and watch the model remember.

Left out for now; tutorial 3 adds all three:

- streaming the answer as it arrives
- saving the list anywhere past the process
- a real terminal around the chat

### The problem

```text
> Remember this word: pelican
Got it — I'll remember the word **"pelican"**.
blocks: reasoning, message
> Which word did I ask you to remember? Answer with the word only.
You haven't asked me to remember a word yet in this conversation.
blocks: reasoning, message
```

That is the tutorial 1 run: the second request carried only the second question.

### What changes

```text
src/harness/
~   model/client.py           LangChain adapter replaces the raw call
~   model/text.py             reads answers from typed blocks
+   chat/loop.py              the message list that is the memory
+   chat/prompt.py            fills the system prompt file with date and directory
+   chat/prompts/system.txt   the standing order, as data
+   tui/app.py                line chat with a context count and /new
+   tui/commands.py           the slash commands
~   __main__.py               starts the chat
tests/                        offline tests for the list, prompt, and commands
```

## In detail

### How it works

You type the first question and the harness appends it behind the system message, then sends
the whole list, system text first and history after (knowledge base: HarnessEngineeringCourse).
The reply is appended too, so the list holds your question and the model's own answer. On the
second turn the model sees all of it, including its own earlier answer, so the word comes back.

```text
[system] -> [system, user] -> [system, user, assistant] -> ...
```

The `context: N messages` line makes this growth visible; later tutorials put a price on it (8)
and cut it back (10). You type `/new` and the harness keeps only the system message, so the next
question travels alone and the model forgets again. It is the same cause as tutorial 1, now under your control.

### Design decisions

- **The harness owns the list, not the model or the server.** Later tutorials trim that list and
  save it to disk, which is only possible because you hold it.
- **The system prompt is a text file, not code.** It is filled with today's date and the working
  directory, so the standing order stays data you can read and change without touching code.
- **The adapter is the only place with vendor knowledge.** The model is swappable because nothing
  above the adapter sees a header or a URL.

### Run it

```bash
git checkout tut02
just tutorial
```

```text
> Remember this word: pelican
Got it, I'll remember pelican.
context: 3 messages
> Which word did I ask you to remember? Answer with the word only.
pelican
context: 5 messages
> /new
new conversation
> Which word did I ask you to remember? Answer with the word only.
You haven't asked me to remember a word.
context: 3 messages
```

`just tutorial` takes the same lines from your keyboard, and Ctrl-D leaves the chat.

### Under the hood

The reply still arrives as typed blocks, as in tutorial 1. The text reader joins only the text
blocks, so the list holds answers and never reasoning.

### Key takeaways

- The message list is the memory: you resend it whole every turn.
- The system prompt sits first and shapes every answer.
- One adapter hides the vendor, so the model stays swappable.

### What is still missing

The list lives in one variable and dies with the process, and each answer arrives all at once.
Tutorial 3 gives the list a keeper and adds the terminal that streams the answer.
