# pi (pi-coding-agent) — harness anatomy

> pi (pi-coding-agent) is a minimal, extension-driven coding agent for the terminal, written in TypeScript (a typed superset of JavaScript) and shipped as compiled JavaScript.

## What it is

pi was built by Earendil Works as a small, hackable alternative to large closed coding assistants. It runs in the terminal, edits files, runs shell commands, and talks to many different model providers through one shared interface, with its behavior described in `docs/usage.md` and its extension system described in `docs/extensions.md`.

The single design idea that shapes everything is deliberate omission plus extension: the core in `dist/core/` ships only the agent loop, tools, sessions, and events, while permission popups, sub-agents, plan mode, and external tool protocols are left out on purpose (see `docs/usage.md`) so that extensions built on `dist/core/event-bus.js` and `dist/core/extensions/` can add them without forking the core.

## Architecture at a glance

- `dist/core/agent-session.js` — owns the agent loop: `prompt()`, steering queues, retry wiring, and the `beforeToolCall` / `afterToolCall` hook installation.
- `dist/core/agent-session-runtime.js` — owns multi-session management (new, resume, fork, clone, import) used by the run modes in `dist/modes/`.
- `dist/core/session-manager.js` — owns durable conversation storage: the branchable message tree, `buildSessionContext()`, and creation modes (`create()`, `open()`, `inMemory()`, `forkFrom()`).
- `dist/core/system-prompt.js` — owns system prompt assembly via `buildSystemPrompt()`, including tool lists, guidelines, project context, and skill catalogs.
- `dist/core/model-registry.js` and `dist/core/model-resolver.js` — own provider abstraction: the merged model catalog, `Model` interface, credential resolution, and `provider/id` reference parsing.
- `dist/core/tools/` (`read.js`, `write.js`, `edit.js`, `grep.js`, `find.js`, `ls.js`, `bash.js`, `index.js`, `tool-definition-wrapper.js`) — owns the seven built-in tools and their schemas, plus truncation helpers in `truncate.js` and `output-accumulator.js`.
- `dist/core/compaction/` (`compaction.js`, `utils.js`, `branch-summarization.js`) — owns context-overflow handling: cut-point search, summary generation, and branch summaries.
- `dist/core/extensions/` with `dist/core/event-bus.js` — owns the extension (plugin) lifecycle: discovery, loading via jiti (a just-in-time TypeScript loader), and the roughly 30-event bus that extensions subscribe to.
- `dist/core/skills.js` with `dist/core/resource-loader.js` — owns skills and memory files: scanning for `SKILL.md` directories and loading `AGENTS.md` / `CLAUDE.md` project context.

## Operation map

