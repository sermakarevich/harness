# opencode — harness operation inventory

Source: a local clone of `sst/opencode`, commit `e03db9b`.
Only `packages/opencode/src/` was examined; nothing outside it is cited below.

## 1. Pure LLM call

- **Where:** `packages/opencode/src/session/llm.ts`
  `packages/opencode/src/session/llm/request.ts`
  `packages/opencode/src/session/llm/native-request.ts`
- **Key symbols:** `LLM.Service`, `LLM.use`, `StreamInput` / `StreamRequest`, `run("LLM.run")`, `LLMRequestPrep.prepare`, `LLMNative.request` / `LLMNative.model`, `streamText`, `wrapLanguageModel`
- **How it works:** There is no one-request-one-text helper without tools; every call goes through `LLM.Service.stream`. `run()` resolves the provider client, auth, and config concurrently, then calls `LLMRequestPrep.prepare()` to build system text, messages, tools, and parameters. It then branches on a native gate: by default it calls AI SDK (Artificial Intelligence Software Development Kit, the library used to call models) `streamText()` with a `wrapLanguageModel` middleware that rewrites prompts per provider, passing temperature, token limits, tools, headers, and abort signal through. `native-request.ts` is the alternate path that lowers the request to a canonical `LLM.request()` with system parts and generation settings.
- **Notable detail:** SDK-level retry is forcibly disabled (`maxRetries` defaults to 0) because retry lives higher up in `processor.ts`; tools are never sent as an empty list — some providers force `strict: false` on all tools, and one compatibility path injects a `_noop` tool when replaying prior tool calls with zero tools enabled.

## 2. Streaming

- **Where:** `packages/opencode/src/session/llm/ai-sdk.ts`
  `packages/opencode/src/session/llm/native-runtime.ts`
  `packages/opencode/src/session/llm.ts`
  `packages/opencode/src/session/processor.ts`
- **Key symbols:** `LLMAISDK.adapterState`, `LLMAISDK.toLLMEvents`, `LLMNativeRuntime.stream`, `LLM.Interface.stream`, `SessionProcessor.process`, `handleEvent`, `updatePart` / `updatePartDelta`
- **How it works:** `llm.ts:stream()` creates one `AbortController` (an abort signal source used to cancel the request) per stream, calls `run()`, and converges both runtimes to a single `Stream<LLMEvent>` (a stream of typed events such as text deltas and tool calls). The AI SDK path converts the SDK's `fullStream` into those events; the native path merges model events with tool-dispatch results through a queue. `processor.ts:process()` consumes the event stream and its `handleEvent` switches on text, reasoning, tool-call, tool-result, and step events, writing incremental part updates as tokens arrive.
- **Notable detail:** The adapter state must be reset on the `finish` event or counters and block IDs leak into the follow-up stream; orphan text deltas with no preceding start event are silently dropped.

## 3. Conversation state

- **Where:** `packages/opencode/src/session/message-v2.ts`
  `packages/opencode/src/session/session.ts`
  `packages/opencode/src/storage/storage.ts`
- **Key symbols:** `MessageV2.toModelMessagesEffect`, `MessageV2.toModelMessages`, `MessageV2.page` / `stream` / `parts` / `get`, `MessageV2.filterCompacted`, `MessageV2.cursor`, `Session.Service`, `MessageTable` / `PartTable`
- **How it works:** History is a durable SQLite database (DB, a local file database) accessed with Drizzle (a TypeScript database toolkit): `MessageTable` plus `PartTable`, joined by message id. `page()` does cursor-paginated fetches (newest first, then reversed) and `stream()` loops pages to rebuild full messages with parts. Before every model turn, `toModelMessagesEffect()` converts stored messages to model messages, with per-model handling of images inside tool results and truncation, while `filterCompacted()` hides superseded ranges. Prompt assembly reloads this projected history on each turn.
- **Notable detail:** Some model APIs only accept strings in tool results, so image attachments are extracted and re-injected as synthetic user messages — but only when that model advertises image input; otherwise it becomes a user-visible error instead of silently dropping the image.

