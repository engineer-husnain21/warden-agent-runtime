# 0002: Durable runs with LangGraph checkpoints and interrupts

- **Status:** Accepted
- **Date:** 2026-11-02

## Context

Two requirements (CLAUDE.md 12.1) need a run to survive a stop:

- **Human-in-the-loop:** a risky tool call pauses the run until an admin approves or rejects it.
  That can take minutes or days, longer than any request or process lifetime.
- **Durable runs:** a run that crashes or is stopped mid-way resumes from its last checkpoint,
  not from the start. Re-running finished steps would repeat real side effects (a second GitHub
  issue) and waste LLM tokens.

## Decision

`AgentRunOrchestrator` is a LangGraph `StateGraph`:
`plan → (select → check_permission → [await_approval] → execute → review)* → report`.

- **Checkpoints:** the graph is compiled with a checkpointer and uses the run id as `thread_id`, so
  LangGraph saves the state after every node. `CheckpointRepository` owns the official
  `AsyncSqliteSaver`; the orchestrator only receives the saver through DI and never opens connections.
- **Separate file:** checkpoints live in their own SQLite file (`CHECKPOINT_DATABASE_URL`), so they
  never compete with the app database for SQLite's single writer lock.
- **Approval:** `await_approval` calls `interrupt(payload)`, which saves the state and ends the stream.
  `resume(run_id, ApprovalDecision)` continues with `Command(resume=...)`.
- **Crash recovery:** `resume(run_id)` without a decision continues from the last checkpoint.
- **Plain JSON state:** `RunState` holds only JSON values (Pydantic models are stored as dicts), so
  checkpoints do not depend on Python class paths and stay readable.

## Consequences

- A paused or crashed run survives restarts. An integration test kills a run inside step 2's tool
  call, then resumes it with a new orchestrator and checks that the plan and step 1 do not run again.
- LangGraph re-runs an interrupted node **from its start** on resume. Two rules follow:
  - `await_approval` must emit nothing before `interrupt()`. The "awaiting approval" event is built
    from the interrupt payload in the stream instead.
  - A crash *inside* `execute` re-runs that tool call. That gives at-least-once delivery for the one
    interrupted call; finished steps are never repeated.
- PostgreSQL would need `langgraph-checkpoint-postgres`. `CheckpointRepository` is the only place to
  change, and it fails with a clear configuration error until then.