| # | Operation | Implemented in | In one line |
|---|---|---|---|
| 1 | Pure LLM call | `dist/core/sdk.js`, `dist/core/agent-session.js`, `dist/core/compaction/compaction.js` | One-shot streamed model call with no tool loop, used for summaries. |
| 2 | Streaming | `dist/core/agent-session.js`, `dist/core/tools/bash.js` | Token and tool-output deltas re-emitted as events for live display. |
| 3 | Conversation state | `dist/core/session-manager.js`, `dist/core/messages.js` | Branchable session tree converted into the model message list. |
| 4 | System prompt assembly | `dist/core/system-prompt.js` | Rendered tool list plus adaptive guidelines and project context. |
| 5 | Provider & model abstraction | `dist/core/model-registry.js`, `dist/core/model-resolver.js` | One model interface over four wire protocols and custom providers. |
| 6 | Reliability | `dist/core/agent-session.js`, `dist/core/http-dispatcher.js`, `dist/core/settings-manager.js`, `dist/core/model-resolver.js` | Turn-level retries with backoff, idle timeouts, and model fallback. |
| 7 | Tool definitions | `dist/core/tools/index.js`, `dist/core/tools/tool-definition-wrapper.js`, `dist/utils/tools-manager.js` | Seven schema-defined built-ins plus hot-registered extension tools. |
| 8 | Agent loop | `dist/core/agent-session.js` | Model responds, tools run through hooks, repeat until no calls. |
| 9 | Parallel tool calls | `dist/core/tools/file-mutation-queue.js`, `dist/core/compaction/compaction.js` | Sibling calls preflight in order, run together, results re-ordered. |
| 10 | File tools | `dist/core/tools/read.js`, `dist/core/tools/write.js`, `dist/core/tools/edit.js`, `dist/core/tools/grep.js`, `dist/core/tools/find.js`, `dist/core/tools/ls.js` | Paged reads, targeted edits, search and listing with mutation queue. |
| 11 | Shell execution | `dist/core/tools/bash.js`, `dist/core/bash-executor.js`, `dist/core/exec.js` | Shell spawn with streamed output, tree kill on abort or timeout. |
| 12 | Permission / approval gate | `dist/core/agent-session.js` | No popup; extensions veto or rewrite tool calls via events. |
| 13 | Session persistence | `dist/core/session-manager.js`, `dist/core/session-cwd.js` | JSONL (JSON Lines) message tree with versions, forks, and labels. |
| 14 | Snapshot & revert | `—` | not implemented — only suggested as an extension example. |
| 15 | Token accounting & cost | `dist/core/model-registry.js`, `dist/core/compaction/compaction.js` | Per-message usage records with cache-split costs drive displays. |
| 16 | Context overflow & compaction | `dist/core/compaction/compaction.js`, `dist/core/compaction/utils.js`, `dist/core/compaction/branch-summarization.js`, `dist/core/session-manager.js` | Cut at turn boundary, summarize prefix, reload summary plus tail. |
| 17 | Tool output offloading | `dist/core/tools/truncate.js`, `dist/core/tools/output-accumulator.js`, `dist/core/tools/bash.js`, `dist/core/bash-executor.js` | Tail-truncate over-limit output and spill full text to a file. |
| 18 | Memory files | `dist/core/resource-loader.js`, `dist/core/system-prompt.js` | Walk-up `AGENTS.md` collection injected verbatim into the prompt. |
| 19 | Skills / progressive disclosure | `dist/core/skills.js`, `dist/core/system-prompt.js` | Only name plus description in prompt; body loads on demand. |
| 20 | Sub-agents / delegation | `—` | not implemented — SDK (Software Development Kit) composes sessions instead. |
| 21 | Planning & todo tracking | `—` | not implemented — no plan mode or task list in core. |
| 22 | MCP / dynamic external tools | `—` | not implemented — MCP (Model Context Protocol) would arrive as an extension. |
| 23 | Hooks, plugins & events | `dist/core/event-bus.js`, `dist/core/agent-session.js`, `dist/core/extensions/` | TypeScript extensions on a shared event bus with veto and patch. |
| 24 | Background & concurrency | `dist/core/agent-session.js`, `dist/core/agent-session-runtime.js`, `dist/modes/` | Queued steering plus session swapping; no background shell tasks. |

## How each operation works

### 1. Pure LLM call

The single-request primitive is `streamSimple`, imported from the `@earendil-works/pi-ai/compat` package, which streams exactly one model response for one message list with no tool loop attached. `AgentSession` in `dist/core/agent-session.js` wires this function in as `agent.streamFn` (checked around `agent-session.js:171`), so every agentic turn is built on top of this plain call. The only tool-free use inside the package itself is compaction in `dist/core/compaction/compaction.js`: `generateSummary()` turns the conversation into plain text, wraps it in `<conversation>` tags with a fixed summarization prompt, and sends it with no tools. The Software Development Kit (SDK, the library interface for embedding pi) surface for this is described in `docs/sdk.md`. That keeps summarization cheap and predictable, since the model cannot call tools mid-summary.

**Watch out:** the summarizer caps output at `maxTokens = min(0.8 * reserveTokens, model.maxTokens)` in `dist/core/compaction/compaction.js`, so the summary itself can never eat the response reserve.

### 2. Streaming

As response tokens arrive, the agent object updates `agent.state.streamingMessage`, and `AgentSession` in `dist/core/agent-session.js` re-emits those pieces as `message_update` events carrying `text_delta` (plain text) or `thinking_delta` (model reasoning) payloads defined alongside `AssistantMessageEvent`. Partial tool output travels the same event path via `tool_execution_update`, so the Terminal User Interface (TUI, the interactive terminal display) shows file and shell progress live. The `isStreaming` flag simply reads `agent.state.isStreaming`, and long shell output from `dist/core/tools/bash.js` is throttled to one display update per 100 milliseconds (`BASH_UPDATE_THROTTLE_MS = 100`). The event shapes for consumers are documented in `docs/sdk.md` and `docs/json.md`. Streaming here is a display feed, not a control channel.