## 4. System prompt assembly

- **Where:** `packages/opencode/src/session/system.ts`
  `packages/opencode/src/session/prompt.ts`
  `packages/opencode/src/session/prompt/default.txt`
- **Key symbols:** `SystemPrompt.provider`, `SystemPrompt.Service.environment` / `skills` / `mcp`, `instruction.system()`, `LLMRequestPrep.prepare`
- **How it works:** `SystemPrompt.provider()` picks a static template from `session/prompt/*.txt` by matching the model id (Claude variants, GPT variants, Gemini, and others each get their own file, with `default.txt` as fallback). Each turn combines the environment block (model and provider ids, working directory, whether version control is git, platform, date, project references), loaded instruction files, MCP (Model Context Protocol, a standard for connecting external tool servers) additions, and skill listings with the message history. A final prepare step joins the agent prompt, template, and extra system input, and fires plugin hooks that can transform the result.
- **Notable detail:** Some OAuth (Open Authorization, a login-token standard) and workflow models bypass `role: system` messages entirely; plugin-appended system entries beyond the first two are collapsed into one joined block, so their ordering as separate messages is not preserved.

## 5. Provider & model abstraction

- **Where:** `packages/opencode/src/provider/provider.ts`
  `packages/opencode/src/provider/transform.ts`
  `packages/opencode/src/config/config.ts`
- **Key symbols:** `Provider.Service`, `Provider.Model` / `Provider.Info`, `list` / `getProvider` / `getModel` / `getLanguage` / `closest` / `getSmallModel` / `defaultModel`, `fromModelsDevModel` / `fromModelsDevProvider`, `ProviderTransform.message` / `temperature` / `topP` / `topK` / `options` / `providerOptions` / `maxOutputTokens` / `variants`, `OUTPUT_TOKEN_MAX`
- **How it works:** The catalog is a record of provider id to info, each holding its models, built from models.dev data plus environment, config, and custom sources. Each model entry carries its API coordinates, capabilities (temperature, reasoning, attachments, tool calls, input/output modalities), context limits, cost, and variants. `getLanguage()` resolves a model to an AI SDK client through per-package loaders, and `transform.ts` normalizes every request per model: messages, sampling settings, provider options, and the output token cap (`OUTPUT_TOKEN_MAX` is 32000).
- **Notable detail:** One gateway integration rewrites the client type before variants are computed so reasoning fields use native names; one provider's completion-URL mode silently strips reasoning options, and `getSmallModel()` honors both config and a plugin hook for the small (cheap) model choice.

## 6. Reliability

- **Where:** `packages/opencode/src/session/retry.ts`
  `packages/opencode/src/provider/error.ts`
  `packages/opencode/src/session/processor.ts`
- **Key symbols:** `SessionRetry.delay` / `retryable` / `policy`, `RETRY_INITIAL_DELAY` / `RETRY_BACKOFF_FACTOR` / `RETRY_JITTER_FACTOR` / `RETRY_MAX_DELAY` / `RETRY_MAX_RETRIES`, `ProviderError.parseAPICallError` / `parseStreamError`, `MessageV2.fromError`
- **How it works:** `processor.ts:process()` wraps the whole stream run in an effect-level retry using `SessionRetry.policy()`, marking the session status as retrying between attempts. `retryable()` excludes context-overflow errors, always retries server (5xx) errors, matches rate-limit, overload, network, and timeout phrases, and maps usage-limit errors to upgrade prompts. `delay()` prefers `retry-after` response headers when present, otherwise exponential backoff (2 seconds doubling per attempt plus 25% random jitter, capped at 30 seconds), with at most 5 attempts. `error.ts` classifies API call errors versus streamed JSON error payloads versus context overflow (message match, status 413, or length-exceeded codes).
- **Notable detail:** There is no per-request timeout on model calls and no automatic fallback model on error; fallback is only the choice of runtime plus routing summaries to the small model, with a `doom_loop` permission question after 3 identical tool calls.

