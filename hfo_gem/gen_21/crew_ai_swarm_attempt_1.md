# Crew AI Swarm Attempt 1 — Pilot Notes

BLUF
- Two-lane PREY orchestration with OBSIDIAN roles (Observer, Bridger, Shaper, Assimilator) is live.
- Receipts append to the blackboard; OTEL-like spans write to temp/otel; Verify quorum runs and records votes.
- Engage makes at most one small, allowlisted LLM call per lane when `OPENROUTER_API_KEY` is present; skipped otherwise.

## Quick run

```bash
# Optional: use a cheap/fast model hint
OPENROUTER_MODEL_HINT=haiku \
  python3 scripts/crew_ai/runner.py \
  --intent hfo_mission_intent/2025-10-30/mission_intent_daily_2025-10-30.v5.yml
```

Outputs
- Blackboard: `hfo_blackboard/obsidian_synapse_blackboard.jsonl`
- Spans: `temp/otel/trace-*.jsonl`
- Verify quorum: PASS/FAIL receipt with votes and threshold

Roles
- Perceive → Observer
- React → Bridger
- Engage → Shaper
- Yield → Assimilator
- Post-lane: Immunizer + Disruptor

Safety and cost
- Chunk ≤200 lines, placeholder ban, canary-first, measurable tripwires, explicit revert
- LLM calls bounded (low max_tokens) and limited to cheap/fast allowlisted models; presence-only secret audit

References
- Mission intent v5: `hfo_mission_intent/2025-10-30/mission_intent_daily_2025-10-30.v5.yml`
- Agent guide: `AGENTS.md` (see “Using the Crew AI pilot”)
- Crew README: `scripts/crew_ai/README.md`
- Runner: `scripts/crew_ai/runner.py`

Next steps
- Add per-mission LLM budget cap (requests/tokens)
- Enforce engage_llm span count in Verify when a key is present
- Expand validators and CI gating
