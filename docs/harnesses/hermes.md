# hermes-agent — harness anatomy

> hermes-agent is an open-source personal Artificial Intelligence (AI) coding and operations agent written in Python.

## What it is

hermes-agent (version `0.21.1` per `pyproject.toml`) is a community-built personal agent described in `AGENTS.md` as running one shared agent core across many surfaces: a Command Line Interface (CLI, the terminal program), a messaging gateway (Telegram, Discord, Slack and about twenty platforms), a text interface, and a desktop app. It is built to do real computer work across sessions — driving a terminal, editing files, remembering user and project facts, delegating to sub-agents (child agents it spawns), and running scheduled jobs — and it is extended primarily through plugins and skills rather than by growing the core.

The single design idea that shapes everything is stated in `AGENTS.md`: per-conversation prompt caching is sacred. A prompt cache (the provider's reuse of computation for the repeated start of a prompt) makes long conversations cheap, so hermes-agent freezes the system prompt, tool list, memory snapshot, and plugin sections for the whole session and only rebuilds them on context compression or at the next session. Every other choice — frozen plugin frames in `agent/system_prompt.py`, deferred skill and memory activation, the wire-format sidecar in `agent/turn_context.py` — exists to keep that cached prefix byte-stable.

## Architecture at a glance

- `agent/` — the agent core: turn loop, message assembly, providers, retries, compaction, delegation, hooks, and memory wiring (for example `agent/conversation_loop.py`, `agent/turn_context.py`, `agent/system_prompt.py`).
- `tools/` — the model-facing tools and their safety machinery: each file self-registers tools, plus guards, approvals, terminals, checkpoints, and output limits (for example `tools/registry.py`, `tools/terminal_tool.py`, `tools/approval.py`).
- `hermes_state*.py` (for example `hermes_state.py`, `hermes_state_sessions.py`, `hermes_state_messages.py`, `hermes_state_schema.py`) — the Structured Query Language Lite (SQLite, a file-based database) persistence layer: sessions, messages, usage rows, and schema.
- `providers/` plus `agent/provider_registry.py` and `agent/provider_base.py` — provider abstraction: a registry of named providers, declarative profiles, and catalog name mapping.
- `skills/` plus `agent/skill_bundles.py` and `tools/skills_tool.py` — progressive disclosure (showing summaries first, full detail only on demand) for skills and skill bundles.
- `plugins/` and `plugin-catalog/` plus `agent/plugin_llm.py` and `tools/plugin_guard.py` — the plugin system: discovery, install/update gating, and guarded model access for trusted plugins.
- `tools/checkpoint_manager.py` and `tools/working_diff.py` — snapshot and revert: a shared shadow git store plus working-tree diff views.
- `gateway/`, `hermes_cli/`, and `apps/` — the surfaces that share the core: the messaging gateway, the terminal program, and the desktop and companion apps.
- `mcp_serve.py`, `tools/mcp_tool.py`, and `optional-mcps/` — Model Context Protocol (MCP, the standard for external tool servers) in both directions: Hermes as client of outside servers and Hermes itself exposed as a server.
- `batch_runner.py`, `tools/daemon_pool.py`, `tools/process_registry.py`, and `agent/periodic_scheduler.py` — background work and concurrency: batch datasets, daemon threads, tracked subprocesses, and one shared timer heap.

## Operation map

| # | Operation | Implemented in | In one line |
|---|---|---|---|
| 1 | Pure LLM call | `agent/chat_completion_nonstream.py`, `agent/chat_completion_helpers.py`, `agent/oneshot.py`, `run_agent.py` | Stateless one-shot call plus threaded non-streaming request dispatcher. |
| 2 | Streaming | `agent/chat_completion_stream_monitor.py`, `agent/stream_delivery.py`, `agent/stream_single_writer.py` | Single-writer delta sink with fan-out delivery and staleness watchdog. |
| 3 | Conversation state | `agent/turn_context.py`, `agent/message_metadata.py`, `hermes_state_messages.py` | Staged turn context with timestamped appends and wire-format sidecar. |
| 4 | System prompt assembly | `agent/system_prompt.py`, `agent/prompt_builder.py`, `agent/coding_context.py` | Once-per-session three-tier prompt, cached for prefix reuse. |
| 5 | Provider & model abstraction | `agent/provider_registry.py`, `agent/provider_base.py`, `providers/base.py`, `providers/__init__.py`, `agent/models_dev.py`, `agent/model_metadata.py` | Global plus scoped provider maps with declarative profiles and catalog mapping. |
| 6 | Reliability | `agent/retry_utils.py`, `agent/error_classifier.py`, `agent/api_error_summary.py`, `agent/turn_loop_errors.py`, `agent/fallback_cooldown.py` | Classified errors carrying recovery hints drive jittered retry and failover. |
| 7 | Tool definitions | `model_tools.py`, `toolsets.py`, `toolset_distributions.py`, `tools/registry.py` | Self-registering tool files resolved into model-ready schemas per toolset. |
| 8 | Agent loop | `agent/conversation_loop.py`, `agent/turn_tool_round.py`, `run_agent.py` | Bounded model-then-tools loop with persist-before-execute durability. |
| 9 | Parallel tool calls | `agent/tool_executor.py`, `agent/tool_dispatch_helpers.py` | Order-preserving batch planner splitting parallel and sequential segments. |
| 10 | File tools | `tools/file_tools.py`, `tools/file_operations.py`, `tools/file_tools_paths.py` | Guarded file tools over one terminal-backed filesystem implementation. |
| 11 | Shell execution | `tools/terminal_tool.py`, `tools/terminal_tool_result.py`, `tools/terminal_tool_guards.py`, `tools/shell_heredoc.py` | Multi-backend shell runner with guards, redaction, and head-plus-tail truncation. |
| 12 | Permission / approval gate | `tools/approval.py`, `tools/approval_smart.py`, `tools/approval_floors.py`, `tools/approval_human_wait.py`, `tools/approval_prompt.py` | Layered floors, model judge, and human prompt before risky commands. |
| 13 | Session persistence | `agent/session_persistence.py`, `agent/session_activity.py`, `hermes_state.py`, `hermes_state_sessions.py`, `hermes_state_schema.py`, `docs/session-lifecycle.md` | Append-only message flush to SQLite with lifecycle flags and snapshots. |
| 14 | Snapshot & revert | `tools/checkpoint_manager.py`, `tools/working_diff.py`, `agent/file_safety.py` | Shadow git snapshots per directory per turn with validated restore. |
| 15 | Token accounting & cost | `agent/account_usage.py`, `agent/billing_usage.py`, `agent/aux_accounting.py`, `hermes_state_usage.py`, `agent/usage_pricing.py`, `agent/credits_tracker.py` | Coalescing background writer for per-turn tokens, costs, and balances. |
| 16 | Context overflow & compaction | `agent/context_engine.py`, `agent/context_compressor.py`, `agent/context_compressor_summary.py`, `agent/native_compaction.py`, `agent/micro_compaction.py`, `agent/turn_context_compaction.py`, `agent/turn_overflow.py`, `docs/micro-compaction.md` | Prune-then-summarize compressor with preflight, overflow, and micro passes. |
| 17 | Tool output offloading | `tools/tool_output_limits.py`, `tools/tool_result_storage.py`, `tools/hook_output_spill.py`, `agent/inline_tool_executors.py`, `tools/budget_config.py` | Three-layer cap, spill-to-disk with preview, and per-turn budget. |
| 18 | Memory files | `AGENTS.md`, `agent/AGENTS.md`, `agent/memory_manager.py`, `agent/memory_provider.py`, `tools/memory_tool.py` | Frozen session-start memory snapshot with fenced, capped provider recall. |
| 19 | Skills / progressive disclosure | `skills/`, `agent/skill_bundles.py`, `agent/skill_commands.py`, `tools/skills_tool.py`, `tools/skill_manager_tool.py` | Name-only listing with full skill body loaded only on view. |
| 20 | Sub-agents / delegation | `agent/delegation_context.py`, `tools/async_delegation.py`, `tools/delegate_tool.py`, `tools/delegate_tool_dispatch.py`, `agent/subagent_lifecycle.py` | Fresh child agents with own sessions; parent sees only the summary. |
| 21 | Planning & todo tracking | `tools/todo_tool.py`, `agent/plan_prompt.py`, `agent/moa_loop.py` | In-memory revisioned todo store plus prompt-driven plan and advisor modes. |
| 22 | MCP / dynamic external tools | `mcp_serve.py`, `tools/mcp_tool.py`, `tools/mcp_tool_discovery.py`, `tools/mcp_tool_lifecycle.py`, `optional-mcps/` | Background client loop with lazy connect, retries, and vendored servers. |
| 23 | Hooks, plugins & events | `agent/api_request_hooks.py`, `agent/shell_hooks.py`, `agent/verify_hooks.py`, `agent/plugin_llm.py`, `agent/plugin_stream_hooks.py`, `plugins/`, `plugin-catalog/`, `tools/plugin_guard.py` | Payload hooks, stdin-JSON (JavaScript Object Notation, the text format tool schemas use) shell hooks, and queued stream observers. |
| 24 | Background & concurrency | `tools/terminal_tool_background.py`, `tools/daemon_pool.py`, `tools/process_registry.py`, `agent/periodic_scheduler.py`, `agent/background_review.py`, `batch_runner.py` | Tracked background processes, daemon pool, timer heap, and batch runner. |

## How each operation works

### 1. Pure LLM call

A Large Language Model (LLM, the model that writes replies and tool calls) can be called without any conversation history through `agent/oneshot.py`, whose `run_oneshot` builds a fresh message list from an instruction string plus user input (or a named template) and sends it via `agent/auxiliary_client.py`. It never reads or writes the session history, so it is safe for titles, summaries, and judges. The conversational non-streaming path uses `_NonStreamRequest` in `agent/chat_completion_nonstream.py`, which runs `_dispatch_nonstreaming_api_request` on a worker thread and polls for its result. That dispatcher switches on `agent.api_mode` in `agent/chat_completion_helpers.py` (one branch per provider wire format) and builds a per-request client with `make_client(reason, kind)` in `run_agent.py`. Each per-request client is registered for abort so a watchdog kills only that worker connection, never the shared client.

**Watch out:** after a watchdog kill the worker thread joins with `timeout=2.0s` and synthesizes a `TimeoutError` if nothing arrived; `run_oneshot` defaults are `temperature=0.3`, `max_tokens=1024`, `timeout=60.0`.

### 2. Streaming

Streamed output flows through a single-writer fence owned by `agent/stream_single_writer.py`, where `claim_stream_writer` hands out an integer token for the delta sink (the one place text fragments go) and `stream_writer_is_current` checks the token is still valid. The actual fan-out lives in `agent/stream_delivery.py` in `StreamDeliveryMixin`, which sends each fragment to the registered stream callbacks and accumulates visible text as a list of parts to avoid slow repeated string copying. It also removes duplicate interim assistant messages by comparing whitespace-normalized text so the user does not see the same chunk twice. Liveness is watched by `StreamingWaitMonitor` in `agent/chat_completion_stream_monitor.py`, which polls the stream every `0.3s` and records activity every `30.0s`. Stale streams that stay silent past the timeout are killed instead of hanging forever.

**Watch out:** below `60s` of silence it only records activity, at `60s` and above it prints `waiting on <model> — no stream output for Ns`; deduplication is one-way prefix matching, so streamed text longer than the final text never suppresses a resend.

### 3. Conversation state

Each turn starts in `agent/turn_context.py` with `build_turn_context`, which copies the stored conversation history into a working message list and stages the new user message. Appends go through `append_message` in `agent/message_metadata.py`, which stamps a timestamp and adds the message to the live list, then the builder restores or reuses the cached system prompt and makes sure the database (DB, the structured store on disk) session row exists. The bytes sent to the provider use an `api_content` sidecar (a parallel copy kept alongside the stored message): `compose_user_api_content` merges memory and plugin injections into that sidecar, and `substitute_api_content` swaps it into `content` just for the wire. This keeps the cached prefix byte-stable even while the stored view stays clean and readable. Durable writes go through `SessionMessagesMixin` in `hermes_state_messages.py`, which appends each message to SQLite and bumps the session counters.

**Watch out:** ordering matters — the DB session row is created only after the system prompt is restored or built, otherwise a fresh agent stores `system_prompt=NULL` and pays a prefix-cache miss.

### 4. System prompt assembly

The system prompt is built once per session by `agent/system_prompt.py` with helpers in `agent/prompt_builder.py`, then cached on the agent object so the provider reuses its cached computation every turn. Only compression triggers a rebuild, which is the one deliberate exception to the freeze rule. The prompt has three tiers joined with blank lines: `stable` (identity, guidance, environment hints, coding brief), `context` (workspace snapshot, caller message, context files), and `volatile` (skills index, memory, timestamp). Posture comes from `ContextProfile` plus `RuntimeMode` in `agent/coding_context.py`, and `system_prompt_parts` returns `(prefix, workspace, trailing)` so assembly can place a cache boundary just before the snapshot. Context-file reads run on a background daemon thread with a timeout so a slow disk never stalls startup.

**Watch out:** the context-file read default is `5.0s` (overridable by `context_file_read_timeout`), and on timeout the file is skipped; plugin sections are frozen per session and restored from stored prompt bytes by strict frame match, never by re-running plugin code on resume.

### 5. Provider & model abstraction

Providers are tracked by `ProviderRegistry` in `agent/provider_registry.py`, which keeps one global name-to-provider map plus per-profile scoped maps with merge, lookup, and snapshot/restore for plugin unload. Each provider's identity and chooser metadata come from `ProviderBase` in `agent/provider_base.py` (with catalog behavior in `providers/base.py` and exports in `providers/__init__.py`), while `ProviderProfile` is a declarative record of login method, endpoints, and quirks such as wire mode, base address, fixed temperature, fallback models, and hooks. Registration in `agent/provider_registry.py` is last-writer-wins so user plugins override bundled providers, and `get_provider_profile` maps `custom:*` names onto the generic `custom` policy. Model-name translation lives in `agent/models_dev.py` with metadata in `agent/model_metadata.py`, mapping Hermes names to outside catalog identifiers with a 4-hour in-memory Time To Live (TTL, cache expiry). Local-endpoint detection in `agent/model_metadata.py` decides when traffic stays on the machine.

**Watch out:** name normalization differs per registry (plain strip versus lowercased key); `custom:` names fall back to the generic `custom` wire policy unless explicitly registered; the Tailscale shared-address `100.64.0.0/10` block counts as local even though the standard private-address check excludes it (`agent/model_metadata.py`).

### 6. Reliability

Failures are classified once into `FailoverReason` plus `ClassifiedError` in `agent/error_classifier.py`, which carry recovery hints (retryable, should compress, should rotate credential, should fall back) so the retry loop never re-matches error strings. Waits between retries come from `jittered_backoff` in `agent/retry_utils.py`, which computes `min(base*2^(attempt-1), max_delay)` plus a random jitter fraction to avoid synchronized retries. Messy error bodies become one log-safe line in `agent/api_error_summary.py`, which reduces raw web-page (HyperText Markup Language, HTML) bodies, address-lookup (Domain Name System, DNS) failures, and client-library (Software Development Kit, SDK) errors while redacting secrets. `handle_outer_loop_error` in `agent/turn_loop_errors.py` separates deterministic local-processing bugs (stop immediately) from provider-path errors (retry up to a cap). Cooldown for the primary model is armed by `agent/fallback_cooldown.py` only on rate-limit, billing, or upstream reasons when leaving the primary.

**Watch out:** backoff defaults are `base_delay=5.0`, `max_delay=120.0`, `jitter_ratio=0.5`; the rate-limit cooldown is `min(60*(2**backoff_count), 14400)` up to a 4-hour cap; the outer-loop cap is the smaller of the max-errors constant and `max_iterations`.

### 7. Tool definitions

Every tool file under `tools/*.py` declares itself by calling `register()` in `tools/registry.py` at import time with its name, description, JSON schema (the text format tool parameters are written in), handler, toolset, and availability check. `discover_builtin_tools()` in `tools/registry.py` finds those modules with an Abstract Syntax Tree (AST, a parse of source-code structure) scan and imports them, so adding a file adds a tool. `get_tool_definitions()` in `model_tools.py` resolves the enabled toolsets from `toolsets.py`, subtracts disabled ones, filters by availability probes, merges dynamic schema overrides, and returns model-ready function dicts sent on every provider call. Sampling of toolset lists for batch data generation lives separately in `toolset_distributions.py` and is not part of the live path. The registry is therefore the single source of truth for what the model is allowed to call.

**Watch out:** quiet-mode definition memoization is capped at 8 entries with Least Recently Used (LRU, evict the longest-unused first) eviction; tool error bodies are capped at 2048 characters.

### 8. Agent loop

One user turn is driven by `run_conversation()` in `agent/conversation_loop.py` as a bounded loop alternating model call and tool round. Each pass assembles the provider request, calls `perform_api_call()`, normalizes the response, and either finishes the text reply or enters `run_tool_round()` in `agent/turn_tool_round.py`. That tool round validates, caps, and dedupes the requested calls, stores the assistant tool-call message in the session DB before any side effect happens, executes the tools, appends the tool-result messages, runs post-tool compression, and returns a verdict of continue, break, or return. Final reply bookkeeping happens in `finalize_turn` in `agent/conversation_loop.py`. The `AIAgent` class plus the thin execution wrapper live in `run_agent.py`.

**Watch out:** persist-before-execute is a durability invariant — if the canonical DB append fails, the turn ends with `session_persistence_failed` and the tools never run (`agent/turn_tool_round.py`).

### 9. Parallel tool calls

Concurrency is planned before it happens by `_plan_tool_batch_segments()` in `agent/tool_dispatch_helpers.py`, which keeps the model's call order and splits calls into ordered `("parallel"|"sequential", calls)` segments. A call becomes a sequential barrier if it appears in `_NEVER_PARALLEL_TOOLS`, has unparseable or non-dict arguments, or is not parallel-safe; path-scoped file tools join a parallel run only when they do not conflict on writes. Parallel segments run together in a daemon thread pool in `agent/tool_executor.py` via `execute_tool_calls_concurrent` and `DaemonThreadPoolExecutor` in `tools/daemon_pool.py`, while sequential segments use inline dispatch. Every path converges on the same observe-commit-project result pipeline so parallel and sequential calls produce identical records. The planner is therefore what keeps concurrent execution deterministic from the model's point of view.

**Watch out:** at most 8 concurrent worker threads, a `420.0s` batch guard, and a `120.0s` start-ordering gate; `_NEVER_PARALLEL_TOOLS = {"clarify", "manage_connections"}`.

### 10. File tools

The model-facing tools `read_file`, `write_file`, `patch`, and `search_files` are declared in `tools/file_tools.py` via `registry.register()`, with guards, pagination, truncation, and device-path blocks layered around them. The real filesystem input/output lives in `tools/file_operations.py` as `ShellFileOperations`, which routes compound shell probes through the terminal backend's `execute()` so one implementation serves local, container, and Secure Shell (SSH, encrypted remote login) backends. Path resolution lives in `tools/file_tools_paths.py` in `_resolve_path_for_task`, which resolves every relative path against the task's live terminal working directory — never the agent process directory — handling home-directory marks, container-versus-host namespaces, and workspace-divergence warnings. Read budgets come from `_get_max_read_chars` in `tools/file_tools.py`. Search, read, and edit therefore share one path and one execution backend.

**Watch out:** the read budget default is 100,000 characters (configurable via `file_read_max_chars`); files over 512,000 bytes trigger a wide-read hint.

### 11. Shell execution

Shell commands run through `terminal_tool()` in `tools/terminal_tool.py`, which manages backends (local, container, SSH, modal, daytona, vercel_sandbox, plus plugins), per-task environments, working-directory tracking, background sessions, superuser plumbing, and pre-execution guards. The guards in `tools/terminal_tool_guards.py` reject bad working directories, shell-level background operators, long-lived foreground servers, and supervised-gateway self-restart commands before anything executes. Heredoc (inline multi-line input) bodies are stripped for analysis by `strip_inert_heredoc_bodies` in `tools/shell_heredoc.py` so inert text is not mistaken for code. Foreground results are finished by `finalize_foreground_result()` in `tools/terminal_tool_result.py`, which handles superuser output, output transforms, terminal color-code (American National Standards Institute escape-code, ANSI) stripping, secret redaction, exit-code notes, and truncation with a full-output spill file.

**Watch out:** foreground timeout maximum is `600s`; over-limit foreground calls are promoted to tracked background; truncation keeps 40 percent head plus 60 percent tail.

### 12. Permission / approval gate

Per-session approval state, gateway queues, and the denial tally live in `tools/approval.py`, whose `check_all_command_guards()` gate runs before terminal and code-execution dispatch. Unconditional blocks live in `tools/approval_floors.py`, which fires on a hard blocklist, superuser password piping, and user `approvals.deny` patterns even in permissive or switched-off settings. Commands that survive the floors go to a smart model guardian in `tools/approval_smart.py` (`_smart_verdict` returns approve, deny, or escalate), then to a human through the terminal callback in `tools/approval_prompt.py` (`prompt_dangerous_approval`), a gateway round-trip, or a plugin transport. Waiting for the human uses `human_wait_window` and `human_wait_ceiling` in `tools/approval_human_wait.py`, which measures only verifiably human-blocked time so slow answers do not time out parallel batches. Denials accumulate toward a breaker that stops runaway sessions.

**Watch out:** the human-wait margin is `60.0s` and the ceiling is `approvals.timeout + 60`; the denial-breaker default threshold is 3 with the tally capped at 256 sessions.

### 13. Session persistence

Live messages flush append-only to SQLite through `_persist_session` in `agent/session_persistence.py`, using an in-memory persisted marker so already-written rows are skipped on the next flush. Ephemeral recovery scaffolding flags are skipped so a resumed session does not replay synthetic turns. User rows store clean readable content plus an `api_content` sidecar when the wire bytes differ, and multimodal parts are projected to text for storage. Session rows in `hermes_state_sessions.py` (on the `SessionDB` base in `hermes_state.py` with schema in `hermes_state_schema.py`) carry lifecycle flags (`suspended`, `resume_pending`), source tags, and parent links for compression continuations. Activity snapshots for heartbeats and resume views are built by `build_activity_snapshot` in `agent/session_activity.py`, with status labels from `classify_session_status` and resume caps from `resolved_max_resume_messages`. The lifecycle narrative is documented in `docs/session-lifecycle.md`.

**Watch out:** the activity heartbeat minimum interval is `60.0s`, and the resume and export guard caps at 20,000 messages.

### 14. Snapshot & revert

Before file-mutating tools run, `CheckpointManager` in `tools/checkpoint_manager.py` snapshots the working directory once per directory per turn into one shared shadow git store under `~/.hermes/checkpoints/store/`. Projects are keyed by the first 16 hex characters of the absolute path's SHA-256 hash (a fingerprint function), with refs under `refs/hermes/`, per-project indexes, and an agent-write ledger tracking what the agent changed. Restore in `tools/checkpoint_manager.py` validates hex hashes and relative paths, then reapplies a checkpoint; `collect_working_diff` in `tools/working_diff.py` shows unstaged, staged, and full diffs including untracked files via `git diff --no-index`. `is_write_denied` in `agent/file_safety.py` is defense-in-depth denial for credentials and state paths, not the snapshot itself. Snapshots are therefore automatic and cheap, while restore is explicit and validated.

**Watch out:** guards cap at 50,000 files and 50 untracked files, with checkpoint pruning default of 7 days retention.

### 15. Token accounting & cost

Per-turn token counts and dollar estimates are queued with `queue_token_counts` and written by `flush_token_counts` in `agent/account_usage.py` to a coalescing background writer that updates session totals and per-route `session_model_usage` rows in `hermes_state_usage.py`. Pricing resolves per-million-token rates into a cost figure through `estimate_usage_cost` in `agent/usage_pricing.py` with normalization in `agent/billing_usage.py`. Helper calls without a session handle (compression, title generation) publish their session identity through a ContextVar (a scoped shared variable) and record at one chokepoint via `record_auxiliary_usage` in `agent/aux_accounting.py`. Balances and thresholds live in `CreditsState` in `agent/credits_tracker.py` with snapshots in `AccountUsageSnapshot` and `CanonicalUsage`. The portal dollar bars and header micro displays read from this layer to render the `/usage` view.

**Watch out:** the low-balance alert threshold is $5.00; usage bands sit at 50, 75, and 90 percent, and amounts under $0.01 render as sub-cent.

### 16. Context overflow & compaction

Overflow policy is owned by `ContextEngine` in `agent/context_engine.py` with `should_compress` deciding when the history is too full, while `ContextCompressor` in `agent/context_compressor.py` does the shrinking: it prunes old tool results first via `prune_tool_results_only`, then summarizes the middle while protecting the head and tail, inserting a `[CONTEXT COMPACTION]` summary marker built with `agent/context_compressor_summary.py`. Turn-start runs idle then preflight passes in `agent/turn_context_compaction.py`, and provider overflow errors (context-length-exceeded style) compress with cooldown bypass and retry, or end the turn with a typed `OverflowVerdict` in `agent/turn_overflow.py`. Server-side native compaction for one flagship model family on the direct route is tried first in `agent/native_compaction.py`, with the local compressor as fallback. Optional micro-compaction in `agent/micro_compaction.py` (documented in `docs/micro-compaction.md`) folds one assistant exchange per turn into a rolling summary between turns.

**Watch out:** defaults compact at 75 percent full while protecting the first 3 and last 6 messages; the native-compaction safety margin is 8,192 tokens; micro-compaction is off by default with defrag at 2000 tokens.

### 17. Tool output offloading

Large tool results pass through three layers defined across `tools/tool_output_limits.py`, `tools/tool_result_storage.py`, and `tools/budget_config.py`. Layer one caps each result inline via `get_tool_output_limits` (`max_bytes`, `max_lines`, `max_line_length` in `BudgetConfig`). Layer two stores oversize results with `maybe_persist_tool_result` in `$HERMES_HOME/cache/spillover/{id}.txt` and replaces the in-context text with a short preview plus the file path for paged reading, recoverable with `extract_persisted_path`. Layer three enforces a per-turn aggregate budget across all tool results with `enforce_turn_budget`. Automation-script (hook, a background script that reacts to events) context is spilled separately with a head/tail preview via `spill_if_oversized` in `tools/hook_output_spill.py`. `INLINE_TOOL_EXECUTORS` in `agent/inline_tool_executors.py` holds only the inline dispatch table and no spill logic.

**Watch out:** thresholds are 100,000 characters per result, 200,000 per turn, 1,500 preview characters, 50,000 for MCP tools, 10,000 for hook spill, with 24-hour spillover expiry; `read_file` is pinned to unlimited to avoid persist-read loops.

### 18. Memory files

Long-term notes enter the prompt from two files: `MEMORY.md` (agent notes) and `USER.md` (user profile), managed by `MemoryManager` in `agent/memory_manager.py` with provider fan-out in `agent/memory_provider.py` and the model-facing writer in `tools/memory_tool.py` (`memory_tool`, `MemoryStore`). They enter the system prompt as a frozen snapshot at session start; mid-session `memory` tool writes reach disk but do not rebuild the prompt, preserving the prompt cache. Provider recall text is fenced, cleaned by `sanitize_memory_context`, and capped before injection, and trivial prompts skip recall entirely to save cost. The two `AGENTS.md` files (root `AGENTS.md` and `agent/AGENTS.md`) carry repository-level instructions loaded with the workspace context. Prefetch and per-turn sync keep the store fresh without touching the frozen prompt.

**Watch out:** provider context is capped at 6,000 characters (4,000 head plus 1,500 tail), subdirectory hints at 32,000, with store defaults of 2200 memory and 1375 user characters.

### 19. Skills / progressive disclosure

A skill is a directory under `skills/` holding a `SKILL.md` (YAML frontmatter — YAML Ain't Markup Language, a config text format — plus instructions) with `references/`, `templates/`, `scripts/`, and `assets/` alongside. The listing tool in `tools/skills_tool.py` (`skill_view` plus the list path) returns name and description only, while viewing returns the full content with linked files, so detail loads on demand instead of all up front. The `/skill` command in `agent/skill_commands.py` expands into a model-facing message embedding the full skill body with scaffold markers via `build_bundle_invocation_message`. Bundles are YAML files under the home `skill-bundles/` directory listing several skills to load into one user message, scanned by `scan_bundles` and served by `get_skill_bundles` in `agent/skill_bundles.py`. Discovery caching and install/update management live in `tools/skill_manager_tool.py`.

**Watch out:** if a bundle and a skill share a short name (slug), the bundle wins — slash dispatch checks bundles first by design; the discovery cache TTL is `30.0s`.

### 20. Sub-agents / delegation

Children are built by `_build_child_agent` in `tools/delegate_tool_dispatch.py` with context from `delegated_child_context` in `agent/delegation_context.py`: fresh conversation history, their own task identifier and dedicated session-DB handle, the parent toolsets minus child-blocked tools, and a focused system prompt from goal plus context. The parent sees only the call and the summary result, never the child intermediate steps, which keeps the parent context small. The synchronous path in `tools/delegate_tool.py` runs one or several children in parallel; with `background=true` the work dispatches per-task-group units in `tools/async_delegation.py` on a daemon executor and pushes a completion event onto the process-registry queue, surfacing as a new turn. Lifecycle states ride in `SubagentHandle` and `SubagentState` in `agent/subagent_lifecycle.py`. Isolation flags plus an environment marker keep the Kanban dispatcher identity separate.

**Watch out:** there is no wall-clock kill for slow child work — staleness is progress-based: `450s` idle between turns and `1200s` stuck on the same tool, then interrupt plus a `120s` grace before a forced `stalled` finish.

### 21. Planning & todo tracking

Todos live in `TodoStore` in `tools/todo_tool.py` as in-memory items of `{id, content, status, parent?}` scoped per agent. One `todo_tool` reads the list when `todos` is omitted, else replaces or merges by identifier with a monotonic revision number that rejects stale updates. The list is re-injected after compression under an active-task-list-preserved marker, keeping only active items plus active parents so plans survive compaction. Plans have no separate engine: `build_plan_prompt` in `agent/plan_prompt.py` returns a normal-turn prompt that forbids implementation and requires a markdown plan under `.hermes/plans/`. The advisor mode in `agent/moa_loop.py` (Mixture of Agents, parallel advisor models) marks one turn advisor-enabled where parallel reference advisors without tools advise and the normal loop aggregator keeps tool calling.

**Watch out:** caps are 256 todo items, 4000 characters per item, 512,000 result characters; reference fan-out is capped at 8 workers.

### 22. MCP / dynamic external tools

As a client, Hermes connects to the `mcp_servers` configuration entries (standard input/output, streamable HyperText Transfer Protocol (HTTP), and Server-Sent Events — SSE, a one-way streaming transport) on one background daemon event loop with long-lived per-server `MCPServerTask` entries in `tools/mcp_tool.py`. Discovery in `tools/mcp_tool_discovery.py` (`discover_mcp_tools`) registers remote tools into the local registry, while `tools/mcp_tool_lifecycle.py` (`shutdown_mcp_servers`) tracks child process identifiers and groups for orphan kill. Lazy servers defer connecting until first tool use; failures get a geometrically capped retry cooldown so a dead server does not stall turns. The opposite direction is `mcp_serve.py`, which exposes Hermes conversations as a standard-input/output MCP server. Ready-made definitions ship in `optional-mcps/` with 65 vendored server definitions.

**Watch out:** lazy-connect defaults to OFF per server; the malware-database (Open Source Vulnerabilities, OSV) preflight timeout is `12.0s`, just above the `10s` check, and fails open; stale schema-cache phantom tools are deregistered on live connect.

### 23. Hooks, plugins & events

Request payloads pass through `ApiRequestHooksMixin` in `agent/api_request_hooks.py`, which coerces, redacts, and caps payloads and routes request errors through the lifecycle handler. Shell `hooks:` configuration entries in `agent/shell_hooks.py` (`ShellHookSpec`, `register_from_config`) wire standard-input JSON scripts receiving `{hook_event_name, tool_name, tool_input, session_id, cwd, extra}` whose standard-output JSON can block, modify, or add context; registration requires per-event-per-command allowlist consent. Streaming observers in `agent/plugin_stream_hooks.py` (`enqueue_plugin_stream_hook`) give each callback its own bounded queue plus daemon worker so plugin code never runs on the token path. Round-end verification in `agent/verify_hooks.py` (`pre_verify`) is a continue gate with bounded nudges. Trusted plugins get host-routed model access through `PluginLlm` in `agent/plugin_llm.py`, gated by allow-override flags, with install safety from `scan_plugin` and runtime guarding in `tools/plugin_guard.py`. Catalogued plugins ship under `plugins/` and `plugin-catalog/`.

**Watch out:** exit-code 2 blocks only `pre_tool_call`; hooks fail open unless configured fail-closed; the stream queue holds 1024 entries and drops oldest when full; a `dangerous` plugin verdict blocks even with `--force`.

### 24. Background & concurrency

`terminal(background=true)` spawns through `spawn_background_process` in `tools/terminal_tool_background.py` via the process registry in `tools/process_registry.py` (a local subprocess, or remote execute in a sandbox), with a rolling output buffer, poll, log, wait, and kill operations, a JSON (JavaScript Object Notation) checkpoint for crash recovery, and a gateway routing stamp so completion and watch notifications start a new turn. Threads come from `DaemonThreadPoolExecutor` in `tools/daemon_pool.py`, which uses daemon workers without the standard-library exit join so wedged work never blocks exit, and propagates context variables. `PeriodicScheduler` in `agent/periodic_scheduler.py` replaces per-child sleep threads with one daemon timer heap where each due body runs on a short-lived worker without self-overlap. Post-turn review in `agent/background_review.py` (`prepare_background_review_run`) forks an agent after a turn on a daemon thread to propose memory and skill writes without touching the main prompt cache. Batch datasets in JSON Lines (JSONL, one object per line) run through `batch_runner.py` on a multiprocessing pool with per-batch outputs and `--resume`.

**Watch out:** registry limits are 200,000 output characters, `1800s` finished-process TTL, 64 processes with LRU eviction; watch-pattern minimum interval is `15s` with a 3-strike limit and 8 lifetime hits; review cancel waits only `2.0s` so the foreground turn never blocks.

## Distinctive choices

- Prompt cache is treated as a correctness invariant, not an optimization: the prompt is frozen per session in `agent/system_prompt.py` and plugin sections restore from stored bytes by strict frame match instead of re-running code.
- The provider wire format travels as a sidecar, not as the stored message: `compose_user_api_content` and `substitute_api_content` in `agent/turn_context.py` keep stored content clean while the sent bytes stay cache-stable.
- Tool calls persist before they execute: `agent/turn_tool_round.py` ends the turn with `session_persistence_failed` if the database append fails, so tools never run without a record.
- Snapshots are automatic shadow-git checkpoints, not user commits: `tools/checkpoint_manager.py` snapshots once per directory per turn under `~/.hermes/checkpoints/store/` keyed by path hash.
- Oversize tool output spills to disk with a preview pointer instead of truncating silently: `tools/tool_result_storage.py` writes `$HERMES_HOME/cache/spillover/{id}.txt` while `tools/budget_config.py` caps per-result and per-turn totals.
- Child-agent staleness is progress-based, not wall-clock: `agent/subagent_lifecycle.py` and `tools/async_delegation.py` interrupt after `450s` idle or `1200s` stuck on one tool, with no fixed kill timer.

## What we take from it

- Copy the frozen-prompt-plus-sidecar pattern (`agent/system_prompt.py`, `agent/turn_context.py`): it keeps provider caches hot and makes every turn cheaper without losing memory or plugin injections.
- Copy persist-before-execute (`agent/turn_tool_round.py`) and automatic per-turn shadow snapshots (`tools/checkpoint_manager.py`): durability and undo should be invariants, not optional flags.
- Copy the three-layer output discipline (`tools/tool_output_limits.py`, `tools/tool_result_storage.py`, `tools/budget_config.py`): cap inline, spill to disk with a preview, then cap the turn total — large outputs stay usable instead of blowing up context.
- Do not copy the Hermes-specific provider quirk tables (`agent/provider_registry.py`, `agent/provider_base.py`, `agent/models_dev.py`) verbatim: the profiles, fallback maps, and catalog translations encode its supported providers and will rot in a new harness.
- Do not copy the gateway-flavored waiting machinery (`tools/approval_human_wait.py`, `agent/periodic_scheduler.py`, `tools/process_registry.py`) unless you also run multi-surface messaging: human-wait ceilings, timer heaps, and routing stamps solve Hermes's always-on deployment, not a minimal harness.
