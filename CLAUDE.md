# AI Project Structure Guidelines (Python)

This is the standard structure for every AI project we build in Python. It keeps code clean, layered and easy to track, so anyone on the team can open any project and know where everything is.

Give this file to your coding agent as well (save it as `CLAUDE.md` or `ARCHITECTURE.md` in the repo root) so it follows these rules from the first line of code.

---

## 1. Request Flow

Every request follows one path, top to bottom:

```
main.py → middlewares → routers → services → orchestrators → agents → clients (LLM, search, external APIs)
                                     ↓
                               repositories → db
```

---

## 2. Folder Structure

```
project-root/
  app/
    main.py              # App setup, middleware and router registration
    core/                # Config, DI, logging, custom exceptions
    middlewares/         # Request ID, logging, global error handler
    routers/             # Endpoints only, no logic
    schemas/             # Request/response DTOs (Pydantic)
    services/            # Business logic
    orchestrators/       # Runs the flow between agents
    agents/              # base_agent.py + one class per agent
    prompts/             # Prompts as .md files
    clients/             # LLM, search and external API clients
    repositories/        # Data access
    models/              # DB entities (SQLAlchemy)
    db/                  # DB session and setup
  tests/
    unit/                # Mirrors app/ folder by folder
    integration/         # End-to-end flows
  web/                   # Frontend (if any)
  data/                  # Sample/demo data
  .env.example           # All env vars with dummy values
  .gitignore
  pyproject.toml
  README.md
```

Every folder inside `app/` has an `__init__.py`.

---

## 3. Layer Responsibilities

| Layer | Does | Never does |
|---|---|---|
| `main.py` | Creates the app, registers middlewares and routers | Business logic |
| `middlewares/` | Cross-cutting work on every request: logging, request ID, error handling | Call services or agents |
| `routers/` | Receive request, validate with schema, call one service, return response | Logic, DB calls, LLM calls |
| `services/` | Business rules, decide what happens, call orchestrators and repositories | Talk to HTTP or LLM APIs directly |
| `orchestrators/` | Decide which agent runs, in what order, and pass data between them | DB calls, direct LLM calls |
| `agents/` | One focused AI task each (plan, research, write, review) | Touch the DB, call other agents directly |
| `clients/` | The only place that talks to outside APIs (LLM, search, email, etc.) | Business logic |
| `repositories/` | All reads and writes to DB or files | Business logic |
| `models/` | DB table definitions | Logic |
| `schemas/` | Input/output shapes and validation | Logic |
| `prompts/` | Prompt text, one file per prompt | Code |
| `core/` | Settings, DI setup, logger, exception classes | Feature logic |

---

## 4. Dependency Rules

1. Calls only go **downward** in the flow. A lower layer never imports a higher one.
2. **No skipping layers.** A router never calls a repository or an agent directly.
3. Agents never call each other. The orchestrator connects them.
4. Only `clients/` talk to the outside world. Only `repositories/` touch data.
5. Depend on base classes or Protocols, not on concrete classes. Inject the real one through DI.
6. No circular imports. If two modules need each other, the design is wrong.

---

## 5. Naming Conventions

**Golden rule:** one main class per file, and the file name is the class name in snake_case.
`planner_agent.py` holds only `PlannerAgent`.

| Thing | Convention | Example |
|---|---|---|
| Files / folders | snake_case | `research_service.py` |
| Classes | PascalCase + layer suffix | `ResearchService`, `PlannerAgent` |
| Functions / methods | snake_case, verb first | `create_report()`, `get_by_id()` |
| Variables | snake_case | `report_id` |
| Constants | UPPER_SNAKE | `MAX_RETRIES` |
| Private members | `_` prefix | `_llm_client` |
| Abstract base classes | `Base` prefix | `BaseAgent`, `BaseRepository` |
| Interfaces | Plain name as Protocol (no `I` prefix) | `LlmClient`, `SearchClient` |
| Implementations | Provider prefix | `GroqLlmClient`, `TavilySearchClient` |
| Request DTOs | `Request` suffix | `CreateResearchRequest` |
| Response DTOs | `Response` suffix | `ResearchReportResponse` |
| Agent input/output | `Input` / `Output` suffix | `PlannerInput`, `PlannerOutput` |
| DB entities | Singular noun | `ResearchJob` |
| Router files | `<feature>_router.py` | `research_router.py` |
| URLs | Versioned, plural, kebab-case | `/api/v1/research-jobs` |
| Prompt files | `<agent>_<purpose>.md` | `planner_system.md` |
| Test files | `test_<file>.py` | `test_planner_agent.py` |
| Test functions | `test_<what>_when_<condition>_<expected>` | `test_run_when_no_sources_raises_error` |
| Env vars | UPPER_SNAKE | `LLM_PROVIDER`, `GROQ_API_KEY` |

