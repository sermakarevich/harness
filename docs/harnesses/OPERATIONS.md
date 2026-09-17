# Harness operations — what a harness actually does

> A harness is everything around the model that is not the model. This document lists the operations a harness performs, easiest first, and shows how three real harnesses implement each one.

## How to read this

Difficulty runs from Tier 1 (a few lines of code, no saved state) through Tier 2 (needs a loop or a data structure kept in memory), Tier 3 (needs saved data on disk, an outside process, or a fixed data contract), and Tier 4 (needs a policy decision, work happening at the same time, or a second model call to work), up to Tier 5 (changes the shape of the whole system and is hard to add later). opencode is a terminal coding agent written in TypeScript and built by SST. pi is a minimal, extension-driven terminal coding agent written in TypeScript and shipped as compiled JavaScript, built by Earendil Works. hermes-agent is a personal coding and operations agent from Nous Research that runs one shared core across a terminal program, messaging gateways, and desktop apps. MCP stands for Model Context Protocol, a standard for connecting outside tool servers at runtime.

## The operations at a glance

| # | Operation | Tier | opencode | pi | hermes |
|---|---|---|---|---|---|
| 1 | Pure LLM call | 1 | single streaming entry point | one-shot streamed summary call | stateless oneshot plus dispatcher |
| 2 | Streaming | 1 | typed event stream consumer | token deltas as events | single-writer fan-out delivery |
| 3 | Conversation state | 2 | database-backed message parts | branchable session message tree | staged turn context sidecar |
| 4 | System prompt assembly | 2 | per-turn template plus environment | rendered tools plus guidelines prompt | once-per-session cached prompt |
| 5 | Provider & model abstraction | 3 | catalog with per-model normalization | merged catalog four protocols | global plus scoped registries |
| 6 | Reliability | 4 | stream-level retry with backoff | turn retries idle timeout fallback | classified errors jittered failover |
| 7 | Tool definitions | 2 | declarative schemas auto-converted | seven schemas plus extension registration | self-registering files per toolset |
| 8 | Agent loop | 2 | turn loop over streaming steps | prompt turn loop with hooks | bounded model-then-tools loop |
| 9 | Parallel tool calls | 4 | concurrent dispatch by identifier | ordered preflight concurrent execution | batch planner thread pool |
| 10 | File tools | 2 | scoped read write edit search | paged reads queued mutations | guarded tools terminal-backed filesystem |
| 11 | Shell execution | 2 | parsed spawn tail-kept output | streamed spawn tree kill | multi-backend guarded redacted runner |
| 12 | Permission / approval gate | 4 | ordered rules interactive replies | extension veto via events | layered floors model judge human |
| 13 | Session persistence | 3 | sessions messages parts tables | versioned branchable message tree | append-only message flush |
| 14 | Snapshot & revert | 5 | hidden repository commit restore | — | shadow store per-turn snapshots |
| 15 | Token accounting & cost | 3 | per-turn usage exact pricing | per-message usage cost records | background writer session totals |
| 16 | Context overflow & compaction | 4 | budget check summarize prune | cut-point summarize reload tail | prune-then-summarize multi-pass compressor |
| 17 | Tool output offloading | 3 | spill-to-disk preview plus hints | tail-truncate spill full file | three-layer cap spill budget |
| 18 | Memory files | 3 | global project instructions injected | walk-up files injected verbatim | frozen start snapshot capped recall |
| 19 | Skills / progressive disclosure | 3 | names listed body on demand | name description prompt file read | name-only list view loads |
| 20 | Sub-agents / delegation | 5 | child sessions depth-limited tool | — | fresh children summary only |
| 21 | Planning & todo tracking | 4 | session todos plan agents | — | in-memory todos prompt plans |
| 22 | MCP / dynamic external tools | 4 | namespaced adapted external tools | — | background loop vendored servers |
| 23 | Hooks, plugins & events | 5 | global bus sequential hooks | extension bus veto patch | payload shell stream observers |
| 24 | Background & concurrency | 5 | session jobs serialized runs | queued steering session swapping | tracked processes timer batch |

## Operations in detail

### 1. Pure LLM call

**Tier 1.** One request with no tools and no loop is just a function call with no state to manage.

**What it is.** A Large Language Model (LLM, the artificial intelligence model that generates text) receives a list of messages and returns one text answer. There is no memory between calls and no tools for the model to use. This is the building block every other operation wraps.

**How the three do it.**

- **opencode:** every model call flows through one streaming service in `packages/opencode/src/session/llm.ts`, prepared by `packages/opencode/src/session/llm/request.ts`, so even the simplest call returns a stream of events rather than a single string.
- **pi:** the primitive is a one-shot streamed call with no tool loop attached, wired in as `agent.streamFn` in `dist/core/agent-session.js` and used on its own only for summaries in `dist/core/compaction/compaction.js`.
- **hermes-agent:** stateless calls go through `run_oneshot` in `agent/oneshot.py`, which builds a fresh message list and never touches session history, while the conversational non-streaming path dispatches on a worker thread in `agent/chat_completion_nonstream.py`.

**Where they agree / differ.** All three funnel model calls through one shared entry point, but opencode and pi only expose streaming entry points while hermes-agent keeps a separate plain non-streaming path for one-off calls.

**In LangGraph / Python**

A single node that calls the model and writes the reply into message state is the whole operation. LangGraph gives you the graph wiring and the message list handling for free through `MessagesState`; the actual model call is one line of ordinary LangChain code inside your node function.

```python
from langgraph.graph import StateGraph, START, END, MessagesState

class MyState(MessagesState):
    pass

model = get_model()

def call_model(state: MyState):
    return {"messages": [model.invoke(state["messages"])]}

builder = StateGraph(MyState)
builder.add_node("call_model", call_model)
builder.add_edge(START, "call_model")
builder.add_edge("call_model", END)
graph = builder.compile()
```

*Effort:* built in

### 2. Streaming

**Tier 1.** Forwarding tokens as they arrive is a thin display pipe with no saved state.

**What it is.** Instead of waiting for the full answer, the harness shows or forwards each piece of text the moment it arrives. The screen fills in word by word while the answer is still being generated. Underneath, the harness still collects the pieces into one final message.

**How the three do it.**

- **opencode:** both model runtimes are converted into one typed event stream in `packages/opencode/src/session/llm/ai-sdk.ts` and `packages/opencode/src/session/llm/native-runtime.ts`, consumed piece by piece by `packages/opencode/src/session/processor.ts`, which writes incremental updates as tokens arrive.
- **pi:** arriving tokens update the in-progress message and are re-emitted as `message_update` events carrying text pieces from `dist/core/agent-session.js`, with shell output throttled to one display update per 100 milliseconds, purely as a display feed.
- **hermes-agent:** output flows through a single-writer fence in `agent/stream_single_writer.py` so only one owner writes text fragments, fanned out to display callbacks by `agent/stream_delivery.py`, with a watchdog in `agent/chat_completion_stream_monitor.py` that kills streams silent past the timeout.

