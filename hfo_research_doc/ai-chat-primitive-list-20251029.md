Here’s a single **Markdown** with ~50 testable primitives for PettingZoo MPE `simple_tag_v3`. No metrics. Each entry: purpose, implementation sketch, knobs.

---

# Simple Tag — Full Primitive Catalog (No Scores)

**Scope**: PettingZoo MPE `simple_tag_v3` (3 predators, 1 prey, bounded arena, obstacles).
**Interface**: `plan(obs, blackboard) -> {agent_id: action_vec}`.
**Blackboard**: `prey_est`, `mates_pos`, `escape_vecs`, `exits`, `roles`, `slots`, `grid_belief`.
**Stability**: clamp action norm; EMA headings; hysteresis on switches.

---

## A) Geometric / Robotic steering (1–15)

1. **Potential-Field Pursuit**
   How: attract to prey, repel walls/obstacles/peers.
   Knobs: `k_attr,k_rep_obs,k_rep_peer,r_inf,heading_ema,max_speed`.

2. **Voronoi Ownership + Pursuit**
   How: compute Voronoi; pursue within own cell; edge-seek otherwise.
   Knobs: `rebuild_n,wall_pad,handoff_thresh,cell_bias`.

3. **Kalman Prey Tracker (CV)**
   How: KF on `[x,y,vx,vy]`; publish `prey_est(t+τ)`.
   Knobs: `Q_pos,Q_vel,R_meas,lookahead_tau,outlier_gate`.

4. **Particle-Filter Prey Tracker**
   How: PF over prey pose; resample; publish mean.
   Knobs: `num_particles,process_noise,meas_noise,resample_alpha`.

5. **IMM Tracker (CV/CA)**
   How: switch between constant-vel and constant-accel modes.
   Knobs: `mode_trans_prob,Q_cv,Q_ca,R`.

6. **Pure Pursuit**
   How: steer directly to prey position.
   Knobs: `gain,max_speed,heading_ema`.

7. **Lead Pursuit (Time-to-Intercept)**
   How: solve linear intercept; fall back to pure pursuit if no solution.
   Knobs: `max_tau,solve_eps,fallback_gain`.

8. **Proportional Navigation (PN)**
   How: command acceleration ∝ LOS rate to prey.
   Knobs: `nav_const,los_ema,max_accel`.

9. **Velocity Obstacles (VO)**
   How: choose velocity outside collision cones.
   Knobs: `horizon,radial_margin,prior_weight`.

10. **Reciprocal VO (RVO/ORCA-lite)**
    How: reciprocal avoidance with peers; blend with pursuit.
    Knobs: `orca_tau,blend,peer_weight`.

11. **Wall Tangent Assist**
    How: near wall, project motion onto tangent; blend with seek.
    Knobs: `wall_margin,tangent_gain,blend_alpha`.

12. **A* Waypoint Chase**
    How: grid A* from self→prey; follow first waypoint; replan N steps.
    Knobs: `grid_res,replan_n,heuristic_w`.

13. **RRT-lite Intercept**
    How: sample tree toward prey; pick short feasible branch.
    Knobs: `iters,step,goal_bias`.

14. **Bezier Arc Intercept**
    How: generate offset arc; connect to prey line; follow.
    Knobs: `arc_offset,curv_gain,commit_thresh`.

15. **Constant-Bearing Closure**
    How: steer to keep prey at fixed bearing while closing range.
    Knobs: `bearing_target_deg,close_gain,bearing_gain`.

---

## B) Chokepoints, exits, and intercept (16–25)

16. **Exit Enumeration + Blocking**
    How: detect gaps; assign blockers; hold offset line.
    Knobs: `exit_radius,hold_dist,assign_policy,handoff_hys`.

17. **Gatekeeper Swap**
    How: rotating guard on top two exits; timed swap to avoid feints.
    Knobs: `swap_n,entry_bias,guard_width`.

