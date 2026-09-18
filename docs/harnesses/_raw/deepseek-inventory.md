# DeepSeek Harness — harness operation inventory

Project root: `/Users/sergii/git/harness/.analysis/deepseek-src`, version `0.1.6-alpha.2`, commit `ddefc45`.
The product is a set of small plugins on the Cordis plugin framework. Cordis is the vendored plugin system underneath: plugins contribute services, typed events, and reversible registrations to a shared context.

## 1. Pure LLM call

- **Where:** `packages/llm/llm/src/index.ts`
  `packages/llm/llm/src/types.ts`
  `packages/llm/llm/src/call-config.ts`
- **Key symbols:** `LlmRuntime`, `LlmRuntime.prepareCall`, `PreparedLlmCall`, `PreparedAdapterCall`, `GenerateOptions`
- **How it works:** A caller builds provider-neutral `GenerateOptions` with provider, model, messages, tools, and controls. LLM means large language model, the AI model that writes the answers. `LlmRuntime.prepareCall` looks up the adapter registration for that provider route and binds one adapter generation. It resolves call defaults with model info and deep-freezes the config. The returned `PreparedLlmCall.stream` is one-shot: it rejects reuse or config mismatch, then dispatches through the captured registration plus the `llm/stream` waterfall event.
- **Notable detail:** Prepared dispatch is single-use and bound to one generation, so settings changed between prepare and dispatch cannot mix one generation's capabilities with another endpoint.

## 2. Streaming

- **Where:** `packages/llm/llm/src/types.ts`
  `packages/llm/llm/src/assembler.ts`
  `packages/llm/llm/src/assistant-stream.ts`
  `packages/llm/llm/src/index.ts`
- **Key symbols:** `StreamChunk`, `LlmAdapter.stream`, `BlockAssembler.push`, `assembleAssistantStream`, `TimedStreamChunk`
- **How it works:** Every adapter implements `stream`, which returns an async stream of `StreamChunk` frames: block starts, text deltas, reasoning deltas, tool-call deltas, block ends, usage, and finish. An index ties interleaved deltas to one block. Each block end carries the fully assembled content block so consumers do not reassemble it themselves. `BlockAssembler.push` folds chunks in order into partial blocks and records usage and the terminal finish. `LlmRuntime` wraps dispatch in the `llm/stream` waterfall so retry, replay, and routing plugins can observe or short-circuit, then turns adapter throws into terminal error or aborted finishes.
- **Notable detail:** Adapters must send usage before the terminal finish and nothing after it. Deltas for an index already closed by a block end are ignored as malformed.

## 3. Conversation state

- **Where:** `packages/core/session/src/index.ts`
  `packages/core/session/src/surface.ts`
  `packages/core/session/src/types.ts`
  `packages/session/session-projection/src/index.ts`
- **Key symbols:** `Session`, `SessionEventMap`, `SurfaceManager`, `foldSurface`, `Session.deriveMessages`, `deriveEventMessage`
- **How it works:** The conversation is an append-only log of typed session events, which is the single source of truth. Model history is never stored separately. It is derived by walking only events that carry a surface marker. An append marker adds to the tail. A replace marker shadows an old range with one new node. `deriveMessages` caches this fold and rebuilds only on replacement.
- **Notable detail:** `request/header` and `request/context` are log-only events. The latest header rebuilds the next request envelope through `foldRequestHeader`.

## 4. System prompt assembly

- **Where:** `packages/core/system-prompt/src/index.ts`
  `packages/context/agent-instructions/src/index.ts`
  `packages/context/time-context/src/index.ts`
  `packages/context/file-reference/src/index.ts`
- **Key symbols:** `SystemPrompt`, `PromptSection`, `PromptContext`, `PromptAssembly`, `assemble`, `renderPrompt`, `system-prompt/assemble`
- **How it works:** Each plugin registers small named pieces: prompt sections, dynamic context snippets, tool-schema providers, and template variables. Both global and per-agent scoped registrations exist, and scoped ones hide globals with the same name. Before each model step the agent loop calls `assemble`, which resolves all text providers and sorts sections by a central numeric order then by name. Tool ordering and restrictions are applied, then the `system-prompt/assemble` waterfall event lets further plugins edit the result. The loop renders the sections and stores the text as a system message log node.
- **Notable detail:** A central order table fixes positions from `HARNESS_IDENTITY` at -1000 up to the deployment persona suffix at 10200. A section marked complete forces the whole prompt to that one section after the waterfall still runs.