**Watch out:** streaming is observation-only for extensions — `message_end` handlers in `dist/core/agent-session.js` may replace the finalized message but must keep the same `role`.

### 3. Conversation state

The durable history is a session tree stored by `SessionManager` in `dist/core/session-manager.js`, where each entry has a parent identifier and the active path is found by walking from the leaf to the root with `getBranch()`. Before each model call, `buildSessionContext()` turns that path into the message list, splicing any compaction summary in first when a `CompactionEntry` sits on the path, and converting branch summaries and extension custom messages into plain messages. `convertToLlm()` in `dist/core/messages.js` maps pi's extended roles (`bashExecution`, `custom`, `branchSummary`, `compactionSummary`) onto the roles the provider understands. Before every model call the `context` event hands extensions a deep copy of the messages so they can filter without destroying history. The on-disk layout behind this tree is specified in `docs/session-format.md` and the SDK (Software Development Kit) view in `docs/sdk.md`.

**Watch out:** extension `custom` entries persist in the session file but never enter model context — only `custom_message` entries do — and assigning `agent.state.messages` in `dist/core/agent-session.js` copies only the top-level array.

### 4. System prompt assembly

`buildSystemPrompt()` in `dist/core/system-prompt.js` takes the custom prompt, selected tools, tool snippets, prompt guidelines, appended text, working directory, context files, and skills, and renders one prompt. It always includes an `Available tools` list plus a deduplicated `Guidelines` section whose bullets adapt to the active tools, for example showing "use shell commands for file operations" only when the `grep`, `find`, and `ls` tools are absent. A custom prompt supplied via the `--system-prompt` flag or a `.pi/SYSTEM.md` file replaces the default body, but project context files are still appended inside `<project_context>` as `<project_instructions path="...">` blocks, followed by the skill catalog, the date, and the working directory. Extensions can chain edits to this prompt every turn through the `before_agent_start` event, each handler seeing the previous handler's output as described in `docs/extensions.md`. General usage is covered in `docs/usage.md`.

**Watch out:** the current date and working directory are always appended last in `dist/core/system-prompt.js`, and in custom-prompt mode the skills section is included only when the `read` tool is active, since skills are useless without it.

### 5. Provider & model abstraction

`ModelRegistry` in `dist/core/model-registry.js` merges the built-in model list with user-defined custom providers from `~/.pi/agent/models.json` behind one `Model` interface carrying the identifier, reasoning support, input types, context window, output limit, cost rates, and compatibility flags. Four wire protocols are supported (`openai-completions`, `openai-responses`, `anthropic-messages`, and `google-generative-ai`), with per-provider and per-model compatibility flags shimming servers that are only partly compatible with the OpenAI (an Application Programming Interface style originated by OpenAI) format. Credential resolution order is the Command Line Interface (CLI, the terminal command flags) `--api-key` flag first, then `auth.json`, then environment variables, then keys inside `models.json`. Model references parse as `provider/id` with an optional `:<thinking>` suffix, resolved by `resolveCliModel()`, `parseModelPattern()`, `findInitialModel()`, and `buildFallbackModel()` in `dist/core/model-resolver.js`, with `thinkingLevelMap` translating the suffix. Providers and model selection are documented in `docs/providers.md` and `docs/models.md`.

**Watch out:** a custom model with no configured credentials loads but stays hidden from `/model` and `--list-models` in `dist/core/model-registry.js`, so keyless local servers such as Ollama or LM Studio need a dummy `apiKey` value to appear.

### 6. Reliability

Turn-level retry is configured through the settings in `docs/settings.md` and applied in `dist/core/agent-session.js`: it is on by default with 3 attempts and exponential backoff starting at a 2-second base delay, and it re-runs failed turns while emitting `auto_retry_start` and `auto_retry_end` events documented in `docs/json.md`. The internal `_retryAttempt` counter resets on the first non-error assistant response, so one recovery does not poison later turns. Provider-level retries default to `0` in `dist/core/settings-manager.js` and `dist/core/model-resolver.js`, which surfaces transient quota errors to the agent instead of stalling inside the low-level client. The Hypertext Transfer Protocol (HTTP, the network layer) idle timeout defaults to 300 seconds through `configureHttpDispatcher()` in `dist/core/http-dispatcher.js`. If a saved session names a model that no longer exists, `restoreModelFromSession()` in `dist/core/model-resolver.js` picks a fallback and returns a `modelFallbackMessage` warning.