## 7. Tool definitions

- **Where:** `packages/opencode/src/tool/tool.ts`
  `packages/opencode/src/tool/registry.ts`
  `packages/opencode/src/tool/json-schema.ts`
  `packages/opencode/src/session/tools.ts`
  `packages/opencode/src/tool/schema.ts`
- **Key symbols:** `Tool.define`, `Tool.init`, `Tool.Def` / `Info` / `Context`, `ToolRegistry.Service.tools` / `all`, `ToolJsonSchema.fromTool` / `fromSchema`, `SessionTools.resolve`, `ProviderTransform.schema`
- **How it works:** Tools are declared with `Tool.define(id, Effect)` where the id is the name (for example `read`), the description comes from a matching `.txt` file, and parameters are an Effect Schema (a TypeScript schema-definition library) struct. A `wrap()` step adds argument decoding and automatic output truncation. The registry builds built-in tools, adds custom file and plugin tools, filters by provider and model, and lets plugins mutate definitions. `SessionTools.resolve()` converts each definition into an AI SDK tool object with a JSON schema (JavaScript Object Notation schema, the model-facing argument shape) and an execute closure that bridges back into effect execution.
- **Notable detail:** The JSON schema is not hand-written: it is generated from the Effect Schema with local reference inlining and a `WeakMap` (a garbage-collected key-value cache) cache, with special handling for integer bounds and union types; plugin tools can override the generated schema.

## 8. Agent loop

- **Where:** `packages/opencode/src/session/prompt.ts`
  `packages/opencode/src/session/processor.ts`
  `packages/opencode/src/session/llm.ts`
  `packages/opencode/src/session/llm/ai-sdk.ts`
- **Key symbols:** `SessionPrompt.loop` / `runLoop`, `SessionProcessor.create` / `process` / `handleEvent`, `LLM.stream`, `streamText`, `LLMAISDK.toLLMEvents`, `DOOM_LOOP_THRESHOLD`
- **How it works:** `prompt.ts:runLoop()` is the outer turn loop: it creates an assistant message, resolves tools, builds system and model messages, then calls `processor.process()`. `process()` calls `llm.stream()`, adapts the SDK stream to events, and feeds them to `handleEvent()`, which creates and updates tool, text, reasoning, step, and patch parts. `process()` returns continue, stop, or compact; `runLoop` checks the finish reason, content filters, structured output, compaction and overflow flags, and the agent step limit, then either breaks or continues.
- **Notable detail:** There is no hand-written while-loop over tool calls: multi-step tool iteration inside one turn is owned by the AI SDK `streamText` call, and opencode only loops at turn level (one `streamText` per `process()` call). A doom-loop guard asks a `doom_loop` permission question after 3 identical consecutive tool calls.

## 9. Parallel tool calls

- **Where:** `packages/opencode/src/session/llm.ts`
  `packages/opencode/src/session/processor.ts`
  `packages/opencode/src/tool/registry.ts`
  `packages/opencode/src/session/tools.ts`
- **Key symbols:** `ctx.toolcalls`, `ensureToolCall` / `readToolCall` / `settleToolCall`, `Deferred`, `Effect.forEach` with unbounded concurrency, `streamText` tool dispatch
- **How it works:** Parallelism comes from the AI SDK dispatching multiple tool-call events in the same step; each call runs its execute closure from `session/tools.ts` concurrently through an effect bridge. The processor tracks each in-flight call by tool-call id with a deferred completion signal, creating `pending` then `running` tool parts. Completion is matched by id through tool-result and tool-error events. Cleanup awaits all pending calls concurrently.
- **Notable detail:** There is no single `Promise.all` (a JavaScript construct that waits for many tasks at once) tool executor; unbounded concurrency appears only for definition building, provider setup, and cleanup. Overlapping calls need per-call-id abort signals, independent pending/running/completed/error states, and id-based result matching — assuming serial execution breaks state.

