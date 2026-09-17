# Chapter 1 — One raw call: what actually goes over the wire

No framework in this chapter — just one plain HTTP call (a single request and
response over the web) to the model, so you can see the exact bytes our
harness is built on. The whole script is `scripts/raw_call.py`, run it with:

```bash
just ch01
```

Expected output — a single word:

```text
pong
```

## Walking through `scripts/raw_call.py`

`load_settings()` reads your key and endpoint from `.env`, so the script
itself never contains a secret. Next it builds a fresh session id:

```python
session_id = f"harness-raw-{uuid.uuid4()}"
```

`uuid4()` makes a random unique identifier; the prefix marks where it came
from. Then comes the call itself — the URL, the headers, and the body in one place:

```python
resp = httpx.post(
    f"{s.base_url}/responses",
    headers={
        "Authorization": f"Bearer {s.api_key}",
        "x-opencode-session": session_id,
        "User-Agent": s.user_agent,
    },
    json={"model": s.model, "input": "Reply with exactly one word: pong"},
    timeout=60,
)
```

The URL is the base URL plus `/responses`. We use the Responses API
(Application Programming Interface, the web protocol the model speaks) and
not the older `chat/completions` endpoint because this is a per-model rule:
GPT and Muse-Spark models live behind `/responses`, while DeepSeek, GLM and
Kimi use `/chat/completions` and Qwen and MiniMax use `/messages`. Our
default model is `muse-spark-1.3-contributor`, so `/responses` it is
(see `docs/NOTES.md` for the verified mapping).

The headers carry the two mandatory credentials plus an identifier.
`Authorization: Bearer …` proves who we are — bare requests without it are
rejected. `x-opencode-session` is the second mandatory header: OpenCode uses
it for routing and prompt caching (reusing work from earlier calls), so one
conversation must keep one stable id. The `User-Agent` names our client,
because OpenCode rejects generic library defaults.

The request body is deliberately tiny — a model name and one input string.
No tools, no history, no options. The answer is shaped differently from the
older API: text does not sit at the top level but nested inside output items:

```python
# Responses API: output is a list of items; text lives in output[i].content[j].text
texts = [
    part["text"]
    for item in data.get("output", [])
    for part in item.get("content", [])
    if part.get("type") == "output_text"
]
```

We collect every `output_text` part and print them joined — which gives
`pong`. Anything else (an empty answer) falls back to printing the raw data.

## The limitation this leaves us with

This chapter proves the transport works, but the model here can only turn
text into text: it remembers nothing between calls, it cannot act on the
world, and this request shape is vendor-specific — switch providers and every
line changes. Chapter 2 fixes the last problem first by hiding this call
behind a uniform model interface.