**Watch out:** keep `retry.provider.maxRetries` at `0` — a higher value can stall the agent until provider quota resets — and requests facing a server-asked delay longer than `maxRetryDelayMs` (60 seconds) fail immediately instead of waiting silently, per `dist/core/settings-manager.js`.

### 7. Tool definitions

Seven built-in tools exist — `read`, `bash`, `edit`, `write`, `grep`, `find`, and `ls` — with the default allowlist being `read, bash, edit, write`, as assembled by `createCodingTools()` and `createReadOnlyTools()` in `dist/core/tools/index.js`. Each tool is a TypeBox schema object (a runtime type definition), for example the shell schema `{ command, timeout? }` in `dist/core/tools/bash.js`, wrapped by `wrapToolDefinition()` in `dist/core/tools/tool-definition-wrapper.js` into the provider's function-calling format. Custom tools come from `defineTool()` for SDK (Software Development Kit) users or `pi.registerTool()` for extensions, and each can contribute a one-line `promptSnippet` plus `promptGuidelines` bullets that teach the model when to use it. Scoping uses tool allowlists, `excludeTools`, `--no-builtin-tools`, and `--no-tools`, managed with `dist/utils/tools-manager.js`. The full list and registration flow are described in `docs/extensions.md`, `docs/sdk.md`, and `docs/usage.md`.

**Watch out:** `promptGuidelines` bullets are appended flat into the shared `Guidelines` section of `dist/core/system-prompt.js` with no tool-name prefix, so each bullet must name its own tool ("Use my_tool when...") — "this tool" is unresolvable by the model.

### 8. Agent loop

`AgentSession.prompt()` in `dist/core/agent-session.js` is the entry point: it expands `/skill:` and template references, fires the `input` event, then fires `before_agent_start`, then hands off to the turn loop. Each turn the model responds, every tool call passes through the `beforeToolCall` extension hook installed by `_installAgentToolHooks()`, executes, passes through `afterToolCall`, appends the result, and calls the model again until a turn ends with no tool calls. Lifecycle events mark the boundaries: `turn_start` and `turn_end` per turn, `agent_start` and `agent_end` for the whole run, as documented in `docs/extensions.md` and `docs/sdk.md`. Messages queued mid-run split by urgency: `steer()` interrupts after the current turn's tool calls finish, while `followUp()` waits until the agent is fully idle.

**Watch out:** calling `prompt()` while streaming without a `streamingBehavior` option throws in `dist/core/agent-session.js` — but extension slash commands bypass the queue entirely and execute immediately even mid-stream.

### 9. Parallel tool calls

In the default parallel mode, sibling tool calls from one assistant message are preflighted one at a time in the assistant's source order, so `tool_execution_start` events fire in that order, and then they execute at the same time with interleaved `tool_execution_update` events. Completion events (`tool_execution_end`) fire in whatever order the tools finish, but the final `toolResult` messages are re-emitted in the original assistant source order so the model sees a stable layout. Edits to the same file get extra safety from `withFileMutationQueue()` in `dist/core/tools/file-mutation-queue.js`, which serializes same-file writes while different files still run in parallel. The event ordering contract is part of `docs/extensions.md`, and the summary path reuses related ordering logic in `dist/core/compaction/compaction.js`.

**Watch out:** a `tool_call` handler is not guaranteed to see sibling tool results from the same assistant message in `ctx.sessionManager`, because preflight in `dist/core/agent-session.js` runs before any sibling has finished.

### 10. File tools

The `read` tool in `dist/core/tools/read.js` takes `{ path, offset?, limit? }` for paged reads of large files. The `write` tool in `dist/core/tools/write.js` creates or overwrites whole files, while the `edit` tool in `dist/core/tools/edit.js` applies targeted modifications and returns both a `details.diff` for the terminal display and a unified `details.patch` for SDK (Software Development Kit) consumers. Search and listing are covered by `grep` in `dist/core/tools/grep.js`, `find` in `dist/core/tools/find.js`, and `ls` in `dist/core/tools/ls.js`. Every mutating file tool runs through `withFileMutationQueue()` in `dist/core/tools/file-mutation-queue.js` so concurrent writes to the same file serialize instead of racing. Usage patterns are shown in `docs/usage.md` and `docs/sdk.md`.

