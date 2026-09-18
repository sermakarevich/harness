# pi — harness operation inventory

Package version `0.80.2`, installed npm package `@earendil-works/pi-coding-agent`.
All `Where` paths below are relative to that root. Read docs first, confirmed with targeted greps in `dist/`.

## 1. Pure LLM call

- **Where:**
  - `docs/sdk.md`
  - `dist/core/sdk.js`
  - `dist/core/agent-session.js`
  - `dist/core/compaction/compaction.js`
- **Key symbols:** `streamSimple` (imported from `@earendil-works/pi-ai/compat`), `agent.streamFn`, `generateSummary()`, `completeSummarization()`
- **How it works:** The single-request primitive is `streamSimple(model, context, options)`, which streams one model response for one message list with no tool loop. `AgentSession` wires it in as `agent.streamFn` (checked at `agent-session.js:171`), so every turn is built on top of this one-shot call. The only tool-free use inside the package is compaction: `generateSummary()` serializes the conversation to plain text, wraps it in `<conversation>` tags plus a fixed summarization system prompt, and calls it with no tools attached.
- **Notable detail:** The summarizer caps output at `maxTokens = min(0.8 * reserveTokens, model.maxTokens)`, so the summary itself can never eat the response reserve.

## 2. Streaming

- **Where:**
  - `docs/sdk.md`
  - `docs/json.md`
  - `dist/core/agent-session.js`
  - `dist/core/tools/bash.js`
- **Key symbols:** `session.subscribe()`, `message_update` / `AssistantMessageEvent` (`text_delta`, `thinking_delta`), `isStreaming`, `tool_execution_update`, `BASH_UPDATE_THROTTLE_MS`
- **How it works:** As tokens arrive, the agent updates `agent.state.streamingMessage` and `AgentSession` re-emits them as `message_update` events carrying `text_delta` (or `thinking_delta`) payloads; `isStreaming` simply reads `agent.state.isStreaming`. Partial tool output travels the same path via `tool_execution_update`. Long bash output is throttled to one TUI update per 100 ms (`BASH_UPDATE_THROTTLE_MS = 100`).
- **Notable detail:** Streaming is observation-only for extensions: `message_end` handlers may replace the finalized message but must keep the same `role`.

## 3. Conversation state

- **Where:**
  - `docs/session-format.md`
  - `docs/sdk.md`
  - `dist/core/session-manager.js`
  - `dist/core/messages.js`
- **Key symbols:** `SessionManager.buildSessionContext()`, `getBranch()`, `agent.state.messages`, `convertToLlm()`, `context` event
- **How it works:** The durable history is the session tree (leaf-to-root walk via `getBranch()`); `buildSessionContext()` turns that path into the LLM message list, splicing in the compaction summary first when a `CompactionEntry` is on the path and converting branch-summary and extension custom messages to plain messages. `convertToLlm()` maps extended roles (`bashExecution`, `custom`, `branchSummary`, `compactionSummary`) onto provider roles. Before every model call the `context` event hands extensions a deep copy of the messages to filter non-destructively.
- **Notable detail:** Extension `custom` entries are persisted in the session file but never enter LLM context — only `custom_message` entries do; and assigning `agent.state.messages` copies only the top-level array.

## 4. System prompt assembly

- **Where:**
  - `dist/core/system-prompt.js`
  - `docs/usage.md`
  - `docs/extensions.md`
- **Key symbols:** `buildSystemPrompt()`, `formatSkillsForPrompt()`, `before_agent_start` (`systemPrompt` / `systemPromptOptions`), `.pi/SYSTEM.md`, `.pi/APPEND_SYSTEM.md`
- **How it works:** `buildSystemPrompt()` takes `{ customPrompt, selectedTools, toolSnippets, promptGuidelines, appendSystemPrompt, cwd, contextFiles, skills }` and renders an `Available tools` list plus a deduplicated `Guidelines` section whose bullets adapt to the active tools (e.g. "use bash for file ops" only when grep/find/ls are absent). A custom prompt (`--system-prompt`, `SYSTEM.md`) replaces the default body but project context files are still appended inside `<project_context>` as `<project_instructions path="...">` blocks, followed by the skill catalog, date, and cwd. Extensions chain edits per turn through `before_agent_start`, each seeing the previous handler's output.
- **Notable detail:** Current date and working directory are always appended last, and in custom-prompt mode the skills section is included only when the `read` tool is active (skills are useless without it).

## 5. Provider & model abstraction