**Suffix list:** `Service`, `Orchestrator`, `Agent`, `Client`, `Repository`, `Request`, `Response`, `Input`, `Output`, `Middleware`, `Error`.

---

## 6. Agent Rules

Every agent inherits `BaseAgent` and exposes one public method.

```python
# agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from pydantic import BaseModel

TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)

class BaseAgent(ABC, Generic[TInput, TOutput]):
    name: str

    def __init__(self, llm_client: "LlmClient", prompt_loader: "PromptLoader") -> None:
        self._llm_client = llm_client
        self._prompt_loader = prompt_loader

    @abstractmethod
    async def run(self, input: TInput) -> TOutput: ...
```

- Input and output are always Pydantic models.
- Prompts are loaded from `prompts/`, never written inside Python files.
- One agent = one job. If you describe it with "and", split it.
- Agents return data. They do not save, send or log business events.

---

## 7. Config and Dependency Injection

- All settings live in `core/config.py` using `pydantic-settings`, read from `.env`.
- No hardcoded keys, URLs or model names in code.
- `.env.example` lists every variable with a dummy value.
- Wire dependencies in `core/dependencies.py` and inject with FastAPI `Depends`.
- Switching LLM provider (Groq, Gemini, etc.) must only need a `.env` change.

---

## 8. Code Quality

- Type hints on every function and method.
- Use `async` for anything that does I/O.
- Raise custom exceptions from `core/exceptions.py`. The global error middleware turns them into proper HTTP responses.
- Use the shared logger from `core/logging.py`. No `print()`.
- Tools: `ruff` (lint + format), `mypy` (types), `pre-commit` (runs both before every commit).
- Keep files small. If a file passes ~300 lines, split it.

---

## 9. Testing

- `tests/unit/` mirrors `app/` folder by folder.
- Unit tests never call a real LLM or API. Use fake clients.
- `tests/integration/` covers full request flows.
- Every agent and service has at least one test.

---

## 10. Git Hygiene