**Where they agree / differ.** All three treat streaming as an observation layer over one canonical stream, and all three converge on it: one stream, many watchers, never two writers.

**In LangGraph / Python**

You change nothing in the graph: you consume the same invocation with `graph.stream` and a stream mode instead of `graph.invoke`. Token-by-token delivery is built in, so the only code you write yourself is the small display loop that prints each piece as it arrives.

```python
config = {"configurable": {"thread_id": "abc"}}
for chunk, metadata in graph.stream(
    {"messages": [{"role": "user", "content": "hi"}]},
    config,
    stream_mode="messages",
):
    print(chunk.content, end="", flush=True)
```

*Effort:* built in

### 3. Conversation state

**Tier 2.** Keeping history across turns needs a list you hold in memory and rebuild before each call.

**What it is.** The harness remembers what was said earlier in the conversation and sends the whole history back to the model with each new turn. This is what makes the model appear to remember things. The harness must convert its stored records into the message shape the model provider expects.

**How the three do it.**

- **opencode:** history lives durably in a small local file database (SQLite, a database stored in a single file on disk) as messages plus smaller fragments called parts, read with page-based queries in `packages/opencode/src/session/message-v2.ts` and rebuilt fresh into model messages every turn.
- **pi:** history is a branchable session tree managed by `dist/core/session-manager.js`, where each entry points at a parent and the active path is walked from leaf to root, then converted for the provider by `convertToLlm()` in `dist/core/messages.js`.
- **hermes-agent:** each turn starts with `build_turn_context` in `agent/turn_context.py`, which copies stored history into a working list and stamps new messages via `agent/message_metadata.py`, keeping a parallel provider-ready copy alongside the stored message so the stored view stays clean.

**Where they agree / differ.** All three rebuild the model-facing message list from durable storage on every turn rather than keeping one cached list, and all three keep provider-specific quirks out of the stored records.

**In LangGraph / Python**

Conversation memory is a checkpointer attached at compile time plus a thread id passed with every call; LangGraph then loads history, merges new messages, and saves again automatically. You write no storage code at all for the common case, and you reach for an explicit database checkpointer only when memory must survive restarts.

```python
from langgraph.checkpoint.memory import InMemorySaver

builder = StateGraph(MyState)
builder.add_node("call_model", call_model)
builder.add_edge(START, "call_model")
builder.add_edge("call_model", END)
graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "abc"}}
graph.invoke({"messages": [{"role": "user", "content": "hi"}]}, config)
```

*Effort:* built in

### 4. System prompt assembly

**Tier 2.** Building the opening instruction block each turn is string assembly over data you already hold.

**What it is.** Every conversation starts with a system prompt: background instructions that tell the model who it is, what tools it has, what directory it works in, and what day it is. The harness rebuilds this block regularly from static text plus live context. Getting this assembly right shapes everything the model does.

**How the three do it.**

- **opencode:** the prompt is assembled fresh every turn in `packages/opencode/src/session/system.ts`, picking a per-model template from `packages/opencode/src/session/prompt/default.txt` and combining it with environment facts, instruction files, and the skill listing.
- **pi:** one function `buildSystemPrompt()` in `dist/core/system-prompt.js` renders the available-tools list plus a deduplicated guidelines section whose bullets adapt to the active tools, with project files appended inside marked blocks and the date and working directory always last.
- **hermes-agent:** the prompt is built once per session by `agent/system_prompt.py` with helpers in `agent/prompt_builder.py` in three tiers (stable identity, workspace context, volatile skills and memory) and then frozen so the provider reuses its cached computation every turn.

**Where they agree / differ.** opencode and pi rebuild the prompt every turn for freshness while hermes-agent freezes it per session for cache savings; that freshness-versus-cache-cost trade is the central design split.

**In LangGraph / Python**

LangGraph gives you nothing here: assembling the opening instruction block is ordinary Python string building that runs before the model call. You write a small helper returning a `SystemMessage` and prepend its result to the history inside your `call_model` node.

```python
from langchain_core.messages import SystemMessage

def build_system_prompt(date: str, cwd: str) -> SystemMessage:
    text = f"You are a coding agent. Date: {date}. Cwd: {cwd}."
    return SystemMessage(content=text)

def call_model(state: MyState):
    first = build_system_prompt("2026-09-16", "/repo")
    return {"messages": [model.invoke([first] + state["messages"])]}
```

*Effort:* a few lines

### 5. Provider & model abstraction

**Tier 3.** Supporting many models behind one interface needs a stored catalog plus per-model translation rules.

**What it is.** Different model vendors have different web addresses, login methods, message shapes, and prices. The harness hides all of that behind one interface so the rest of the code just says which model it wants. A catalog records each model's abilities, size limits, and cost per million input and output tokens.

**How the three do it.**

- **opencode:** the catalog in `packages/opencode/src/provider/provider.ts` maps each vendor to its models with abilities, limits, and cost, while `packages/opencode/src/provider/transform.ts` reshapes messages and settings per model so new vendors mostly mean new catalog data.
- **pi:** `ModelRegistry` in `dist/core/model-registry.js` merges the built-in list with user files behind one model interface, supporting four wire protocols with compatibility flags, while `dist/core/model-resolver.js` parses `provider/id` references and resolves login credentials.
- **hermes-agent:** `ProviderRegistry` in `agent/provider_registry.py` keeps one global name-to-vendor map plus per-profile scoped maps, with declarative vendor records in `agent/provider_base.py` and model-name translation in `agent/models_dev.py` backed by a 4-hour cache.

**Where they agree / differ.** All three converged on the same shape: a registry mapping names to vendor records plus a translation layer per model, with user overrides winning over bundled entries.

**In LangGraph / Python**

LangGraph gives you nothing here either: the catalog of vendors, model names, limits, and prices is an ordinary Python dictionary plus a small factory function you write by hand. Every sketch in this document reaches the model through that factory, written once as `get_model()`, so swapping vendors never touches graph code.

```python
CATALOG = {"assistant": {"base_url": "https://llm.example/v1"}}

def get_model(name="assistant"):
    conf = CATALOG[name]
    return ChatModel(base_url=conf["base_url"])  # ordinary Python class you write

model = get_model("assistant")
```

*Effort:* a day's work

### 6. Reliability

**Tier 4.** Retries with waiting, error sorting, and fallback models are policy decisions, not just loops.

**What it is.** Model calls fail: rate limits, overloaded servers, broken networks, expired logins. The harness sorts each failure into a kind, waits longer after each repeated failure, tries again a bounded number of times, and may switch to a backup model. Without this, one hiccup kills the whole session.

**How the three do it.**

