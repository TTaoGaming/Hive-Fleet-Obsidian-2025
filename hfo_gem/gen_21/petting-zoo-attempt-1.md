# PettingZoo Attempt 1 — MAS scaffold and 2×2 baselines (2025-10-29)

Summary
- Renamed MAS scaffold to `hfo_petting_zoo_mas/` and added a CLI runner.
- Purpose: make it easy to plug in per-agent predator/prey logic for `mpe.simple_tag_v3`, supporting heterogeneous policies and hierarchical coordination.

Artifacts
- Package: `hfo_petting_zoo_mas/`
- Runner: `scripts/run_pz_custom_mas.py`
- Results (examples):
  - `hfo_petting_zoo_results/simple_tag_v3_matrix_20251029T213405Z_seed42_eps100.json`
  - `hfo_petting_zoo_results/simple_tag_v3_matrix_20251029T215659Z_seed5_eps100.json`

How to run
```bash
PYTHONPATH=. python3 scripts/run_pz_custom_mas.py --episodes 10 --seed 42 --continuous --pred-policies random,random,random --prey-policy random
```

Hooks to implement next
- Custom predator policy per agent (e.g., Lead, Flanker, Sweeper) via subclassing `BasePolicy` or `FnPolicy`.
- Optional `Coordinator` to assign formations/roles each step.
- Add a naive chase heuristic (baseline) and compare vs Random.

Notes
- Role inference: `adversary_*` -> predator, others -> prey.
- Parallel API is used (PettingZoo `parallel_env`), continuous actions by default.
- See `AGENTS.md` Paths and artifacts section for one-liners.