## 10. File tools

- **Where:** `packages/opencode/src/tool/read.ts`
  `packages/opencode/src/tool/write.ts`
  `packages/opencode/src/tool/edit.ts`
  `packages/opencode/src/tool/glob.ts`
  `packages/opencode/src/tool/grep.ts`
- **Key symbols:** `ReadTool`, `WriteTool`, `EditTool`, `GlobTool`, `GrepTool`, `Parameters`, `DEFAULT_READ_LIMIT`, `MAX_LINE_LENGTH`, `MAX_BYTES`, `lock()`, `Ripgrep.glob` / `grep`
- **How it works:** Each file exposes a `Parameters` schema (file path plus offset/limit for read, old/new string plus replace-all for edit, pattern/path/include for glob and grep) and an execute function. Execution resolves absolute paths, checks external-directory rules, asks the matching permission, then uses filesystem utilities or ripgrep (a fast file-search tool) and returns a title, metadata, and output. Read lists directories with `/` suffixes and suggests near-matches on a miss; write and edit publish filesystem watcher events and attach code-diagnostics output.
- **Notable detail:** Limits are easy to get wrong: read truncates any line over 2000 characters and caps output at 50 KB with offset-continuation hints; glob and grep hard-cap at 100 results with a truncated flag; edit serializes per file with a one-at-a-time lock, rejects empty old strings on existing files, preserves the BOM (Byte Order Mark, invisible file-header bytes), and normalizes line endings.

## 11. Shell execution

- **Where:** `packages/opencode/src/tool/shell.ts`
  `packages/opencode/src/tool/shell/prompt.ts`
  `packages/opencode/src/tool/truncate.ts`
  `packages/opencode/src/tool/truncation-dir.ts`
- **Key symbols:** `ShellTool`, `ShellID.ToolID`, `parse` / `collect` / `ask` / `run`, `tail` / `preview`, `Truncate.write` / `limits` / `output`, `MAX_LINES`, `MAX_BYTES`, `MAX_METADATA_LENGTH`
- **How it works:** The command is parsed with tree-sitter (a syntax-parsing library) bash/powershell grammars; a collect step builds a scan of directories, patterns, and always-ask flags, and an ask step requests external-directory plus shell permission before spawning. `run()` spawns the child process with the resolved shell, working directory, merged plugin environment, and a timeout (default 2 minutes). Output streams through text decoding, updates live metadata, spills to a truncation-directory file past the byte cap, and the final output keeps the tail plus a truncation notice and timeout/abort notes with the exit code.
- **Notable detail:** Unlike generic truncation (which keeps the head preview), shell keeps the tail of the output plus a sliding in-memory window of twice the byte cap, spilling the full log to disk; process kill uses a 3-second force delay, and the live per-chunk preview is separately capped at 30000 characters.

## 12. Permission / approval gate

- **Where:** `packages/opencode/src/permission/index.ts`
  `packages/opencode/src/permission/evaluate.ts`
  `packages/opencode/src/permission/arity.ts`
  `packages/opencode/src/agent/subagent-permissions.ts`
- **Key symbols:** `Permission.Service.ask` / `reply` / `list`, `Permission.evaluate` / `merge` / `visibleTools` / `disabled` / `fromConfig`, `BashArity.prefix` / `ARITY`, `deriveSubagentSessionPermission`, `PermissionV1.RejectedError` / `DeniedError` / `CorrectedError`
- **How it works:** Every tool calls `ctx.ask()` with its permission kind, patterns, and metadata, which calls `Permission.ask()`. It evaluates the permission against ordered rulesets with wildcard matching where the last matching rule wins; a deny throws immediately, an allow skips prompting, otherwise it creates a pending entry with a deferred signal, publishes an Asked event, and blocks until a reply of once, always, or reject arrives. `always` appends allow rules and auto-resolves other matching pendings; `reject` fails sibling requests in the same session.
- **Notable detail:** Merging rules is plain array flattening where order decides precedence; hiding a tool from the list only happens on a full-wildcard deny, so granular denies still show the tool but prompt at runtime; shell `always` patterns use token-arity prefixes (for example `npm run dev` counts as 3 tokens, flags never count); subagents inherit only parent denies plus external-directory rules and default-deny task and todo tools unless their own agent allows them.

