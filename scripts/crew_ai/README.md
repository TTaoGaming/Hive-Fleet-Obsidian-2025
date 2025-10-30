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
python3 scripts/crew_ai/runner.py \
  --intent hfo_mission_intent/2025-10-30/mission_intent_daily_2025-10-30.v5.yml
```

Outputs:
- Blackboard receipts in `hfo_blackboard/obsidian_synapse_blackboard.jsonl`
- Spans in `temp/otel/trace-*.jsonl`

Notes:
- If no `OPENROUTER_API_KEY` is set, the Engage step gracefully skips the remote call and records a failed but non-fatal audit.

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

## ARC-Challenge (research-grade, MCQ)

Evaluate models on the official AI2 ARC-Challenge dataset (validation split by default). This is a standard, widely-used benchmark for non-trivial reasoning.

Single-model run:
```bash
# uses env OPENROUTER_MODEL_HINT if set
python3 scripts/crew_ai/arc_challenge_eval.py --limit 200

# or pick a model explicitly
OPENROUTER_MODEL_HINT=deepseek/deepseek-chat-v3-0324 \
  python3 scripts/crew_ai/arc_challenge_eval.py --limit 0
```

Swarm run (one lane per allowlisted model):
```bash
python3 scripts/crew_ai/arc_swarm_runner.py --limit 200
```

Outputs:
- Digest: `hfo_crew_ai_swarm_results/YYYY-MM-DD/run-<ts>/swarmlord_digest.md`
- JSON: `hfo_crew_ai_swarm_results/YYYY-MM-DD/run-<ts>/arc_swarm_results.json`

Notes:
- Limit defaults to 200 for cost control; set `--limit 0` for the full split.
- Accuracy is computed on the validation split for easy, labeled scoring.
