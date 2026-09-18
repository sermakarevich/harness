# Chapter 2 — The LangChain adapter: one interface for any model

Chapter 1 talks to exactly one vendor in exactly one dialect. LangGraph (the
Python library we use to describe the agent as a graph of steps) does not
speak vendor dialects at all — it only accepts a LangChain `BaseChatModel`
(the common base class every LangChain-compatible model object inherits
from). So this chapter wraps the raw HTTP call in that uniform shape. All of
it lives in `src/harness/model/client.py` (`make_model`) and
`src/harness/model/text.py` (`text_of`); check it live with:

```bash
just smoke
```

Expected output (verified against the live endpoint, see `docs/NOTES.md`):

```text
invoke  : pong
stream  : 1 2 3 4 5
OK
```

## `make_model`: the single place that knows about OpenCode

```python
def make_model(settings: Settings, session_id: str) -> BaseChatModel:
    """Build a chat model tied to one conversation.

    The session id travels with each request so replies stay in the same
    conversation.
    """
    return ChatOpenAI(
        model=settings.model,
        api_key=settings.api_key,
        base_url=settings.base_url,
        use_responses_api=True,
        default_headers={
            "x-opencode-session": session_id,
            "User-Agent": settings.user_agent,
        },
    )
```

`make_model` builds a `ChatOpenAI` object pointed at the OpenCode Go base
URL. The session id is an argument — not a constant — because OpenCode maps
one header value to one conversation for routing and prompt caching (reusing
work from earlier calls), so every conversation needs its own id and its own
model object. Everything vendor-specific (the Responses API flag, the two
mandatory headers) lives inside this one function, which means swapping
providers later touches only this file.

## `text_of`: protection against two content shapes

```python
def text_of(message: BaseMessage) -> str:
    """Return the plain text of a message.

    Some replies arrive in pieces, so we join the text pieces together.
    """
    content = message.content
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") in ("text", "output_text"):
            parts.append(block.get("text", ""))
    return "".join(parts)
```

A plain chat model returns `content` as a simple string. Ours does not: the
Responses API returns a list of typed blocks (reasoning and `output_text`
dictionaries), as the transport spike in `docs/NOTES.md` discovered. `text_of`
joins the `text` and `output_text` blocks into one string, so the rest of the
harness never cares which shape arrived.

## The transport spike outcome

From the "LangChain adapter" section of `docs/NOTES.md`: the primary path
worked on the first try — plain `ChatOpenAI` with `use_responses_api=True`
and the session id plus user agent in `default_headers`. No custom fallback
class was needed. `just ch01` printed `pong`; `just smoke` printed the three
lines above. The key never appears in output or error text.

## Limitation fixed

Chapter 1 left us with a vendor-specific call; that is gone. Any code that
accepts a `BaseChatModel` can now drive our model without knowing OpenCode
exists — and LangGraph only ever accepts a `BaseChatModel`. What is still
missing is everything around the model: memory, tools, and the loop itself.
Chapter 3 builds the loop.
