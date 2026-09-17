# hermes-agent — harness operation inventory

Project root: `/Users/sergii/.hermes/hermes-agent`. Version `0.21.1` (from `pyproject.toml` `[project] version`).
Factual inventory of how this harness implements each operation; no redesign notes.

## 1. Pure LLM call

- **Where:** `agent/chat_completion_nonstream.py`
  `agent/chat_completion_helpers.py`
  `agent/oneshot.py`
  `run_agent.py`
- **Key symbols:** `_NonStreamRequest`, `_dispatch_nonstreaming_api_request`, `run_oneshot`, `call_llm`
- **How it works:** `agent/oneshot.py` `run_oneshot` builds a stateless `messages` list (a `system` message from `instructions` plus a `user` message from `user_input`, or from a named template) and calls `agent/auxiliary_client.py` `call_llm` with `task`, `max_tokens`, `temperature`, `timeout`. It never touches session history. The conversational non-streaming path uses `_NonStreamRequest`, which runs `_dispatch_nonstreaming_api_request` on a worker thread and polls it. `_dispatch_nonstreaming_api_request` switches on `agent.api_mode` (`codex_responses`, `anthropic_messages`, `bedrock_converse`, `moa`, default OpenAI (Application Programming Interface, the web-request format apps use to call a model) chat completions) and creates a per-request client via `make_client(reason, kind)`.
- **Notable detail:** Per-request clients are registered for abort so watchdogs force-close the worker connection, never the shared client; after a watchdog kill the worker thread joins with `timeout=2.0s` and synthesizes `TimeoutError` if no result arrived. `run_oneshot` defaults are `temperature=0.3`, `max_tokens=1024`, `timeout=60.0`.

## 2. Streaming

- **Where:** `agent/chat_completion_stream_monitor.py`
  `agent/stream_delivery.py`
  `agent/stream_single_writer.py`
- **Key symbols:** `StreamingWaitMonitor`, `StreamDeliveryMixin`, `claim_stream_writer`, `stream_writer_is_current`
- **How it works:** `claim_stream_writer` returns an integer token claiming the delta sink (the single place streamed text fragments go); `stream_writer_is_current` returns true while that token is still active, falling back to unfenced mode if the fence is missing. `StreamDeliveryMixin` fans each text fragment out to the stream callbacks, accumulates visible text in a list of parts to avoid slow repeated string copying, and removes duplicate interim assistant messages by comparing normalized whitespace. `StreamingWaitMonitor` polls the stream every `0.3s`, records activity every `30.0s`, and kills stale streams that stay silent past the stale timeout.
- **Notable detail:** At `60s` of no output the message changes: below `60s` it only records activity, at `60s` and above it prints `waiting on <model> — no stream output for Ns`. Interim deduplication is prefix-match one way only; streamed text longer than the final text never suppresses a resend.

## 3. Conversation state

- **Where:** `agent/turn_context.py`
  `agent/message_metadata.py`
  `hermes_state_messages.py`
- **Key symbols:** `build_turn_context`, `append_message`, `stamp_message_timestamp`, `SessionMessagesMixin`, `substitute_api_content`, `compose_user_api_content`
- **How it works:** `build_turn_context` copies `conversation_history` into `messages`, stages the new user message, and calls `append_message`, which stamps a `timestamp` and appends to the live list; it then restores or reuses the cached system prompt and makes sure the database (DB, the structured store on disk) session row exists. The bytes sent over the wire use an `api_content` sidecar (a parallel copy of the message kept alongside the stored one): `compose_user_api_content` merges memory and plugin injections into it, and `substitute_api_content` swaps the sidecar into `content` so the prompt-cache prefix (the reused beginning of the prompt the provider bills cheaply) stays byte-stable. `SessionMessagesMixin.append_message` writes each message to SQLite (Structured Query Language Lite, a file-based database) and bumps the session's message and tool-call counters.
- **Notable detail:** Ordering matters: the DB session row is created only after the system prompt is restored or built, otherwise a fresh agent stores `system_prompt=NULL` and pays a prefix-cache miss.

## 4. System prompt assembly

- **Where:** `agent/system_prompt.py`
  `agent/prompt_builder.py`
  `agent/coding_context.py`
