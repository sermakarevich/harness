# Tutorial 2 — Messages stack into memory

After this tutorial the model remembers what you said earlier in the same run, and you
know exactly where that memory lives: one list your harness keeps and resends every turn.

## In short

### The concepts

- **The list is the memory.** A conversation is a list of messages with three roles:
  - `system`: the standing order, always first
  - `user`: what you type
  - `assistant`: what the model answered before
  The model keeps nothing; your harness keeps the list and resends all of it every turn:
  "Every call replays the entire conversation history. The harness fakes memory."
  (knowledge base: AGENTIC_ENGINEERING_PATTERS).
  - opencode rebuilds the list fresh every turn from message parts in a local database.
  - pi walks its branchable session tree down the active path before each call.
  - hermes-agent copies stored history into a working list at the start of each turn.
- **The system prompt is the standing order.** It sits first and shapes every answer. The
  rulebook is the highest-leverage configuration point because it lands in the system
  prompt every turn (knowledge base: OsmaniHarness). The payload is system text first,
  then the full history, on every call (knowledge base: HarnessEngineeringCourse).
  - opencode assembles the prompt fresh every turn from a template plus live facts.
  - pi renders tools and guidelines into the prompt, with date and directory last.
  - hermes-agent builds the prompt once per session and freezes it to reuse cached work.
- **The adapter is the vendor seam.** It is the only code that knows the model's server.
  Everything above it gets a model object and never sees a header or a URL, so swapping
  the backend never touches the agent code (knowledge base: HarnessEngineeringCourse).
  - opencode maps vendors to models in a catalog with per-model translation rules.
  - pi merges its built-in model list with your files behind one model interface.
  - hermes-agent keeps one global name-to-vendor map plus per-profile scoped maps.

### Scope

1. You keep a list of messages and resend it every turn.
2. You put a system prompt first.
3. You reach the model through one adapter.

Left out on purpose: streaming, saving the list, and a real terminal. Tutorial 3 adds them.

### The problem

Without a list, each question is a fresh call, and the exchange looks like this:

```text
> Remember this word: pelican
pelican noted.
> Which word did I ask you to remember? Answer with the word only.
I do not know; I see only this one question.
```

### What changes

```text
+ scripts/chat_list.py                 a chat that resends the list
+ src/harness/chat/prompt.py           build the system prompt
+ src/harness/chat/prompts/system.txt  the standing order
+ src/harness/model/client.py          the one adapter
+ src/harness/model/text.py            read text out of replies
+ tests/                               offline checks for the above
```

## In detail

### How it works

You start with a list of one: the system message. Each turn appends your line, sends the
whole list, and appends the reply:

```text
[system] -> [system, user] -> [system, user, assistant] -> ...
```

On turn two the model sees the whole list, including its own earlier answer; that is why
it repeats `pelican` back to you. The `context` count after each reply is the list length,
so you watch it grow from 3 to 5. Tutorial 8 puts a price on that growth, and tutorial 10
cuts it back. `/new` throws the list away and keeps only the system message, so the next
question starts over at one.

### Design decisions

- **The harness owns the list, not the model or the server.** Nothing on the server
  persists, so the list lives on your side. Later tutorials trim, save, and price it.
- **The system prompt is a text file filled with the date and the working directory.**
  The standing order is data, not code. Fresh facts on every run ground each answer.
- **The adapter is the only place with vendor knowledge.** Headers and keys live there
  and nowhere else. The chat takes a model object, so swapping backends never touches it.

### Run it

```bash
git checkout tut02
just tutorial
```

```text
> Remember this word: pelican
Got it, I'll remember: pelican.
context: 3 messages
> Which word did I ask you to remember? Answer with the word only.
pelican
context: 5 messages
> /new
new conversation
context: 1 messages
> Which word did I ask you to remember? Answer with the word only.
You haven't asked me to remember a word.
context: 3 messages
```

### Under the hood

The reply arrives as typed blocks (tutorial 1). The text helper joins only the text
blocks, so the list holds answers, not reasoning.

### Key takeaways

- The message list is the memory: your harness keeps it and resends all of it every turn.
- The system prompt sits first and shapes every answer; rules set there land every turn.
- One adapter hides the vendor, so the chat code never sees a header or a URL.

### What is still missing

The list lives in one Python variable and dies with the process, so a restart wipes the
memory. The answer also arrives all at once, and there is still no terminal to talk in.
Tutorial 3 gives the list a keeper, streams each answer as it arrives, and adds the
terminal.