## 5. Provider & model abstraction

- **Where:** `packages/llm/llm/src/index.ts`
  `packages/llm/llm-deepseek/src/adapter.ts`
  `packages/llm/llm-deepseek/src/index.ts`
  `packages/llm/deepseek-llm-api-extensions/src/index.ts`
- **Key symbols:** `LlmAdapter`, `LlmRuntime.registerAdapter`, `DeepSeekAdapter`, `ChatCompletionsAdapter`, `DeepSeekMessagesAdapter`, `DeepSeekLlmApiExtensionRegistry`, `resolveModel`, `listModels`
- **How it works:** `LlmAdapter` is the abstract provider contract. Only `stream` is required and the rest has defaults. `LlmRuntime` holds adapters in a map keyed by provider-route string. `registerAdapter` commits routes all-or-nothing and rejects duplicates, returning a disposer with an atomic replace. `DeepSeekAdapter` picks `DeepSeekMessagesAdapter` or `ChatCompletionsAdapter` from the validated connection protocol. Top-level DeepSeek request fields are separately extensible: plugins register a field on `DeepSeekLlmApiExtensionRegistry`, whose prepare step merges frozen fields plus a joint accept commit after a successful HTTP (web request) response.
- **Notable detail:** `listModels` is advisory only: consumers must not reject unlisted model ids, and `resolveModel` is the exact-model query. Retry policy is captured at registration, so policy changes require a registration replace.

## 6. Reliability

- **Where:** `packages/llm/llm/src/retry-policy.ts`
  `packages/llm/llm/src/error.ts`
  `packages/llm/llm-retry/src/index.ts`
  `packages/llm/llm-retry/src/history.ts`
- **Key symbols:** `resolveRetryPolicy`, `RetryPolicyConfig`, `normalizeLlmFailure`, `LlmError`, `LlmFailure`, `backoff`, `cancellableDelay`, `idleWatchdog`
- **How it works:** Each provider route owns a retry policy resolved by `resolveRetryPolicy`. Normal mode retries only listed retryable codes, while always mode retries every failure. The `dsh-llm-retry` plugin (`@deepseek-ai/dsh-llm-retry`) runs the policy on the `agent/request-error` extension point. It logs a durable retry event before a cancellable wait so retries survive replay. Backoff is exponential with a cap and symmetric jitter. Transport safety comes from timeout helpers: a per-read idle watchdog maps idle streams to a timeout failure, and a deadline helper bounds file API calls.
- **Notable detail:** Defaults are 5 max retries, 500 ms initial delay, 10 s max delay, 0.1 jitter ratio, retryable empty response, rate limit, server, timeout, and transport errors. No cross-provider fallback was found: retries stay on the same provider route.

## 7. Tool definitions

- **Where:** `packages/core/tools/src/index.ts`
  `packages/core/tools/src/schema.ts`
  `packages/core/agent-tool-presentation/src/index.ts`
- **Key symbols:** `ToolDefinition`, `defineTool`, `ToolRuntime`, `ToolOutputDefinition`, `ToolRestriction`, `presentCall`, `presentResult`
- **How it works:** Authors declare a tool with `defineTool`, giving name, description, parameters, output schema, and an execute body. One schema language covers both inputs and outputs. The registry (`ToolRuntime` on `ctx.tools`) checks the definition and shows only name, description, and parameters to the model: timeouts, concurrency flags, and UI (user interface) functions never go on the wire. One call runs in order: parse args once, `tools/pre-execute` for allow or deny, guards, `tools/execute` wrappers for timeout and retry, the execute body, `tools/post-execute`, content finalizing, and a `tools/result` notification. Failures use typed errors for bad args and bad output.
- **Notable detail:** A provider result carries both schemas and known names so assembly can tell a config typo apart from a deliberately hidden tool. PTC (Program-Tool-Call) mode collapses all direct calls to one reserved `run_code` transport, with sub-calls re-entering the same pipeline.