18. **Funnel-to-Wall**
    How: two agents form moving wedge to push prey into wall.
    Knobs: `wedge_angle,advance_rate,standoff`.

19. **Cutoff Predictor**
    How: project prey to nearest boundary; intercept that point.
    Knobs: `proj_horizon,cut_gain,recalc_n`.

20. **Corner Closer**
    How: detect corner approach; coordinate L-shaped cut.
    Knobs: `corner_dist,axis_bias,commit_hys`.

21. **Lane Sealing**
    How: partition arena into lanes; seal lane transitions.
    Knobs: `lane_w,seal_gain,handoff_rules`.

22. **Time-to-Collision Map**
    How: compute TTI to cells; move to lowest-tti ridge.
    Knobs: `grid_res,tti_horizon,ridge_weight`.

23. **Intercept Cones**
    How: keep prey inside cone from wall/agent anchor.
    Knobs: `cone_angle,advance_rate,anchor_select`.

24. **S-curve Denial**
    How: create S-shaped approach to cut last-second jukes.
    Knobs: `s_amp,s_len,phase_rate`.

25. **Angle Gatekeeper**
    How: agent maintains bearing window to deny pass-through.
    Knobs: `bearing_min,bearing_max,window_gain`.

---

## C) Formations and encirclement (26–33)

26. **Fixed-Angle Envelopment (0/120/240)**
    How: slot bearings around prey; hold ring.
    Knobs: `slot_angles,slot_r,slot_gain,reassign_on_swap`.

27. **Adaptive Slot Count**
    How: slots = f(free-space); hysteresis on change.
    Knobs: `min_slots,max_slots,free_thresh,hys`.

28. **Phase-Offset Ring**
    How: ring rotation with phase offsets to avoid holes.
    Knobs: `tempo_hz,phase_offsets,ring_r`.

29. **Wedge Formation**
    How: V-shape behind prey; apex pressures, wings close.
    Knobs: `wedge_angle,apex_bias,wing_offset`.

30. **Hammer–Anvil**
    How: one holds direction, others drive prey into it.
    Knobs: `anvil_line,drive_gain,commit_tau`.

31. **Shepherding Gradient**
    How: set virtual “no-go” behind prey; push via gradient.
    Knobs: `field_center,field_gain,falloff`.

32. **Coverage Disc Packing**
    How: maximize non-overlap discs around prey vector.
    Knobs: `disc_r,repulse_gain,align_gain`.

33. **Formation Spacing Constraint**
    How: soft min inter-agent distance.
    Knobs: `spacing,repulse_gain,slot_jitter`.

---

## D) Search, sweep, and reacquire (34–40)

34. **Lawnmower Sweep**
    How: back-and-forth lines until prey seen.
    Knobs: `lane_w,sweep_speed,turn_margin`.

35. **Spiral Sweep**
    How: outward/inward spiral from last-seen.
    Knobs: `spiral_rate,rad_step,stop_radius`.

36. **Frontier-Based Search**
    How: choose boundary of unknown cells on belief grid.
    Knobs: `grid_res,frontier_gain,decay`.

37. **Pincer Reacquire**
    How: two expand, one holds center, close when contact.
    Knobs: `expand_rate,close_thresh,center_bias`.

38. **Herd-to-Sensor**
    How: force prey toward agent with best observation.
    Knobs: `sensor_bias,drive_gain,handoff_hys`.

39. **Last-Velocity Projection**
    How: predict by last prey velocity; scan arc around it.
    Knobs: `proj_tau,arc_span,arc_step`.

40. **Entropy-Minimizing Patrol**
    How: select route that most reduces belief entropy.
    Knobs: `entropy_gain,route_len,replan_n`.

---

## E) Role, tasking, and coordination (41–48)

41. **Hungarian Role Assigner**
    How: cost = time-to-slot/exit; solve; cooldown.
    Knobs: `cost_w,assign_cd,max_turn`.

42. **Min-Cost Flow Multi-Assignment**
    How: solve many-to-many slots with capacities.
    Knobs: `cap_w,dist_w,reassign_hys`.