- **Where:**
  - `docs/providers.md`
  - `docs/models.md`
  - `dist/core/model-registry.js`
  - `dist/core/model-resolver.js`
- **Key symbols:** `ModelRegistry` (`create()`, `inMemory()`, `find()`, `getAvailable()`), `resolveCliModel()`, `parseModelPattern()`, `findInitialModel()`, `buildFallbackModel()`, `thinkingLevelMap`, `compat`
- **How it works:** `ModelRegistry` merges built-in model entries with `~/.pi/agent/models.json` custom providers behind one `Model` interface (`id`, `reasoning`, `input`, `contextWindow`, `maxTokens`, `cost`, `compat`). Four wire APIs are supported (`openai-completions`, `openai-responses`, `anthropic-messages`, `google-generative-ai`), with per-provider/per-model `compat` flags shimming partial OpenAI compatibility. Credential resolution order is CLI `--api-key`, then `auth.json`, then environment variable, then `models.json` keys; model references parse as `provider/id` with an optional `:<thinking>` suffix.
- **Notable detail:** A custom model with no configured auth loads but stays hidden from `/model` and `--list-models`, so keyless local servers (Ollama, LM Studio) need a dummy `apiKey` value to appear.

## 6. Reliability

- **Where:**
  - `docs/settings.md`
  - `docs/json.md`
  - `dist/core/agent-session.js`
  - `dist/core/http-dispatcher.js`
  - `dist/core/settings-manager.js`
  - `dist/core/model-resolver.js`
- **Key symbols:** `retry` settings (`enabled`, `maxRetries`, `baseDelayMs`, `provider.timeoutMs/maxRetries/maxRetryDelayMs`), `_retryAttempt`, `auto_retry_start` / `auto_retry_end`, `DEFAULT_HTTP_IDLE_TIMEOUT_MS`, `configureHttpDispatcher()`, `restoreModelFromSession()`
- **How it works:** Agent-level retry (default on, 3 attempts, exponential backoff from 2 s) re-runs failed turns and emits `auto_retry_start/end` events; the retry counter resets on the first non-error assistant response. Provider/SDK-level retries default to `0` so transient quota errors surface to the agent instead of blocking inside the SDK. HTTP idle timeout defaults to 300 s via `configureHttpDispatcher()`. If a saved session's model is no longer available, `restoreModelFromSession()` falls back and returns a `modelFallbackMessage` warning.
- **Notable detail:** Keep `retry.provider.maxRetries` at `0` (a higher value can stall the agent until provider quota resets), and requests facing a server-asked delay longer than `maxRetryDelayMs` (60 s) fail immediately instead of waiting silently.

## 7. Tool definitions

- **Where:**
  - `docs/extensions.md`
  - `docs/sdk.md`
  - `docs/usage.md`
  - `dist/core/tools/index.js`
  - `dist/core/tools/tool-definition-wrapper.js`
  - `dist/utils/tools-manager.js`
- **Key symbols:** `allToolNames`, `createToolDefinition()`, `createCodingTools()`, `createReadOnlyTools()`, `wrapToolDefinition()`, `defineTool()`, `pi.registerTool()`, `promptSnippet`, `promptGuidelines`
- **How it works:** Seven built-ins exist (`read`, `bash`, `edit`, `write`, `grep`, `find`, `ls`; default allowlist is `read, bash, edit, write`), each a TypeBox `Type.Object` schema (e.g. `bashSchema = { command, timeout? }`) wrapped by `wrapToolDefinition()` into the provider's function-calling format. Custom tools come from `defineTool()` (SDK) or `pi.registerTool()` (extensions, hot-added without reload) and can contribute a one-line `promptSnippet` plus `promptGuidelines` bullets. CLI/SDK scoping uses `tools` allowlists, `excludeTools`, `--no-builtin-tools`, and `--no-tools`.
- **Notable detail:** `promptGuidelines` bullets are appended flat into the shared `Guidelines` section with no tool-name prefix, so each bullet must name its own tool ("Use my_tool when...") — "this tool" is unresolvable by the model.

## 8. Agent loop

- **Where:**
  - `docs/extensions.md`
  - `docs/sdk.md`
  - `dist/core/agent-session.js`