## 8. Agent loop

- **Where:** `packages/core/agent-loop/src/agent.ts`
  `packages/core/agent-loop/src/runtime-context.ts`
  `packages/core/agent/src/index.ts`
- **Key symbols:** `ReactLoopAgent`, `Agent`, `assembleContextFor`, `executeToolCalls`, `InboxTarget`, `turnBoundary`
- **How it works:** A step is one model request plus the tools it calls, and a turn is zero or more steps. The loop drives one session through turns and steps. Each step assembles the prompt for the owning agent, prepares the model request from log history, streams the assistant reply, then schedules any requested tool calls. Tool results and extra context are committed in model order before the next step. Inbox targets control timing: next-turn versus next-step injection, plus steering, wake, cancel, and maintenance modes. The loop also owns agent creation, scoped registration, and ordered teardown.
- **Notable detail:** The first admitted step reserves the system head before user messages even for an empty prompt, so the prompt travels only as system message history.

## 9. Parallel tool calls

- **Where:** `packages/core/agent-loop/src/tool-calls.ts`
  `packages/core/agent-loop/src/constants.ts`
  `packages/core/tools/src/index.ts`
- **Key symbols:** `ToolRuntime.executionMode`, `isConcurrencySafe`, `executeToolCalls`, `runGroup`, `DEFAULT_MAX_PARALLEL_TOOL_CALLS`
- **How it works:** Only an exact true from a tool's `isConcurrencySafe` check makes a call parallel. Missing tools, hidden tools, exceptions, or any other value mean exclusive, which is the safe default when unsure. The scheduler walks the model's call list in order. An exclusive call is a barrier run alone, while parallel calls form a group run in a bounded rolling pool capped by `maxParallelToolCalls`. Later calls are re-classified just before start, so a call that turns exclusive waits for the pool to drain. Dispatch may overlap, but results and log events commit in original model order.
- **Notable detail:** Only `read` and `read_image` declare themselves concurrency-safe. Write, edit, bash, glob, and grep stay exclusive by default. The default cap is 10 parallel tool calls.

## 10. File tools

- **Where:** `packages/fs/fs/src/index.ts`
  `packages/fs/fs-local/src/index.ts`
  `packages/fs/tool-fs/src/index.ts`
  `packages/fs/tool-fs-search/src/index.ts`
  `packages/fs/tool-str-replace-editor/src/index.ts`
  `packages/fs/fs-observation-policy/src/index.ts`
- **Key symbols:** `FileSystem`, `writeText`, `editText`, `fs/write-intent`, `fs/edit-intent`, `fs/observed`, `RipgrepRun`
- **How it works:** `ctx.fs` is the filesystem seam, an abstract swappable service, and `fs-local` is the local-disk backend. The `tool-fs` package owns only schemas, validation, read windows, and log events. Reads support line windows plus byte and line-length caps and stream large files. Every read logs an observed event recording file presence or absence. Writes and edits pass through single-slot intent guards, and the optional observation-policy plugin enforces read-before-write using per-session observed state. Search tools do not use `ctx.fs` or the shell at all: they spawn the bundled ripgrep binary through `ctx.subprocess` with fixed argument templates.
- **Notable detail:** Over-cap glob sampling is an explicit deployment choice with a required config and no default. The string replace editor requires an exact unique match of the old text.

## 11. Shell execution

- **Where:** `packages/shell/shell/src/index.ts`
  `packages/shell/tool-bash/src/index.ts`
  `packages/shell/tool-bash-persistent/src/index.ts`
  `packages/shell/bash-local/src/index.ts`
  `packages/shell/bash-sandbox/src/index.ts`
  `packages/subprocess/subprocess/src/index.ts`
  `packages/sandbox/sandbox/src/index.ts`
  `packages/sandbox/sandbox-policy/src/index.ts`