- **opencode:** the whole stream is wrapped in a retry policy from `packages/opencode/src/session/retry.ts` applied in `packages/opencode/src/session/processor.ts`, retrying server and rate-limit errors with exponential waiting up to 5 attempts while error sorting lives in `packages/opencode/src/provider/error.ts`.
- **pi:** turn-level retry is configured through settings and applied in `dist/core/agent-session.js` with 3 attempts and exponential waiting from a 2-second base, a 300-second network idle timeout via `dist/core/http-dispatcher.js`, and a fallback model pick in `dist/core/model-resolver.js` when a saved model no longer exists.
- **hermes-agent:** failures are classified once into recovery hints in `agent/error_classifier.py`, waits come from randomized exponential waiting in `agent/retry_utils.py`, and the primary model cools down after rate-limit or billing errors via `agent/fallback_cooldown.py`.

**Where they agree / differ.** All three retry above the raw network client rather than inside it, and all three sort errors first and retry second; they differ on fallback, with pi and hermes-agent switching models and opencode only rerouting summaries to a cheaper model.

**In LangGraph / Python**

LangGraph hands you the retry machinery for free: a `RetryPolicy` on the node re-runs failed steps with backoff, while `with_retry` and `with_fallbacks` harden the model object itself. What you still write by hand is the policy around it — which errors deserve a retry, how long to wait, and when to switch to the backup model.

```python
from langgraph.types import RetryPolicy

primary = model.with_retry(stop_after_attempt=3)
resilient = primary.with_fallbacks([get_model("backup")])

def call_model(state: MyState):
    return {"messages": [resilient.invoke(state["messages"])]}

builder = StateGraph(MyState)
builder.add_node("call_model", call_model,
                 retry_policy=RetryPolicy(max_attempts=3))
builder.add_edge(START, "call_model")
builder.add_edge("call_model", END)
```

*Effort:* a few lines

### 7. Tool definitions

**Tier 2.** Declaring what tools exist is a data structure: name, description, and parameter shape per tool.

**What it is.** Tools are the actions the model may request, such as reading a file or running a command. Each tool is declared with a name, a plain-language description, and a parameter schema written in JavaScript Object Notation (JSON, a text format for structured data) that says which arguments it takes. The harness sends these declarations with every model call so the model knows what it can ask for.

**How the three do it.**

- **opencode:** tools are declared with a define call in `packages/opencode/src/tool/tool.ts` pairing a name with a schema structure, collected by `packages/opencode/src/tool/registry.ts`, and converted into model-facing functions with JSON schemas by `SessionTools.resolve` in `packages/opencode/src/session/tools.ts`.
- **pi:** seven built-in tools are assembled by `createCodingTools()` in `dist/core/tools/index.js` as schema objects wrapped by `wrapToolDefinition()` in `dist/core/tools/tool-definition-wrapper.js`, with custom tools added through extension registration calls managed with `dist/utils/tools-manager.js`.
- **hermes-agent:** every file under `tools/` self-registers at import time by calling `register()` in `tools/registry.py` with name, description, schema, handler, and group, and `get_tool_definitions()` in `model_tools.py` resolves the enabled groups into model-ready declarations on every call.

**Where they agree / differ.** All three keep a registry as the single source of truth for what the model may call, and all three let outside code add tools; hermes-agent's self-registering files are the most automatic variant of the same idea.

**In LangGraph / Python**

Declaring a tool is a decorated Python function whose docstring and type hints become the model's parameter schema, and LangGraph's `ToolNode` plus `bind_tools` do the rest for free. You hand-write each tool's schema and behavior; the registry is just the plain list you pass to both the model and the node.

```python
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

@tool
def read_file(path: str) -> str:
    """Read a file and return its text."""
    return open(path).read()[:8000]

tools = [read_file]
bound = model.bind_tools(tools)
node = ToolNode(tools)
```

*Effort:* a few lines

### 8. Agent loop

**Tier 2.** The loop itself is simple: call the model, run requested tools, append results, repeat until done.

**What it is.** One model call rarely finishes the job. The harness runs a loop: send messages to the model, and if the model requests tool actions, execute them, append their results to the history, and call the model again. The loop stops when the model answers with no further tool requests or hits a step limit.

**How the three do it.**

- **opencode:** the outer loop in `packages/opencode/src/session/prompt.ts` creates an assistant message, resolves tools, and calls `process()` in `packages/opencode/src/session/processor.ts`, which streams one model step and returns continue, stop, or compact before the next turn begins.
- **pi:** `AgentSession.prompt()` in `dist/core/agent-session.js` expands references, fires lifecycle events, then loops turns where each model response passes tool calls through before- and after-execution hooks until a turn ends with no calls.
- **hermes-agent:** `run_conversation()` in `agent/conversation_loop.py` alternates model calls with tool rounds from `agent/turn_tool_round.py`, which validates, caps, and dedupes requested calls, stores the tool-call message before executing anything, then appends results and returns a continue, break, or return verdict.

**Where they agree / differ.** All three loop at the turn level with explicit stop conditions and lifecycle markers around each turn; hermes-agent additionally stores the tool-call record before executing, so tools never run without a saved record.

**In LangGraph / Python**

The loop is graph structure, not a `while` statement you write: the model node routes to a `ToolNode` through the built-in `tools_condition` and tool results route back until no calls remain. LangGraph owns the repetition and the stop condition, which is why this document builds it explicitly with `StateGraph`; `create_react_agent` is the one-line shortcut for the same shape when you do not need to teach the machinery.

```python
from langgraph.prebuilt import ToolNode, tools_condition

builder = StateGraph(MyState)
builder.add_node("call_model", call_model)
builder.add_node("tools", ToolNode([read_file]))
builder.add_edge(START, "call_model")
builder.add_conditional_edges("call_model", tools_condition,
                              {"tools": "tools", END: END})
builder.add_edge("tools", "call_model")
graph = builder.compile(checkpointer=InMemorySaver())
```

*Effort:* built in

### 9. Parallel tool calls

**Tier 4.** Running several tool actions at once needs concurrency control plus order bookkeeping.

**What it is.** The model often requests several independent actions in one turn, such as reading three files. Running them at the same time is much faster than one after another. The harness must track each running call by an identifier, match each result to its request, and present results in a stable order so the model is never confused.

**How the three do it.**

- **opencode:** sibling calls from one step run concurrently through execution closures set up in `packages/opencode/src/session/llm.ts`, tracked per call identifier with deferred completion signals in `packages/opencode/src/session/processor.ts` and matched back by identifier on completion.
- **pi:** sibling calls are checked one at a time in source order, then executed at the same time with interleaved progress events, while completion events fire in finish order but result messages are re-emitted in the original source order per `dist/core/agent-session.js`, with same-file edits serialized by `dist/core/tools/file-mutation-queue.js`.
- **hermes-agent:** a planner in `agent/tool_dispatch_helpers.py` splits calls into ordered parallel and sequential segments (file writes to the same path become sequential barriers) and parallel segments run together in a daemon worker pool via `agent/tool_executor.py`.

**Where they agree / differ.** All three preserve the model's original call order in what the model sees even though execution finishes out of order, and all three serialize conflicting file writes; the planner that decides what may run together is explicit only in hermes-agent.

**In LangGraph / Python**

LangGraph gives you both halves: a plain `ToolNode` already executes sibling calls concurrently, and `Send` lets you fan out custom work to parallel worker nodes when one tool call is not enough. What you write by hand is the small splitter that turns one request into many, plus the ordering and conflict rules when two calls touch the same file.

