# Crew AI Pilot — Secrets and Setup

This pilot reads `mission_intent_daily_YYYY-MM-DD.v5.yml`, runs 2 lanes with PREY steps, and executes a minimal multi-agent crew per lane (Observer for Perceive, Bridger for React, Shaper for Engage, Assimilator for Yield; plus Immunizer and Disruptor checks), writes receipts to the blackboard, and emits simple OpenTelemetry-like spans.

## Secrets (OpenRouter)

Never commit secrets. Use one of the following:

1) Local .env (recommended for dev)
   - Copy `.env.example` to `.env` at repo root
   - Set values:
     - `OPENROUTER_API_KEY=...`
     - `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`
     - Optional: `OPENROUTER_MODEL_HINT=<cheap/fast model>`
   - The runner loads `.env` automatically and only audits presence (not the value).

2) GitHub Secrets (for CI)
   - In GitHub: Settings → Secrets and variables → Actions → New repository secret
   - Add `OPENROUTER_API_KEY` (and optional `OPENROUTER_BASE_URL`)
   - Reference these in your workflow or container environment at runtime.

Security notes:
- Do not paste your key into code, blackboard receipts, or committed files.
- The runner writes an audit line to the blackboard that only indicates presence/absence of the key.

## Run locally (pilot)

The pilot will perform at most one guarded LLM call per lane during the Engage phase if `OPENROUTER_API_KEY` is present. The call uses an allowlisted cheap/fast model, low `max_tokens` (<= 96), and logs only a short preview in the blackboard.

```bash
# Preferred while runner.py is being sanitized
python3 scripts/crew_ai/runner_unified.py \
  --intent hfo_mission_intent/2025-10-31/mission_intent_2025-10-31.v1.yml
```

Alternate (direct orchestrator):

```bash
python3 scripts/crew_ai/orchestrator.py \
  --intent hfo_mission_intent/2025-10-31/mission_intent_2025-10-31.v1.yml
```

Outputs:
- Blackboard receipts in `hfo_blackboard/obsidian_synapse_blackboard.jsonl`
- Spans in `temp/otel/trace-*.jsonl`
- Per-step artifacts per lane under: `hfo_crew_ai_swarm_results/YYYY-MM-DD/run-<ts>/lane_<name>/attempt_1/`
  - `perception_snapshot.yml` (Perceive)
  - `react_plan.yml` (React)
  - `engage_report.yml` (Engage)
  - `yield_summary.yml` (Yield)
- Swarmlord-level run artifacts under: `hfo_crew_ai_swarm_results/YYYY-MM-DD/run-<ts>/`
  - `mission_pointer.yml` (pointer to mission intent and run config)
  - `swarmlord_digest.md` (BLUF, matrix, diagram, notes)

Notes:
- If no `OPENROUTER_API_KEY` is set, the Engage step gracefully skips the remote call and records a failed but non-fatal audit.

### Perception snapshot (human + machine)

Each lane writes a YAML snapshot during the Perceive phase capturing:
- mission_id, lane, timestamp, trace_id
- PREY phases, safety (chunk limits, placeholder ban, tripwires)
- LLM config summary (model_hint, tokens, temperature, timeout, response_format, reasoning, allowlist, api_key presence)
- Paths (blackboard, spans file, lane_dir)

Use this to debug context and to feed downstream tools or validators without scraping logs.

### React plan
- Cynefin domain and rationale; approach/tripwires; chunk limit; C2/CBR hints; quorum config.

### Engage report
- Actions executed, safety bounds (tokens, placeholder ban), and LLM call metadata (ok/model/latency/status/error, preview).

### Yield summary
- Collected agent keys, evidence refs across lane, and a note that Verify quorum runs post‑yield.

## Next steps
- Add budgeting/rate limits per mission to cap LLM calls.
- Externalize model allowlist and limits into mission intent or policy file.
- Expand Verify to assert per-lane engage_llm spans when keys are present.

## Mixed lightweight eval (harder than simple math)

Use `scripts/crew_ai/mixed_light_eval.py` to run a tiny mixed benchmark that stresses logic, strict formatting, table math, JSON extraction, dates, and string transforms. It uses the same OpenRouter client and stays low-cost by default.

Dataset: `scripts/crew_ai/evals/mini_mix_eval.jsonl`

Examples:

```bash
# default: uses env OPENROUTER_MODEL_HINT if set
python3 scripts/crew_ai/mixed_light_eval.py

# pick a model explicitly via env
OPENROUTER_MODEL_HINT=deepseek/deepseek-chat-v3-0324 \
  python3 scripts/crew_ai/mixed_light_eval.py --limit 0

# write JSON output somewhere
python3 scripts/crew_ai/mixed_light_eval.py --output temp/evals/mixed_eval_results.json
```

Scoring notes:
- Enforces strict outputs (e.g., letter-only, True/False, integer-only, or JSON-only) to catch instruction-following drift.
- Reports per-category accuracy and format-failure rate to surface brittle behavior beyond raw correctness.

## ARC-Challenge under the unified PREY workflow

ARC evaluation now runs inside the same PREY lanes orchestrated by the pilot runner. Use a mission intent with `provider: arc` (see `hfo_mission_intent/2025-10-31/mission_intent_2025-10-31.v1.yml`). The runner will spawn one lane per allowlisted model by default and write the same Gen22 artifacts, receipts, spans, quorum, and digest.

Run (unified):
```bash
python3 scripts/crew_ai/runner_unified.py \
  --intent hfo_mission_intent/2025-10-31/mission_intent_2025-10-31.v1.yml
```

Notes:
- The `engage` phase executes ARC eval per lane/model and records metrics in `engage_report.yml`.
- Lanes, validators, receipts, and digest are identical to non-ARC runs; ARC is just a provider adapter.
- The legacy `arc_swarm_runner.py` is deprecated and retained only as a thin wrapper for backward compatibility.

### Budget and limits (recommended)

- Smoke: `limit=50`, `lanes-per-model=1`, `max_tokens=400`
- Quick compare: `limit=100`, `lanes-per-model=1–2`, `max_tokens=400–1000`
- Balanced default: `limit=200`, `lanes-per-model=2`, `max_tokens=400`
- Robust snapshot: `limit=500`, `lanes-per-model=1–2`, `max_tokens=400–1000`

Reasoning controls are env-driven and applied to supported models only:
- `OPENROUTER_REASONING=true|false`
- `OPENROUTER_REASONING_EFFORT=low|medium|high` (default: medium)

Optional cost estimates:
- Set `OPENROUTER_PRICE_DEFAULT_PER_1K=<usd>` or per-model keys like `OPENROUTER_PRICE_OPENAI_GPT_OSS_20B_PER_1K=<usd>` to see estimated spend in the digest.
