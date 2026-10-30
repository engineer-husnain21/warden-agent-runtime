# Warden Agent Runtime — 7-Day Plan

## Progress
- [x] Day 1 — Setup (Day 0) + foundation: config, logging, exceptions, DB, middlewares, CI
- [x] Day 2 — Data layer, LLM clients, auth
- [ ] Day 3 — MCP servers + ToolClient
- [ ] Day 4 — Policies + agents
- [ ] Day 5 — LangGraph orchestrator: approval interrupt + checkpoints
- [ ] Day 6 — Services, routers, Streamlit console
- [ ] Day 7 — Evals + CI gate, README, ADRs, demo, final review

## Rules that apply every day
- One branch per day → PR → merge with **"Create a merge commit"** (never squash), then delete the branch.
- Commit and push autonomously once the green check passes and no secrets are staged (CLAUDE.md 12.4).
- Every commit is green. The green check (PowerShell, Windows):
  `uv run ruff check . ; uv run ruff format --check . ; uv run mypy ; uv run pytest -q`
  (pre-commit and CI run exactly these commands as local `uv run` hooks / steps).
- **mypy targets live in one place:** `[tool.mypy] files` in pyproject.toml, and bare `uv run mypy` in the green check,
  pre-commit and CI all read it. It starts as `["app", "tests"]`. The commit that creates a new top-level Python folder
  adds that folder to `files` in the same commit: `mcp_servers` (Day 3 #2), `web` (Day 6 #11), `evals` (Day 7 #1).
  mypy never points at a folder that doesn't exist.
- Unit tests use only `FakeLlmClient` / `FakeToolClient` / httpx `MockTransport`. No network.
- The last commit of each day is `docs(plan): mark Day N complete` (ticks the checkbox above).
- No Docker. Everything runs with `uv run` on Windows.

## Decisions taken up front
| Decision | Choice | ADR |
|---|---|---|
| Tool execution | `ToolExecutorAgent` (non-LLM, inherits `BaseAgent`, keeps its constructor contract, uses only `ToolClient`) | 0001 |
| Durable runs | LangGraph `interrupt()` + checkpoints via `CheckpointRepository` (official async saver chosen from the DB URL) | 0002 |
| Step/audit persistence | Orchestrator yields `StepEvent`s; `AgentRunService` persists `RunStep` + `AuditLogEntry` | 0003 |
| CI eval gate | Real Groq, separate job on PRs to `main`, success ≥ 0.8, backoff + concurrency ≤ 2, GitHub MCP in dry-run | 0004 |
| Prompt loading | `PromptLoader` Protocol + `FilePromptLoader` in `app/core/` | — |
| Cost | `LlmClient` returns usage incl. estimated cost from per-model prices in `.env` | — |

Default roles (`TOOL_PERMISSION_RULES` in config):
- **viewer**: read-only tools (`warehouse.*`, `github.list_issues`, `notifier.list_outbox`). Everything else is denied.
- **operator**: all tools; `github.create_issue` and `notifier.send_notification` need approval.
- **admin**: all tools allowed. Only an admin can approve or reject.

---

## Day 1 — Setup (Day 0) + foundation
**Goal:** A green, CI-checked FastAPI skeleton with config, logging, exceptions, DB + Alembic and core middlewares.
**Branch:** `main` for the two docs commits, then `feat/day-1-setup-foundation`

| # | Commit | Files | Proving test |
|---|---|---|---|
| 0a | `docs: add project guidelines (CLAUDE.md)` | CLAUDE.md | — (docs) |
| 0b | `docs: add 7-day project plan` | docs/PLAN.md | — (docs) |
| 1 | `build: init uv project with Python 3.12` | pyproject.toml, uv.lock, .python-version, app/__init__.py, tests/unit/test_smoke.py | `test_import_app_when_installed_succeeds` |
| 2 | `chore: add .gitignore, .gitattributes and .env.example` | .gitignore (section 10 + `*.db`, `evals/reports/`), .gitattributes (`* text=auto eol=lf`), .env.example | smoke test still green |
| 3 | `build: configure ruff, mypy and pytest` | pyproject.toml (tool sections, strict mypy with `files = ["app", "tests"]`, asyncio_mode=auto) | `uv run mypy` + pytest green |
| 4 | `chore: add pre-commit hooks for ruff, mypy and pytest` | .pre-commit-config.yaml (local hooks: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, `uv run pytest -q`) | `uv run pre-commit run --all-files` |
| 5 | `chore: scaffold app layer packages` | app/{core,middlewares,routers,schemas,services,orchestrators,agents,prompts,clients,repositories,models,db}/__init__.py, tests/unit/<same>/__init__.py, tests/integration/__init__.py | `test_layer_packages_when_imported_exist` |
| 6 | `ci: add GitHub Actions workflow for lint, types and tests` | .github/workflows/ci.yml (setup-uv, `uv sync`, ruff, bare `uv run mypy`, pytest on windows-latest + ubuntu-latest) | CI run green on push |
| 7 | `feat(core): add Settings with pydantic-settings` | app/core/config.py, .env.example | tests/unit/core/test_config.py `test_settings_when_env_missing_uses_defaults` |
| 8 | `feat(core): add shared logger with request id context` | app/core/logging.py | test_logging.py `test_get_logger_when_request_id_set_includes_it` |
| 9 | `feat(core): add custom exception hierarchy` | app/core/exceptions.py (`WardenError`, `NotFoundError`, `PermissionDeniedError`, `InvalidInputError`, `ExternalServiceError`, `AgentOutputError`; no name clashes with `pydantic.ValidationError`) | test_exceptions.py `test_not_found_error_when_created_has_404_status` |
| 10 | `feat(db): add async engine and session factory` | app/db/session.py, app/db/base.py | tests/unit/db/test_session.py `test_get_session_when_sqlite_memory_executes_select` |
| 11 | `build(db): set up Alembic for async SQLite` | alembic.ini, app/db/migrations/{env.py,script.py.mako} | `test_alembic_upgrade_when_empty_db_succeeds` |
| 12 | `feat(middlewares): add RequestIdMiddleware with access logging` | app/middlewares/request_id_middleware.py | `test_dispatch_when_no_header_sets_x_request_id` |
| 13 | `feat(middlewares): add ErrorHandlerMiddleware` | app/middlewares/error_handler_middleware.py | `test_dispatch_when_warden_error_returns_json_error` |
| 14 | `feat(app): add main.py with health router` | app/main.py, app/routers/health_router.py, app/core/dependencies.py | tests/integration/test_health.py `test_get_health_when_app_running_returns_ok` |
| 15 | `docs(plan): mark Day 1 complete` | docs/PLAN.md | — |

Unplanned extra commit: `chore: ignore local Claude Code settings` (.gitignore).

**Run / test:**
`uv sync ; uv run pre-commit install ; uv run alembic upgrade head ; uv run uvicorn app.main:app --reload --no-access-log`
then `curl.exe http://127.0.0.1:8000/api/v1/health` + the green check.
**Done when:** CI is green on GitHub; `/api/v1/health` returns `{"status":"ok"}` with an `X-Request-ID` header; `alembic upgrade head` creates `warden.db`.
**Risks → fallback:** async Alembic on Windows path issues → use `sqlite+aiosqlite:///./warden.db` relative URL and run sync `run_sync` in env.py. Mypy strictness slows the day → enable strict only for `app/`, relax for tests.

---

## Day 2 — Data layer, LLM clients, auth
**Goal:** Persist runs, steps, approvals and audit entries, and call Groq/Gemini through one `LlmClient` switched by `.env`.
**Branch:** `feat/day-2-data-and-llm-clients`

| # | Commit | Files | Proving test |
|---|---|---|---|
| 1 | `feat(models): add AgentRun and RunStep entities` | app/models/agent_run.py, app/models/run_step.py | tests/unit/models/test_agent_run.py `test_agent_run_when_created_has_pending_status` |
| 2 | `feat(models): add Approval and AuditLogEntry entities` | app/models/approval.py, app/models/audit_log_entry.py | `test_audit_log_entry_when_created_sets_timestamp` |
| 3 | `build(db): add initial migration for runs, steps, approvals, audit` | app/db/migrations/versions/0001_initial.py | `test_alembic_upgrade_when_applied_creates_all_tables` |
| 4 | `feat(repositories): add BaseRepository and AgentRunRepository` | app/repositories/base_repository.py, agent_run_repository.py | `test_get_by_id_when_missing_raises_not_found` |
| 5 | `feat(repositories): add ApprovalRepository` | app/repositories/approval_repository.py | `test_list_pending_when_mixed_statuses_returns_only_pending` |
| 6 | `feat(repositories): add append-only AuditLogRepository` | app/repositories/audit_log_repository.py | `test_repository_when_inspected_has_no_update_or_delete` + ordering test |
| 7 | `feat(clients): add LlmClient Protocol and LlmResponse with usage` | app/clients/llm_client.py, app/schemas/llm_usage.py, tests/fakes/{__init__,fake_llm_client}.py, **CLAUDE.md 12.3** (new row: `tests/fakes/`, fake clients for unit tests, `Fake<Name>Client`) | `FakeLlmClient` satisfies the Protocol (mypy) + `test_fake_llm_client_when_called_returns_scripted_reply` |
| 8 | `feat(clients): add retry with exponential backoff for rate limits` | app/clients/backoff.py | `test_retry_with_backoff_when_429_then_ok_retries_once` |
| 9 | `feat(clients): add GroqLlmClient` | app/clients/groq_llm_client.py | MockTransport: `test_complete_when_ok_returns_tokens_and_cost` |
| 10 | `feat(clients): add GeminiLlmClient` | app/clients/gemini_llm_client.py | MockTransport: `test_complete_when_ok_returns_tokens_and_cost` |
| 11 | `feat(core): add PromptLoader and LLM provider wiring` | app/core/prompt_loader.py, app/core/file_prompt_loader.py, app/core/dependencies.py | `test_get_llm_client_when_provider_gemini_returns_gemini` , `test_load_when_file_missing_raises_not_found` |
| 12 | `feat(middlewares): add ApiKeyAuthMiddleware with roles` | app/middlewares/api_key_auth_middleware.py, app/schemas/role.py, app/main.py, config `API_KEYS` + `AUTH_EXEMPT_PATHS` (default `/api/v1/health`, `/docs`, `/openapi.json`) | `test_dispatch_when_key_unknown_returns_401`, `test_dispatch_when_viewer_key_sets_role`, `test_dispatch_when_exempt_path_without_key_passes` (parametrised over the 3 paths); Day 1 `test_get_health_when_app_running_returns_ok` stays green with no key |
| 13 | `docs(plan): mark Day 2 complete` | docs/PLAN.md | — |

Extra commits: `chore: hide Alembic template from GitHub language stats`, `feat(db): add column helpers and shared db_session test fixture` (split out of #1), `docs: allow autonomous commits in workflow rules`.
Notes: `httpx` moved from dev to runtime dependency (#8); `ConfigurationError` and `AuthenticationError` (401) added to `core/exceptions.py` (#11, #12).

**Run / test:** `uv run alembic upgrade head ; uv run pytest tests/unit/repositories tests/unit/clients -q` + the green check.
Manual smoke (needs `GROQ_API_KEY` or `GEMINI_API_KEY` in `.env`):
`uv run python -c "import asyncio; from app.core.dependencies import get_llm_client; from app.schemas.llm_message import LlmMessage; print(asyncio.run(get_llm_client().complete([LlmMessage(role='user', content='Say hi')])))"`.
**Done when:** the migration creates 4 tables; the LLM provider switches between Groq and Gemini by editing only `LLM_PROVIDER`; an unauthenticated request gets a 401.
**Risks → fallback:** Gemini API differences eat time → ship Groq first, Gemini via its OpenAI-compatible endpoint. SQLAlchemy async session lifetimes in tests → one `session` fixture with `sqlite+aiosqlite:///:memory:` + `StaticPool`.

---

## Day 3 — MCP servers + ToolClient
**Goal:** Three FastMCP servers (warehouse, github, notifier) reachable only through `McpToolClient`.
**Branch:** `feat/day-3-mcp-servers`
**Manual prerequisite (user):** create `warden-sandbox` (`gh repo create warden-sandbox --public --add-readme`) and a fine-grained token (see the appendix).

| # | Commit | Files | Proving test |
|---|---|---|---|
| 1 | `chore(data): add demo orders dataset` | data/orders.csv (≈500 orders, failed ones with causes) | `test_orders_csv_when_loaded_has_failed_orders` |
| 2 | `feat(mcp-warehouse): seed demo SQLite from data/` | mcp_servers/__init__.py, mcp_servers/warehouse/{__init__,seed}.py, pyproject.toml (`mcp_servers` added to mypy `files`) | tests/unit/mcp_servers/warehouse/test_seed.py `test_seed_when_run_twice_is_idempotent` |
| 3 | `feat(mcp-warehouse): add read-only SQL tools` | mcp_servers/warehouse/server.py (`list_tables`, `describe_table`, `run_query`; opened `mode=ro`) | `test_run_query_when_select_returns_rows` |
| 4 | `feat(mcp-warehouse): reject write statements and cap rows` | server.py | `test_run_query_when_delete_raises_error` |
| 5 | `feat(mcp-github): add list and create issue tools in dry-run mode` | mcp_servers/github/{__init__,server}.py | `test_create_issue_when_dry_run_returns_fake_issue` |
| 6 | `feat(mcp-github): add live mode via GitHub REST API` | mcp_servers/github/github_api.py | MockTransport: `test_create_issue_when_live_posts_to_repo` |
| 7 | `feat(mcp-notifier): add mock notifier with outbox table` | mcp_servers/notifier/{__init__,server}.py | `test_send_notification_when_called_writes_outbox_row` |
| 8 | `feat(clients): add ToolClient Protocol and tool schemas` | app/clients/tool_client.py, app/schemas/tool_call.py (`ToolSpec`, `ToolCall`, `ToolResult`), tests/fakes/fake_tool_client.py | `test_fake_tool_client_when_called_returns_scripted_result` |
| 9 | `feat(clients): add McpToolClient over stdio` | app/clients/mcp_tool_client.py, config `MCP_SERVERS` | tests/integration/test_mcp_tool_client.py `test_list_tools_when_servers_started_returns_all_three` |
| 10 | `feat(core): start and stop MCP sessions in app lifespan` | app/main.py, app/core/dependencies.py | `test_lifespan_when_app_starts_connects_tool_client` |
| 11 | `docs(plan): mark Day 3 complete` | docs/PLAN.md | — |

**Run / test:** `uv run python -m mcp_servers.warehouse.seed ; uv run mcp dev mcp_servers/warehouse/server.py` (MCP Inspector) ; `uv run pytest tests/unit/mcp_servers tests/integration -q` + the green check.
**Done when:** `McpToolClient.list_tools()` returns the tools of all 3 servers; with `GITHUB_MODE=live`, one real issue is created in `warden-sandbox`.
**Risks → fallback:** stdio subprocesses on Windows (Proactor loop, `uv run` paths) → launch with `sys.executable -m mcp_servers.<name>.server`; if that still fails, use FastMCP's streamable-HTTP transport on localhost ports. GitHub token issues → stay in dry-run and do the live demo on Day 7.

---

## Day 4 — Policies + agents
**Goal:** Permission decisions and five single-job agents, all unit-tested with fakes.
**Branch:** `feat/day-4-policies-and-agents`

| # | Commit | Files | Proving test |
|---|---|---|---|
| 1 | `feat(policies): add ToolPermissionPolicy with role rules` | app/policies/{__init__,tool_permission_policy}.py, app/schemas/policy_decision.py, config `TOOL_PERMISSION_RULES`, **CLAUDE.md sections 1/2/3/5 tables** | tests/unit/policies/test_tool_permission_policy.py parametrised role×tool matrix, e.g. `test_decide_when_operator_creates_issue_needs_approval` |
| 2 | `feat(agents): add BaseAgent` | app/agents/base_agent.py (exactly as in section 6) | `test_base_agent_when_run_not_implemented_cannot_instantiate` |
| 3 | `feat(agents): add PlannerAgent with planner prompts` | app/agents/planner_agent.py, app/schemas/agents/planner.py, app/prompts/planner_system.md | `test_run_when_llm_returns_steps_returns_plan` |
| 4 | `feat(agents): add ToolSelectorAgent` | tool_selector_agent.py, schemas/agents/tool_selector.py, prompts/tool_selector_system.md | `test_run_when_tool_unknown_raises_agent_output_error` |
| 5 | `feat(agents): add ToolExecutorAgent as non-LLM agent` | tool_executor_agent.py, schemas/agents/tool_executor.py | `test_run_when_called_never_uses_llm_client` |
| 6 | `docs(adr): add 0001 ToolExecutorAgent as a non-LLM agent` | docs/adr/0001-tool-executor-agent.md | — (docs) |
| 7 | `feat(agents): add StepReviewerAgent` | step_reviewer_agent.py, schemas/agents/step_reviewer.py, prompts/step_reviewer_system.md | `test_run_when_result_empty_returns_not_ok` |
| 8 | `feat(agents): add ReporterAgent` | reporter_agent.py, schemas/agents/reporter.py, prompts/reporter_system.md | `test_run_when_steps_given_returns_markdown_report` |
| 9 | `feat(agents): repair malformed LLM JSON once before failing` | app/agents/base_agent.py helper `_parse_output` (protected, no new public method) | `test_run_when_json_invalid_twice_raises_agent_output_error` |
| 10 | `docs(plan): mark Day 4 complete` | docs/PLAN.md | — |

**Run / test:** `uv run pytest tests/unit/policies tests/unit/agents -q` + the green check.
**Done when:** every agent has a passing test with `FakeLlmClient`; the policy matrix covers all 3 roles × all tools; CLAUDE.md tables list `policies/`, `mcp_servers/`, `evals/`.
**Risks → fallback:** LLM JSON adherence → use the provider JSON mode + Pydantic schema in the prompt; repair-once loop (commit 9).

---

## Day 5 — LangGraph orchestrator: approval interrupt + checkpoints
**Goal:** `AgentRunOrchestrator` runs plan → (select → policy → approve? → execute → review)* → report, pauses on `needs_approval`, and resumes from its checkpoint.
**Branch:** `feat/day-5-orchestrator`

| # | Commit | Files | Proving test |
|---|---|---|---|
| 1 | `feat(schemas): add RunState and StepEvent models` | app/schemas/run_state.py, app/schemas/step_event.py | `test_step_event_when_serialised_roundtrips` |
| 2 | `feat(repositories): add CheckpointRepository` | app/repositories/checkpoint_repository.py (official async saver selected by URL scheme) | `test_get_saver_when_sqlite_url_persists_and_reloads_checkpoint` |
| 3 | `feat(orchestrators): add graph skeleton with plan and report nodes` | app/orchestrators/agent_run_orchestrator.py | `test_stream_when_plan_has_no_steps_yields_report_event` |
| 4 | `feat(orchestrators): add select, execute and review step loop` | same | `test_stream_when_two_steps_yields_events_in_order` |
| 5 | `feat(orchestrators): enforce ToolPermissionPolicy and deny calls` | same | `test_stream_when_viewer_creates_issue_yields_denied_event` |
| 6 | `feat(orchestrators): pause with interrupt on needs_approval` | same | `test_stream_when_operator_creates_issue_pauses_awaiting_approval` |
| 7 | `feat(orchestrators): resume from checkpoint with approval decision` | same (`Command(resume=...)`) | `test_resume_when_rejected_skips_tool_and_continues` |
| 8 | `feat(orchestrators): attach tokens, latency and cost to StepEvents` | same, app/schemas/step_event.py | `test_stream_when_llm_used_events_carry_usage` |
| 9 | `feat(orchestrators): cap steps and retry a step on failed review` | same, config `MAX_STEPS`, `MAX_STEP_RETRIES` | `test_stream_when_review_fails_twice_marks_step_failed` |
| 10 | `test(orchestrators): resume crashed run from last checkpoint` | tests/integration/test_orchestrator_resume.py | `test_resume_when_crash_after_step_one_does_not_rerun_step_one` |
| 11 | `docs(adr): add 0002 durable runs with LangGraph checkpoints` | docs/adr/0002-durable-runs-langgraph-checkpoints.md | — |
| 12 | `docs(adr): add 0003 service persists orchestrator StepEvents` | docs/adr/0003-step-event-stream-persistence.md | — |
| 13 | `docs(plan): mark Day 5 complete` | docs/PLAN.md | — |

The orchestrator imports only agents, policies, schemas and the `CheckpointRepository` saver (injected). It has no DB sessions and no direct LLM or tool calls.
**Run / test:** `uv run pytest tests/unit/orchestrators tests/integration/test_orchestrator_resume.py -q` + the green check.
**Done when:** with fakes, a run pauses on `create_issue`, survives a process restart and resumes without repeating finished steps.
**Risks → fallback:** LangGraph interrupt/resume semantics (nodes re-run from the start on resume) → keep the side effect only in the node *after* the interrupt node. If the saver wrapper fights with aiosqlite, give the saver its own connection from `DATABASE_URL`.

---

## Day 6 — Services, routers, Streamlit console
**Goal:** The full API (runs, steps, report, metrics, approvals, audit) and a web console to submit runs, watch traces and approve.
**Branch:** `feat/day-6-api-and-console`

| # | Commit | Files | Proving test |
|---|---|---|---|
| 1 | `feat(schemas): add agent run, approval and audit DTOs` | app/schemas/agent_run_dtos.py, approval_dtos.py, audit_dtos.py | `test_create_agent_run_request_when_task_empty_fails_validation` |
| 2 | `feat(services): add AuditService` | app/services/audit_service.py | `test_record_when_called_appends_entry` |
| 3 | `feat(services): add AgentRunService create and get` | app/services/agent_run_service.py | `test_create_run_when_valid_persists_pending_run` |
| 4 | `feat(services): persist StepEvents as RunStep and audit entries` | agent_run_service.py | `test_execute_when_events_streamed_persists_each_step_and_audit` |
| 5 | `feat(services): add ApprovalService approve and reject with resume` | app/services/approval_service.py | `test_decide_when_non_admin_raises_permission_denied` |
| 6 | `feat(services): resume interrupted runs on startup` | agent_run_service.py, app/main.py lifespan | `test_resume_pending_when_run_left_running_resumes_it` |
| 7 | `feat(routers): add agent runs router` | app/routers/agent_run_router.py: `POST /api/v1/agent-runs` (202), `GET /{id}`, `/{id}/steps`, `/{id}/report`, `/{id}/metrics` | tests/unit/routers `test_post_agent_runs_when_valid_returns_202` |
| 8 | `feat(routers): add approvals router` | app/routers/approval_router.py: `GET /api/v1/approvals?status=pending`, `POST /{id}/decisions` | `test_post_decision_when_viewer_returns_403` |
| 9 | `feat(routers): add audit log router` | app/routers/audit_log_router.py: `GET /api/v1/audit-log-entries` (admin) | `test_get_audit_log_when_admin_returns_entries` |
| 10 | `test(integration): full run with approval through the API` | tests/integration/test_agent_run_flow.py (fake LLM, MCP dry-run) | `test_run_when_approved_completes_with_report_and_audit` |
| 11 | `feat(web): add Streamlit console with run list and task form` | web/__init__.py, web/app.py, web/api_client.py, pyproject.toml (`web` added to mypy `files`) | tests/unit/web `test_api_client_when_create_run_posts_task` (MockTransport) |
| 12 | `feat(web): add run trace and metrics view` | web/pages/run_detail.py | Streamlit `AppTest`: `test_run_detail_when_loaded_shows_steps_table` |
| 13 | `feat(web): add approvals inbox` | web/pages/approvals.py | `AppTest`: `test_approvals_when_approve_clicked_calls_api` |
| 14 | `docs(plan): mark Day 6 complete` | docs/PLAN.md | — |

**Run / test:** terminal 1 `uv run uvicorn app.main:app --no-access-log` ; terminal 2 `uv run streamlit run web/app.py` ;
`curl.exe -X POST http://127.0.0.1:8000/api/v1/agent-runs -H "X-API-Key: operator-dev-key" -H "Content-Type: application/json" -d "{\"task\":\"Find orders that failed in the last 24 hours and open a GitHub issue for the top 3 causes\"}"` + the green check.
**Done when:** the headline task runs end-to-end with real Groq: it pauses, an admin approves it in the console, the issue is created (dry-run or live), and the report, trace, metrics and audit log are all visible.
**Risks → fallback:** a heavy day → if behind, cut the console to one page (runs + approve buttons) and move the metrics view to Day 7 morning. Background-task + session lifetime bugs → the service opens its own session per run via the session factory.

---

## Day 7 — Evals + CI gate, README, ADRs, demo, final review
**Goal:** Measured quality (30+ scenarios, CI gate ≥ 0.8), a complete README with real numbers, ≥ 4 ADRs, a recorded demo and a clean review.
**Branch:** `feat/day-7-evals-and-docs`

| # | Commit | Files | Proving test |
|---|---|---|---|
| 1 | `feat(evals): add scenario schema and YAML loader` | evals/__init__.py, evals/scenario.py, pyproject.toml (`evals` added to mypy `files`) | tests/unit/evals `test_load_scenarios_when_yaml_invalid_raises` |
| 2 | `feat(evals): add runner with success rate and tool-call accuracy` | evals/runner.py (in-process app via httpx `ASGITransport`, semaphore 2, backoff, auto-decides approvals per scenario) | `test_score_when_expected_tools_match_returns_full_accuracy` (fake LLM) |
| 3 | `feat(evals): add warehouse query scenarios` | evals/scenarios/warehouse_*.yaml (10) | `test_all_scenarios_when_loaded_are_valid` |
| 4 | `feat(evals): add github and notifier scenarios` | evals/scenarios/{github,notifier}_*.yaml (10) | same |
| 5 | `feat(evals): add permission and approval scenarios` | evals/scenarios/policy_*.yaml (10+: deny, approve, reject per role) | same |
| 6 | `feat(evals): write JSON and Markdown reports and enforce threshold` | evals/runner.py, evals/reports/.gitkeep | `test_main_when_score_below_threshold_exits_1` |
| 7 | `ci: add eval job on PRs to main with Groq secret` | .github/workflows/evals.yml (`GITHUB_MODE=dry-run`, `EVAL_THRESHOLD=0.8`, uploads report artifact) | eval job green on this PR |
| 8 | `docs(adr): add 0004 CI eval gate with real LLM` | docs/adr/0004-ci-eval-gate.md | — |
| 9 | `docs: add README with architecture, quickstart and API examples` | README.md (problem, Mermaid request-flow diagram, quickstart, curl examples, design decisions) | — |
| 10 | `docs: add real eval metrics and cost/latency numbers` | README.md (from evals/reports + /metrics of the demo run) | — |
| 11 | `docs: add recorded demo run` | docs/demo/demo.md (API transcript), docs/demo/warden-demo.gif (≤ 10 MB, recorded with ScreenToGif) | — |
| 12 | `refactor: fix findings from CLAUDE.md compliance review` | as found (layer imports, naming, file size ≤ 300 lines, type hints, no print) | full green check + import-direction test `test_layers_when_imported_never_import_upward` |
| 13 | `docs(plan): mark Day 7 complete` | docs/PLAN.md | — |

**Final review checklist:** sections 1–4 (flow, folders, `__init__.py`, no upward or skipped imports), 5 (naming/suffixes), 6 (agents), 7 (no hardcoded keys, `.env.example` complete), 8 (ruff/mypy/no print/≤ 300 lines), 9 (every agent and service tested), 10 & 12.4 (no secrets, no squash merges), 12.3 placements.
**Run / test:** `uv run python -m evals.runner --threshold 0.8` (real Groq, writes `evals/reports/`) + the green check; open the PR to `main` → the `evals` job must pass.
**Done when:** 30+ scenarios, success ≥ 0.8 locally and in CI; README shows real metrics; 4 ADRs; demo GIF committed; review findings fixed.
**Risks → fallback:** Groq rate limits/flakiness → concurrency 1, longer backoff, cache the scenario plan per run; if CI is still flaky, run the job on `workflow_dispatch` + PRs and record the reason in ADR 0004. Score below 0.8 → fix prompts first, never lower the threshold silently.

---

## Appendix — fine-grained GitHub token for warden-sandbox
1. Create the repo: `gh repo create warden-sandbox --public --add-readme` (Issues are on by default).
2. GitHub → avatar → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
3. Name `warden-sandbox-issues`, expiration 30 days, resource owner = your account.
4. **Repository access:** *Only select repositories* → `warden-sandbox`.
5. **Repository permissions:** *Issues: Read and write*. *Metadata: Read-only* is added automatically. Leave everything else on *No access*.
6. Generate, copy it once, and put it only in local `.env` as `GITHUB_TOKEN=...` with `GITHUB_REPO=<you>/warden-sandbox` and `GITHUB_MODE=live`.
   It is never committed and never added to CI (CI uses dry-run).