43. **Ant-Like Task Switching**
    How: logits from local cues; ε-greedy; TTL.
    Knobs: `feat_w,eps,min_ttl,switch_penalty`.

44. **Priority Scheduler**
    How: ordered tactics; switch on no-progress.
    Knobs: `score_w,patience,cooldowns`.

45. **Feature-Based Tactics Picker**
    How: features → logits → tactic index; hysteresis.
    Knobs: `feat_gains,min_hold,hys,eps_mix`.

46. **Leader–Follower Temporary Stack**
    How: choose transient leader; others keep relative offsets.
    Knobs: `leader_rule,offsets,leader_cd`.

47. **Token-Passing Commit**
    How: only token holder may commit; others shape.
    Knobs: `token_ttl,handoff_rule,stall_hys`.

48. **Timed Role Carousel**
    How: rotate roles every N steps regardless of state.
    Knobs: `N,entry_cooldown,priority_bias`.

---

## F) Maneuvers and micro-control (49–55)

49. **Raptor-Style Dive**
    How: if alignment ok and in window, short boost; cooldown.
    Knobs: `align_deg,τ_lookahead,boost_mag,boost_dur,cooldown`.

50. **Juke-Resistant Zig Response**
    How: low-pass prey heading; commit only after dwell.
    Knobs: `heading_ema,commit_dwell,turn_rate_cap`.

51. **Stop–Go Lunge**
    How: brake to bait, then lunge on heading change.
    Knobs: `brake_mag,trigger_delta,lung e_gain`.

52. **Elliptic Approach**
    How: approach along ellipse aligned to prey velocity.
    Knobs: `a_axis,b_axis,phase_rate`.

53. **Phase-Locked Sweep**
    How: synchronize agent sweeps out-of-phase.
    Knobs: `tempo_hz,phase_set,amplitude`.

54. **PID Heading Control**
    How: PID on heading error to target.
    Knobs: `Kp,Ki,Kd,windup,max_turn`.

55. **Speed Governor**
    How: modulate speed by curvature and proximity.
    Knobs: `curve_k,prox_k,v_min,v_max`.

---

## G) Robustness aids and training utilities (56–60)

*Use to harden policies; optional in final eval.*

56. **Adversarial Prey Scripts**
    How: zig-zag, obstacle-hug, feint-to-exit, stop–go.
    Knobs: `mix,p_len,feint_angle,corner_bias`.

57. **Noise/Latency Injection**
    How: obs noise, action delay, dropout.
    Knobs: `obs_std,act_delay,drop_prob`.

58. **Domain Randomization**
    How: randomize obstacle layout, start poses.
    Knobs: `obs_count,seed_range,spawn_margin`.

59. **Slippage/Jitter Model**
    How: perturb commanded velocity.
    Knobs: `slip_prob,jitter_std,bias`.

60. **Partial-View Masking**
    How: hide prey when occluded; require reacquire.
    Knobs: `mask_prob,unmask_tau,occl_margin`.

---

## Minimal code stubs

**Primitive base**

```python
class Primitive:
    def __init__(self, **p): self.p = SimpleNamespace(**p)
    def reset(self, env_cfg): pass
    def plan(self, obs, bb): raise NotImplementedError
    def update(self, transition, bb): pass
```

**Hungarian role assigner**

```python
def assign(cost):  # cost[i,j]
    row_ind, col_ind = linear_sum_assignment(cost)
    return list(zip(row_ind, col_ind))
```

**EMA heading and clamp**

```python
def ema_heading(key, v, alpha):
    state[key] = alpha*v + (1-alpha)*state.get(key, v)
    return state[key]
def clip_norm(v, vmax):
    n = np.linalg.norm(v); return v if n<=vmax or n==0 else v*vmax/n
```

---

## Harness notes