```python
from langgraph.types import Send

def fan_out(state: MyState):
    items = state["items"]  # one entry per independent call
    return [Send("worker", {"item": x}) for x in items]

builder = StateGraph(MyState)
builder.add_node("worker", worker)
builder.add_conditional_edges("call_model", fan_out, ["worker"])
graph = builder.compile()
```

*Effort:* a few lines

### 10. File tools

**Tier 2.** Reading, writing, editing, and searching files is straightforward input-output with limits.

**What it is.** The agent needs hands for the workspace: read a file or directory, write a new file, change part of a file, find files by name pattern, and search file contents for text. Each tool validates its arguments, resolves paths safely, and caps how much text comes back so one giant file cannot flood the conversation.

**How the three do it.**

- **opencode:** each file tool pairs a parameter schema with an execution function in its own file under `packages/opencode/src/tool/` (`read.ts`, `write.ts`, `edit.ts`, `glob.ts`, `grep.ts`), resolving absolute paths, asking permission, and returning bounded output with diagnostics.
- **pi:** the `read` tool in `dist/core/tools/read.js` pages through large files by offset and limit, `write` in `dist/core/tools/write.js` replaces whole files, `edit` in `dist/core/tools/edit.js` applies targeted changes, and `grep`, `find`, and `ls` cover search and listing, with mutating tools serialized per file through `dist/core/tools/file-mutation-queue.js`.
- **hermes-agent:** the model-facing tools are declared in `tools/file_tools.py` with guards and pagination, real filesystem input-output lives in `tools/file_operations.py` behind one terminal-backed implementation serving local and remote backends, and path resolution in `tools/file_tools_paths.py` anchors every relative path at the task's live working directory.

**Where they agree / differ.** All three converged on the same tool family (paged read, whole write, targeted edit, name search, content search) with bounded reads and per-file write serialization; the shared trait is limits everywhere.

**In LangGraph / Python**

LangGraph contributes only the `ToolNode` that runs your functions; every file tool itself is ordinary Python you write by hand with path checks and output caps. The discipline that matters — page large reads, bound every return, serialize writes to the same path — lives entirely in your code, not in the framework.

```python
from pathlib import Path
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

@tool
def read_file(path: str, offset: int = 0, limit: int = 50) -> str:
    """Read one page of a file so big files cannot flood context."""
    lines = Path(path).read_text().splitlines()
    return "\n".join(lines[offset:offset + limit])

node = ToolNode([read_file])
```

*Effort:* a day's work

### 11. Shell execution

**Tier 2.** Spawning a command and capturing its output is one well-understood operating-system operation.

**What it is.** Many tasks need real commands: run tests, install packages, check version-control status. The harness starts a child process in a shell, captures its standard output and error streams, enforces a timeout, and reports the exit code. Long output must be trimmed so it fits in the conversation.

**How the three do it.**

- **opencode:** commands go through `packages/opencode/src/tool/shell.ts` with prompt help from `packages/opencode/src/tool/shell/prompt.ts`, parsing the command text, asking permission, spawning with a 2-minute default timeout, and keeping the tail of over-long output with a spill file via `packages/opencode/src/tool/truncate.ts`.
- **pi:** commands spawn through the configured shell with output streamed piece by piece into an accumulator in `dist/core/bash-executor.js`, created via `dist/core/tools/bash.js` with low-level spawning in `dist/core/exec.js`, killing the whole process tree on abort or timeout.
- **hermes-agent:** shell commands run through `terminal_tool()` in `tools/terminal_tool.py` across local, container, and remote backends with pre-execution guards in `tools/terminal_tool_guards.py`, heredoc-aware analysis in `tools/shell_heredoc.py`, and finishing (color-code stripping, secret redaction, truncation with spill file) in `tools/terminal_tool_result.py`.

**Where they agree / differ.** All three stream output live, kill the full process tree on timeout or abort, and spill over-long output to a file; opencode keeps the tail while generic truncation elsewhere keeps the head, and hermes-agent layers the most guards (directory, background-operator, and self-restart checks).

**In LangGraph / Python**

LangGraph gives you nothing here: running a command is an ordinary Python tool around `subprocess` with a timeout, an exit code, and trimmed output. You write the guards yourself — timeouts, output caps, and which commands are even allowed — and the `ToolNode` from the agent loop simply executes whatever your function returns.

```python
import subprocess
from langchain_core.tools import tool

@tool
def run(cmd: str) -> str:
    """Run a shell command with timeout; keep the tail of long output."""
    p = subprocess.run(cmd, shell=True, capture_output=True,
                       text=True, timeout=120)
    out = (p.stdout + p.stderr)[-4000:]
    return f"exit={p.returncode}\n{out}"
```

*Effort:* a day's work

### 12. Permission / approval gate

**Tier 4.** Deciding what is dangerous is a policy judgment that needs rules plus a human in the loop.

**What it is.** Some actions are risky: deleting files, running untrusted commands, sending data outside. Before such a call runs, the harness checks an ordered list of allow and deny rules, and if no rule matches it asks a human (or a policy) to approve once, approve always, or reject. The answer is recorded so repeats are handled consistently.

**How the three do it.**

- **opencode:** every tool asks through `Permission.ask()` in `packages/opencode/src/permission/index.ts`, evaluated against ordered allow and deny rules in `packages/opencode/src/permission/evaluate.ts` where the last match wins, blocking on a pending entry until a once, always, or reject reply arrives, with shell prefix logic in `packages/opencode/src/permission/arity.ts`.
- **pi:** there is deliberately no built-in popup; the gate is the tool-call extension event fired from `dist/core/agent-session.js`, where any handler can veto with a reason or rewrite arguments in place, so every approval policy is user-written extension code.
- **hermes-agent:** layered gates run before dispatch from `tools/approval.py`: unconditional blocks in `tools/approval_floors.py` fire first, a model judge in `tools/approval_smart.py` returns approve, deny, or escalate, then a human is asked via terminal, gateway, or plugin transport with human-only waiting time measured in `tools/approval_human_wait.py`.

**Where they agree / differ.** All three separate unconditional denies from ask-the-human cases, but the human step differs completely: built-in interactive replies in opencode, user-written extensions in pi, and a layered floor plus model judge plus human chain in hermes-agent.

**In LangGraph / Python**

The pause-and-resume machinery is built in: `interrupt` freezes the graph mid-turn with a question attached, and `Command(resume=...)` continues it once the human answers. What you write by hand is the policy around that pause — the ordered allow and deny rules, what counts as risky enough to ask, and how the answer is recorded.

```python
from langgraph.types import interrupt, Command

def gate(state: MyState):
    verdict = interrupt({"question": "Run: rm -rf /tmp/x? (yes/no)"})
    if verdict != "yes":
        return {"messages": ["Denied by policy."]}
    return Command(goto="run_tool", update={})

graph.invoke(state, config)
graph.invoke(Command(resume="yes"), config)  # after the human answers
```

