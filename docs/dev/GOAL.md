# GOAL — Tutorial: Build an Agent Harness Step by Step

**Status:** planning · **Created:** 2026-09-16 · **Owner:** Sergii

---

## 1. What we are building

A **hands-on tutorial** that builds an *agent harness* from scratch, one small step at
a time, in Python with **LangGraph**.

> **Harness** = everything around the model that is not the model itself: the loop that
> calls it, the tools it can use, the files it can read and write, the memory it keeps,
> the rules that stop it from doing something dangerous, and the budget that stops it
> from burning money. The common shorthand is `agent = model + harness`.
>
> **LangGraph** = a Python library from the LangChain project for describing an agent as
> a graph of steps (nodes) with explicit state passed between them, instead of one big
> `while` loop. It gives us persistence, pausing for human approval, and streaming
> for free.

Each tutorial must end with **runnable code** that does something visible, and a short
explanation of *which model limitation* that tutorial's code patches. The tutorial is the
deliverable; the harness it produces is the worked example.

Audience: a Python engineer who has called an LLM API before but has never built an agent
loop. Plain language, every abbreviation spelled out on first use.

---

## 2. Hard constraints

| Constraint | Decision |
|---|---|
| Language | **Python** only (3.12+) |
| Package / env manager | **uv** — `uv init`, `uv add`, `uv run`, lockfile committed |
| Task runner | **justfile** — every tutorial runnable as `just tutNN`, plus `just fmt`, `just lint`, `just test` |
| Agent framework | **LangGraph** (+ `langchain-core`; `langchain-openai` only as a transport adapter) |
| Model access | **OpenCode Go subscription key** — pure LLM calls, no vendor agent loop |
| Secrets | Key is read from `~/.local/share/opencode/auth.json` at runtime. Never committed, never printed, never pasted into chat. |

**No hidden magic rule:** if a tutorial can be written with ~30 lines of our own code
instead of importing a prebuilt abstraction, we write the 30 lines first and *then* show
the library version. The point of the tutorial is to see the machinery.

---

## 3. Model transport (already verified)

Full details in [`docs/dev/NOTES.md`](NOTES.md) — verified live on 2026-09-12 against
`muse-spark-1.3-contributor`.

- Base URL: `https://opencode.ai/zen/go/v1`, endpoint `/responses` (OpenAI Responses API).
- Required headers: `Authorization: Bearer $KEY`, `x-opencode-session: <stable-id>`,
  and a real user-agent string. Bare curl without a session header is rejected
  (`MissingSessionID`).
- Key and endpoint must be paired: the **Go** key works only against the **Go** endpoint;
  the **Zen** key only against `https://opencode.ai/zen/v1`.
- Protocol is per model: GPT / Muse-Spark → `/responses`, DeepSeek / GLM / Kimi →
  `/chat/completions`, Qwen / MiniMax → `/messages` (Anthropic protocol).

**Open spike (tutorial 1–2 risk):** LangGraph expects a LangChain chat-model object. We
need to confirm that `ChatOpenAI(base_url=..., default_headers={...})` with the Responses
API can carry the mandatory `x-opencode-session` header and stream correctly — and if it
cannot, write a thin custom `BaseChatModel` over `httpx` instead. This is the first thing
to test, because everything else sits on it.

---

## 4. Tutorial outline (each tutorial = one model limitation patched)

| # | Tutorial | Limitation it fixes |
|---|---|---|
| 0 | Project setup: `uv`, `justfile`, layout, config, secret loading | — |
| 1 | One pure LLM call, no framework, raw `httpx` | baseline: model only reads and writes text |
| 2 | Wrap the OpenCode Go endpoint as a LangChain chat model | framework needs a uniform model interface |
| 3 | Minimal ReAct loop as a LangGraph graph (reason → act → observe) | model cannot act on the world |
| 4 | Tools: filesystem read/write, then `bash` as the general-purpose tool | fixed toolsets limit what the agent can do |
| 5 | Sandbox + self-verification (run tests, read logs, fix) | model cannot check its own work |
| 6 | State and persistence: checkpointer, session id ↔ conversation | no memory across turns or restarts |
| 7 | Context management: compaction + tool-output offloading to disk | context rot as the window fills |
| 8 | Skills with progressive disclosure | loading every tool up front poisons context |
| 9 | Policy gate + human-in-the-loop approval (LangGraph `interrupt`) | model will happily run `rm -rf` |
| 10 | Budget and cost tracking, call limits, prompt caching | runaway spend |
| 11 | Subagents and delegation with clean context windows | complex subtasks pollute the main context |
| 12 | Long-horizon: plan files, continuation loop, test-grounded completion | agent quits early on multi-window work |
| 13 | Observability: structured events + traces | you cannot fix what you cannot see |
| 14 | Evaluation: a small task set, and locating failures as model-vs-harness | "it feels better" is not evidence |
| 15 | Self-improving harness — and why "it changed itself" ≠ "it got better" | measurement trap in self-evolution |

