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
