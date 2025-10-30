# Daily TODO — 2025-10-30

Subject: Investigate suspected boundary/constraint bug in simple_tag_v3 (heuristic prey near walls)

Context
- Evaluator: `scripts/pz_eval_simple_tag_v3.py` (with `--diag-boundary`)
- Policy under test: `PFPursuit` predators (`custom:scripts.agents.pf_pursuit:PFPursuit`)
- Results:
  - PF vs Random (30 eps, seed 42): catch_rate=0.867, prey_near_boundary_frac≈0.323, pred_near_boundary_frac≈0.019
    - JSON: `hfo_petting_zoo_results/simple_tag_v3_eval_20251030T084216Z_seed42_eps30_predcustom-scripts.agents.pf_pursuit-PFPursuit_preyrandom.json`
  - PF vs Heuristic (30 eps, seed 42): catch_rate=0.000, prey_near_boundary_frac≈0.749, pred_near_boundary_frac≈0.020
    - JSON: `hfo_petting_zoo_results/simple_tag_v3_eval_20251030T084225Z_seed42_eps30_predcustom-scripts.agents.pf_pursuit-PFPursuit_preyheuristic.json`

Hypothesis
- Heuristic prey frequently hugs the walls (bounded box), which combined with speed advantage and our current repulsion makes closing difficult.
- Alternate hypothesis: predators encounter an effective “invisible wall” near bounds due to overly strong wall repulsion or action normalization, preventing final closing.
- Less likely: prey occasionally exceeds bounds (clipping/teleport). Need explicit exceeded-bound counters to rule out.

Action items (today)
- [ ] Add exceeded-bound counters to evaluator diagnostics:
  - Count steps where |x|>1.0+1e-6 or |y|>1.0+1e-6 for any agent (by role).
  - Add co-near-boundary metric: fraction of steps where prey near-boundary and nearest predator also near-boundary.
- [ ] Re-run PF vs heuristic with diagnostics across seeds {5, 42, 101} (30 eps each). Save JSON and record boundary stats.
- [ ] Try Wall-Tangent Assist variant (blend) vs heuristic prey (30 eps, seed 42). Compare catch_rate and boundary metrics.
- [ ] Try Lead/TTI pursuit vs heuristic prey (30 eps, seed 42). Compare catch_rate and boundary metrics.
- [ ] Verify env configuration assumptions: continuous_actions=True; default speeds (prey faster than predators), obstacle count, max_cycles. Document if parameters differ in `mpe2`.
- [ ] Sanity-check `detect_tag_event` for current `mpe2` infos (contact/is_caught/tagged); verify reward-based fallback still correct.
- [ ] Optional: GIF a few heuristic-prey episodes near walls for visual confirmation (use scripts/run_pz_make_matrix_gif.sh as template).

Acceptance criteria
- No exceeded-bound events observed → conclude boundary hugging is within expected dynamics, not an escape bug.
- If co-near-boundary spikes with low catch rate, prioritize wall-tangent and lead pursuit to address closing.
- Provide short summary with metrics and next-step recommendations.
