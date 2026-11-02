# 0003: The service persists orchestrator StepEvents

- **Status:** Accepted
- **Date:** 2026-11-02

## Context

Every step of a run must be stored (`RunStep`: trace, tokens, latency, cost) and every tool decision
audited (`AuditLogEntry`). The layer rules (CLAUDE.md sections 3–4) do not allow the obvious places:

- the orchestrator may not make DB calls;
- agents may not save or log business events;
- only repositories touch data, and services are the layer that calls them.

Steps still need to be saved *as they happen*, not only at the end. A crash must not lose the trace,
and the web console shows a live run.

## Decision

`AgentRunOrchestrator.stream()` / `resume()` are async generators that yield a typed `StepEvent` for
every node (plan, tool selection, permission check, approval, tool call, review, report). Each event
carries the step index, tool, arguments, output, policy decision and the LLM usage of the agent
that produced it.

`AgentRunService` (Day 6) iterates the stream. For each event it writes a `RunStep` through
`AgentRunRepository` and, for permission checks, approvals and tool calls, an `AuditLogEntry`
through `AuditLogRepository`. When the stream ends paused (an "awaiting approval" event), it creates
an `Approval` row and sets the run status.

## Consequences

- The orchestrator stays free of I/O: it imports only agents, policies and schemas, and is
  unit-tested with in-memory checkpoints and fake clients.
- Persistence happens per event, so the stored trace is complete up to the moment of a crash.
- Usage numbers travel on the events, so the service can store per-step and per-run totals without
  knowing anything about agents.
- One more schema (`StepEvent`) to keep in step with `RunStep`; the service maps one to the other.