**Watch out:** search match lines are hard-capped at 500 characters (`GREP_MAX_LINE_LENGTH` in `dist/core/tools/grep.js`), so long-line matches arrive pre-truncated.

### 11. Shell execution

Commands spawn through the configured shell with standard output and standard error piped and streamed piece by piece into an `OutputAccumulator` in `dist/core/bash-executor.js`, created through `createLocalBashOperations()` and `createBashTool()` in `dist/core/tools/bash.js` with low-level spawning in `dist/core/exec.js`. The tool schema is `{ command, timeout? }`, where the timeout is an optional number of seconds with no default value. Aborting with the Escape key or hitting the timeout kills the whole process tree via `killProcessTree()`, and `waitForChildProcess()` resolves without hanging on output handles inherited by detached child processes. Interactive `!command` sends output to the model while `!!command` marks it `excludeFromContext`, and extensions can intercept both through the `user_bash` event to wrap the local backend or return a synthetic result, per `docs/extensions.md`.

**Watch out:** the `timeout` parameter is in seconds, not milliseconds — and `detached: true` process spawning in `dist/core/tools/bash.js` is only process-tree bookkeeping, not a background-task feature.

### 12. Permission / approval gate

There is no built-in permission popup, and that is deliberate: `docs/usage.md` states pi intentionally leaves out permission popups. The gate is the `tool_call` extension event, fired from `AgentSession._installAgentToolHooks()` in `dist/core/agent-session.js` after `tool_execution_start` and before the tool runs. Any handler can return `{ block: true, reason }` to veto the call — the documented example in `docs/extensions.md` asks the user to confirm `rm -rf` via `ctx.ui.confirm` — or it can edit `event.input` in place to rewrite arguments, with later handlers seeing earlier edits. Event-type helpers such as `isToolCallEventType()` keep the dispatch strict.

**Watch out:** mutated tool arguments are not re-validated against the schema in `dist/core/agent-session.js`, and if a `tool_call` handler itself throws, execution is blocked with the message "Extension failed, blocking execution".

### 13. Session persistence

Sessions auto-save as JSONL (JSON Lines, one JSON object per line) under `~/.pi/agent/sessions/--<path>--/<timestamp>_<uuid>.jsonl`, managed by `SessionManager` in `dist/core/session-manager.js` with working-directory helpers in `dist/core/session-cwd.js`. Every entry after the header carries an 8-character hexadecimal `id` plus a `parentId`, forming a branchable tree with a movable leaf pointer. Files self-declare format versions 1 through 3 (`CURRENT_SESSION_VERSION = 3`) and migrate to version 3 automatically on load. Resume, fork (`/fork`), clone (`/clone`), in-tree navigation (`/tree`), and ephemeral `--no-session` mode all build on the same manager through `create()`, `open()`, `continueRecent()`, `inMemory()`, `forkFrom()`, `appendMessage()`, `appendCompaction()`, `appendCustomEntry()`, `appendLabelChange()`, and `branch()`. The lifecycle is described in `docs/sessions.md` and the file layout in `docs/session-format.md`.

**Watch out:** labels are not fields on entries but separate `label` entries pointing at a `targetId` in `dist/core/session-manager.js` (clear one by setting the label to `undefined`), and `SessionManager.inMemory()` gives a fully functional session with no file at all.

### 14. Snapshot & revert

The core ships no workspace snapshot, checkpoint, stash, or revert mechanism: no such symbol exists anywhere in `dist/core/` outside output-truncation code, and `docs/extensions.md` lists git (a version-control system) checkpointing only as an extension example ("stash at each turn, restore on branch"). The intended path is an extension that snapshots the working files on turn or session events and restores them on branch navigation. Nothing in the settings or session format supports rolling the file system back. This is a deliberate gap, not an oversight.

**Watch out:** `OutputAccumulator.snapshot()` in `dist/core/tools/output-accumulator.js` is about truncating long tool output (see the offloading operation), not workspace state — searching for "snapshot" finds the wrong thing.