`.gitignore` must include at least:

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.env
```

Never commit API keys, `.venv` or cache folders.

---

## 11. Adding Anything New

When you need something that does not fit an existing folder, follow these steps before writing code:

1. **Check first.** Re-read section 3. Most new things belong to an existing layer.
2. **Define its one job.** Write one sentence for what it does and what it never does.
3. **Place it in the flow.** Decide who calls it and what it calls. It must fit the top-to-bottom flow in section 1 without breaking the dependency rules.
4. **Create a folder** under `app/` with a plural snake_case name and an `__init__.py`.
5. **Pick a suffix** for its classes and use it on every class in that folder.
6. **Add a base class or Protocol** if it will have more than one implementation.
7. **Mirror it** in `tests/unit/`.
8. **Update this file:** add a row to the tables in sections 1, 2, 3 and 5, so the next developer knows where it lives.

If you are not sure where something goes, ask before building it. A wrong placement is cheap to fix on day one and expensive later.

---

## 12. Project-Specific Rules: Warden Agent Runtime

> Sections 1–11 are the team standard and always win. This section only adds what is specific to this project.

### 12.1 What we are building

**Warden** is a governed runtime for AI agents that take real actions. A user submits a task in plain language
(for example: *"Find orders that failed in the last 24 hours and open a GitHub issue for the top 3 causes"*).
Warden plans the task, calls tools through MCP, pauses for human approval before risky actions, records every
step in an audit log, and measures its own quality with an eval suite that runs in CI.

Core capabilities (all must be done in 1 week):

1. Task runs: create a run, execute it, get its status, final report and full step trace.
2. Tools through MCP: 3 MCP servers, reached only through `clients/`.
3. Permissions: every tool call is checked against the caller's role (`viewer`, `operator`, `admin`).
4. Human-in-the-loop: risky tool calls pause the run until a human approves or rejects; the run then resumes.
5. Durable runs: a paused or crashed run resumes from its last checkpoint, not from the start.
6. Audit log: who asked, which tool, which arguments, which decision, result, timestamp. Append-only.
7. Observability: tokens, latency and estimated cost per step and per run, viewable through the API and the web console.
8. Evals: 30+ scenarios with task success rate and tool-call accuracy; CI fails if scores drop below a threshold.

Out of scope (do not build unless Day 7 has spare time and the user agrees): sandboxed code execution,
real email sending, Docker/containers, multi-tenant organisations, SSO.

### 12.2 Tech stack

Python 3.12, `uv`, FastAPI, LangGraph, official `mcp` Python SDK (FastMCP), SQLAlchemy 2 (async) + aiosqlite,
SQLite (single local file, no server needed), Alembic, pydantic-settings, pytest + pytest-asyncio, ruff, mypy, pre-commit,
GitHub Actions. **No Docker**: everything runs locally with `uv run`. The DB URL lives in `.env`, so switching to
PostgreSQL later must only need a `.env` change. LLM providers: Groq and Gemini behind one `LlmClient` Protocol, switched only through `.env`.
Web console in `web/` (Streamlit) for runs, traces and approvals.

### 12.3 Where things live (decided placements)

| Thing | Location | Class names |
|---|---|---|
| Task-run graph (LangGraph) | `app/orchestrators/` | `AgentRunOrchestrator` |
| Agents (one job each) | `app/agents/` | `PlannerAgent` (splits task into steps), `ToolSelectorAgent` (picks tool + arguments for one step), `StepReviewerAgent` (judges if a step result is good enough), `ReporterAgent` (writes final report) |
| LLM access | `app/clients/` | Protocol `LlmClient`; `GroqLlmClient`, `GeminiLlmClient` |
| MCP tool access | `app/clients/` | Protocol `ToolClient`; `McpToolClient` |
| LangGraph checkpoints | `app/repositories/` | `CheckpointRepository` (injected into the orchestrator through DI; the orchestrator never opens DB sessions) |
| Runs, steps, approvals, audit | `app/repositories/` + `app/models/` | `AgentRunRepository`, `ApprovalRepository`, `AuditLogRepository`; entities `AgentRun`, `RunStep`, `Approval`, `AuditLogEntry` |
| Business logic | `app/services/` | `AgentRunService`, `ApprovalService`, `AuditService` |
| API-key → role | `app/middlewares/` | `ApiKeyAuthMiddleware` |
| **New layer:** permission decisions | `app/policies/` | Suffix `Policy`. `ToolPermissionPolicy` returns `allow` / `deny` / `needs_approval` for a tool call + role. Pure logic, no I/O. Called by orchestrators. Rules come from `core/config.py`. |
| **New, outside `app/`:** MCP servers | `mcp_servers/<name>/` | Separate processes, own `server.py`. `warehouse` (read-only SQL on a demo SQLite database seeded from `data/`), `github` (list/create issues on a test repo), `notifier` (mock: writes to an outbox table). The app never imports from here. |
| **New, outside `app/`:** eval suite | `evals/` | `scenarios/*.yaml`, `runner.py`, `reports/` (git-ignored). |
| Architecture decisions | `docs/adr/` | `0001-<title>.md` |
| Day plan | `docs/PLAN.md` | — |

When any of these new layers is created, update the tables in sections 1, 2, 3 and 5 in the same commit (section 11, step 8).

### 12.4 Git and commit rules

- **Small commits.** One logical change per commit. Aim for roughly 30–120 changed lines; never mix unrelated changes.
- **Conventional Commits**, English, imperative: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`, `ci:`, `build:`.
  Example: `feat(policies): add ToolPermissionPolicy with role rules`.
- **Every commit must be green:** ruff, mypy and pytest pass (pre-commit enforces it). Never use `--no-verify`.
- **Commit and push on your own** when the green check passes. Before each commit, verify no `.env`, `*.db`, keys or
  tokens are staged. Ask the user only for: PR merges, deviations from `docs/PLAN.md`, new dependencies, design
  decisions, anything involving secrets, or when something fails twice.
- **Push after every commit** so GitHub activity reflects real progress.
- **Branch per feature/day** (`feat/day-2-mcp-servers`), open a PR with a clear description, and merge it with
  *"Create a merge commit"* or *"Rebase and merge"*. **Never squash**, because squash collapses the small commits.
- Never commit `.env`, API keys, tokens, `.venv`, caches or eval reports.

### 12.5 Working rules for the coding agent

- Follow `docs/PLAN.md` day by day. Do not start the next day's work early.
- If a requirement is unclear or something does not fit the layers, **stop and ask** before writing code.
- Write the test together with (or before) the code it covers. Unit tests use fake clients only.
- Comments, docstrings, logs and terminal output are in English.
- At the end of each day: run the full test suite, update `docs/PLAN.md` progress checkboxes, and give the user a short summary.