## 13. Session persistence

- **Where:** `packages/opencode/src/session/session.ts`
  `packages/opencode/src/storage/storage.ts`
  `packages/opencode/src/storage/schema.ts`
- **Key symbols:** `Session.Service` (`create` / `createNext`, `get`, `list` / `listGlobal`, `messages`, `updateMessage`, `updatePart`), `fromRow` / `toRow`, `getUsage`, `Storage.Service` (`read` / `write` / `update` / `list` / `remove`), `SessionTable`, `MessageTable`, `PartTable`
- **How it works:** Live session state lives in the SQLite database through the session tables, not in the generic storage layer: creation inserts a session row with slug and timestamps, get and list select and convert rows, and messages and parts are read and written through the message module plus update helpers. Resuming is just fetching the session row plus its messages and parts, with cost and token totals copied onto the session row. `Storage.Service` is a separate generic JSON (JavaScript Object Notation, a text data format) key-value file store where key arrays become nested JSON files.
- **Notable detail:** The file store uses a per-file transactional re-entrant lock plus a versioned migrations chain, so copying only the session tables loses locking and old-layout migration; session cost and tokens are denormalized (copied) onto the session row rather than computed on read.

## 14. Snapshot & revert

- **Where:** `packages/opencode/src/snapshot/index.ts`
  `packages/opencode/src/session/revert.ts`
  `packages/opencode/src/patch/index.ts`
- **Key symbols:** `Snapshot.Service` (`track`, `patch`, `restore`, `revert`, `diff`, `diffFull`), `Patch` (`hash`, `files`), `SessionRevert.Service` (`revert`, `unrevert`, `cleanup`)
- **How it works:** Snapshots use a hidden git repository (Git, a version control system) under the data directory, driven with `--git-dir` plus `--work-tree` pointing at the real work folder. `track()` stages and commits the worktree and returns a commit hash, and step start/finish message parts store those hashes. Reverting finds the target message or part, collects later patch parts, saves the current hash, restores the old state, reverts per file, then writes a session diff and sets a revert marker; un-revert restores the saved hash and cleanup deletes truncated messages and parts.
- **Notable detail:** It reuses object hashes from the source repo to avoid re-hashing huge checkouts, serializes git access with a per-directory one-at-a-time lock, and passes paths NUL-separated with special quoting rules — naive path handling breaks on filenames with colons, spaces, or quotes.

## 15. Token accounting & cost

- **Where:** `packages/opencode/src/session/session.ts`
  `packages/opencode/src/session/processor.ts`
  `packages/opencode/src/provider/provider.ts`
  `packages/opencode/src/session/message.ts`
- **Key symbols:** `Session.getUsage`, `Usage` (`inputTokens`, `outputTokens`, `reasoningTokens`, `cacheReadInputTokens`, `cacheWriteInputTokens`, `totalTokens`), `Provider.Model` (`cost`, `tiers`), `Tokens`
- **How it works:** After each model turn, the processor's step-finish handler calls `Session.getUsage()`. That function normalizes provider-specific cache fields, subtracts cached tokens from input because the AI SDK now includes cached tokens in the input count, splits output versus reasoning tokens, picks tiered pricing by context size, and computes cost with exact decimal math per million tokens for input, output, cache read, cache write, and reasoning. Totals are added to the assistant message and the step-finish part, and the same token totals feed the overflow check.
- **Notable detail:** One provider's usage bypasses per-token math via a nano-credit unit, reasoning is charged at the output rate as a workaround, and all inputs pass through safe-number guards — summing raw provider fields would double-count cache and can produce not-a-number or negative costs.

## 16. Context overflow & compaction