- **Key symbols:** `ShellExecutor`, `ShellExecRequest`, `ShellRunResult`, `ShellProcess`, `SubprocessRuntime`, `SandboxBashExecutor`, `scrubbedParentEnv`
- **How it works:** The `bash` tool is a thin consumer of the `ctx.shell` seam. Each foreground call runs a fresh shell with no state kept between calls, and callers pass a working directory instead of changing directory. Resolve fills defaults and caps, run handles foreground execution with timeout kill, and start publishes a background handle registered with the jobs service. The local executor spawns through `ctx.subprocess` with a scrubbed environment plus model-friendly overrides. The sandbox executor wraps the same argument list through the sandbox service and reports mode and enforcement facts.
- **Notable detail:** The child environment strips credential-shaped names and all harness-owned names, then merges back only explicit entries. The persistent bash variant serializes per-owner commands and requires an owning agent.

## 12. Permission / approval gate

- **Where:** `packages/interaction/user-approval/src/index.ts`
  `packages/interaction/user-approval/src/types.ts`
  `packages/interaction/permission-presets/src/index.ts`
  `packages/interaction/tool-ask-user/src/index.ts`
  `packages/guard/timeout-policy/src/index.ts`
  `packages/client/ui-approval/src/index.ts`
- **Key symbols:** `ApprovalService`, `ApprovalPolicy`, `ApprovalOutcome`, `setApprovalPolicy`, `PermissionPresetService`, `ask_user_question`
- **How it works:** The approval service on `ctx.approval` is the single gate for whether an action may proceed. A caller requests approval with agent, tool name, call id, and reason. Policy never auto-rejects without asking, while policy ask runs a waterfall chain of answerers where the first answer wins. Every ask writes a log-only audit pair of asked plus decided events inside an open turn, and only an allowed-once grant permits that one action. Callers fail closed on rejected, cancelled, or unavailable outcomes. Presets bundle two independent knobs, sandbox mode and approval policy, into named choices such as workspace-write and full access.
- **Notable detail:** Fail-closed normalization turns a missing, throwing, or off-vocabulary answerer into unavailable. The request omits tool args and links through the call id to avoid drift.

## 13. Session persistence

- **Where:** `packages/session/session-persistence/src/storage-contract.ts`
  `packages/session/session-persistence/src/handle.ts`
  `packages/session/session-persistence-jsonl/src/storage.ts`
  `packages/session/session-checkpoint-policy/src/index.ts`
- **Key symbols:** `SessionPersistence`, `SessionHandle`, `JsonlSessionHandle`, `validateStoredEvents`, `assertContiguous`, `materializeAppendBatch`
- **How it works:** Storage is reached only through one open handle per session. A write handle is the single mutator and a read handle only observes. Live session events buffer in a bounded write-behind window, 200 ms max delay in the JSONL (JSON lines, one JSON object per line) backend, and drain as append batches. Only flush promises crash durability. Crash recovery does not truncate: it returns the valid contiguous prefix and the reader appends closers for the interrupted tail, covering missing tool errors, open step ends, and a synthetic interrupted turn end.
- **Notable detail:** Semantic checkpoints live in the checkpoint-policy package: the stream event flushes before adapter dispatch, the execute event flushes top-level calls, and the pre-step event flushes the prior step. Failures are fail-closed.

## 14. Snapshot & revert

- **Where:** `packages/core/session/src/index.ts`
  `packages/session/session-format/src/chain.ts`
  `packages/deliverables/workspace-changes/src/index.ts`
- **Key symbols:** `Session.snapshotEvents`, `snapshotSessionEvent`, `Session.fork`, `SessionForkError`, `session/end-seed`, `workspace/changes`
- **How it works:** A snapshot is a frozen copy of an event range through `snapshotEvents`. Resume replays the full stored log as seed. Fork copies a prefix through a boundary into a child seed with an exact inherited event count and a tagged end-seed marker. Workspace file changes are snapshotted separately with working-tree snapshots at turn start and end plus whole-file captures around file-tool edits, announced by a workspace changes event.
- **Notable detail:** No revert verb or symbol was found. The closest durable primitives are fork with a boundary and resume with repair.

