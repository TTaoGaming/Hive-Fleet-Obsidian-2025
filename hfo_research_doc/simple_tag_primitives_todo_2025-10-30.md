# Simple Tag Primitives — Implementation TODO (Singles First)

Scope: PettingZoo MPE `simple_tag_v3` (3 predators, 1 prey, bounded arena, obstacles). We will implement and test single-agent "policy primitives" first, then compose them into multi-agent meta-layers aligned with OBSIDIAN roles and a virtual stigmergy coordination layer.

References:
- Source list: `hfo_research_doc/ai-chat-primitive-list-20251029.md` (50+ primitives, no scores)
- Evaluator: `scripts/pz_eval_simple_tag_v3.py` (pred vs prey configurable; custom policies)
- Example custom policy: `scripts/agents/sample_custom_agent.py` (FleeCentroid)

Contract for policies:
- Class must accept `(role: str, baseline: str)` in `__init__`
- Must implement `select_action(self, penv, agent_name: str) -> np.ndarray | int`
- May use a shared in-memory blackboard (module-global) for ephemeral state: `prey_est`, `mates_pos`, `escape_vecs`, `exits`, `roles`, `slots`, `grid_belief`
- Stability aids: clamp action norm; EMA headings; hysteresis on discrete switches

Run harness (examples):
- Random preds vs heuristic prey (research):
  - `./.venv/bin/python scripts/pz_eval_simple_tag_v3.py --pred random --prey heuristic --episodes 100 --seed 42`
- Heuristic preds vs custom prey:
  - `./.venv/bin/python scripts/pz_eval_simple_tag_v3.py --pred heuristic --prey custom:scripts.agents.sample_custom_agent:FleeCentroid --episodes 50 --seed 7`

Acceptance criteria for each primitive:
- Code lives under `scripts/agents/` as a class (one file per primitive or grouped by type)
- Works with evaluator; returns valid continuous action for its role
- Knobs exposed via class kwargs with sensible defaults
- Prints/records its knob values and any blackboard fields it sets (stdout is fine; JSON logging optional later)
- Sanity run: `episodes=20, seed=42` completes without errors; JSON result saved

---

## Phase 1 — Single-agent pursuit/avoid primitives (implement first)

1. [ ] Potential-Field Pursuit (A1)
   - Purpose: attract to prey, repel walls/obstacles (peer repulsion optional for singles)
   - Knobs: `k_attr, k_rep_obs, r_inf, heading_ema, max_speed`
   - File: `scripts/agents/pf_pursuit.py` → class `PFPursuit`
   - Role: pred
   - Notes: Use wall distance as obstacle proxy; clamp output

2. [ ] Lead Pursuit / Time-to-Intercept (A7)
   - Purpose: compute lead point by solving linear intercept; fallback to pure pursuit
   - Knobs: `max_tau, solve_eps, fallback_gain`
   - File: `scripts/agents/lead_pursuit.py` → class `LeadPursuit`
   - Role: pred
   - Notes: Use prey vel from env; clip to arena bounds

3. [ ] Proportional Navigation (PN) Steering (A8)
   - Purpose: steer proportional to LOS rate; robust to zig-zags
   - Knobs: `nav_const, los_ema, max_accel`
   - File: `scripts/agents/pn_steer.py` → class `PNSteer`
   - Role: pred
   - Notes: Estimate LOS rate with EMA; integrate to velocity proxy then map to action

4. [ ] Wall-Tangent Assist (A11)
   - Purpose: near wall, project motion onto tangent then blend back to pursuit
   - Knobs: `wall_margin, tangent_gain, blend_alpha`
   - File: `scripts/agents/wall_tangent.py` → class `WallTangentAssist`
   - Role: pred
   - Notes: Reuse from enhanced predator idea; uses arena bound≈1.0

5. [ ] Prey State Estimator — Kalman CV (A3)
   - Purpose: estimate `[x,y,vx,vy]` and publish `prey_est(t+τ)` to blackboard
   - Knobs: `Q_pos, Q_vel, R_meas, lookahead_tau, outlier_gate`
   - File: `scripts/agents/estimators.py` → class `KFPreyCV`
   - Role: shared utility (feeds others)
   - Notes: Optional if env gives exact state; keep modular for noise injections

6. [ ] Last-Velocity Projection (D39)
   - Purpose: predict prey by last vel; bias plan around projection
   - Knobs: `proj_tau, arc_span`
   - File: `scripts/agents/last_vel_proj.py` → class `LastVelProj`
   - Role: pred
   - Notes: Lightweight alternative to KF

7. [ ] Speed Governor (F55)
   - Purpose: modulate speed by curvature and proximity to target/walls
   - Knobs: `curve_k, prox_k, v_min, v_max`
   - File: `scripts/agents/speed_governor.py` → class `SpeedGovernor`
   - Role: pred/prey (wrapper decorator)
   - Notes: Apply after direction selection; keeps motion smooth

8. [ ] Juke-Resistant Zig Response (F50)
   - Purpose: low-pass prey heading; commit after dwell to avoid overreacting
   - Knobs: `heading_ema, commit_dwell, turn_rate_cap`
   - File: `scripts/agents/zig_response.py` → class `ZigResponse`
   - Role: pred (wrapper/decorator)
   - Notes: Combine with Lead/PN output