### 15. Token accounting & cost

Every assistant message carries a `Usage` record with `input`, `output`, `cacheRead`, `cacheWrite`, `totalTokens`, and `cost` fields, as specified in `docs/session-format.md` and computed from the active model's per-million-token rates in `dist/core/model-registry.js`. The `/session` command and the terminal footer surface running token and cost totals from these records, per `docs/sessions.md`. Compaction in `dist/core/compaction/compaction.js` and the `ctx.getContextUsage()` helper prefer the most recent assistant `Usage` entry and fall back to `estimateTokens()` heuristics for trailing messages via `calculateContextTokens()` and `getLastAssistantUsage()`. Because rates merge in from `models.json` overrides, custom providers get correct pricing without code changes.

**Watch out:** prompt-cache reads and writes are accounted and priced separately from plain input tokens in `dist/core/model-registry.js`, so caching discounts show up as `cacheRead` volume rather than reduced input.

### 16. Context overflow & compaction

Automatic compaction triggers when `contextTokens > contextWindow - reserveTokens`, with the default reserve of 16384 tokens, using `shouldCompact()` in `dist/core/compaction/compaction.js`. `prepareCompaction()` walks backwards from the newest message to a `firstKeptEntryId` that keeps roughly 20000 recent tokens (`keepRecentTokens`), normally cutting at turn boundaries found by `findCutPoint()` and `findTurnStartIndex()` in `dist/core/compaction/utils.js`. Then `compact()` summarizes everything before the cut with `generateSummary()` over `serializeConversation()` output in the fixed Goal, Constraints, Progress, Decisions, and Next-Steps format, appends a `CompactionEntry` through `dist/core/session-manager.js`, and reloads so the model sees the summary plus the kept tail. Two recovery paths differ: context-overflow compaction auto-retries the aborted turn once, while threshold compaction does not retry. Branch switching (`/tree`) reuses the same machinery through `collectEntriesForBranchSummary()` and `generateBranchSummary()` in `dist/core/compaction/branch-summarization.js`. Behavior and settings are documented in `docs/compaction.md` and `docs/settings.md`.

**Watch out:** a cut is never placed at a tool result in `dist/core/compaction/utils.js` — the result must stay with its tool call — and when one giant turn exceeds the whole keep budget ("split turn"), pi summarizes the turn prefix and history separately and merges them.

### 17. Tool output offloading

Tool output is tail-truncated by default in `dist/core/tools/truncate.js` (head truncation via `truncateHead()` exists for cases where the end matters less), using `truncateTail()` and `truncateLine()` with `DEFAULT_MAX_LINES` of 2000 and `DEFAULT_MAX_BYTES` of 50 kilobytes. Over-limit content is cut with head and tail markers stating how much was dropped, and `OutputAccumulator.snapshot({ persistIfTruncated: true })` in `dist/core/tools/output-accumulator.js` spills the full text to a file referenced by `fullOutputPath` on the result message (for shell commands, `BashExecutionMessage.fullOutputPath` in `dist/core/bash-executor.js` and `dist/core/tools/bash.js`). When conversations are serialized for summarization, tool results are additionally capped at 2000 characters per `docs/session-format.md`. Interactive `!!` commands set `excludeFromContext` so their output never enters model context at all.

**Watch out:** the shell executor in `dist/core/bash-executor.js` tolerates twice the normal budget (`DEFAULT_MAX_BYTES * 2` = 100 kilobytes) before truncating, and search output in `dist/core/tools/grep.js` is line-capped at 500 characters independently of the byte budget.

### 18. Memory files

At startup the loader in `dist/core/resource-loader.js` collects a global memory file, then walks up from the working directory through ancestor directories gathering `AGENTS.md` and `CLAUDE.md` files (including `.MD` case variants) via `loadAgentsFiles()`, producing an `agentsFiles` list of `{ path, content }` pairs. Those contents are injected verbatim into the system prompt by `dist/core/system-prompt.js`, wrapped as `<project_instructions path="...">` blocks inside `<project_context>`. Full prompt replacement lives in a project or global `SYSTEM.md` file, while `APPEND_SYSTEM.md` appends without replacing, and `--no-context-files` disables all of it, per `docs/usage.md`.

