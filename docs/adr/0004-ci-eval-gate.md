# 0004: CI eval gate with a real LLM

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

Unit tests use fake LLM clients (CLAUDE.md section 9). They prove the plumbing: routing,
permissions, persistence, resume. They cannot prove that the agents still make the right
decisions with the real model.

On Day 6, the first real run of the headline task failed on a column the model invented
(`cause` instead of `failure_reason`), while every unit test was green. On Day 7, the first eval
run found more problems of this kind that no unit test had caught:
- a filter on `'payment timeout'` instead of `'payment_timeout'`;
- a race where a run still said `awaiting_approval` after its approval was decided;
- an eval task that YAML cut short at a `#`.

Prompt, model and tool-description changes need a check that uses the real LLM before merging.

The constraint is the token budget. The Groq free tier for `openai/gpt-oss-120b` allows:
- 8,000 tokens per minute;
- 1,000 requests per day;
- a daily token cap on top of those.

A scenario uses about 3–6k tokens, and the full suite about 120–150k, close to a whole day's
free-tier budget. Running the full suite on every push to a PR would use up the day's budget
after one or two runs, and later runs would fail on rate limits instead of on quality.

## Decision

**Scenarios and scoring:**
- 31 YAML scenarios in `evals/scenarios/`, in four groups: warehouse questions, GitHub,
  notifier, and permissions/approvals.
- Each scenario states the task, the caller's role, how the "human" answers approvals, and the
  expected tools, denials and report facts.
- `evals/runner.py` drives the real app in-process (httpx `ASGITransport`, real lifespan, real
  MCP servers) with temp databases and generated API keys.
- GitHub is always dry-run, so CI never creates an issue.
- Task success rate is the share of scenarios where every expectation holds. Tool-call accuracy
  is the mean Jaccard overlap of picked vs expected tools.
- Both scores must be **≥ 0.8** (`EVAL_THRESHOLD`), otherwise the runner exits 1.

**Two tiers, because of the free-tier token budget:**

| Trigger | Scenarios | Tokens (approx.) | Purpose |
|---|---|---|---|
| Pull request to `main` | `smoke` tag: 9 scenarios | 35–45k | Gate every PR |
| "Run workflow" button (`workflow_dispatch`, default `full`) and local runs | all 31 | 120–150k | Full quality numbers, before a release and for the README |

The smoke subset is tagged in the YAML (`tags: [smoke]`) and selected with `--tag smoke`.
A unit test keeps it at 8–10 scenarios and makes it cover:
- every group (warehouse, GitHub, notifier, policy);
- an approval, a rejection and a policy denial.

The 9 smoke scenarios:
- warehouse top failure reasons and payment-timeout count, the two schema-hallucination guards;
- the headline task with approval;
- a rejected issue;
- an approved and a rejected notification;
- a viewer denied an issue;
- the viewer headline, where the query runs and the issue is denied;
- an admin write without a pause.

**CI details:** `.github/workflows/evals.yml`.
- The Groq key comes from the `GROQ_API_KEY` repository secret.
- The Markdown report goes to the job summary. The JSON report, which holds each scenario's
  trace and final report, is uploaded as an artifact.

**Rate limits are handled, not avoided:**
- concurrency 1;
- the LLM client retries 429s with exponential backoff and honours `Retry-After`, with up to 8
  attempts during evals;
- the runner reruns a scenario, after a growing pause, when it failed on a rate limit or another
  provider error.

## Consequences

- A prompt or model change that breaks tool choice, permissions or report facts fails the PR on
  the smoke subset, with a per-scenario report that says what went wrong.
- Regressions outside the smoke subset are caught only by a full run. Run it, with the button or
  locally, before merging prompt or tool-description changes, and before quoting numbers.
- The per-minute token limit sets the pace. A smoke run takes about 5–10 minutes and a full run
  about 25–35 minutes. A full run costs about $0.03 at Groq list prices.
- A real LLM is not deterministic. The 0.8 threshold leaves room for an occasional miss, but a
  scenario that fails often is a signal to fix prompts or tool descriptions, never to lower the
  threshold quietly.
- Forks do not get the secret, so the eval job only runs for branches of this repository.
- If the budget becomes a bottleneck, there are three options: a paid tier (then run the full
  suite on PRs), a nightly full run, or the gate on Gemini through the existing `LLM_PROVIDER`
  switch.