## 15. Token accounting & cost

- **Where:** `packages/llm/token-meter/src/index.ts`
  `packages/llm/token-meter/src/types.ts`
  `packages/llm/token-meter/src/estimate.ts`
- **Key symbols:** `TokenMeter.measure`, `TokenMeasurement`, `TokenSurfaceNode`, `TokenUsage`, `estimateMessage`, `priceSurface`
- **How it works:** `TokenMeter` replays the durable session tail and exposes `measure`, which returns a detached immutable measurement with log revision, baseline, surface delta, and totals. The effective header's routed provider and model select image pricing through the model service. Retained images cost visual tokens plus model-visible text, while other routes keep a fixed heuristic of 4 chars per token with small per-block and per-role overhead. Provider usage counts are disjoint: uncached input plus cache read, cache write, and output. A provider usage baseline is reused only when the anchor header matches canonically and its total covers the full priced anchor, else an estimated repricing is used.
- **Notable detail:** No monetary cost field exists: accounting is token pressure only. Total tokens equal baseline plus surface delta, floored at zero. Cost hits in source are prose only.

## 16. Context overflow & compaction

- **Where:** `packages/compaction/compaction/src/index.ts`
  `packages/compaction/compaction-basic/src/region.ts`
  `packages/compaction/compaction-tool-result-pruner/src/index.ts`
  `packages/compaction/command-compact/src/index.ts`
- **Key symbols:** `CompactionEngine`, `BasicCompactionEngine`, `CompactionTrigger`, `compactIfNeeded`, `compactNow`, `compactRegion`, `selectCompactableRange`, `ToolResultPruner.pruneSession`
- **How it works:** Automatic work hooks the pre-step event for pressure using the token meter, and the request-error event for the canonical context overflow code. Selection keeps a priced recent tail, never splits an assistant tool-call and result pair, and skips surface node zero when it is a system prompt. A run appends a compaction start event, summarizes with the model, appends a compaction summary with shadow pricing, then replaces the range with one user message carrying a replace marker. The manual compact command calls `compactNow` while the agent is idle. Optional tool-result pruning runs before summary selection.
- **Notable detail:** Shadow-price protocol: a replace must sit directly after its metering event so plain consumers can subtract cost without per-node state. Recovery runs inside the open step and retries only when pruning or summarization advances the replacement generation.

## 17. Tool output offloading

- **Where:** `packages/spill/spill/src/index.ts`
  `packages/spill/spill-policy/src/index.ts`
  `packages/spill/spill-local/src/store.ts`
  `packages/util/output-retention/src/index.ts`
- **Key symbols:** `SpillStore.saveText`, `SpillRef`, `SpillLocator`, `TextRetainer`, `ItemRetainer`, `offloadOldestImages`, `PRUNE_MARKER`
- **How it works:** Two separate paths bound oversized outputs. Spill policy listens on the post-execute event: plain-text results over the inline byte cap are saved verbatim to a session-scoped private file, then replaced in-model with a bounded head and tail preview plus a retrieval notice that still fits the cap. Image offload appends a durable offload decision naming the oldest retained image occurrences, and later requests send placeholder text instead. The retainer library is only the mechanical bounding helper with exact omission counts.
- **Notable detail:** Best effort: with no session owner, no spill backend, or a save failure, the inline result is kept and success never turns into an error. The read tool is skipped by the model-facing arm to avoid a spill loop.

## 18. Memory files

- **Where:** `packages/context/agent-instructions/src/index.ts`
  `packages/context/agent-instructions/src/config.ts`
- **Key symbols:** `loadBaselineInstructionSet`, `discoverBaselineInstructionFiles`, `findProjectRoot`, `renderAgentInstructions`, `reconcileInstructionContext`
- **How it works:** This is the AGENTS.md style memory loader. Before the first request it walks up from the session folder using version-control markers to find the project root, then loads ordered candidates plus local overlays plus the user-global file. Files are read through the filesystem service with per-file byte caps and a total budget, duplicates are collapsed, then the set is rendered once into durable conversation context. After that, successful read, write, and edit tool uses touch nested or changed instruction files into the inbox for reconciliation. An identity string covers root, markers, budgets, and candidate lists so resume can detect a changed baseline.
- **Notable detail:** Default candidates are `AGENTS.md` and `CLAUDE.md` with local overlays `AGENTS.local.md` and `CLAUDE.local.md` and `.git` as the project root marker. No separate vector or long-term memory store was found in these paths.

