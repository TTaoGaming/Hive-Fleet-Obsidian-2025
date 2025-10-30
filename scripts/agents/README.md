# Agents folder

This folder hosts simple_tag_v3 agent policies and primitives. Start with single-agent primitives, then compose into multi-agent meta-layers aligned with OBSIDIAN roles and a virtual stigmergy layer.

Planning and checklists:
- See `hfo_research_doc/simple_tag_primitives_todo_2025-10-30.md` for the phased TODO (singles first, then multi-agent enablers).

Evaluator:
- Use `scripts/pz_eval_simple_tag_v3.py` to run predator vs prey matchups.
- Custom policy spec: `custom:module:Class`, e.g. `custom:scripts.agents.sample_custom_agent:FleeCentroid`.

Example quick run:
```bash
./.venv/bin/python scripts/pz_eval_simple_tag_v3.py \
  --pred heuristic \
  --prey custom:scripts.agents.sample_custom_agent:FleeCentroid \
  --episodes 20 \
  --seed 42
```