*Effort:* a few lines

### 13. Session persistence

**Tier 3.** Saving a session to disk and resuming it later needs durable storage with a versioned layout.

**What it is.** Conversations must survive restarts. The harness writes every message to disk or a database as it goes, and loading a session later restores the full history. Good persistence also supports forks (branching a session into a variant), labels, and running without saving at all for throwaway chats.

**How the three do it.**

- **opencode:** sessions, messages, and parts live in database tables defined in `packages/opencode/src/storage/schema.ts` and managed from `packages/opencode/src/session/session.ts`, with a separate generic key-value file store in `packages/opencode/src/storage/storage.ts` for ancillary data; resuming is just re-reading the rows.
- **pi:** sessions auto-save as one JSON object per line under a sessions directory, managed by `SessionManager` in `dist/core/session-manager.js` with working-directory helpers in `dist/core/session-cwd.js`, where every entry carries an identifier plus a parent pointer forming a branchable tree with format versions and automatic migration.
- **hermes-agent:** live messages flush append-only to the database through `agent/session_persistence.py`, skipping already-written rows via a persisted marker, with session lifecycle flags and parent links in `hermes_state_sessions.py` and resume views built by `agent/session_activity.py` as described in `docs/session-lifecycle.md`.

**Where they agree / differ.** All three append durable records during the turn rather than saving at the end, so an interrupted session resumes cleanly; opencode and hermes-agent use a local database while pi uses line-delimited text files with parent pointers.

**In LangGraph / Python**

Short-term saving is the same checkpointer from operation 3: attach it at compile time, pass a thread id per call, and LangGraph loads history, merges new messages, and saves again automatically. Swapping the in-memory saver for `SqliteSaver` or `PostgresSaver` makes sessions survive restarts with no other code change. What you still write by hand is everything around it — labels, forks via `get_state_history` plus `update_state`, and any version-migration rules for old sessions.

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# SqliteSaver.from_conn_string returns a context manager, so the connection
# is opened and closed around the work rather than constructed directly.
with SqliteSaver.from_conn_string("sessions.db") as saver:
    graph = builder.compile(checkpointer=saver)
    config = {"configurable": {"thread_id": "abc"}}
    graph.invoke({"messages": [{"role": "user", "content": "hi"}]}, config)
    history = list(graph.get_state_history(config))
```

*Effort:* a few lines

### 14. Snapshot & revert

**Tier 5.** Undoing file changes touches the whole workspace and is hard to bolt on afterwards.

**What it is.** The agent edits real files and sometimes makes things worse. A snapshot captures the state of the working directory before changes so the user can rewind to an earlier point. Each snapshot is tied to a position in the conversation, giving the session an undo button for the file system.

**How the three do it.**

- **opencode:** snapshots use a hidden version-control repository under the data directory driven from `packages/opencode/src/snapshot/index.ts`, committing the work folder and storing commit hashes on message parts, with reverting and un-reverting tied to conversation position in `packages/opencode/src/session/revert.ts`.
- **pi:** the core ships no workspace snapshot or revert mechanism at all; `docs/extensions.md` lists version-control checkpointing only as an extension example, so snapshots would arrive as user-written extension code (note that similarly named truncation helpers in `dist/core/tools/output-accumulator.js` are about tool output, not workspace state).
- **hermes-agent:** `CheckpointManager` in `tools/checkpoint_manager.py` snapshots the working directory once per directory per turn into one shared shadow store keyed by path fingerprint, with restore validating hashes and paths and diff views from `tools/working_diff.py`.

**Where they agree / differ.** opencode and hermes-agent converged on the same design (automatic hidden version-control snapshots per turn, explicit validated restore), while pi deliberately omits it; automatic snapshots with manual restore is the shared pattern where it exists.

**In LangGraph / Python**

LangGraph's time travel (`get_state_history`, `update_state`) rewinds the conversation for free, but it knows nothing about your files: snapshotting the working directory and restoring it is ordinary Python you write by hand, typically a copy or a hidden version-control commit per turn. Say this plainly — half of this operation lives entirely outside the graph, which is why it sits in Tier 5.

```python
import shutil

def snapshot(cwd: str, dest: str) -> str:
    shutil.copytree(cwd, dest, dirs_exist_ok=True)
    return dest

snapshot("/repo", "/tmp/snapshots/turn-12")
states = list(graph.get_state_history(config))
graph.update_state(config, {"messages": states[1].values["messages"]})
```

*Effort:* a project of its own

### 15. Token accounting & cost

**Tier 3.** Counting tokens and money needs stored per-turn records plus a price table.

**What it is.** Every model call consumes input tokens (text sent in) and output tokens (text generated), and vendors charge per million tokens with discounts for reused cached content. The harness records usage per turn, looks up each model's rates, and shows running totals plus dollar cost so spending never surprises anyone.

**How the three do it.**

- **opencode:** after each turn the handler in `packages/opencode/src/session/processor.ts` calls usage collection in `packages/opencode/src/session/session.ts`, which normalizes provider cache fields and splits reasoning tokens, pricing them with exact decimal math from model data in `packages/opencode/src/provider/provider.ts`.
- **pi:** every assistant message carries a usage record with input, output, cache-read, cache-write, total, and cost fields priced from the active model's rates in `dist/core/model-registry.js`, surfaced by the session command and terminal footer, with recent usage preferred for context estimates in `dist/core/compaction/compaction.js`.
- **hermes-agent:** per-turn counts are queued and written by a coalescing background writer in `agent/account_usage.py` into per-route usage rows in `hermes_state_usage.py`, priced per million tokens through `agent/usage_pricing.py`, with balances and thresholds in `agent/credits_tracker.py`.

**Where they agree / differ.** All three store usage on the message or turn record and price from the model catalog, and all three account cached tokens separately from plain input so cache discounts stay visible.

**In LangGraph / Python**

Token counts come for free: every reply carries `usage_metadata` with input, output, and total tokens, and `UsageMetadataCallbackHandler` collects them across a run. Prices, per-turn records, and running dollar totals are ordinary Python you write by hand — a small rate table plus addition against the model catalog from operation 5.

```python
from langchain_core.callbacks import UsageMetadataCallbackHandler

tracker = UsageMetadataCallbackHandler()

def call_model(state: MyState):
    reply = model.invoke(state["messages"], config={"callbacks": [tracker]})
    used = reply.usage_metadata
    cost = (used["input_tokens"] * 3.0 + used["output_tokens"] * 15.0) / 1e6
    return {"messages": [reply]}