- **Key symbols:** `AgentSession.prompt()`, `steer()`, `followUp()`, `_installAgentToolHooks()` (`beforeToolCall` / `afterToolCall`), `turn_start` / `turn_end`, `agent_start` / `agent_end`
- **How it works:** `prompt()` expands `/skill:` and `/template` references, fires the `input` event, then `before_agent_start`, then hands off to the `Agent` turn loop: model responds, each tool call passes through the `beforeToolCall` extension hook, executes, passes through `afterToolCall`, the result is appended, and the model is called again until a turn ends with no tool calls. Messages queued mid-stream split by urgency: `steer()` runs after the current turn's tool calls finish, `followUp()` waits until the agent is fully idle.
- **Notable detail:** Calling `prompt()` while streaming without `streamingBehavior` throws — but extension slash-commands bypass the queue entirely and execute immediately even mid-stream.

## 9. Parallel tool calls

- **Where:**
  - `docs/extensions.md`
  - `dist/core/tools/file-mutation-queue.js`
  - `dist/core/compaction/compaction.js`
- **Key symbols:** `tool_execution_start` / `tool_execution_update` / `tool_execution_end` ordering, `withFileMutationQueue()`
- **How it works:** In the default parallel mode, sibling tool calls from one assistant message are preflighted sequentially in assistant source order (`tool_execution_start` fires in that order), then executed concurrently with interleaved `tool_execution_update`s; `tool_execution_end` fires in completion order but the final `toolResult` messages are re-emitted in assistant source order. Same-file edits are additionally serialized by a file-mutation queue while operations on different files still run in parallel.
- **Notable detail:** A `tool_call` handler is not guaranteed to see sibling tool results from the same assistant message in `ctx.sessionManager`, because preflight runs before any sibling has finished.

## 10. File tools

- **Where:**
  - `docs/usage.md`
  - `docs/sdk.md`
  - `dist/core/tools/read.js`
  - `dist/core/tools/write.js`
  - `dist/core/tools/edit.js`
  - `dist/core/tools/grep.js`
  - `dist/core/tools/find.js`
  - `dist/core/tools/ls.js`
  - `dist/core/tools/file-mutation-queue.js`
- **Key symbols:** `createReadTool()`, `createWriteTool()`, `createEditTool()`, `createGrepTool()`, `createFindTool()`, `createLsTool()`, `withFileMutationQueue()`, `GREP_MAX_LINE_LENGTH`
- **How it works:** `read` takes `{ path, offset?, limit? }` for paged reads; `write` creates/overwrites, `edit` applies targeted modifications (returning `details.diff` for the TUI and a unified `details.patch` for SDK consumers); `grep`/`find`/`ls` cover search and listing. All mutating file tools run through the file-mutation queue so concurrent same-file operations serialize instead of racing.
- **Notable detail:** Grep match lines are hard-capped at 500 characters (`GREP_MAX_LINE_LENGTH`), so long-line matches arrive pre-truncated.

## 11. Shell execution

- **Where:**
  - `dist/core/tools/bash.js`
  - `dist/core/bash-executor.js`
  - `dist/core/exec.js`
  - `docs/extensions.md`
- **Key symbols:** `createLocalBashOperations()`, `createBashTool()`, `execCommand()`, `OutputAccumulator`, `killProcessTree()`, `waitForChildProcess()`, `user_bash` event
- **How it works:** Commands spawn through the configured shell with piped stdout/stderr streamed chunk-by-chunk into an `OutputAccumulator`; the schema is `{ command, timeout? }` where timeout is optional seconds with no default. Abort (Esc) or timeout kills the entire process tree, and the waiter resolves without hanging on stdio handles inherited by detached descendants. Interactive `!command` sends output to the model while `!!command` marks it `excludeFromContext`; extensions can intercept both via `user_bash` and either wrap the local backend or return a synthetic result.
- **Notable detail:** The `timeout` parameter is in seconds, not milliseconds — and `detached: true` process spawning is only a kill-tree bookkeeping detail, not a background-task feature.

## 12. Permission / approval gate

- **Where:**
  - `docs/usage.md`
  - `docs/extensions.md`
  - `dist/core/agent-session.js`
- **Key symbols:** `beforeToolCall` hook (`_installAgentToolHooks()`), `tool_call` event, `{ block: true, reason }`, `isToolCallEventType()`
- **How it works:** There is no built-in permission popup — this is deliberate (`docs/usage.md`: pi "intentionally does not include ... permission popups"). The gate is the `tool_call` extension event, fired from `AgentSession._installAgentToolHooks()` after `tool_execution_start` and before execution: any handler can return `{ block: true, reason }` to veto the call (the documented example confirms `rm -rf` via `ctx.ui.confirm`), or mutate `event.input` in place to rewrite arguments. Later handlers see earlier mutations.
- **Notable detail:** Mutated tool arguments are not re-validated against the schema, and if a `tool_call` handler itself throws, execution is blocked with "Extension failed, blocking execution".

