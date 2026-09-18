# Harness project — notes

## Pure LLM call via OpenCode Go (verified 2026-09-12)

Raw model access with no agent loop, using the OpenCode Go subscription key.
Verified live against `muse-spark-1.3-contributor`.

### Endpoints

| Provider | Base URL | Example model | Protocol |
|---|---|---|---|
| OpenCode Go | `https://opencode.ai/zen/go/v1` | `muse-spark-1.3-contributor` → `/responses` | Responses API (`@ai-sdk/openai`) |
| OpenCode Zen | `https://opencode.ai/zen/v1` | `deepseek-v4-flash` → `/chat/completions` | OpenAI-compatible |

Model↔endpoint mapping is per-model, see https://opencode.ai/docs/go/ (Go)
and https://opencode.ai/docs/zen/ (Zen). Rule of thumb: GPT/Muse-Spark →
`/responses`, DeepSeek/GLM/Kimi → `/chat/completions`, Qwen/MiniMax →
`/messages` (Anthropic protocol).

### Mandatory headers (Go endpoint)

Bare curl is rejected with `MissingSessionID`. Required:

- `Authorization: Bearer $KEY` — key from `~/.local/share/opencode/auth.json`
  (`opencode-go` entry). Never commit it, never paste it into chat.
- `x-opencode-session: <stable-id>` — one stable ID per conversation
  (routing + prompt caching).
- A real user agent (`-A "something/1.0"`), not a generic library default.

Key/endpoint pairing matters: Go key → Go endpoint only, Zen key → Zen
endpoint only. Cross-pairing returns `Invalid API key`.

### Exact call (copy-paste, key never displayed)

```bash
export KEY=$(python3 -c "import json; print(json.load(open('$HOME/.local/share/opencode/auth.json'))['opencode-go']['key'])")
curl https://opencode.ai/zen/go/v1/responses \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -H "x-opencode-session: <your-session-id>" \
  -A "harness-dev/1.0" \
  -d '{"model":"muse-spark-1.3-contributor","input":"hello"}'
```

Note: `export` and `curl` must run in the same shell.

### Why this matters for our harness

This is the raw transport our harness will wrap: session IDs map to
conversations, the Responses API is the completion surface, and token/cost
control lives here — not in the agent loop.

## LangChain adapter (verified 2026-09-17)

Primary path worked on the first try: plain `ChatOpenAI` with no fallback
class needed. Constructor: `ChatOpenAI(model=settings.model,
api_key=settings.api_key, base_url=settings.base_url,
use_responses_api=True, default_headers={"x-opencode-session":
session_id, "User-Agent": settings.user_agent})`. `just tut01` printed
`pong`; `just smoke` printed `invoke  : pong`, `stream  : 1 2 3 4 5`, `OK`.
Content shape: `invoke` returns `AIMessage.content` as a **list of typed
blocks** (reasoning + output_text dicts), not a plain string — hence the
`text_of()` helper that joins `text`/`output_text` blocks. No errors hit
(key never appears in output or error text).