```

*Effort:* a few lines

### 16. Context overflow & compaction

**Tier 4.** Detecting a full context and shrinking it takes a second summarization call plus protection rules.

**What it is.** Models accept only a fixed amount of text per call. As history grows it eventually stops fitting, so the harness watches total size against the model's limit, and when the budget runs out it summarizes the older middle into a short recap while keeping the newest turns intact. The next turn then sees the recap plus the recent tail.

**How the three do it.**

- **opencode:** the safe budget comes from `usable()` in `packages/opencode/src/session/overflow.ts`, and on overflow the compactor in `packages/opencode/src/session/compaction.ts` keeps only recent turns fitting a preserve budget, summarizing the older head with a model call built in `packages/opencode/src/session/summary.ts` while separately blanking old tool outputs.
- **pi:** automatic compaction triggers when tokens exceed the window minus a 16384-token reserve, walking back to a cut at a turn boundary via `dist/core/compaction/utils.js` (never splitting a tool call from its result), then summarizing the prefix and reloading summary plus tail through `dist/core/compaction/compaction.js`.
- **hermes-agent:** policy lives in `agent/context_engine.py` while `agent/context_compressor.py` prunes old tool results first then summarizes the middle protecting head and tail, with turn-start preflight passes in `agent/turn_context_compaction.py`, provider-overflow recovery in `agent/turn_overflow.py`, and optional per-turn micro-summaries in `agent/micro_compaction.py`.

**Where they agree / differ.** All three converged on summarize-the-middle plus protect-the-tail with a never-split-tool-pairs rule; all three prune tool outputs before summarizing prose, differing only in how many passes and recovery paths they add around that core.

**In LangGraph / Python**

LangGraph hands you the sharp tools — `trim_messages` to cut history to a budget and `RemoveMessage` with `REMOVE_ALL_MESSAGES` to swap the summarized middle back in — but the policy is yours to write: when the budget trips, which turns to protect, and the summarization call itself. Compaction is one more node on the conditional path out of `call_model`, not a feature you switch on.

```python
from langchain_core.messages import RemoveMessage, trim_messages

def compact(state: MyState):
    tail = trim_messages(state["messages"], max_tokens=8000)
    recap = model.invoke(tail + [{"role": "user", "content": "Summarize our work so far."}])
    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), recap] + tail}

builder = StateGraph(MyState)
builder.add_node("compact", compact)
```

*Effort:* a day's work

### 17. Tool output offloading

**Tier 3.** Keeping giant results out of context needs a disk spill file plus a pointer the model can follow.

**What it is.** A single command can print megabytes. Feeding all of that to the model would instantly fill its context and budget, so the harness trims over-long results to a short preview, saves the full text to a file on disk, and tells the model the file path plus how to read more. Nothing is lost; most of it just stays out of the expensive context.

**How the three do it.**

- **opencode:** every tool run passes through truncation in `packages/opencode/src/tool/truncate.ts`, saving full text to a tool-output file managed by `packages/opencode/src/tool/truncation-dir.ts` and showing the model only a head preview plus the path with read-with-offset guidance, with files older than 7 days cleaned hourly.
- **pi:** output is tail-trimmed by default in `dist/core/tools/truncate.js` with line and byte caps, and `snapshot({ persistIfTruncated: true })` in `dist/core/tools/output-accumulator.js` spills full text to a file referenced by a full-output path on the result message, with extra caps when serializing for summaries.
- **hermes-agent:** three layers span `tools/tool_output_limits.py` (per-result caps), `tools/tool_result_storage.py` (spill oversize results under a cache directory, replacing context text with preview plus path), and `tools/budget_config.py` (per-turn aggregate budget across all results).

**Where they agree / differ.** All three converged on the same discipline: cap inline text, spill the full result to a file, hand the model a preview plus a path; hermes-agent adds the third layer of a per-turn total budget on top of the shared core.

**In LangGraph / Python**

LangGraph gives you nothing here: capping output, spilling the full text to disk, and handing the model a preview plus a path is ordinary Python inside a tool function. The `ToolNode` from the agent loop runs it unchanged — the discipline of cap, spill, and pointer lives entirely in your code.

```python
import subprocess
from pathlib import Path
from langchain_core.tools import tool

@tool
def run(cmd: str) -> str:
    """Run a command; spill full output to disk, return preview plus path."""
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    full = p.stdout + p.stderr
    if len(full) > 4000:
        path = Path("/tmp/spills/out.txt")
        path.write_text(full)
        return f"exit={p.returncode}\n{full[:4000]}\n...full output in {path}"
    return f"exit={p.returncode}\n{full}"
```

*Effort:* a few lines

### 18. Memory files

**Tier 3.** Loading instruction files from disk means discovery, layering rules, and prompt injection.

**What it is.** Memory files are plain instruction documents (such as AGENTS.md) that live in the project or home directory and tell the agent lasting facts: coding style, commands, things to remember. The harness finds them at startup, reads them, and pastes their contents into the prompt so the model follows them without being told twice.

**How the three do it.**

- **opencode:** `systemPaths()` in `packages/opencode/src/session/instruction.ts` collects one global file plus the first project-level match walking upward, reads them in parallel with source-path prefixes, and resolves nearby instruction files on each file read, parsing includes via `packages/opencode/src/config/markdown.ts`.
- **pi:** the loader in `dist/core/resource-loader.js` collects a global file then walks up through ancestor directories gathering AGENTS.md and CLAUDE.md files, injected verbatim into the system prompt by `dist/core/system-prompt.js` inside marked project-context blocks.
- **hermes-agent:** long-term notes are managed by `agent/memory_manager.py` with provider fan-out in `agent/memory_provider.py` and a model-facing writer in `tools/memory_tool.py`, entering the prompt as a frozen snapshot at session start so mid-session writes reach disk without rebuilding the cached prompt.

**Where they agree / differ.** All three walk upward from the working directory collecting instruction files into the prompt, but opencode takes only the first project-level match while pi stacks every ancestor, and hermes-agent freezes the snapshot for the session while the others re-read regularly.

**In LangGraph / Python**

LangGraph gives you nothing here either: finding instruction files, layering them (nearer directories winning over farther ones, project over global), and pasting them into the prompt is ordinary Python with `pathlib` feeding the `build_system_prompt` helper from operation 4. Note the long-term `store` is a different operation — per-user learned memory — while memory files are just files on disk.

```python
from pathlib import Path

def load_memory_files(cwd: str) -> str:
    texts = []
    for parent in [Path(cwd), *Path(cwd).parents]:
        for name in ("AGENTS.md", "CLAUDE.md"):
            found = parent / name
            if found.exists():
                texts.append(found.read_text())
                break
    return "\n\n".join(reversed(texts))