**Watch out:** context files load regardless of project trust in `dist/core/resource-loader.js` — unlike `.pi/` settings, extensions, skills, and prompts, which stay unloaded until the project is trusted.

### 19. Skills / progressive disclosure

At startup `loadSkills()` and `loadSkillsFromDir()` in `dist/core/skills.js` scan global directories (`~/.pi/agent/skills/`, `~/.agents/skills/`), project directories (`.pi/skills/`, `.agents/skills/` up to the repository root, only after the project is trusted), packaged, settings, and Command Line Interface (CLI) paths for `SKILL.md` directories, following the Agent Skills standard leniently. Only each skill's `name` and `description` frontmatter fields enter the system prompt through `formatSkillsForPrompt()` in `dist/core/system-prompt.js`, rendered as Extensible Markup Language (XML, a tag-based format) per the standard. The full skill body loads on demand: either the model reads the skill file with the `read` tool, or the user invokes `/skill:name` with trailing arguments appended as `User: <args>`. Discovery and invocation are documented in `docs/skills.md`.

**Watch out:** a skill without a `description` is silently skipped in `dist/core/skills.js` (the one hard failure), name collisions keep the first-found skill with a warning, and unlike the standard, pi does not require the skill name to match its directory name.

### 20. Sub-agents / delegation

The core ships no spawn-subagent tool and no child-context Application Programming Interface (API, the function surface one program offers another): no such symbol exists in `dist/core/sdk.js`, and `docs/usage.md` names sub-agents among the deliberately omitted features. The documented composition primitive is `createAgentSession()` from `dist/core/sdk.js` combined with `SessionManager.inMemory()` from `dist/core/session-manager.js`, as described in `docs/sdk.md`. An extension registers a normal tool whose `execute()` creates a child session (typically in-memory for a clean context), prompts it, and returns the result as tool content. There is no nesting depth limit or privilege separation in the core because children are just independent sessions.

**Watch out:** because delegation is only nested `createAgentSession()` calls, a child gets none of the parent's history unless the tool author copies messages in — isolation is total by default.

### 21. Planning & todo tracking

There is no native plan mode, todo list, or task tracker in the core: no plan or todo symbol exists, and `docs/usage.md` groups plan mode and to-do lists with the intentionally omitted features while `docs/extensions.md` lists "stateful tools (todo lists, connection pools)" as an extension example. Planning state survives only incidentally through the structured summary format in `docs/compaction.md` (Goal, Constraints, Progress with Done, In Progress, and Blocked states, Decisions, Next Steps) and through extensions persisting their own state via `pi.appendEntry()` custom entries. Fixed workflows arrive as slash commands such as `/review` and prompt templates rather than dynamic plans.

**Watch out:** the structured summary format is the closest thing to a native plan artifact — but it is a lossy narrative regenerated by the model in `dist/core/compaction/compaction.js`, not a machine-checked task list, so completion state can drift.

### 22. MCP / dynamic external tools

There is deliberately no built-in MCP (Model Context Protocol, the open standard for connecting models to external tools) support: `docs/usage.md` names it among the omitted features, and no MCP (Model Context Protocol) client, transport, or tool mapping exists anywhere in `dist/core/` or the docs in `docs/extensions.md` and `docs/models.md`. Dynamic external capability arrives through two other doors instead. First, asynchronous extension factories fetch remote configuration at startup and call `pi.registerProvider()` or `pi.registerTool()` (the documented local-model example shows the pattern). Second, `models.json` custom providers point any supported wire protocol at an external server. An MCP (Model Context Protocol) bridge would itself be an extension built on `registerTool()`.

**Watch out:** extension-registered tools appear immediately in `pi.getAllTools()` with no reload needed, so a hypothetical MCP (Model Context Protocol) extension could add or remove remote tools live mid-session.

### 23. Hooks, plugins & events