- **Where:** `packages/opencode/src/session/overflow.ts`
  `packages/opencode/src/session/compaction.ts`
  `packages/opencode/src/session/summary.ts`
- **Key symbols:** `usable()`, `isOverflow()`, `SessionCompaction.Service` (`isOverflow`, `prune`, `process`, `create`, `select`, `estimate`), `COMPACTION_BUFFER`, `PRUNE_MINIMUM`, `PRUNE_PROTECT`, `buildPrompt`
- **How it works:** `usable()` is the safe input budget: the model input limit minus a reserve (config value, or the smaller of 20000 and the max output tokens), or the context limit minus max output when no input limit exists. `isOverflow()` returns true when token totals reach that budget, unless auto-compaction is off or the context is zero. On overflow the processor flags the need for compaction; selection keeps only recent turns fitting the preserve budget (default 25 percent of usable, clamped between 2000 and 15000 tokens) using estimated token counts with partial-turn splitting, the older head is summarized by a model call into a compaction summary pair, and pruning separately blanks old tool outputs by marking their timestamps.
- **Notable detail:** Pruning protects the newest 2 turns, 40000 tokens of tool calls, already-summarized messages, and the skill tool, and only writes when pruned estimates exceed 20000 — trimming everything would delete recent evidence and protected tool results.

## 17. Tool output offloading

- **Where:** `packages/opencode/src/tool/truncate.ts`
  `packages/opencode/src/tool/truncation-dir.ts`
  `packages/opencode/src/tool/tool.ts`
  `packages/opencode/src/tool/registry.ts`
- **Key symbols:** `Truncate.Service` (`output`, `write`, `limits`, `cleanup`), `MAX_LINES`, `MAX_BYTES`, `TRUNCATION_DIR`, `Result` (`content`, `truncated`, `outputPath`)
- **How it works:** Every tool run is wrapped to call truncate on its output unless the tool already marked itself truncated. When line count and byte size fit the limits (config values or the 2000-line / 50 KB defaults), output passes through unchanged. Otherwise the full text is saved to a tool-output file on disk and the model only sees a head preview (or tail preview when requested) plus a truncation notice and the saved file path with search and read-with-offset guidance. Files older than 7 days are deleted by an hourly cleanup.
- **Notable detail:** Byte accounting adds newline bytes per line and reports removed units as bytes when the byte cap was hit versus lines otherwise, and the hint text changes when the agent has the task tool — returning only clipped text with no spill file and no output-path metadata breaks the resume path.

## 18. Memory files

- **Where:** `packages/opencode/src/session/instruction.ts`
  `packages/opencode/src/config/markdown.ts`
  `packages/opencode/src/project/project.ts`
- **Key symbols:** `Instruction.Service` (`system`, `systemPaths`, `find`, `resolve`, `clear`), `instructionFiles` (`AGENTS.md`, `CLAUDE.md`, `CONTEXT.md`), `globalFiles`, `ConfigMarkdown.parse`, `FILE_REGEX`, `SHELL_REGEX`
- **How it works:** `systemPaths()` collects one global file (the config-directory `AGENTS.md` or home `CLAUDE.md`), then the first project-level match found walking upward (first match wins, ancestors do not stack), plus extra config globs and remote URLs (web addresses). `system()` reads them in parallel and prefixes each with its source path for the system prompt. `resolve()` additionally walks upward from each file read by the read tool and attaches nearby instruction files once per message. The markdown loader supports `@file` includes and shell-command expansion with strict settings-header parsing plus a permissive fallback.
- **Notable detail:** Nested `AGENTS.md` files do not stack except through on-read resolution, `CONTEXT.md` still works but is deprecated, and behavior changes under project-config-disable and prompt-compat flags — hardcoding a fixed filename list misses these cases.

## 19. Skills / progressive disclosure

- **Where:** `packages/opencode/src/skill/index.ts`
  `packages/opencode/src/skill/discovery.ts`
  `packages/opencode/src/tool/skill.ts`
  `packages/opencode/src/tool/skill.txt`