## 19. Skills / progressive disclosure

- **Where:** `packages/skill/skill/src/index.ts`
  `packages/skill/tool-skill/src/index.ts`
  `packages/skill/skill-filesystem/src/index.ts`
- **Key symbols:** `SkillProvider`, `SkillCandidate`, `SkillSummary`, `SkillDefinition`, `renderSkillContent`, `FileSystemSkillProvider`
- **How it works:** Skills are local instruction packs that stay unloaded until needed. The skill package is only a merging registry, while providers such as the filesystem provider discover directory-bundle or flat Markdown (a lightweight text format) skills with YAML (a human-readable config header) frontmatter from project, custom, user, and bundled roots. The tool package publishes a durable session catalog of names plus descriptions and one model tool to load a single full body on demand. That is progressive disclosure: a short list first, full text only when needed. A user typing a slash name for a user-invocable skill injects the same canonical skill content block as instructions context.
- **Notable detail:** Lower rank wins duplicate names across roots, from project files at 100 up to bundled skills at 600. Names must match lowercase alphanumeric words joined by single dashes.

## 20. Sub-agents / delegation

- **Where:** `packages/subagent/subagent/src/index.ts`
  `packages/subagent/tool-subagent/src/index.ts`
  `packages/subagent/subagent-spawn-in-process/src/index.ts`
  `packages/subagent/subagent-claude-code/src/index.ts`
  `packages/experimental/agent-team/src/index.ts`
- **Key symbols:** `SubagentRuntime`, `SubagentProvider`, `SpawnInProcessProvider`, `ClaudeCodeProvider`, `TeamService`, `startContinuable`
- **How it works:** `ctx.subagents` is a named-provider registry behind one interface. Same-process providers such as spawn run each child as a fresh child agent on the same Cordis context with its own session and system prompt and zero parent conversation. Out-of-process providers such as the Claude Code bridge invoke the official agent SDK (software development kit) CLI (command-line tool) in the parent workspace through the subprocess service. The model-facing subagent tool selects one configured provider. Foreground calls dispose after collection, while background calls own a job or a continuable child id. Agent Teams is a separate lead-plus-teammates layer with roster, mailbox, task board, and journal over the lead session log.
- **Notable detail:** Spawn and Claude Code providers do not inherit parent context. Default delegation depth is 1. The subagent tool preflights the child model route and model selection.

## 21. Planning & todo tracking

- **Where:** `packages/plan/plan-mode/src/index.ts`
  `packages/todo/tool-todo/src/index.ts`
  `packages/goal/goal/src/index.ts`
  `packages/goal/goal-round-driver/src/index.ts`
  `packages/workflow/workflow/src/index.ts`
  `packages/workflow/tool-ralph/src/index.ts`
- **Key symbols:** `PlanModeController`, `EXIT_PLAN_MODE`, `todo_write`, `GoalService`, `renderGoalRoundPrompt`, `WorkflowEngine`, `RALPH_SCRIPT`
- **How it works:** Plan mode is logged per-agent collaboration state. While active a deployment-owned guidance section is added and the exit tool presents the full plan for user approve or keep-planning review. Todos are whole-list replacement: each write call appends a snapshot, replay is last-write-wins, and the list clears on the next turn start. Goals are same-session event-sourced objectives with compare-and-set mutations, phases for active, paused, blocked, and complete, and round caps, where the round driver auto-queues one followup prompt per round at quiescence. Workflows run orchestration scripts that fan out to subagent children. Ralph is a fixed foreground loop that starts one fresh structured-output child per round with only the immutable objective plus a bounded prior handoff.
- **Notable detail:** The exit tool stays registered while inactive so the tool catalog is stable. Todo config switches single versus multi in-progress discipline. Ralph defaults to 256 max rounds with 16384 chars each for handoff and result.