```

*Effort:* a few lines

### 19. Skills / progressive disclosure

**Tier 3.** On-demand knowledge packs need discovery on disk plus a list-now, load-later contract.

**What it is.** Skills are bundles of extra instructions for specific jobs (deploying, testing, reviewing) that would bloat the prompt if all loaded up front. The harness lists only each skill's name and short description in the prompt, and the full body loads only when the model actually needs it. Small prompt by default, full detail on demand.

**How the three do it.**

- **opencode:** discovery in `packages/opencode/src/skill/discovery.ts` scans skill files from global, project, config, and remote sources, the prompt lists only names plus descriptions, and the full body is injected only when the model calls the skill tool in `packages/opencode/src/tool/skill.ts`.
- **pi:** `loadSkills()` in `dist/core/skills.js` scans global, project, packaged, and settings paths for skill directories, only each skill's name and description enter the prompt via `dist/core/system-prompt.js`, and the full body loads when the model reads the skill file or the user invokes it as a slash command.
- **hermes-agent:** each skill is a directory under `skills/` holding an instruction file with linked companions, the listing tool in `tools/skills_tool.py` returns name and description only, viewing returns the full content, and bundles group several skills into one message via `agent/skill_bundles.py`.

**Where they agree / differ.** All three converged completely on name-plus-description up front with body-on-demand loading; that convergence across three independent codebases is the strongest signal in this document that the pattern is correct.

**In LangGraph / Python**

The list-now, load-later contract maps directly onto tools: each skill's name and description ride on a `@tool` docstring the model sees every turn, while the full body loads only when the model calls a small reader tool — the same `bind_tools` plus `ToolNode` machinery from operation 7. Discovery (scanning skill directories for new packs) is ordinary Python you write by hand.

```python
from pathlib import Path
from langchain_core.tools import tool

@tool
def list_skills() -> str:
    """List available skills by name and one-line description."""
    return "deploy: ship the app. review: critique a diff."

@tool
def read_skill(name: str) -> str:
    """Load one skill's full instructions on demand."""
    return Path(f"skills/{name}/SKILL.md").read_text()
```

*Effort:* a few lines

### 20. Sub-agents / delegation

**Tier 5.** Child agents with clean contexts reshape session, permission, and lifecycle machinery.

**What it is.** For a big task the main agent spawns a child agent: a fresh conversation with its own short context focused on one subtask, such as exploring a module. The parent sees only the child's final summary, keeping the parent's context small. The harness must create, track, limit, and clean up these children.

**How the three do it.**

- **opencode:** delegation is a tool call implemented by `TaskTool.execute()` in `packages/opencode/src/tool/task.ts`, enforcing a maximum nesting depth, resolving the child definition from `packages/opencode/src/agent/agent.ts`, and granting the child the parent's denies plus directory rules from `packages/opencode/src/agent/subagent-permissions.ts`.
- **pi:** the core ships no spawn-child tool and no child-context interface; per `dist/core/sdk.js` and `docs/usage.md` the composition primitive is creating a separate session, so delegation would be an extension whose tool builds a child session, prompts it, and returns the result, with total isolation by default.
- **hermes-agent:** children are built by `_build_child_agent` in `tools/delegate_tool_dispatch.py` with context from `agent/delegation_context.py` (fresh history, own session handle, parent tool groups minus blocked tools), run singly, in parallel, or in the background via `tools/async_delegation.py`, with lifecycle states in `agent/subagent_lifecycle.py`.

**Where they agree / differ.** opencode and hermes-agent agree that children get fresh contexts and restricted permissions while the parent sees only the summary; pi omits the tool entirely, leaving isolation total but all plumbing to extension authors.

**In LangGraph / Python**

LangGraph owns the fan-out: a child agent is a compiled subgraph invoked with its own thread id and a trimmed tool list, fanned out to with `Send`, while the parent keeps only the returned summary. What you write by hand is the policy around children — maximum nesting depth, which tools they may touch, and cleanup when they finish — which is why this sits in Tier 5.

```python
from langgraph.types import Send

child = builder.compile(checkpointer=InMemorySaver())  # the worker graph

def delegate(state: MyState):
    jobs = state["jobs"]  # one entry per subtask
    return [Send("child", {"messages": [{"role": "user", "content": j}]}) for j in jobs]

parent = StateGraph(MyState)
parent.add_node("child", lambda s: {"messages": child.invoke(s)["messages"][-1:]})
parent.add_conditional_edges("call_model", delegate, ["child"])
```

*Effort:* a project of its own

### 21. Planning & todo tracking

**Tier 4.** A task list the agent maintains needs state rules plus a mode that forbids editing.

**What it is.** For multi-step work the agent keeps a visible checklist: what is done, what is in progress, what is blocked. Plan mode goes further by forbidding file edits until the user approves a written plan. The checklist survives across turns and compaction so progress is never lost mid-task.

**How the three do it.**

- **opencode:** todos are per-session rows managed by `Todo.Service` in `packages/opencode/src/session/todo.ts`, replaced whole-list per call through `packages/opencode/src/tool/todo.ts`, while plan mode is two agent definitions (build versus plan) with plan exit confirmed and recorded in `packages/opencode/src/tool/plan.ts`.
- **pi:** there is no native plan mode, todo list, or tracker in the core; per `docs/usage.md` and `docs/extensions.md` these are intentionally omitted extension examples, with planning state surviving only incidentally inside the structured compaction summary format from `dist/core/compaction/compaction.js`.
- **hermes-agent:** todos live in an in-memory revisioned store in `tools/todo_tool.py` that rejects stale updates and re-injects active items after compaction, while plans have no separate engine: `build_plan_prompt` in `agent/plan_prompt.py` returns a normal-turn prompt that forbids implementation and requires a written plan file.

**Where they agree / differ.** opencode and hermes-agent agree todos are agent-maintained state with exactly one in-progress item and plans are enforced by mode or prompt rather than a separate engine; pi leaves both to extensions, betting its users prefer to build their own.

**In LangGraph / Python**

Todos are one extra state field plus a small updater with the exactly-one-in-progress rule enforced in plain Python. Plan mode needs no separate engine: a prompt that forbids edits plus an `interrupt` gate — the same pause-and-resume machinery from operation 12 — that freezes the graph until a human approves the written plan.

```python
from langgraph.types import interrupt

def apply_todos(state: MyState, items: str) -> dict:
    """Replace the whole todo list; keep exactly one item in progress."""
    todos = [line for line in items.splitlines() if line.strip()]
    return {"todos": todos}

def plan_gate(state: MyState):
    verdict = interrupt({"question": "Approve this plan? (yes/no)"})
    if verdict != "yes":
        return {"messages": ["Plan rejected; revise, do not implement."]}
    return {"messages": ["Plan approved; implement it."]}