## 13. Session persistence

- **Where:**
  - `docs/sessions.md`
  - `docs/session-format.md`
  - `dist/core/session-manager.js`
  - `dist/core/session-cwd.js`
- **Key symbols:** `SessionManager.create()`, `.open()`, `.continueRecent()`, `.inMemory()`, `.forkFrom()`, `appendMessage()` / `appendCompaction()` / `appendCustomEntry()` / `appendLabelChange()`, `branch()`, `CURRENT_SESSION_VERSION = 3`
- **How it works:** Sessions auto-save as JSONL under `~/.pi/agent/sessions/--<path>--/<timestamp>_<uuid>.jsonl`, where every entry (except the header) carries an 8-char hex `id` and `parentId` forming a branchable tree with a movable leaf. Files self-declare versions 1–3 and are auto-migrated to v3 on load; resume, fork (`/fork`), clone (`/clone`), in-place tree navigation (`/tree`), and ephemeral `--no-session` mode all build on the same `SessionManager`.
- **Notable detail:** Labels are not fields on entries but separate `label` entries pointing at `targetId` (clear by setting the label to `undefined`), and `SessionManager.inMemory()` gives a fully functional session with no file at all.

## 14. Snapshot & revert

- **Where:**
  - `docs/extensions.md`
- **Key symbols:** NOT FOUND as a built-in — git checkpointing ("stash at each turn, restore on branch") is listed only as an extension example
- **How it works:** The core ships no workspace snapshot, checkpoint, stash, or revert mechanism; no `snapshot`/`revert`/`checkpoint` symbol exists outside output-truncation code. The intended path is an extension that snapshots (e.g. via git) on turn/session events and restores on branch navigation.
- **Notable detail:** `OutputAccumulator.snapshot()` is about truncating long tool output (see operation 17), not workspace state — a re-implementer grepping for "snapshot" will find the wrong thing.

## 15. Token accounting & cost

- **Where:**
  - `docs/session-format.md`
  - `docs/sessions.md`
  - `dist/core/model-registry.js`
  - `dist/core/compaction/compaction.js`
- **Key symbols:** `Usage` (`input`, `output`, `cacheRead`, `cacheWrite`, `totalTokens`, `cost`), per-million `cost` rates on model entries, `calculateContextTokens()`, `getLastAssistantUsage()`, `estimateTokens()`, `ctx.getContextUsage()`
- **How it works:** Every assistant message carries a `Usage` record with input/output plus prompt-cache read/write counts and a four-part cost breakdown, computed from the active model's per-million-token rates (merged from `models.json` overrides). `/session` and the TUI footer surface running tokens and cost; compaction and `getContextUsage()` prefer the last assistant `Usage` and fall back to `estimateTokens()` heuristics for trailing messages.
- **Notable detail:** Cache reads and writes are accounted (and priced) separately from plain input tokens, so prompt-caching discounts show up as `cacheRead` volume rather than reduced input.

## 16. Context overflow & compaction

- **Where:**
  - `docs/compaction.md`
  - `docs/settings.md`
  - `dist/core/compaction/compaction.js`
  - `dist/core/compaction/utils.js`
  - `dist/core/compaction/branch-summarization.js`
  - `dist/core/session-manager.js`
- **Key symbols:** `shouldCompact()`, `prepareCompaction()`, `compact()`, `findCutPoint()`, `findTurnStartIndex()`, `generateSummary()`, `serializeConversation()`, `reserveTokens` (16384), `keepRecentTokens` (20000)
- **How it works:** Auto-compaction triggers when `contextTokens > contextWindow - reserveTokens` (default reserve 16384). `prepareCompaction()` walks backwards to `firstKeptEntryId` keeping ~20000 recent tokens, normally cutting at turn boundaries; `compact()` summarizes everything before the cut with the structured Goal/Constraints/Progress/Decisions/Next-Steps format, appends a `CompactionEntry`, and reloads so the model sees summary plus kept messages. Two recovery paths differ: context-overflow compacts then auto-retries the aborted turn once, while threshold compaction does not retry. Branch switching (`/tree`) reuses the same machinery via `collectEntriesForBranchSummary()` / `generateBranchSummary()`.
- **Notable detail:** A cut is never placed at a tool result (it must stay with its tool call); when one giant turn exceeds the whole keep budget ("split turn"), pi summarizes the turn prefix and history separately and merges them.

