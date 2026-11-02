# 0001: Tool calls run through a non-LLM ToolExecutorAgent

- **Status:** Accepted
- **Date:** 2026-11-02

## Context

The request flow in CLAUDE.md is `orchestrators → agents → clients`, and layers may not be skipped.
A tool call happens in three parts:

1. `ToolSelectorAgent` (LLM) picks the tool and arguments.
2. `ToolPermissionPolicy` decides allow / deny / needs_approval, and a human may need to approve.
3. The tool actually runs.

Step 3 must stay separate from step 1, because the permission check and the approval pause happen
between them. So something has to run the approved call. If `AgentRunOrchestrator` called `ToolClient`
directly, it would skip the agents layer. If the selector also ran the tool, the policy check would
have to sit inside an agent, and agents must not know about roles or approvals.

The team's `BaseAgent` (CLAUDE.md section 6) has a fixed constructor `(llm_client, prompt_loader)`,
which assumes every agent uses an LLM.

## Decision

Add a fifth agent, `ToolExecutorAgent`, that only runs one already-approved `ToolCall` through the
`ToolClient` Protocol and returns the `ToolResult`.

- It inherits `BaseAgent` unchanged and keeps the constructor contract:
  `__init__(llm_client, prompt_loader, tool_client)` calls `super().__init__(llm_client, prompt_loader)`
  and adds the tool client. It never uses the LLM client. A unit test checks this.
- Its output (`ToolExecutorOutput`) has empty `usage`, so per-step cost tracking works the same for
  all agents.
- Tool failures come back as `ToolResult(ok=False)`, not exceptions, so the orchestrator can let
  `StepReviewerAgent` judge them and retry.

## Consequences

- The flow stays `orchestrators → agents → clients` with no skipped layer, and the orchestrator
  imports only agents, policies and schemas.
- Every agent is built and injected the same way through DI.
- `ToolExecutorAgent` receives an LLM client it does not use. That costs nothing at runtime (DI
  provides one shared client), and it is cheaper than changing the team-wide `BaseAgent` contract.
- "One agent = one AI task" is relaxed slightly: this agent's one task is executing a tool, not
  reasoning. If more non-LLM agents appear, revisit with a separate base class.
