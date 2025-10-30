# Clarification Pass 4 — 2025-10-30

orchestrator: Swarmlord of Webs (sole human interface)

## BLUF
- Success means: minimal-to-zero babysitting mid-loop, safe autonomous retries, and independently verified fixes delivered on a schedule.
- Defaults: TDD-first, GitOps-style flow, strict safety envelope, and quorum-based Verify before any digest to the user.
- Scale path: multiple PREY lanes run in parallel behind the Swarmlord; you author intent, then return later to a verified bundle.

---

## Success criteria (explicit)
- Interface autonomy
  - Mid-loop human prompts: 0 (forbidden). All worker dialogue stays behind Swarmlord.
  - Auto-retries: Up to 3 targeted PREY re-runs per failing lane before escalation.
  - Swarmlord approvals: Auto-approve safe sub-steps inside an active mission when inside guardrails (tests green, receipts present, Verify quorum PASS).
- Verification quality
  - Quorum threshold: 2 of 3 validators (immunizer, disruptor, verifier_aux).
  - Hallucination rate: target ≤ 5% (PASS), 5–10% = caution (Swarmlord may return partials), >10% = FAIL and auto re-run.
  - Grounding: Every substantive claim/artifact must have evidence_refs (files/lines/hashes/metrics/URLs).
- Safety envelope
  - Chunk size ≤ 200 lines per write; placeholder ban (no TODO/…/omitted in committed artifacts).
  - Canary-first, measurable tripwires (line counts, placeholder scans, test results, policy checks), explicit revert plan.
  - Blackboard receipts appended for material actions.
- Throughput and latency
  - Lane cycle time budget: soft 5 minutes; mission budget: soft 30 minutes (return best verified partial if exceeded, with plan).
  - Parallelism: start with 2–4 lanes today; grow to 10+ agents via Crew orchestration when stable.
- Outcome
  - “Describe an issue → verified fix” within the mission budget, or return a partial with a concrete next-step plan and receipts.

## Operating mode (TDD + GitOps/DevOps defaults)
- TDD cycle per lane
  1) Write/locate minimal failing test (or reproduce) and log evidence.
  2) Implement the smallest change to make it pass.
  3) Run tests and diagnostics; collect metrics.
  4) If green, proceed to Verify. If red, targeted re-run with narrowed scope.
- GitOps-style discipline
  - Branch-per-mission; receipts and artifacts committed; CI-style Verify gate (lint/tests/metrics) before merging.
  - Canary deploys for risky ops; explicit revert instructions attached to each engage receipt.
- Receipts and telemetry
  - Append-only blackboard JSONL with safety_envelope and evidence_refs.
  - Optional OpenTelemetry-style spans for timing and quorum metadata.

## Orchestration for scaling (parallel PREY lanes)
- Parallel lanes
  - Each lane runs P→R→E→Y sequentially; Swarmlord aggregates Yields and triggers Verify.
  - Backpressure and fairness: lane queue with time-sliced budgets; stalled lanes auto-shrunk (smaller chunks, narrower scope).
- Verify gate
  - Independent validators run checks (grounding, consistency, hallucination rate, SLO conformance).
  - Outcomes: PASS → digest; FAIL → targeted re-run (reduce chunk, add canary, tighten tripwires).
- Retry and escalation policy
  - Max 3 targeted re-runs. On 3× FAIL, escalate to a synthesis lane that proposes alternatives or requests new constraints in the next clarification window (not mid-loop).

## Today’s demo plan (near-term, safe)
- Scope
  - Stand up 2–4 lanes on a contained mission (docs/code lints or bounded scripts) with TDD checks.
  - Use receipts + Verify quorum locally (no external writes beyond repo).
- Deliverables per mission
  - BLUF + matrix + diagram + notes (digest), tests and metrics artifacts, and blackboard receipts.
- Crew expansion path (10+ agents)
  - Introduce a crew manifest (roles, tools, guardrails) and lane templates; start with docs/devops chores and grow to code fixes.

## SLOs (initial)
- Autonomy
  - Mid-loop prompt rate = 0; any occurrence triggers a tripwire and regeneration with reduced scope.
- Quality
  - Verify PASS rate ≥ 80% on first attempt; ≥ 95% within 3 auto-retries.
  - Hallucination rate ≤ 5% target; never > 10% in PASS.
- Timeliness
  - Lane cycle ≤ 5 minutes (soft); mission ≤ 30 minutes (soft) per default.

## Acceptance for Pass 4
- Approve these success criteria and SLOs (autonomy, quality, timeliness).
- Approve TDD + GitOps defaults and auto-retry policy (≤3 targeted re-runs).
- Approve parallel lanes with Verify quorum and backpressure.
- Authorize creation of mission intent YAML v4 embedding these defaults and a crew manifest stub.

## Next step
- On approval, I will create `hfo_mission_intent/2025-10-30/mission_intent_2025-10-30.v4.yml` with: success criteria, SLOs, lane/verify configs, TDD/GitOps defaults, and a minimal crew manifest stub for 2–4 lanes (scalable to 10+).