- **Key symbols:** `Skill.Service` (`get` / `require` / `all` / `dirs` / `available`), `Discovery.Service.pull`, `SkillTool` / `Parameters{name}`, `Skill.fmt`, `CUSTOMIZE_OPENCODE_SKILL_NAME`
- **How it works:** Discovery scans `SKILL.md` files from global skill dirs, upward project directories, config directories, explicit paths, and remote URLs pulled through an index file. Loading parses each file, requires name and description frontmatter (a settings header at the top of the file), and stores name, description, location, and content in instance state. The system prompt lists only names plus descriptions; the full body is injected on demand when the model calls the `skill` tool, which loads the skill, asks skill permission, lists up to 10 sibling files, and returns the body with base directory and file list.
- **Notable detail:** A disk skill with the same name overrides the built-in `customize-opencode` skill because the built-in is registered before disk discovery, and availability is filtered by skill permission — exposing full bodies up front or skipping permission filtering and override order diverges from the design.

## 20. Sub-agents / delegation

- **Where:** `packages/opencode/src/tool/task.ts`
  `packages/opencode/src/tool/task.txt`
  `packages/opencode/src/agent/agent.ts`
  `packages/opencode/src/agent/subagent-permissions.ts`
- **Key symbols:** `TaskTool`, `TaskPromptOps` (`prompt`, `resolvePromptParts`, `cancel`), `Agent.Service.get` / `list`, `deriveSubagentSessionPermission()`, `renderOutput()`, `BACKGROUND_STARTED` / `BACKGROUND_UPDATED`
- **How it works:** `TaskTool.execute()` takes a description, prompt, subagent type, optional task id, and background flag. It enforces a maximum subagent depth (default 1) by walking the parent-session chain, asks task permission, resolves the agent definition, then creates a child session with the parent id (or resumes an existing task id). Child permissions equal parent denies plus external-directory rules, with task and todo tools default-denied unless the subagent explicitly allows them. It runs the prompt in the child session inheriting the parent model unless the agent pins one, and returns the last text part wrapped in a task-state block; background mode goes through the background job service with synthetic results injected back into the parent.
- **Notable detail:** Fresh subagents start with clean context unless a task id resumes the same session, and parent agent restrictions do not propagate except denies and external-directory rules — copying the full parent ruleset over-restricts the child and breaks the design.

## 21. Planning & todo tracking

- **Where:** `packages/opencode/src/session/todo.ts`
  `packages/opencode/src/tool/todo.ts`
  `packages/opencode/src/tool/todowrite.txt`
  `packages/opencode/src/tool/plan.ts`
  `packages/opencode/src/tool/plan-enter.txt`
  `packages/opencode/src/tool/plan-exit.txt`
- **Key symbols:** `Todo.Service.update` / `get`, `TodoWriteTool`, `PlanExitTool`, `Session.plan`, built-in agents `build` / `plan`
- **How it works:** Todos are per-session rows (content, status, priority, position); the todo-write tool replaces the whole list transactionally with ordered delete plus insert and publishes an update event. Plan mode is not a flag but two primary agents: `build` versus `plan`, where the plan agent denies edits outside plan files and denies the general task tool while allowing plan exit. Plan exit asks a confirmation question then writes a synthetic user message switching the agent back to `build`; the plan file path comes from `Session.plan()` (worktree plans directory versus the global data dir). In this checkout `tool/plan.ts` only defines the exit tool; the enter side exists only as prompt text wired through CLI and permissions.
- **Notable detail:** The todo tool takes the entire list each call (no per-item patch), requires exactly one in-progress item, and is denied to general subagents by default — making todos global instead of session-scoped or allowing incremental edits diverges from the design.

## 22. MCP / dynamic external tools

- **Where:** `packages/opencode/src/mcp/index.ts`
  `packages/opencode/src/mcp/catalog.ts`
  `packages/opencode/src/mcp/browser.ts`
  `packages/opencode/src/tool/registry.ts`
  `packages/opencode/src/session/tools.ts`