* Keep each primitive independent and composable.
* Log all knob values and blackboard fields per episode.
* Use deterministic seeds for reproducibility.
* Start with a small subset per run; expand via sweeps or MAP-Elites.
---
Shortlist first, grounded in Simple Tag’s rules: bounded arena with obstacles, 3 slow adversaries vs 1 faster prey, collisions give reward, exiting is penalized for the prey. This favors fast intercept planning, obstacle-aware coverage, and peer-avoidance while closing space. ([pettingzoo.farama.org][1])

# Top primitives to test first

1. **Potential-field pursuit + obstacle/peer repulsion**
   Why: smooth, local, cheap; composes with most tactics; handles walls and teammates. How: attractive vector to prey; repulsive vectors from obstacles, walls, peers; normalize. Knobs: `k_attr, k_rep_obs, k_rep_peer, r_influence, max_speed, heading_ema`. Background: classical potential fields for pursuit/coverage. ([robotics.ucmerced.edu][2])

2. **Voronoi cell ownership + greedy pursuit**
   Why: partitions space to reduce teammate overlap; enables “cover-and-close” around prey. How: Voronoi on predator positions; each agent pursues inside its cell or to the cell boundary closest to the prey; reclip at bounds. Knobs: `rebuild_every_n, wall_padding, handoff_thresh, cell_bias`. Reference: recent encirclement work using Voronoi cells. ([DIVA Portal][3])

3. **Lead pursuit / time-to-intercept**
   Why: prey is faster, so pure chase wastes time; leading improves closure. How: solve linear intercept to a predicted meeting point; fall back to direct seek if no solution due to speed ratio. Knobs: `max_tau, solve_eps, fallback_gain`. Guidance-law lineage. ([ResearchGate][4])

4. **Proportional navigation (PN) steering**
   Why: biologically and robotically observed for agile interception through obstacles; robust to prey zig-zags. How: command acceleration proportional to line-of-sight rate to prey; blend with wall avoidance. Knobs: `nav_const, los_ema, max_accel`. Evidence from insect interception and PN robotics. ([PMC][5])

5. **ORCA/RVO-lite peer avoidance blended with pursuit**
   Why: three predators must avoid each other and obstacles while closing; reciprocal collision avoidance is a standard fix. How: compute admissible velocity set from ORCA; choose the element closest to the pursuit vector. Knobs: `orca_tau, blend, peer_weight`. ORCA canonical references. ([gamma.cs.unc.edu][6])

6. **Chokepoint blocking + exit enumeration**
   Why: Simple Tag has obstacles and walls; cutting escape lanes is high leverage. How: detect gaps between obstacles or to walls; assign blockers by time-to-reach; third agent drives prey toward a blocked lane. Knobs: `exit_radius, assign_policy, hold_dist, handoff_hysteresis`. Aligns with pursuit-evasion literature on barrier strategies. ([robotics.ucmerced.edu][2])

7. **Fixed-angle encirclement (0°/120°/240°) with adaptive spacing**
   Why: minimal coordination to “cap” three arcs around prey; easy to tune and combine with pursuit. How: maintain ring slots around prey; adaptive spacing via soft peer-repulsion. Knobs: `slot_angles, slot_radius, spacing, repulse_gain`. Encirclement patterns surveyed in multi-robot pursuit. ([robotics.ucmerced.edu][2])

8. **Wall-tangent assist**
   Why: prey uses walls; naive pursuit sticks; tangent projection prevents pinballing while keeping pressure. How: when within wall margin, project velocity along wall tangent then blend back to pursuit. Knobs: `wall_margin, tangent_gain, blend_alpha`. Standard boundary-following trick in robotics. ([robotics.ucmerced.edu][2])

9. **Prey state estimator (Kalman CV or IMM CV/CA)**
   Why: noisy observations and occlusion near obstacles; short-horizon prediction improves intercept and blocking. How: KF on `[x,y,vx,vy]` or IMM switching CV↔CA; publish `prey_est(t+τ)` to a blackboard used by all primitives. Knobs: `Q,R, lookahead_tau, mode_trans_prob`. Estimation is standard in pursuit/intercept stacks. ([robotics.ucmerced.edu][2])