Extensions are TypeScript modules loaded via jiti (a just-in-time TypeScript loader, so no compilation step is needed), auto-discovered from the global `~/.pi/agent/extensions/` directory and the trust-gated project `.pi/extensions/` directory managed by `dist/core/extensions/`. They subscribe through `pi.on()` on the shared bus created by `createEventBus()` in `dist/core/event-bus.js`, with registration helpers `pi.registerTool()`, `pi.registerCommand()`, and `pi.setActiveTools()`. The lifecycle runs roughly: `input`, then `before_agent_start`, then `agent_start`, then per turn `turn_start`, `context`, `before_provider_request`, `after_provider_response`, `tool_execution_*`, `tool_call` (veto or mutate), `tool_result` (patch chaining), then `turn_end` and `agent_end`, plus cancellable session events (`session_before_switch`, `session_before_fork`, `session_before_compact`, `session_before_tree`), model selectors, and thinking selectors, all wired in `dist/core/agent-session.js`. The `ExtensionContext` exposes the user interface (`ctx.ui`), session manager, abort signal, and a manual `ctx.compact()` helper. Cross-extension messaging goes through the same shared event bus. The full contract is documented in `docs/extensions.md`.

**Watch out:** `tool_result` handlers chain like middleware (each sees the previous handler's edits and may return partial `{ content, details, isError }` patches), while `tool_call` handlers can only veto via `{ block: true }` — argument changes must be done by mutating `event.input` in place, per `docs/extensions.md`.

### 24. Background & concurrency

There is no built-in background-shell or detached-task primitive: it is deliberately omitted per `docs/usage.md`, and the `detached` flag in `dist/core/tools/bash.js` is only process-tree bookkeeping for kills. Concurrency is cooperative inside `dist/core/agent-session.js`: steering and follow-up messages queue while the agent works (`steer()` runs after the current turn's tool calls, `followUp()` waits for full idle), with `queue_update` events exposing both queues, and the Escape key aborts and restores queued text to the editor. `AgentSessionRuntime` in `dist/core/agent-session-runtime.js` swaps whole sessions (new, resume, fork, clone, import) with `session_shutdown` then `session_start` teardown semantics. Headless parallelism comes from separate processes through the run modes in `dist/modes/` (`InteractiveMode`, `runPrintMode`, `runRpcMode`), described in `docs/sdk.md` and `docs/rpc.md`.

**Watch out:** event subscriptions attach to one specific `AgentSession`, so after any runtime replacement the host must re-subscribe — and extensions must never start background resources (timers, watchers, sockets) in the factory itself, only from `session_start` with cleanup in `session_shutdown`, per `docs/extensions.md`.

## Distinctive choices

- No permission popups on purpose: `docs/usage.md` refuses them and `dist/core/agent-session.js` exposes the `tool_call` veto event instead, so every approval policy is user code rather than a built-in dialog.
- Labels as entries, not fields: `dist/core/session-manager.js` stores session labels as separate `label` entries pointing at a `targetId`, which makes rename and clear operations append-only history edits.
- Tool results re-ordered into source order: `dist/core/agent-session.js` fires completion events in finish order but re-emits `toolResult` messages in assistant order, so parallel execution never scrambles the model's view.
- Skills that require nothing but a description: `dist/core/skills.js` silently skips a skill missing its `description`, keeps the first match on name collision, and never requires the directory name to match — leniency the standard does not have.
- Memory files that ignore trust: `dist/core/resource-loader.js` loads `AGENTS.md` / `CLAUDE.md` even in untrusted projects while `.pi/` extensions and skills stay gated, treating context as data and code as privileged.
- Overflow recovery with two paths: `dist/core/compaction/compaction.js` auto-retries the aborted turn once after context-overflow compaction but never retries after threshold compaction, separating "the model was interrupted" from "the session grew."

## What we take from it

- Copy the veto-and-mutate hook shape from `dist/core/agent-session.js`: one event that can block with a reason plus in-place argument edits covers most approval and rewriting needs with very little code.
- Copy summary-first context building from `dist/core/session-manager.js` and `dist/core/compaction/compaction.js`: always placing the compaction summary before the kept tail gives the model a stable "what happened, what now" frame.
- Copy spill-to-file truncation from `dist/core/tools/output-accumulator.js` and `dist/core/tools/truncate.js`: tail markers plus a `fullOutputPath` reference keep context small without losing evidence.
- Do not copy the missing permission popup or missing sub-agent tool as-is unless you share pi's audience: both gaps in `docs/usage.md` assume expert users who write their own extensions, which is unsafe for shared or novice-facing harnesses.
- Do not copy trust-ignoring memory files from `dist/core/resource-loader.js` without sandboxing: auto-loading ancestor `AGENTS.md` files is convenient but lets any parent directory inject instructions into the model.