- **Key symbols:** `build_memory_guidance`, `ContextProfile`, `RuntimeMode`, `resolve_runtime_mode`, `system_prompt_parts`
- **How it works:** The prompt is built once per session and cached on the agent for prefix caching (reusing the provider's previous computation of the same prefix); only compression triggers a rebuild. Three tiers are joined with blank lines: `stable` (identity, guidance, environment hints, coding brief), `context` (workspace snapshot, caller `system_message`, context files), `volatile` (skills index, memory, timestamp). `ContextProfile` plus `RuntimeMode` decide the coding posture, and `system_prompt_parts` returns `(prefix, workspace, trailing)` so assembly can place a cache boundary before the snapshot. Context-file reads run on a background daemon thread with a timeout.
- **Notable detail:** The context-file read default is `5.0s` (overridable by `context_file_read_timeout`); on timeout the file is skipped. Plugin sections are frozen per session and restored from stored prompt bytes by strict frame match, never by re-running plugin code on resume.

## 5. Provider & model abstraction

- **Where:** `agent/provider_registry.py`
  `agent/provider_base.py`
  `providers/base.py`
  `providers/__init__.py`
  `agent/models_dev.py`
  `agent/model_metadata.py`
- **Key symbols:** `ProviderRegistry`, `ProviderBase`, `CatalogProviderBase`, `ProviderProfile`, `register_provider`, `get_provider_profile`, `ModelInfo`, `is_local_endpoint`
- **How it works:** `ProviderRegistry` holds a global name-to-provider map plus per-profile scoped maps with merge, lookup, and snapshot/restore for plugin unload. `ProviderBase` defines the provider identity plus picker metadata; `ProviderProfile` is a declarative record of auth, endpoints, and quirks (`api_mode`, `base_url`, `fixed_temperature`, `fallback_models`, hooks like `prepare_messages` and `build_extra_body`). `register_provider` is last-writer-wins so user plugins override bundled providers, and `get_provider_profile` also maps `custom:*` names to the generic `custom` policy. `ModelInfo` plus the provider-to-catalog map translate Hermes model names to models.dev catalog IDs (an outside catalog of model capabilities) with a 4-hour in-memory TTL (Time To Live, cache expiry).
- **Notable detail:** Name normalization differs per registry (plain strip versus lowercased key); `custom:` names fall back to the generic `custom` wire policy unless explicitly registered. `is_local_endpoint` treats the Tailscale CGNAT (Carrier-Grade Network Address Translation, a shared private address range) `100.64.0.0/10` block as local even though the standard private-address check excludes it.

## 6. Reliability

- **Where:** `agent/retry_utils.py`
  `agent/error_classifier.py`
  `agent/api_error_summary.py`
  `agent/turn_loop_errors.py`
  `agent/fallback_cooldown.py`
- **Key symbols:** `jittered_backoff`, `FailoverReason`, `ClassifiedError`, `ApiErrorSummaryMixin`, `handle_outer_loop_error`
- **How it works:** `FailoverReason` plus `ClassifiedError` carry recovery hints (`retryable`, `should_compress`, `should_rotate_credential`, `should_fallback`) so the retry loop does not re-match error strings. `jittered_backoff` computes `min(base*2^(attempt-1), max_delay)` plus a random jitter fraction. `_summarize_api_error` reduces HTML (HyperText Markup Language, the raw web-page bodies some errors contain), DNS (Domain Name System, address-lookup), and SDK (Software Development Kit, provider client library) error bodies to one log-safe line with secrets redacted. `handle_outer_loop_error` classifies tracebacks into deterministic local-processing bugs (stop immediately) versus API-path errors (retry up to a cap). The fallback-cooldown helper arms a primary-model cooldown only on rate-limit, billing, or upstream reasons when leaving the primary.
- **Notable detail:** Backoff defaults are `base_delay=5.0`, `max_delay=120.0`, `jitter_ratio=0.5`; the rate-limit cooldown is `min(60*(2**backoff_count), 14400)` (60s doubling to a 4h cap); the outer-loop cap is the smaller of the max-errors constant and `max_iterations`.

## 7. Tool definitions

- **Where:** `model_tools.py`
  `toolsets.py`
  `toolset_distributions.py`
  `tools/registry.py`
- **Key symbols:** `get_tool_definitions`, `handle_function_call`, `ToolEntry`, `register`, `discover_builtin_tools`, `resolve_toolset`
- **How it works:** Each file in `tools/*.py` self-declares a tool (name, description, JSON (JavaScript Object Notation, the text format tool schemas are written in) schema, handler, toolset, availability check) by calling `registry.register()` at import time. `discover_builtin_tools()` finds such modules with an AST (Abstract Syntax Tree, a parse of the source code structure) scan and imports them. `get_tool_definitions()` resolves the enabled toolsets, subtracts disabled toolsets, filters by availability probes, merges dynamic schema overrides, and returns OpenAI-style `{"function": {"name", "description", "parameters"}}` dicts that are sent to the model. `toolset_distributions.py` only samples toolset lists for batch data generation.
- **Notable detail:** Quiet-mode definition memoization is capped at 8 entries with LRU (Least Recently Used, evict the longest-unused first) eviction; tool error bodies are capped at 2048 chars.

## 8. Agent loop

- **Where:** `agent/conversation_loop.py`
  `agent/turn_tool_round.py`
  `run_agent.py`
- **Key symbols:** `run_conversation`, `run_tool_round`, `ToolRoundVerdict`, `stage_tool_call_message`, `AIAgent`, `perform_api_call`, `finalize_turn`
- **How it works:** `run_conversation()` drives one user turn as a bounded `while` loop alternating model call and tool round. Each iteration assembles the API request, calls `perform_api_call()`, normalizes the response, and either finishes the text reply or enters `run_tool_round()`. `run_tool_round()` validates, caps, and dedupes tool calls, stores the assistant tool-call message in the session DB (database) before any side effect, runs the tool calls, appends tool-result messages, runs post-tool compression, and returns a verdict of continue, break, or return. `run_agent.py` defines `AIAgent` plus the thin tool-execution wrapper.
- **Notable detail:** Persist-before-execute is a durability invariant: if the canonical DB append fails, the turn ends with `session_persistence_failed` and the tools never run.

## 9. Parallel tool calls

- **Where:** `agent/tool_executor.py`
  `agent/tool_dispatch_helpers.py`
- **Key symbols:** `_plan_tool_batch_segments`, `_NEVER_PARALLEL_TOOLS`, `execute_tool_calls_concurrent`, `DaemonThreadPoolExecutor`
- **How it works:** The executor first calls `_plan_tool_batch_segments()`, which preserves the model's call order and splits calls into ordered `("parallel"|"sequential", calls)` segments. A call becomes a sequential barrier if it is in `_NEVER_PARALLEL_TOOLS`, has unparseable or non-dict arguments, or is not parallel-safe; path-scoped file tools join a parallel run only when they do not conflict on writes. Parallel segments run concurrently in a daemon thread pool; sequential segments use inline dispatch. All paths converge on the same observe-commit-project result pipeline.
- **Notable detail:** At most 8 concurrent worker threads, a 420.0s batch guard, and a 120.0s start-ordering gate; `_NEVER_PARALLEL_TOOLS = {"clarify", "manage_connections"}`.

## 10. File tools

- **Where:** `tools/file_tools.py`
  `tools/file_operations.py`
  `tools/file_tools_paths.py`
- **Key symbols:** `read_file_tool`, `write_file_tool`, `patch_tool`, `ShellFileOperations`, `_resolve_path_for_task`, `_get_max_read_chars`
- **How it works:** `file_tools.py` declares the model-facing tools `read_file`, `write_file`, `patch`, and `search_files` via `registry.register()`, adding guards, pagination, truncation, and device-path blocks. The actual filesystem I/O (input/output) lives in `file_operations.py` as `ShellFileOperations`, which runs compound shell probes through the terminal backend's `execute()` so one implementation serves local, docker, and SSH (Secure Shell, encrypted remote login) backends. `file_tools_paths.py` resolves every relative path against the task's live terminal working directory, never the agent process directory, handling `~`, container-versus-host namespaces, and workspace-divergence warnings.
- **Notable detail:** The read budget default is 100,000 chars (configurable via `file_read_max_chars`); files over 512,000 bytes trigger a wide-read hint.

## 11. Shell execution

- **Where:** `tools/terminal_tool.py`
  `tools/terminal_tool_result.py`
  `tools/terminal_tool_guards.py`
  `tools/shell_heredoc.py`
- **Key symbols:** `terminal_tool`, `finalize_foreground_result`, `strip_inert_heredoc_bodies`
- **How it works:** `terminal_tool()` runs shell commands in the configured backend (local, docker, SSH, modal, daytona, vercel_sandbox, plus plugins), managing per-task environments, working-directory tracking, background sessions, sudo plumbing, and pre-execution guards. `terminal_tool_guards.py` rejects bad working directories, shell-level background operators, long-lived foreground servers, and supervised-gateway self-restart commands. `finalize_foreground_result()` applies sudo handling, the output-transform hook, ANSI (American National Standards Institute escape-code, terminal color/control characters) stripping, secret redaction, exit-code notes, and head-plus-tail truncation with a full-output spill file. `shell_heredoc.py` strips inert heredoc bodies before analysis.
- **Notable detail:** Foreground timeout max is 600s; over-limit foreground calls are promoted to tracked background; truncation keeps 40% head plus 60% tail.

## 12. Permission / approval gate

- **Where:** `tools/approval.py`
  `tools/approval_smart.py`
  `tools/approval_floors.py`
  `tools/approval_human_wait.py`
  `tools/approval_prompt.py`
- **Key symbols:** `check_all_command_guards`, `request_tool_approval`, `_smart_verdict`, `human_wait_window`, `human_wait_ceiling`, `prompt_dangerous_approval`
- **How it works:** `approval.py` owns per-session approval state, gateway queues, the denial tally, and the `check_all_command_guards()` gate called before terminal and code-execution dispatch. `approval_floors.py` applies unconditional pre-gate blocks (hard blocklist, `sudo -S` piping, user `approvals.deny` globs) that fire even in yolo or mode-off settings. Remaining flagged commands go to a smart LLM (Large Language Model, the model acting as a safety judge) guardian verdict (approve, deny, or escalate), then to a human prompt via CLI (Command Line Interface, the terminal) callback, gateway round-trip, or plugin transport. The human-wait helper measures only verifiably human-blocked time so slow answers do not time out parallel batches.
- **Notable detail:** Human-wait margin is 60.0s and the ceiling is `approvals.timeout + 60`; the denial-breaker default threshold is 3 with the tally capped at 256 sessions.

## 13. Session persistence

- **Where:** `agent/session_persistence.py`
  `agent/session_activity.py`
  `hermes_state.py`
  `hermes_state_sessions.py`
  `hermes_state_schema.py`
  `docs/session-lifecycle.md`
- **Key symbols:** `_persist_session`, `build_activity_snapshot`, `SessionSessionsMixin`, `classify_session_status`, `SessionDB`, `resolved_max_resume_messages`
- **How it works:** Live messages flush append-only to SQLite with an in-dict persisted marker that skips already-written rows. Ephemeral recovery scaffolding flags are skipped so resumed sessions do not replay synthetic turns. User rows store clean `content` plus an `api_content` sidecar when the wire bytes differ, and multimodal parts are projected to text. Session rows carry lifecycle flags (`suspended`, `resume_pending`), source tags, and parent links for compression continuations; `session_activity.py` builds the activity snapshot used for heartbeats and resume views.
- **Notable detail:** The activity heartbeat minimum interval is 60.0s, and the resume/export guard caps at 20,000 messages.

## 14. Snapshot & revert

- **Where:** `tools/checkpoint_manager.py`
  `tools/working_diff.py`
  `agent/file_safety.py`
- **Key symbols:** `CheckpointManager`, `ensure_checkpoint`, `restore`, `collect_working_diff`, `is_write_denied`
- **How it works:** Before file-mutating tools run, one shared shadow git store under `~/.hermes/checkpoints/store/` snapshots the working directory once per directory per turn. Projects are keyed by the first 16 hex chars of the absolute path's SHA-256 hash with refs under `refs/hermes/`, per-project indexes, and an agent-write ledger. Restore validates hex hashes and relative paths, then reapplies a checkpoint; `collect_working_diff` shows unstaged, staged, and all diffs including untracked files via `git diff --no-index`. `file_safety.py` is defense-in-depth write denial for credentials and state paths, not the snapshot itself.
- **Notable detail:** Guards cap at 50,000 files and 50 untracked files, with checkpoint pruning default of 7 days retention.

## 15. Token accounting & cost

- **Where:** `agent/account_usage.py`
  `agent/billing_usage.py`
  `agent/aux_accounting.py`
  `hermes_state_usage.py`
  `agent/usage_pricing.py`
  `agent/credits_tracker.py`
- **Key symbols:** `AccountUsageSnapshot`, `CanonicalUsage`, `CreditsState`, `queue_token_counts`, `flush_token_counts`, `record_auxiliary_usage`, `estimate_usage_cost`
- **How it works:** Per-turn token counts and dollar estimates are queued to a coalescing background writer that updates the session totals and per-route `session_model_usage` rows. Pricing resolves per-million-token rates into a cost result via `estimate_usage_cost` and usage normalization. Auxiliary calls (model helpers without a session handle, such as compression and title generation) publish their session identity via a ContextVar (a scoped shared variable) and record at one chokepoint. Portal dollar bars and header micro displays drive the `/usage` view.
- **Notable detail:** The low-balance alert threshold is $5.00; usage bands sit at 50/75/90%, and amounts under $0.01 render as sub-cent.

## 16. Context overflow & compaction

- **Where:** `agent/context_engine.py`
  `agent/context_compressor.py`
  `agent/context_compressor_summary.py`
  `agent/native_compaction.py`
  `agent/micro_compaction.py`
  `agent/turn_context_compaction.py`
  `agent/turn_overflow.py`
  `docs/micro-compaction.md`
- **Key symbols:** `ContextEngine`, `ContextCompressor`, `should_compress`, `prune_tool_results_only`, `native_compaction_context_management`, `resolve_compact_threshold`, `recover_from_overflow`, `OverflowVerdict`
- **How it works:** `ContextCompressor` prunes old tool results first, then summarizes the middle of the history while protecting the head and tail, inserting a `[CONTEXT COMPACTION]` summary marker. Turn-start runs idle then preflight compaction passes; provider overflow errors (HTTP 413 style, context-length exceeded) compress with cooldown bypass and retry, or end the turn with a typed verdict. Native server-side compaction (only for the gpt-5.6 model on the direct OpenAI route) is tried first with the local compressor as fallback. Micro-compaction optionally folds one assistant exchange per turn into a rolling summary between turns.
- **Notable detail:** Defaults are compact at 75% full, protect the first 3 and last 6 messages; the native-compaction safety margin is 8,192 tokens; micro-compaction is off by default with defrag at 2000 tokens.

## 17. Tool output offloading

- **Where:** `tools/tool_output_limits.py`
  `tools/tool_result_storage.py`
  `tools/hook_output_spill.py`
  `agent/inline_tool_executors.py`
  `tools/budget_config.py`
- **Key symbols:** `get_tool_output_limits`, `maybe_persist_tool_result`, `enforce_turn_budget`, `extract_persisted_path`, `spill_if_oversized`, `BudgetConfig`, `INLINE_TOOL_EXECUTORS`
- **How it works:** Layer 1 caps each tool result inline (`max_bytes`, `max_lines`, `max_line_length`). Layer 2 stores oversize results in `$HERMES_HOME/cache/spillover/{id}.txt` and replaces the in-context text with a short preview plus the file path for paged reading. Layer 3 enforces a per-turn aggregate budget across all tool results. Hook (background automation script) context is spilled separately with a head/tail preview. `inline_tool_executors.py` holds only the inline dispatch table, no spill logic.
- **Notable detail:** Thresholds are 100,000 chars per result, 200,000 per turn, 1,500 preview chars, 50,000 for MCP (Model Context Protocol, the standard for external tool servers) tools, 10,000 for hook spill, with 24h spillover expiry; `read_file` is pinned to unlimited to avoid persist-read loops.

## 18. Memory files

- **Where:** `AGENTS.md`
  `agent/AGENTS.md`
  `agent/memory_manager.py`
  `agent/memory_provider.py`
  `tools/memory_tool.py`
- **Key symbols:** `MemoryManager`, `MemoryProvider`, `MemoryStore`, `memory_tool`, `sanitize_memory_context`
- **How it works:** `MEMORY.md` (agent notes) and `USER.md` (user profile) enter the system prompt as a frozen snapshot at session start; mid-session `memory` tool writes reach disk but do not rebuild the prompt, preserving prompt caching. `MemoryManager` fans hooks out to the builtin provider plus at most one external plugin, with prefetch, per-turn sync, and tool schemas. Provider recall text is fenced, sanitized, and capped before injection, and trivial prompts skip recall. The two `AGENTS.md` files carry repo-level instructions loaded with the workspace context.
- **Notable detail:** Provider context is capped at 6,000 chars (4,000 head plus 1,500 tail), subdirectory hints at 32,000, with store defaults of 2200 memory and 1375 user chars.

## 19. Skills / progressive disclosure

- **Where:** `skills/`
  `agent/skill_bundles.py`
  `agent/skill_commands.py`
  `tools/skills_tool.py`
  `tools/skill_manager_tool.py`
- **Key symbols:** `skill_view`, `scan_bundles`, `get_skill_bundles`, `build_bundle_invocation_message`
- **How it works:** A skill is a directory with a `SKILL.md` (YAML frontmatter plus instructions) plus `references/`, `templates/`, `scripts/`, and `assets/`. The list tool returns name and description only; the view tool returns full content with linked files, so detail loads on demand instead of all up front. The `/skill` command expands into a model-facing message embedding the full skill body with scaffold markers for instruction extraction. Bundles are YAML (YAML Ain't Markup Language, a config text format) files under the home `skill-bundles/` directory listing multiple skills loaded into one user message. Discovery is cached by directory modification-time signature plus disabled-set and platform.
- **Notable detail:** If a bundle and a skill share a slug (short name), the bundle wins — slash dispatch checks bundles first by design; the discovery cache TTL is 30.0s.

## 20. Sub-agents / delegation

- **Where:** `agent/delegation_context.py`
  `tools/async_delegation.py`
  `tools/delegate_tool.py`
  `tools/delegate_tool_dispatch.py`
  `agent/subagent_lifecycle.py`
- **Key symbols:** `delegated_child_context`, `_build_child_agent`, `SubagentHandle`, `SubagentState`
- **How it works:** The parent builds child agent instances with fresh conversation history, their own task ID and dedicated session-DB handle, the parent toolsets minus child-blocked tools, and a focused system prompt built from goal plus context. The parent sees only the call and the summary result, never the child intermediate steps. The sync path runs one or several children in parallel; with `background=true` the work dispatches per-task-group units on a daemon executor and pushes a completion event onto the process-registry queue, surfacing as a new turn. ContextVar flags plus an environment marker isolate the Kanban dispatcher identity.
- **Notable detail:** There is no wall-clock kill for slow child work — staleness is progress-based: 450s idle between turns and 1200s stuck on the same tool, then interrupt plus a 120s grace before a forced `stalled` finish.

## 21. Planning & todo tracking

- **Where:** `tools/todo_tool.py`
  `agent/plan_prompt.py`
  `agent/moa_loop.py`
- **Key symbols:** `TodoStore`, `todo_tool`, `build_plan_prompt`
- **How it works:** `TodoStore` is in-memory per agent with items of `{id, content, status, parent?}`; one `todo_tool` reads the list when `todos` is omitted, else replaces or merges by ID with a monotonic revision number that rejects stale updates. The list is re-injected after compression under an active-task-list-preserved marker, keeping only active items plus active parents. `/plan` has no separate engine — `build_plan_prompt` returns a normal-turn prompt that forbids implementation and requires a markdown plan under `.hermes/plans/`. `/moa` (Mixture of Agents, parallel advisor models) marks one turn MoA-enabled where parallel reference advisors without tools advise and the normal loop/aggregator keeps tool calling.
- **Notable detail:** Caps are 256 todo items, 4000 chars per item, 512,000 result chars; reference fan-out is capped at 8 workers.

## 22. MCP / dynamic external tools

- **Where:** `mcp_serve.py`
  `tools/mcp_tool.py`
  `tools/mcp_tool_discovery.py`
  `tools/mcp_tool_lifecycle.py`
  `optional-mcps/`
- **Key symbols:** `MCPServerTask`, `discover_mcp_tools`, `shutdown_mcp_servers`
- **How it works:** As a client, Hermes connects to `mcp_servers` from config (`stdio`, streamable HTTP, SSE — Server-Sent Events, a one-way streaming transport) on one background daemon event loop with long-lived per-server tasks, discovers their tools, and registers them into the tool registry. Lazy servers defer connecting until first tool use; failures get a geometrically capped retry cooldown. Lifecycle tracks stdio child process IDs and groups for orphan kill. `mcp_serve.py` is the opposite direction — it exposes Hermes conversations as a stdio MCP server. `optional-mcps/` holds 65 vendored server definitions.
- **Notable detail:** Lazy-connect defaults to OFF per server; the OSV (Open Source Vulnerabilities, a malware database) preflight timeout is 12.0s, just above the 10s check, and fails open; stale schema-cache phantom tools are deregistered on live connect.

## 23. Hooks, plugins & events

- **Where:** `agent/api_request_hooks.py`
  `agent/shell_hooks.py`
  `agent/verify_hooks.py`
  `agent/plugin_llm.py`
  `agent/plugin_stream_hooks.py`
  `plugins/`
  `plugin-catalog/`
  `tools/plugin_guard.py`
- **Key symbols:** `ApiRequestHooksMixin`, `ShellHookSpec`, `register_from_config`, `PluginLlm`, `enqueue_plugin_stream_hook`, `scan_plugin`
- **How it works:** `ApiRequestHooksMixin` coerces, redacts, and caps API payloads and dispatches request errors through the lifecycle handler. Shell `hooks:` config entries wire stdin-JSON scripts receiving `{hook_event_name, tool_name, tool_input, session_id, cwd, extra}` whose standard-output JSON can block, modify, or add context; registration requires per-(event, command) allowlist consent. Streaming observers give each callback its own bounded queue plus daemon worker so plugin code never runs on the token path. `pre_verify` is a round-end continue gate with bounded nudges. Trusted plugins get host-routed model access via the plugin LLM handle gated by allow-override flags. `scan_plugin` gates plugin install and update.
- **Notable detail:** Exit-code 2 blocks only `pre_tool_call`; hooks fail open unless configured fail-closed; the stream queue holds 1024 entries and drops oldest when full; a `dangerous` plugin verdict blocks even with `--force`.

## 24. Background & concurrency

- **Where:** `tools/terminal_tool_background.py`
  `tools/daemon_pool.py`
  `tools/process_registry.py`
  `agent/periodic_scheduler.py`
  `agent/background_review.py`
  `batch_runner.py`
- **Key symbols:** `spawn_background_process`, `DaemonThreadPoolExecutor`, `PeriodicScheduler`, `prepare_background_review_run`
- **How it works:** `terminal(background=true)` spawns via the process registry (a local subprocess, or remote execute in a sandbox) with a rolling output buffer, poll/log/wait/kill operations, a JSON checkpoint for crash recovery, and a gateway routing stamp so completion and watch notifications start a new turn. `DaemonThreadPoolExecutor` uses daemon workers without the standard-library exit join, so wedged work never blocks exit, and propagates context variables. `PeriodicScheduler` replaces per-child sleep threads with one daemon timer heap where each due body runs on a short-lived worker without self-overlap. Background review forks an agent after a turn on a daemon thread to propose memory/skill writes without touching the main prompt cache. `batch_runner.py` runs JSONL (JSON Lines, one object per line) datasets via a multiprocessing pool with per-batch outputs and `--resume`.
- **Notable detail:** Registry limits are 200,000 output chars, 1800s finished-process TTL (Time To Live, expiry), 64 processes with LRU eviction; watch-pattern minimum interval is 15s with a 3-strike limit and 8 lifetime hits; review cancel waits only 2.0s so the foreground turn never blocks.