## 22. MCP / dynamic external tools

- **Where:** `packages/mcp/mcp-client/src/index.ts`
  `packages/mcp/mcp-client/src/connection.ts`
  `packages/mcp/mcp-resources/src/index.ts`
- **Key symbols:** `StdioConfig`, `StreamableHttpConfig`, `startConnection`, `registerServerContext`, `McpResourceRuntime`, `publicToolName`
- **How it works:** MCP means Model Context Protocol, a standard for external tools and resources. Each client plugin instance connects to one external MCP (Model Context Protocol) server over a spawned stdio child process or streamable HTTP (web transport), then registers that server's tools on the tool registry under server-qualified names of the form server plus raw name. Lifecycle is effect-scoped: disposal disconnects, unregisters tools, and releases the server name reservation, and live code swap disposes and recreates the connection. Resources are separate: the resource runtime keeps scoped per-server providers and exposes three shared model tools for listing and reading plus a system-prompt section listing live server names.
- **Notable detail:** Server names allow up to 32 letters, digits, dashes, and underscores, and a duplicate name in the same scope throws. Tool call timeout defaults to 60 s and startup errors do not fail by default, with a backoff reconnect policy.

## 23. Hooks, plugins & events

- **Where:** `packages/hooks/hook-protocol/src/index.ts`
  `packages/hooks/hook-protocol/src/runner.ts`
  `packages/hooks/hooks-claude-code/src/index.ts`
  `packages/boot/plugin-manager/src/index.ts`
  `packages/extensions/cordis-host-runner/src/index.ts`
  `packages/extensions/tool-cordis/src/index.ts`
- **Key symbols:** `runHook`, `parseHookOutput`, `matchesMatcher`, `mergeHookOutputs`, `PluginManager`, `DynamicCordisRunnerService`
- **How it works:** The hook protocol is a shared non-plugin library for matching, shell execution, output decoding, restrictive merging, and detached quiescence. The Claude Code bridge mounts unmodified Claude Code command hooks onto harness points such as session start, pre and post tool use, stop, and subagent start and stop. It reads the hooks config once, runs each matched command with a JSON (JavaScript Object Notation) payload on stdin, logs invoked and result events, and folds decisions. The plugin manager handles current-profile composition and bundles through the package manager with file locks and protected modules. The Cordis host runner defines dynamic Cordis plugins from host or client source strings and sandboxes host code in a VM (virtual machine) with precheck plus human-approved client activation.
- **Notable detail:** Updated input and system messages returned from Claude hooks are logged or warned but not honored. The dynamic runner VM (virtual machine) timeout defaults to 5 s.

## 24. Background & concurrency

- **Where:** `packages/jobs/jobs/src/index.ts`
  `packages/jobs/jobs-local/src/index.ts`
  `packages/jobs/tool-jobs/src/index.ts`
  `packages/schedule/schedule/src/index.ts`
  `packages/terminal/terminal/src/index.ts`
- **Key symbols:** `JobRegistry`, `LocalJobRegistry`, `JobId`, `JobStatus`, `ScheduleRuntime`, `TerminalSessionService`, `job_output`, `job_list`, `job_kill`
- **How it works:** Jobs separate contract from storage: the jobs package owns the abstract seam with session-id fenced access and first-wins settlement, while jobs-local is the in-memory process-local registry with per-owner concurrency caps and owner cleanup. The tool package attaches the controller that lets producers start work plus three model tools to list, read with bounded waits, and kill. Unreported completions are injected into a busy owner's next step or wake an idle owner. Schedule is agent-scoped durable one-shot and fixed-rate reminders over the session log, driven only for root agents. Terminal is an owner-scoped persistent PTY (pseudo-terminal, an interactive shell session) registry where backends own mechanics and the service owns ids, publication, authorization, and awaited cleanup.
- **Notable detail:** Max 10 concurrent jobs per owner by default. Tool waits default to 30 s with a 600 s cap and at most 3 consecutive wakes. A background subagent one-shot settles through jobs.