## 17. Tool output offloading

- **Where:**
  - `dist/core/tools/truncate.js`
  - `dist/core/tools/output-accumulator.js`
  - `dist/core/tools/bash.js`
  - `dist/core/bash-executor.js`
  - `docs/session-format.md`
- **Key symbols:** `DEFAULT_MAX_LINES` (2000), `DEFAULT_MAX_BYTES` (50 KB), `truncateHead()`, `truncateTail()`, `truncateLine()`, `OutputAccumulator.snapshot({ persistIfTruncated: true })`, `fullOutputPath`, `excludeFromContext`
- **How it works:** Tool output is tail-truncated by default (head-truncation exists for cases where the end matters less): over-limit content is cut to head/tail markers stating how much was dropped, and the accumulator spills the full text to a file referenced by `fullOutputPath` on the result message (`BashExecutionMessage.fullOutputPath`). Serialization for summarization additionally caps tool results at 2000 characters. Interactive `!!` commands set `excludeFromContext` so their output never enters context at all.
- **Notable detail:** The bash executor tolerates twice the normal budget (`DEFAULT_MAX_BYTES * 2` = 100 KB) before truncating, and grep output is line-capped at 500 chars independently of the byte budget.

## 18. Memory files

- **Where:**
  - `docs/usage.md`
  - `dist/core/resource-loader.js`
  - `dist/core/system-prompt.js`
- **Key symbols:** `loadAgentsFiles()` / `agentsFiles` (`{ path, content }`), `AGENTS.md` / `CLAUDE.md` candidates, `<project_context>` / `<project_instructions>`, `SYSTEM.md` / `APPEND_SYSTEM.md`, `--no-context-files`
- **How it works:** At startup the loader collects a global `AGENTS.md`, then walks up from the cwd through ancestor directories collecting `AGENTS.md`/`CLAUDE.md` (including `.MD` case variants). Contents are injected verbatim into the system prompt wrapped as `<project_instructions path="...">` inside `<project_context>`. Full prompt replacement lives in `SYSTEM.md` (project) or global `SYSTEM.md`, while `APPEND_SYSTEM.md` appends without replacing; `--no-context-files` disables all of it.
- **Notable detail:** Context files load regardless of project trust — unlike `.pi/` settings, extensions, skills, and prompts, which stay unloaded until the project is trusted.

## 19. Skills / progressive disclosure

- **Where:**
  - `docs/skills.md`
  - `dist/core/skills.js`
  - `dist/core/system-prompt.js`
- **Key symbols:** `loadSkills()`, `loadSkillsFromDir()`, `formatSkillsForPrompt()`, `SKILL.md` frontmatter (`name`, `description`), `/skill:name`
- **How it works:** At startup pi scans global (`~/.pi/agent/skills/`, `~/.agents/skills/`), project (`.pi/skills/`, `.agents/skills/` up to the repo root, trust-gated), package, settings, and CLI paths for `SKILL.md` directories, following the Agent Skills standard leniently. Only each skill's name and description enter the system prompt (as XML per the spec); the full body loads on demand when the model `read`s the file or the user invokes `/skill:name` (trailing args appended as `User: <args>`).
- **Notable detail:** A skill without a `description` is silently skipped (the one hard failure), name collisions keep the first-found skill with a warning, and unlike the standard, pi does not require the skill name to match its directory.

## 20. Sub-agents / delegation

- **Where:**
  - `docs/usage.md`
  - `docs/sdk.md`
  - `dist/core/sdk.js`
- **Key symbols:** NOT FOUND as a built-in tool — `createAgentSession()` + `SessionManager.inMemory()` is the documented composition primitive
- **How it works:** The core ships no spawn-subagent tool and no child-context API; this is deliberate (`docs/usage.md`: pi "intentionally does not include ... sub-agents"). The SDK lists "custom tools that spawn sub-agents" as a primary use case: an extension registers a tool whose `execute()` creates a child session via `createAgentSession()` (typically `SessionManager.inMemory()` for a clean context), prompts it, and returns the result as tool content.
- **Notable detail:** Because delegation is just nested `createAgentSession()` calls, a child gets none of the parent's history unless the tool author copies messages in — isolation is total by default.

## 21. Planning & todo tracking

- **Where:**
  - `docs/usage.md`
  - `docs/extensions.md`
  - `docs/compaction.md`
