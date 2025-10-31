# Crew AI Swarm + OSS Transport + ARC — Consolidated Research (Four Attempts)

Date: 2025-10-31
Branch: fix/gpt-oss-transport-arc
Owner: Swarmlord (sole interface)

## BLUF
- Parallel PREY lanes are operational and verified via OTEL span overlap; yields and verify artifacts are consistent across lanes.
- On ARC‑Challenge (validation, limit=100, 2 lanes/model), top models cluster at ~92–96% accuracy; Qwen3‑235B leads at 95.5% with ~1.6s latency.
- OSS transport on GPT‑OSS exhibits empty-content at very low token budgets; reliability stabilizes ≥200–400 tokens; 1000 tokens is a robust default for ARC-like tasks.
- One misconfiguration caused an 11M‑token blowout; add hard guards (token/cost caps) and CI checks to prevent recurrence.

## Scope — the four attempts
1) Parallel PREY lanes demo (10 lanes)
   - Goal: Validate lane concurrency, receipts, and verify quorum.
   - Outcome: 10/10 PASS at attempt=1; spans show concurrent P→R→E→Y with per‑lane engage_llm.
2) Per‑model ARC swarm eval (2 lanes/model over allowlist)
   - Goal: Compare allowlisted models under the same budget; capture accuracy/latency/format‑fail/empty counts.
   - Outcome: Qwen3‑235B best (95.5%); OSS models near 93%; empties rare at 1000 tokens; measured latencies 1.5–2.2s typical, DeepSeek‑V3.x much slower.
3) OSS transport resiliency (gpt‑oss family)
   - Goal: Diagnose empty content and response_format sensitivity; sweep prompts × format × tokens × temp.
   - Outcome: Empties frequent at 16 tokens; near‑zero by 64; robust by 200+; response_format sometimes increases empties; retry‑on‑empty + fallback helps.
4) Misconfigured token limit incident
   - Goal: Post‑mortem of a run that consumed ~11M tokens in one shot.
   - Outcome: Configuration bug; requires caps and CI guardrails.

## Findings and takeaways
- Concurrency verified
  - Evidence: OTEL trace shows simultaneous perceive/react/engage across 10 lanes and per‑lane engage_llm spans.
  - Impact: Confirms PREY lanes scale; thread‑pool scheduling OK.
- Verify and receipts discipline
  - Each lane emitted yield + verify artifacts; digest matrices summarize PASS/FAIL per lane.
  - Blackboard has grounded entries with evidence_refs for major runs.
- Model selection (ARC‑Challenge)
  - Accuracy: 90–96% band; top‑3: Qwen3‑235B (95.5%), DeepSeek‑Chat v3‑0324 (94.5%), GPT‑5‑mini (94.0%).
  - Latency: ~1.5–2.2s for most; DeepSeek‑V3.* 18–22s; Grok‑Code ~3.3s.
  - Robustness: Empty/format‑fail counts low at 1000 tokens; higher empties for GPT‑5‑mini and DeepSeek V3.*.
- OSS transport behavior
  - Empty responses driven by low token budgets; response_format can worsen empties on OSS.
  - Stabilization threshold: ≥200–400 tokens for ARC‑like MC tasks; 1000 tokens default recommended.
- Safety envelope
  - Docs chunking ≤200 lines observed in generated artifacts; placeholder ban maintained in reviewed outputs.
  - One guardrail gap: no hard cap prevented the 11M‑token blowout.

## Comparison to Clarification Pass 4 (success criteria)
- Interface autonomy: PASS — workers operate behind Swarmlord; mid‑loop prompts absent in receipts.
- Auto‑retries ≤3: PARTIAL — per‑lane attempts recorded; ensure explicit cap enforced in code for all lanes.
- Verify quorum (2 of 3): PASS — verify steps/roles present; spans include post‑immunizer/disruptor.
- Safety envelope: PARTIAL — chunk limit and placeholder ban respected; add token/cost caps and policy checks to fully comply.
- Throughput: PASS — 10 lanes complete within soft budgets; per‑lane span windows overlap.
- Outcome cadence: PASS — “Describe issue → verified fix/digest” achieved for evaluated missions.

## Comparison to Clarification Pass 5 (flow/diagrams/topology)
- End‑to‑end flow: PASS — USR→Swarmlord→Lanes→Yields→Verify→Digest evident in artifacts.
- Lane internals with TDD: PARTIAL — tests exist for eval tasks; add explicit negative controls in each cycle to avoid persistent green.
- Verify quorum topology: PASS — immunizer + disruptor spans and verify summaries present.
- GitOps pipeline: PARTIAL — local runs logged; recommend CI job to render diagrams, run sweeps, and validate receipts.
- Crew topology for parallel lanes: PASS — planner→lanes→aggregate→verify observed; per‑model lanes also validated.

## Risks and incidents
- Token blowout (11M tokens)
  - Root cause: misconfigured limit; missing hard cap.
  - Risk: runaway cost; violates Pass‑4 cost/safety guards.
- OSS format sensitivity
  - Response_format sometimes increases empties; retry/fallback logic mitigates but needs policy coverage.

## Recommendations
- Enforce hard token and cost caps
  - Set OPENROUTER_MAX_TOKENS default to 1000; clamp per‑call <= mission/env cap.
  - Add est_cost guards; abort if projected cost > budget.
- Transport resiliency defaults (OSS)
  - Enable retry‑on‑empty once; drop response_format on retry; raise tokens to ≥400 if empties persist.
- Verification hardening
  - Add negative controls per lane; require at least one disruptor probe per cycle (explicit receipt field).
  - CI checks: placeholder scan, receipt JSONL validation, mermaid render, OTEL overlap check.
- Model policy
  - Keep allowlist; prefer Qwen3‑235B or DeepSeek‑Chat v3 for accuracy/latency; use GPT‑OSS‑20B as fast OSS baseline.

## Evidence references (grounding)
- Parallel lanes digest: hfo_crew_ai_swarm_results/2025-10-30/run-1761850703499/swarmlord_digest.md
- OTEL parallelism: temp/otel/trace-mi_parallel_10lanes_2025-10-30-1761849504603.jsonl
- ARC swarm digest: hfo_crew_ai_swarm_results/2025-10-31/run-1761872692535/swarmlord_digest.md
- ARC results JSON: hfo_crew_ai_swarm_results/2025-10-31/run-1761872692535/arc_swarm_results.json
- OSS transport sweep: hfo_crew_ai_swarm_results/2025-10-30/oss_120b_sweep_1761852454563.{md,json}
- OSS transport diag: hfo_crew_ai_swarm_results/2025-10-30/oss_transport_diag_1761866767562.md
- Incident note: hfo_crew_ai_swarm_results/2025-10-31/run-1761869054773/misconfigured-limit-used-11m-tokens.md
- Blackboard receipts: hfo_blackboard/obsidian_synapse_blackboard.jsonl
- Mission clarifications: hfo_mission_intent/2025-10-30/clarification_pass4_2025-10-30.md, clarification_pass5_2025-10-30.md

## Next steps (low‑risk, high‑leverage)
- Add token/cost caps + CI guard; fail closed on misconfig.
- Bake ARC‑default max_tokens=1000; expose per‑mission override with clamp.
- Wire a small CI to validate receipts and render Mermaid diagrams.
- Log explicit disruptor probe receipt per lane; include negative control summary in verify.md.