10. **Hungarian role assigner + simple scheduler**
    Why: reduces thrash; assigns agents to slots/exits/lanes with minimal crossovers; switches tactics only on no-progress. How: build cost matrix (time-to-slot, turn cost), solve; scheduler tries [Voronoi+Pursuit] → [Blocking] → [PF] with patience and hysteresis. Knobs: `cost_weights, reassign_cooldown, patience, hysteresis`. Task allocation and staged tactics are common in pursuit teams. ([robotics.ucmerced.edu][2])

# Why these first

* They match **Simple Tag’s mechanics**: continuous motion, obstacles, team coordination, speed disadvantage for predators. ([pettingzoo.farama.org][1])
* They are **well-documented** in pursuit-evasion and multi-robot navigation, so implementation risk is low and tuning levers are known. ([robotics.ucmerced.edu][2])
* They **compose**: estimator → lead/PN → ORCA blend → Voronoi/encirclement → chokepoint. This yields quick baselines before advanced RL. ([robotics.ucmerced.edu][2])

# Quick setup notes

* Confirm you are on PettingZoo **MPE `simple_tag`** defaults: 3 adversaries, 1 prey, 2 obstacles, bounded map, continuous control. ([pettingzoo.farama.org][1])
* If you later benchmark RL baselines, the **MPE/MADDPG** papers are the canonical references for environment provenance and centralized-training setups. ([arXiv][7])

# Minimal knob sheet to expose now

* PF: `k_attr, k_rep_obs, k_rep_peer, r_influence, max_speed, heading_ema`.
* Voronoi: `rebuild_every_n, handoff_thresh, wall_padding, cell_bias`.
* Lead/PN: `max_tau, solve_eps, fallback_gain` / `nav_const, los_ema, max_accel`.
* ORCA-blend: `orca_tau, blend, peer_weight`.
* Blocking: `exit_radius, assign_policy, hold_dist, handoff_hysteresis`.
* Encirclement: `slot_angles, slot_radius, spacing, repulse_gain`.
* Wall-tangent: `wall_margin, tangent_gain, blend_alpha`.
* Estimator: `Q, R, lookahead_tau` (IMM adds `mode_trans_prob`).
* Roles/Scheduler: `cost_weights, reassign_cooldown, patience, hysteresis`.

If you want, I can convert these ten into a tiny `hfo_primitives/` scaffold with a PettingZoo runner and a JSON knobs file.

[1]: https://pettingzoo.farama.org/environments/mpe/simple_tag/?utm_source=chatgpt.com "Simple Tag - PettingZoo Documentation"
[2]: https://robotics.ucmerced.edu/sites/g/files/ufvvjh1576/f/page/documents/andreaskollingphdthesis.pdf?utm_source=chatgpt.com "Multi-Robot Pursuit-Evasion"
[3]: https://www.diva-portal.org/smash/get/diva2%3A1989723/FULLTEXT01.pdf?utm_source=chatgpt.com "Voronoi-cell based pursuit and evasion strategies in a ..."
[4]: https://www.researchgate.net/publication/352622118_A_Novel_Proportional_Navigation_Based_Method_for_Robotic_Interception_Planning_With_Final_Velocity_Control?utm_source=chatgpt.com "(PDF) A Novel Proportional Navigation Based Method for ..."
[5]: https://pmc.ncbi.nlm.nih.gov/articles/PMC8920034/?utm_source=chatgpt.com "Avoiding obstacles while intercepting a moving target"
[6]: https://gamma.cs.unc.edu/ORCA/?utm_source=chatgpt.com "Optimal Reciprocal Collision Avoidance (ORCA)"
[7]: https://arxiv.org/abs/1706.02275?utm_source=chatgpt.com "Multi-Agent Actor-Critic for Mixed Cooperative-Competitive ... - arXiv"