- **Key symbols:** `MCP.Service` (`tools` / `clients` / `prompts` / `resources` / `status` / `connect` / `disconnect` / `startAuth` / `finishAuth`), `McpCatalog.convertTool` / `defs` / `paginate` / `sanitize` / `toolName`, `McpBrowser.Service.open`, `Permission.visibleTools()`
- **How it works:** `MCP.Service` holds per-instance state of config, status, clients, definitions, and instructions, spawning stdio (standard input/output, a local-process channel), SSE (Server-Sent Events, a streaming HTTP channel), and streaming-HTTP clients through the MCP SDK (Software Development Kit, the MCP client library) rooted at the session directory. It paginates the tool list with a tolerant fallback, caches definitions, and at model-call time `session/tools.ts` adapts native definitions into dynamic tools with progress-aware timeout resets, permission-checked per call and plugin triggers around execution; each key is namespaced as server plus tool. The tool registry itself only uses MCP tools for a mode description, not for merging them into the built-in list.
- **Notable detail:** Tool names are sanitized (non-alphanumeric characters become underscores) and namespaced as `server_tool`, while resource keys escape special characters separately — naively concatenating names or mutating shared definitions breaks keys and cache isolation.

## 23. Hooks, plugins & events

- **Where:** `packages/opencode/src/bus/global.ts`
  `packages/opencode/src/plugin/index.ts`
  `packages/opencode/src/plugin/loader.ts`
  `packages/opencode/src/event-manifest.ts`
- **Key symbols:** `GlobalBus`, `Plugin.Service` (`trigger` / `list` / `init`), `TriggerName`, `PluginLoader.resolve` / `load` / `loadExternal`, `EventManifest` (`Definitions`, `Durable`, `Latest`), `EventV2Bridge`
- **How it works:** `GlobalBus` is a Node event emitter for cross-instance event payloads (auto-assigning each payload an id). `Plugin.Service` loads internal auth plugins plus external plugin origins through the loader (plan, resolve target and entry, compatibility check, dynamic import), builds a plugin input of client, project, worktree, and directory, forwards config and bridge events to each hook's event handler, and exposes `trigger(name, input, output)` which sequentially awaits each matching hook and returns the mutated output (for example tool definition and before/after-execution hooks). The event manifest is a short re-export of event definitions from the shared schema package.
- **Notable detail:** Only hooks matching an async input-output shape are triggerable by name, and `trigger` mutates and returns the same output object rather than merging return values — expecting return-value composition misses plugin edits.

## 24. Background & concurrency

- **Where:** `packages/opencode/src/background/job.ts`
  `packages/opencode/src/session/run-state.ts`
  `packages/opencode/src/server/server.ts`
  `packages/opencode/src/control-plane/workspace.ts`
- **Key symbols:** `BackgroundJob.Service` (`list` / `get` / `start` / `extend` / `wait` / `waitForPromotion` / `promote` / `cancel`), `SessionRunState.Service` (`assertNotBusy` / `cancel` / `ensureRunning` / `startShell`), `Runner.make`, `cancelBackgroundJobs()`
- **How it works:** `background/job.ts` is a thin instance-scoped wrapper over the core background-job registry engine; the task tool uses its start, extend, and wait operations with the session id as job id and parent/child session metadata to correlate. `SessionRunState` keeps a map of session id to runner with idle, busy, and interrupt callbacks, guards concurrent turns through a busy check, and cancel stops both the runner and transitively matching background jobs by id and session metadata. Multi-session concurrency is allowed (different sessions run at once) while same-session runs are serialized. The server (HTTP plus UI events) and control-plane (workspace adapters) provide transport and multi-project hosting, not the job queue itself.
- **Notable detail:** Cancellation is transitive over the parent/child session graph through metadata matching in a loop, not just exact job id — cancelling only the exact id orphans nested subagent background jobs.