Tutorials 0–6 are the **minimum viable harness**. Tutorials 7–15 are the parts teams add
once an agent runs longer than a few minutes; each is optional and independently
skippable, which is itself a lesson (*task–harness fit*: over-fitting bloats, under-fitting
breaks).

---

## 5. Source material

Knowledge base: `../ai_knowledge_wiki/knowledge_base/agent_harness/` (~60 entries).
Primary references, mapped to where they are used:

**Backbone — what a harness is and what it must do**
- `TheAnatomyOfAnAgentHarness/` — the spine of the whole tutorial: derives each harness
  component from a model limitation; filesystem as the foundational primitive, bash as
  the general tool, sandboxes, memory, three defenses against context rot, long-horizon
  loops. Use for tutorials 3–12.
- `BuildYourOwnAgentHarness/` — the "15 jobs every harness must do" table; drives the
  tutorial list and the composability argument. Tutorials 0, 9–11.
- `LangChainCustomHarness/` — `create_agent` + middleware, the four customization levers,
  task–harness fit. Direct LangGraph framing. Tutorials 2–3, 7–11.
- `AmuxHarnessGuide/`, `HarnessEngineering/`, `HarnessEngineeringCourse/` — broader
  guides, use for cross-checking terminology and filling gaps.

**Component-specific**
- `ExternalizationInLLMAgents/` — memory, skills, protocols as one framework. Ch. 6–8.
- `ToolAttentionIsAllYouNeed/` — dynamic tool gating and lazy schema loading. Ch. 8.
- `BitterLessonOfToolCalling/` — how much tool structure to hand-build vs. leave to the
  model. Ch. 4, and a recurring caveat throughout.
- `CodeAsAgentHarness/`, `NOOAObjectOrientedAgents/` — code as the control surface. Ch. 4.
- `BuildingLongRunningAgenticAISystems/`, `UltraLongHorizonAgenticScience/` — long-horizon
  state and accumulation. Ch. 12.
- `TheHarnessEffect/` — orchestration design drives token economics. Ch. 10.
- `Kernel/` — sandbox/browser infrastructure. Ch. 5.

**Evaluation and honesty about results**
- `ModelOrHarnessFailureTaxonomy/` — is this failure the model's or ours? Ch. 14.
- `ScalingLawsAgentHarnesses/`, `ScalingTheHarnessInAgenticAI/` — what actually improves
  with more harness. Ch. 14.
- `HarnessUpdatingIsNotHarnessBenefit/` — self-evolving agents change themselves without
  getting better; the core caution for ch. 15.
- `SelfHarness/`, `AgenticHarnessEngineering/`, `MetaHarness/`, `AutoHarness.md`,
  `HarnessX/`, `PrimeAgentSelfImprovingHarness/` — self-improvement approaches. Ch. 15.

**Context / optional**
- `SmallLanguageModelsAreTheFutureOfAgenticAi/`, `APracticalGuideToBuildingAgents/`,
  `AgenticAIOnMacWithMLX/`, `SemaClaw/`, `NemoClawLocalAgent/`.

---

## 6. Repository layout (target)

```
harness/
├── GOAL.md            # this file (moved to docs/)
├── justfile           # just tut01, just fmt, just lint, just test
├── pyproject.toml     # uv-managed
├── uv.lock
├── docs/
│   ├── NOTES.md       # verified transport notes
│   └── tutorials/      # tutorial prose, one file per tutorial
├── src/harness/       # the harness package, grown tutorial by tutorial
└── tests/
```

Each tutorial adds code rather than rewriting it, so the final `src/harness/` is the
accumulated result of every step and the git history *is* the tutorial.

---

## 7. Definition of done

1. `just setup && just tut01` works on a clean machine with only `uv` and an OpenCode Go key.
2. Every tutorial runs standalone and prints something a reader can see and believe.
3. Tutorial 14 produces a real number on a real task set — before/after harness changes.
4. No secret ever appears in the repository, in the logs, or in tutorial output.
5. Prose is readable by a Python engineer who has never built an agent.

---

## 8. Open questions

- **Transport:** does `langchain-openai` carry the mandatory `x-opencode-session` header
  and stream from `/responses`, or do we write our own `BaseChatModel`? *(blocking ch. 2)*
- **Model choice:** which OpenCode Go model is the default for the tutorial? Tool-calling
  quality matters from ch. 3 onward and varies a lot per model.
- **Tool calling:** does the Go endpoint support native tool/function calling, or do we
  need a prompt-level fallback? This decides how tutorial 3 is written.
- **Sandbox:** local subprocess with an allowlist, Docker, or a hosted sandbox for ch. 5?
- **Rate limits / quota:** what does the subscription actually allow, and do we need
  caching in the tutorial so readers do not burn their quota re-running tutorials?