9. [ ] Potential-Field Flee (mirror of A1 for prey)
   - Purpose: inverse-distance repulsion from predators + obstacle-aware flee
   - Knobs: `k_rep_pred, k_rep_obs, r_inf, inertia`
   - File: `scripts/agents/pf_flee.py` → class `PFFlee`
   - Role: prey
   - Notes: Generalization of current heuristic prey

Sanity runs for Phase 1 (examples):
- `./.venv/bin/python scripts/pz_eval_simple_tag_v3.py --pred custom:scripts.agents.pf_pursuit:PFPursuit --prey heuristic --episodes 20 --seed 42`
- `./.venv/bin/python scripts/pz_eval_simple_tag_v3.py --pred custom:scripts.agents.lead_pursuit:LeadPursuit --prey heuristic --episodes 20 --seed 42`

---

## Phase 2 — Single-agent intercept and environment-aware tactics

10. [ ] Cutoff Predictor (B19)
    - Purpose: project prey to nearest boundary; intercept that point
    - Knobs: `proj_horizon, cut_gain, recalc_n`
    - File: `scripts/agents/cutoff_predictor.py` → class `CutoffPredictor`
    - Role: pred

11. [ ] Corner Closer (B20)
    - Purpose: detect corner approach; bias motion for L-shaped cut
    - Knobs: `corner_dist, axis_bias, commit_hys`
    - File: `scripts/agents/corner_closer.py` → class `CornerCloser`
    - Role: pred

12. [ ] Wall-Aware Flee (prey)
    - Purpose: flee while avoiding wall traps; follow tangent if trapped
    - Knobs: `wall_margin, tangent_gain, escape_bias`
    - File: `scripts/agents/wall_aware_flee.py` → class `WallAwareFlee`
    - Role: prey

Sanity runs for Phase 2:
- `./.venv/bin/python scripts/pz_eval_simple_tag_v3.py --pred custom:scripts.agents.cutoff_predictor:CutoffPredictor --prey heuristic --episodes 20 --seed 42`

---

## Phase 3 — Multi-agent enablers (stub now, full later with stigmergy)

13. [ ] ORCA/RVO-lite Peer Avoidance (A10)
    - Purpose: reciprocal collision avoidance among predators; blend with pursuit
    - Knobs: `orca_tau, blend, peer_weight`
    - File: `scripts/agents/orca_blend.py` → class `ORCABlend`
    - Role: pred (composable wrapper)
    - Notes: For singles, implement wall/obstacle-only variant; full peer logic later

14. [ ] Voronoi Ownership + Pursuit (A2)
    - Purpose: partition by Voronoi; pursue in own cell; edge-seek otherwise
    - Knobs: `rebuild_n, wall_pad, handoff_thresh, cell_bias`
    - File: `scripts/agents/voronoi_pursuit.py` → class `VoronoiPursuit`
    - Role: pred
    - Notes: Provide single-agent fallback = global pursuit

15. [ ] Exit Enumeration + Blocking (B16)
    - Purpose: detect escape gaps; assign blockers
    - Knobs: `exit_radius, hold_dist, assign_policy, handoff_hys`
    - File: `scripts/agents/exit_block.py` → class `ExitBlocking`
    - Role: pred
    - Notes: Single-agent mode: pick most likely exit and shadow it

16. [ ] Fixed-Angle Encirclement (C26)
    - Purpose: maintain ring slots; adaptive spacing
    - Knobs: `slot_angles, slot_r, slot_gain, repulse_gain`
    - File: `scripts/agents/encirclement.py` → class `EncircleFixed`
    - Role: pred
    - Notes: Single-agent mode: prefer slot nearest to heading

17. [ ] Hungarian Role Assigner + Scheduler (E41, E44)
    - Purpose: cost-based assignment and staged tactics
    - Knobs: `cost_w, assign_cd, patience, hysteresis`
    - File: `scripts/agents/assign_and_schedule.py` → classes `RoleAssign`, `TacticScheduler`
    - Role: team layer (later); for now, prepare interface only

---

## Logging and blackboard fields

- `prey_est`: dict with `pos`, `vel`, `t_pred`
- `mates_pos`: list of `[x,y]` for predators (future)
- `escape_vecs`: candidate flee directions (prey)
- `exits`: list of gap descriptors (center, width)
- `roles`: assigned roles per agent
- `slots`: encirclement slot targets
- `grid_belief`: optional occupancy or uncertainty grid

---

## Next steps after Phase 1
- Compose wrappers: e.g., `(LeadPursuit → ZigResponse → SpeedGovernor)`
- Begin multi-agent meta-layer using virtual stigmergy (append-only blackboard updates per step)
- Add light JSON logging of knob settings and blackboard snapshots per episode

---

Maintainer notes:
- Keep each class ≤200 logical lines (excluding blanks/comments)
- No TODO placeholders in committed code; use this doc to track follow-ups
- Prefer deterministic seeds during development (fixed `--seed`)