```

*Effort:* a few lines

### 22. MCP / dynamic external tools

**Tier 4.** Talking to outside tool servers at runtime needs connections, discovery, and failure handling.

**What it is.** Beyond built-in tools, the harness can connect to outside tool servers while it runs and borrow their tools: databases, browsers, cloud services. The harness discovers each server's tool list, adapts remote tools into local ones, retries dead servers with cooldowns, and cleans up child processes on shutdown.

**How the three do it.**

- **opencode:** outside tools arrive through the client service in `packages/opencode/src/mcp/index.ts`, spawned per connection type with browser helpers in `packages/opencode/src/mcp/browser.ts`, cached via `packages/opencode/src/mcp/catalog.ts`, and adapted into model-callable tools at call time in `packages/opencode/src/session/tools.ts` with per-call permission checks.
- **pi:** there is deliberately no built-in outside-server support; per `docs/usage.md` and `docs/models.md` no client or transport exists in the core, so dynamic capability arrives through extension-registered tools instead, and such a bridge would itself be an extension adding tools live mid-session.
- **hermes-agent:** as a client it connects to configured servers on one background event loop with per-server entries in `tools/mcp_tool.py`, discovery registering remote tools into the local registry via `tools/mcp_tool_discovery.py`, lifecycle and orphan cleanup in `tools/mcp_tool_lifecycle.py`, with ready-made definitions in `optional-mcps/`, and it can also serve its own conversations outward via `mcp_serve.py`.

**Where they agree / differ.** opencode and hermes-agent agree on namespaced adaptation with lazy connection and retry cooldowns so one dead server never stalls a turn; pi omits the protocol entirely, treating its extension registry as the only door for outside tools.

**In LangGraph / Python**

Discovery and execution come largely for free: `MultiServerMCPClient` connects to configured servers and adapts each remote tool into a local one your `ToolNode` can run. What you write by hand is everything operational — the server configs, namespacing remote tools so two servers never collide, cooldowns so one dead server never stalls a turn, and cleanup on shutdown.

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import ToolNode

# Each server entry needs an explicit transport; get_tools() is async.
client = MultiServerMCPClient({
    "search": {"url": "http://localhost:8000/mcp", "transport": "streamable_http"},
})
remote_tools = await client.get_tools()
builder = StateGraph(MyState)
builder.add_node("call_model", call_model)
builder.add_node("tools", ToolNode(remote_tools))
```

*Effort:* a day's work

### 23. Hooks, plugins & events

**Tier 5.** Interception points around everything reshape the whole system once added.

**What it is.** Hooks and plugins let outside code observe and change behavior without editing the core: run checks before a tool call, rewrite a result afterwards, watch the token stream, or add whole commands. A shared event channel carries lifecycle announcements (turn started, tool finished, session closing) that plugins subscribe to.

**How the three do it.**

- **opencode:** cross-cutting behavior flows through a global event channel in `packages/opencode/src/bus/global.ts` plus a plugin service in `packages/opencode/src/plugin/index.ts` loading origins via `packages/opencode/src/plugin/loader.ts`, where `trigger(name, input, output)` awaits each matching hook in order over the shared output.
- **pi:** extensions are modules auto-discovered from global and project directories, subscribing through registration calls on the shared channel created by `createEventBus()` in `dist/core/event-bus.js`, with the lifecycle (input, turn and agent boundaries, before and after provider calls, tool veto and patch events, session events) wired in `dist/core/agent-session.js` and managed under `dist/core/extensions/`.
- **hermes-agent:** request payloads pass through hooks in `agent/api_request_hooks.py`, shell configuration entries in `agent/shell_hooks.py` run scripts that may block or add context, streaming observers in `agent/plugin_stream_hooks.py` get bounded queues off the token path, and trusted plugins get guarded model access via `agent/plugin_llm.py`, with catalogued plugins under `plugins/` and `plugin-catalog/`.

**Where they agree / differ.** All three converged on a shared event channel plus ordered hooks that can veto, rewrite, or observe, differing only in packaging (loaded plugin origins, extension modules, shell scripts plus queued observers); pi pushes the most behavior into extensions since its core is smallest.

**In LangGraph / Python**

The model-call hooks are built in: `create_react_agent` takes `pre_model_hook` and `post_model_hook` straight off the shelf, and `get_stream_writer` lets observers emit custom events mid-run. A global bus where any extension can veto or rewrite is ordinary Python you write by hand — most teams start with thin wrapper nodes around `call_model` and only build the bus when several plugins need it.

```python
from langgraph.config import get_stream_writer

def guarded_call_model(state: MyState):
    for hook in hooks:  # hooks: a plain list of functions you register
        hook(state)
    out = call_model(state)
    get_stream_writer()({"event": "turn_finished"})
    return out

builder = StateGraph(MyState)
builder.add_node("call_model", guarded_call_model)
```

*Effort:* a day's work

### 24. Background & concurrency

**Tier 5.** Detached work, queues, and simultaneous sessions change scheduling across the system.

**What it is.** Some work outlives one turn: a long test run, a watched command, a scheduled job, or simply two sessions at once. The harness tracks detached processes with output buffers and kill operations, queues incoming messages while busy, serializes turns within one session, and lets different sessions run simultaneously.

**How the three do it.**

- **opencode:** background work is an instance-scoped wrapper over a job registry in `packages/opencode/src/background/job.ts` (list, start, wait, promote, cancel), with per-session run serialization and transitive cancellation in `packages/opencode/src/session/run-state.ts`, served over transport in `packages/opencode/src/server/server.ts`.
- **pi:** there is no detached-task primitive; concurrency is cooperative inside `dist/core/agent-session.js` (mid-run messages queue as interrupting or idle-waiting with queue-update events), whole sessions swap via `AgentSessionRuntime` in `dist/core/agent-session-runtime.js`, and headless parallelism comes from separate processes through run modes in `dist/modes/`.
- **hermes-agent:** background processes spawn through `tools/terminal_tool_background.py` via the registry in `tools/process_registry.py` with output buffers and crash-recovery checkpoints, threads come from a daemon pool in `tools/daemon_pool.py`, scheduling from one shared timer heap in `agent/periodic_scheduler.py`, and batch datasets run via `batch_runner.py`.

**Where they agree / differ.** All three serialize turns within one session while allowing separate sessions in parallel, and all three queue-while-busy rather than interleaving; they differ on detached work, which hermes-agent and opencode track as first-class jobs while pi leaves to separate processes.

**In LangGraph / Python**

Running sessions at the same time is built in: each `thread_id` is an independent conversation, and `Send` fans work out to parallel workers inside one turn. Detached jobs that outlive a turn — tracked processes with output buffers and kill operations — are ordinary Python you write by hand around the graph, typically one thread per job calling `invoke` with its own thread id.

```python
import threading

def run_job(prompt: str, thread_id: str):
    cfg = {"configurable": {"thread_id": thread_id}}
    graph.invoke({"messages": [{"role": "user", "content": prompt}]}, cfg)

job = threading.Thread(target=run_job, args=("run tests", "job-1"))
job.start()
```

*Effort:* a project of its own

## Build order

Build in tier order; each tier unlocks the next.

1. Tier 1 first — the minimum that talks to a model: 1 (pure call), then 2 (streaming).
2. Tier 2 second — a working single-session agent: 3 (conversation state), 4 (system prompt), 7 (tool definitions), 8 (agent loop), 10 (file tools), 11 (shell execution).
3. Tier 3 third — durability, cost control, and knowledge: 13 (session persistence), 5 (provider abstraction), 15 (token accounting), 17 (tool output offloading), 18 (memory files), 19 (skills).
4. Tier 4 fourth — safety and scale: 6 (reliability), 12 (permission gate), 9 (parallel tool calls), 16 (compaction), 22 (outside tool servers), 21 (planning and todos).
5. Tier 5 last — system-reshaping machinery, all optional for a first harness: 23 (hooks and events), 20 (sub-agents), 24 (background work), 14 (snapshot and revert).