- **Key symbols:** NOT FOUND as a built-in — no plan mode, todo list, or task tracker in core; "stateful tools (todo lists, connection pools)" is an extension example
- **How it works:** There is no native plan mode or todo data structure; this is deliberate (`docs/usage.md` groups plan mode and to-dos with the other intentionally omitted features). Planning state survives only incidentally: compaction and branch summaries use a Goal / Constraints / Progress (Done / In Progress / Blocked) / Decisions / Next Steps template, and extensions persist their own todo state via `pi.appendEntry()` custom entries. Slash commands (`/review`, prompt templates) provide fixed workflows instead of dynamic plans.
- **Notable detail:** The structured summary format is the closest thing to a native plan artifact — but it is a lossy narrative regenerated by the model, not a machine-checked task list, so completion state can drift.

## 22. MCP / dynamic external tools

- **Where:**
  - `docs/usage.md`
  - `docs/extensions.md`
  - `docs/models.md`
- **Key symbols:** NOT FOUND as a built-in — no MCP client, MCP transport, or MCP tool mapping anywhere in core or docs
- **How it works:** There is deliberately no built-in MCP support (`docs/usage.md` names it among the omitted features). Dynamic external capability arrives through two other doors: async extension factories that fetch remote configuration at startup and call `pi.registerProvider()` / `pi.registerTool()` (the documented local-model example), and `models.json` custom providers that point any supported API at an external server. An MCP bridge would itself be an extension using `registerTool()`.
- **Notable detail:** Extension-registered tools appear immediately in `pi.getAllTools()` with no `/reload` needed, so a hypothetical MCP extension could add/remove remote tools live mid-session.

## 23. Hooks, plugins & events

- **Where:**
  - `docs/extensions.md`
  - `dist/core/event-bus.js`
  - `dist/core/agent-session.js`
  - `dist/core/extensions/`
- **Key symbols:** `createEventBus()`, `pi.on()`, `pi.registerTool()`, `pi.registerCommand()`, `pi.setActiveTools()`, `ExtensionContext` (`ctx.ui`, `ctx.sessionManager`, `ctx.signal`, `ctx.compact()`), `session_before_compact` / `session_before_tree` / `tool_call` / `tool_result` / `context` / `before_provider_request` / `after_provider_response`
- **How it works:** Extensions are TypeScript modules (loaded via jiti, no compilation) auto-discovered from `~/.pi/agent/extensions/` and trust-gated `.pi/extensions/`. They subscribe to a ~30-event lifecycle: `input` → `before_agent_start` → `agent_start` → per-turn `turn_start`, `context`, `before_provider_request`, `after_provider_response`, `tool_execution_*`, `tool_call` (veto/mutate), `tool_result` (patch chaining) → `turn_end` → `agent_end`, plus cancellable session events (`session_before_switch/fork/compact/tree`) and model/thinking selectors. Cross-extension messaging goes through the shared `eventBus`.
- **Notable detail:** `tool_result` handlers chain like middleware (each sees the previous handler's edits and may return partial `{ content, details, isError }` patches), while `tool_call` handlers can only veto via `{ block: true }` — argument changes must be done by mutating `event.input` in place.

## 24. Background & concurrency

- **Where:**
  - `docs/usage.md`
  - `docs/sdk.md`
  - `docs/rpc.md`
  - `dist/core/agent-session.js`
  - `dist/core/agent-session-runtime.js`
  - `dist/modes/`
- **Key symbols:** `steer()` / `followUp()` queues, `queue_update`, `AgentSessionRuntime` (`newSession()`, `switchSession()`, `fork()`), run modes (`InteractiveMode`, `runPrintMode`, `runRpcMode`), `session_shutdown`
- **How it works:** There is no built-in background-bash or detached-task primitive (deliberately omitted per `docs/usage.md`; the `detached` flag in `tools/bash.js` is only process-tree bookkeeping). Concurrency is cooperative: steering and follow-up messages queue while the agent works (`queue_update` events expose both queues), Esc aborts and restores queued text to the editor, and `AgentSessionRuntime` swaps whole sessions (new/resume/fork/clone/import) with `session_shutdown` → `session_start` teardown semantics. Headless parallelism comes from separate processes via print, JSON-event, or RPC modes (`dist/modes/`).
- **Notable detail:** Event subscriptions attach to one specific `AgentSession`, so after any runtime replacement the host must re-subscribe — and extensions must never start background resources (timers, watchers, sockets) in the factory itself, only from `session_start` with cleanup in `session_shutdown`.
