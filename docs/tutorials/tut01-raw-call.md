# Tutorial 1 — One raw model call

After this tutorial you have talked to the model once and know what a call is.

## In short

### The concepts

- A model call is plain HTTP: one request, one reply. The secret key travels in
  a header, so the harness owns the key and the model never sees it.
- The request is stateless: nothing is kept between calls, so whatever the model
  must know travels inside the request. "LLMs (large language models) are
  stateless. Every call replays the entire conversation history. The harness
  fakes memory." (knowledge base: AGENTIC_ENGINEERING_PATTERS). Treat the model
  as a stateless compute unit and keep all state across turns outside it
  (knowledge base: HarnessEngineering).
- The reply is a list of typed blocks: `reasoning` first, then a `message` with
  `output_text` parts. The harness decides which blocks you see.

How the three harnesses in `docs/harnesses/OPERATIONS.md` make this call:

- opencode routes every call through one service, so you get events back, not a string.
- pi keeps a one-shot streamed call with no tool loop, used on its own only for summaries.
- hermes-agent runs stateless calls through `run_oneshot`: a fresh list, no history kept.

### Scope

You do three things in this tutorial:

1. You send one request with `httpx`.
2. You read the typed blocks in the reply.
3. You add the three headers the server requires:
   - the key, so the server knows it is you calling
   - the session id, for routing and cached work
   - the user agent, naming your harness

Left out on purpose: any memory of earlier calls. Tutorial 2 adds it.

### The problem

Before this tutorial there is no script, so you get a missing file, not a reply:

```text
$ uv run python scripts/raw_call.py
.venv/bin/python3: can't open file 'scripts/raw_call.py': [Errno 2] No such file or
directory
```

### What changes

```text
+ scripts/raw_call.py          one request, blocks, print
+ tests/test_raw_call.py       block reading without the network
~ src/harness/settings.toml    timeout default
~ justfile                     run the script
```

## In detail

### How it works

You run the script and it loads your settings from the environment. It builds one
request, which carries:

- the model name and the input string
- the key header, so the server knows it is you calling
- the session id header, made fresh for this call
- the user agent header, naming your harness

The server answers with a list of blocks, and you print their kinds plus the joined text:

```text
you -> harness -> HTTP -> model -> blocks -> text
```

The printout shows the block kinds first and `pong` next. Nothing is saved: the session
id is fresh on every run, so a follow-up call starts blank.

### Design decisions

- **The harness makes the session id, not the server.** You get one stable id per
  conversation, which the server uses for routing and prompt caching.
- **Only `output_text` reaches you; reasoning stays inside.** The reasoning blocks are the
  model's scratch work, not its answer, so the harness reads them and shows you the text.
- **The timeout is a setting, not a fixed value.** A hung call would freeze the whole
  harness, so the limit is yours to change in `.env`, not in code.

### The excerpt that carries the idea

**scripts/raw_call.py** joins only the text parts you show and skips the rest:

```python
def text_of(response: dict) -> str:
    """Join every text piece of the reply into one answer."""
    return "".join(
        part["text"]
        for item in response.get("output", [])
        for part in item.get("content", [])
        if part.get("type") == PART_OUTPUT_TEXT
    )
```

### Run it

```bash
git checkout tut01
just tutorial
```

```text
blocks: reasoning, message
pong
```

### Under the hood

The server rejects a request without `x-opencode-session` with `MissingSessionID`, so
you always send a fresh id. It also rejects a generic `User-Agent`, so you send your
harness name instead.

### Key takeaways

- A model call is one plain HTTP request and one reply; everything else is the harness.
- The key and the session id travel in headers the harness sets; the model never sees the key.
- Every request is stateless: you resend what the model must know, and you pick the blocks.

### What is still missing

The model forgets everything the moment your call ends. Ask a follow-up and you get a
blank stare: nothing carries over. Tutorial 2 stacks your messages into a list that is
the memory.
