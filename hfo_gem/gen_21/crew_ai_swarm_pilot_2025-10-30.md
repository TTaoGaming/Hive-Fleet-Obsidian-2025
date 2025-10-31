# Crew AI Swarm Pilot — Gen21 Handoff (2025-10-30)

BLUF
- True 10-lane parallel fan-out/fan-in is operational and verified. Deterministic and LLM modes both emit spans; analyzer reports Parallel detected: True.
- LLM mode is model-hint sensitive in this environment: qwen passes 10/10; oss-120b produced empty content on math micro-tasks. Orchestration is sound; client parsing will be hardened.

What shipped (artifacts)
- Digest: hfo_crew_ai_swarm_results/2025-10-30/run-1761850703499/swarmlord_digest.md
- Spans: temp/otel/trace-swarm_math-1761850703499.jsonl
- Intent: hfo_mission_intent/2025-10-30/mission_intent_parallel_10lanes_2025-10-30.v1.yml
- Pilot: scripts/crew_ai/swarm_math_runner.py (fans out lanes, retries, verifies, fans in digest)

Verification
- Span analyzer confirms overlap across lanes (engage windows) and prints Parallel detected: True.
- Digest summarizes per-lane yields, verify results, and final pass/fail counts (10/10 with qwen hint).
- Blackboard receipt appended for this run (phase: digest; mission_id: mi_parallel_10lanes_2025-10-30).

Safety envelope (operational)
- Chunking: ≤200 lines per write; append-only JSONL for receipts with evidence_refs.
- Tripwires: placeholder_scan, analyzer overlap check, verify quorum threshold.
- Revert: remove last JSONL line if malformed; shrink scope and retry on FAIL.

Model hint note
- qwen/qwen3-235b-a22b-2507: 10/10 PASS (math micro-questions) with strict JSON prompt and micro-retries.
- openai/gpt-oss-120b: Returned empty content paths in this environment for the same prompts. Next change: multi-shape content parsing (message.content, text, parts) and treat empty content as retryable.

Mermaid-safe diagram
```mermaid
graph LR
  F[Fan out (10 lanes)] --> E[Engage]
  E --> Y[Yield per lane]
  Y --> V[Verify per lane]
  V --> A[Analyze spans]
  A --> FI[Fan in digest]
```

Next steps (low-risk improvements)
- Harden oss-120b client parsing and retry-on-empty.
- Optional: add CSV run summaries and speedup estimates (wall-clock vs. sum).

Notes
- All commands are already embedded in existing scripts/README; this file is a handoff pointer. See the digest and spans above for concrete evidence.

## Addendum — ARC swarm aligned with PREY artifacts (2025-10-31)

What changed
- The ARC swarm runner now mirrors the pilot’s per-lane PREY artifact pattern so each lane is auditable:
  - Per-lane directory: `hfo_crew_ai_swarm_results/YYYY-MM-DD/run-<ts>/<sanitized_model>_lane_<n>/attempt_1/`
  - Artifacts: `perception_snapshot.yml`, `react_plan.yml`, `engage_report.yml`, `yield_summary.yml`
- A lightweight lane validator checks that `yield_summary.evidence_refs` includes the other three files and appends a blackboard receipt ("artifact validation PASS/FAIL").

What stayed the same
- Run-level digest (`swarmlord_digest.md`) and results JSON (`arc_swarm_results.json`) are still written in the run directory.
- Safety envelope (≤200 lines/docs, placeholder ban) and blackboard append-only discipline remain unchanged.

Where to look
- Example run directory: `hfo_crew_ai_swarm_results/YYYY-MM-DD/run-<ts>/`
- Blackboard: `hfo_blackboard/obsidian_synapse_blackboard.jsonl` (look for lane artifact receipts and validator PASS entries)
