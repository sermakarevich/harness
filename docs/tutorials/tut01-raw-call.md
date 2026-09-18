# Tutorial 1 — One raw model call

After this tutorial you have talked to the model twice and know why it forgot the first
call by the second.

## In short

### The concepts

- A model call is plain HTTP. You send one request with a model name and a prompt, and you
get one reply back. Everything else around that exchange is the harness.
  - opencode sends even the simplest call through one shared streaming service.
  - pi keeps a one-shot streamed call with no tool loop, used on its own only for summaries.
  - hermes-agent runs stateless one-off calls through `run_oneshot`, outside session history.
- The key travels in a header. Your harness owns the key and adds it to every request, so
the model never sees it.
- The request is stateless. Nothing is kept between calls, not even under the same session id.
Whatever the model must know has to travel inside the request. An LLM (large language model)
is stateless: "LLMs are stateless. Every call replays the entire conversation history. The
harness fakes memory." (knowledge base: AGENTIC_ENGINEERING_PATTERS). Treat the model as a
stateless compute unit and keep all state across turns outside it (knowledge base:
HarnessEngineering).

### Scope

1. You send a request with `httpx` and the three headers the server requires.
2. You read the typed blocks in the reply.
3. You send a second request and watch the model forget.

You keep no memory anywhere yet. Tutorial 2 adds it.

### The problem

```text
$ uv run python -m harness
.venv/bin/python3: No module named harness.__main__; 'harness' is a package and cannot be directly executed
```

There is no entry point yet, so you cannot talk to the model at all.

### What changes

```text
src/harness/
+   model/client.py     sends one prompt, returns the reply
+   model/text.py       reads blocks and plain text from a reply
+   __main__.py         sends two prompts and prints both replies
tests/
+   test_model.py       offline tests for headers, ids, and reply reading
~   settings.toml       timeout default
~   justfile            tutorial recipe runs the harness
```

## In detail

### How it works

You start the run and the harness makes one stable session id for the conversation. For each
of the two prompts it sends one request with the model name, the prompt text, and three headers:
the key, the session id, and a named user agent. The reply is a list of typed blocks, first
`reasoning`, then a `message` holding `output_text` parts. The harness prints the prompt, the
joined plain text, and the block kinds it saw. The second request carries only the second prompt,
so the model cannot know the word from the first one; the session id only routes the call.

```text
you -> harness -> HTTP -> model -> blocks -> text
```

### Design decisions

- **The harness makes the session id, not the server.** One fresh id per run stays stable across
both calls, so you can trace the conversation without asking the server for anything.
- **Only `output_text` reaches you; reasoning stays inside.** You see the answer while the
harness keeps the full block list, so private model notes never leak onto your screen.
- **The timeout is a setting because a hung call would block your whole loop.** You can
raise or lower it from the environment without touching the code that sends the request.

### The excerpt that carries the idea

**src/harness/model/client.py**
```python
def ask(settings: Settings, session_id: str, prompt: str) -> dict:
    """Send one prompt to the model and return the parsed reply."""
    response = httpx.post(
        f"{settings.base_url}{RESPONSES_PATH}",
        headers=headers(settings, session_id),
        json={"model": settings.model, "input": prompt},
        timeout=settings.timeout_seconds,
    )
    response.raise_for_status()
    return response.json()
```

### Run it

```bash
git checkout tut01
just tutorial
```

```text
uv run python -m harness
> Remember this word: pelican
Got it! I'll remember the word: **pelican**.
blocks: reasoning, message
> Which word did I ask you to remember? Answer with the word only.
You haven't asked me to remember a word yet.
blocks: reasoning, message
```

The second answer is the point of the tutorial: the model agreed to remember, then proved it
keeps nothing between calls.

### Under the hood

A request without `x-opencode-session` is rejected with `MissingSessionID`, and a generic
`User-Agent` is rejected too. Both are server rules your harness already satisfies in code.

### Key takeaways

- A model call is plain HTTP: one request, one reply, with your key travelling in a header.
- The request is stateless: nothing is kept between calls, so everything you want the model to
know has to travel inside the request.
- The reply is a list of typed blocks, and the harness decides which blocks you see.

### What is still missing

The model forgets everything after each call, so you cannot hold a conversation yet.
Tutorial 2 stacks messages into a list that is the memory and asks the same two questions again.
