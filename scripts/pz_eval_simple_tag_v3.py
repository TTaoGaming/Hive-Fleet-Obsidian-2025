#!/usr/bin/env python3
"""
Flexible evaluator for PettingZoo MPE simple_tag_v3:
- Choose predator policy (random | heuristic | custom:module:Class)
- Choose prey policy      (random | heuristic | custom:module:Class)

Heuristic set:
- baseline=research: pure pursuit predators; inverse-distance flee prey
- baseline=enhanced:  short-lead pursuit; flee with inertia and stronger repulsion

Custom policy contract:
- Provide a class with signature `class MyPolicy:` and method:
        def select_action(self, penv, agent_name: str) -> "np.ndarray | int":
            # Return a valid action for the given agent at current env state.
  The policy may introspect `penv.unwrapped.world` for positions/velocities
  similar to the heuristics below. For continuous actions, map your desired
  direction in R^2 to a 5-dim Box using `dir_to_continuous_action` logic.

Examples:
  - Random predators vs heuristic fleeing prey (research):
      python scripts/pz_eval_simple_tag_v3.py --pred random --prey heuristic \
             --episodes 100 --seed 42 --baseline research
  - Heuristic predators vs your custom prey:
      python scripts/pz_eval_simple_tag_v3.py \
             --pred heuristic --prey custom:scripts.agents.sample_custom_agent:FleeCentroid
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import importlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    from mpe2 import simple_tag_v3
except Exception:  # pragma: no cover
    from pettingzoo.mpe import simple_tag_v3  # type: ignore

# Ensure repo root is importable so module paths like 'scripts.agents.*' resolve
_THIS = Path(__file__).resolve()
_ROOT = _THIS.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# --------- Utilities ---------

def unit(vec: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    n = np.linalg.norm(vec)
    if n < eps:
        return np.zeros_like(vec)
    return vec / n


def dir_to_continuous_action(d: np.ndarray) -> np.ndarray:
    """Map R^2 desired direction to 5-dim Box action [noop, left, right, down, up]."""
    ax = float(d[0])
    ay = float(d[1])
    out = np.zeros(5, dtype=np.float32)
    if abs(ax) < 1e-6 and abs(ay) < 1e-6:
        out[0] = 1.0
        return out
    if ax < 0:
        out[1] = -ax
    else:
        out[2] = ax
    if ay < 0:
        out[3] = -ay
    else:
        out[4] = ay
    mx = out[1:5].max() if out[1:5].size else 1.0
    if mx > 1e-6:
        out[1:5] = out[1:5] / mx
    return out


# --------- World view helpers ---------

@dataclass
class WorldView:
    prey_pos: np.ndarray
    prey_vel: np.ndarray
    preds_pos: List[np.ndarray]
    preds_vel: List[np.ndarray]
    landmarks: List[np.ndarray]


def get_world_view(raw_env) -> WorldView:
    w = raw_env.world
    prey = [a for a in w.agents if not getattr(a, "adversary", False)][0]
    preds = [a for a in w.agents if getattr(a, "adversary", False)]
    landmarks = [l for l in w.landmarks]
    return WorldView(
        prey_pos=prey.state.p_pos.copy(),
        prey_vel=prey.state.p_vel.copy(),
        preds_pos=[p.state.p_pos.copy() for p in preds],
        preds_vel=[p.state.p_vel.copy() for p in preds],
        landmarks=[l.state.p_pos.copy() for l in landmarks],
    )


# --------- Heuristic policies ---------

def predator_dir_enhanced(view: WorldView, my_pos: np.ndarray, my_vel: np.ndarray) -> np.ndarray:
    """Enhanced pursuit: short-horizon lead with gentle wall handling."""
    k_lead = 0.15
    bound = 1.0
    prey_future = view.prey_pos + k_lead * view.prey_vel
    prey_future = np.clip(prey_future, -bound, bound)
    desired = prey_future - my_pos
    d = unit(desired)
    near = 0.01
    inward = np.zeros(2, dtype=np.float32)
    for i in range(2):
        if abs(my_pos[i]) > (bound - near) and not (abs(prey_future[i]) > (bound - near)):
            inward[i] = -0.15 * np.sign(my_pos[i])
    return unit(d + inward)


def predator_dir_research(view: WorldView, my_pos: np.ndarray, my_vel: np.ndarray) -> np.ndarray:
    """Research baseline: pure pursuit."""
    return unit(view.prey_pos - my_pos)


def prey_dir_enhanced(view: WorldView, my_pos: np.ndarray, my_vel: np.ndarray) -> np.ndarray:
    """Enhanced flee: inverse-distance repulsion from predators plus mild inertia."""
    k_rep_pred = 1.25
    k_inertia = 0.10
    rep = np.zeros(2, dtype=np.float32)
    for p in view.preds_pos:
        v = my_pos - p
        rep += unit(v) / (np.linalg.norm(v) + 1e-6)
    d = k_rep_pred * rep + k_inertia * unit(my_vel)
    return unit(d)


def prey_dir_research(view: WorldView, my_pos: np.ndarray, my_vel: np.ndarray) -> np.ndarray:
    """Research baseline: inverse-distance flee (no inertia)."""
    rep = np.zeros(2, dtype=np.float32)
    for p in view.preds_pos:
        v = my_pos - p
        rep += unit(v) / (np.linalg.norm(v) + 1e-6)
    return unit(rep)


# --------- Policy interface ---------

class BasePolicy:
    role: str  # 'pred' or 'prey'

    def __init__(self, role: str = "pred", baseline: str = "research") -> None:
        self.role = role
        self.baseline = baseline

    def select_action(self, penv, agent_name: str):  # noqa: ANN001
        raise NotImplementedError


class RandomPolicy(BasePolicy):
    def select_action(self, penv, agent_name: str):  # noqa: ANN001
        return penv.action_space(agent_name).sample()


class HeuristicPolicy(BasePolicy):
    def select_action(self, penv, agent_name: str):  # noqa: ANN001
        raw = penv.unwrapped
        w = raw.world
        aobj = next(a for a in w.agents if getattr(a, 'name', None) == agent_name)
        is_pred = getattr(aobj, 'adversary', False)
        my_pos = aobj.state.p_pos.copy()
        my_vel = aobj.state.p_vel.copy()
        view = get_world_view(raw)

        if self.baseline == 'research':
            pred_fn = predator_dir_research
            prey_fn = prey_dir_research
        else:
            pred_fn = predator_dir_enhanced
            prey_fn = prey_dir_enhanced

        if is_pred and self.role == 'pred':
            d = pred_fn(view, my_pos, my_vel)
            return dir_to_continuous_action(d)
        if (not is_pred) and self.role == 'prey':
            d = prey_fn(view, my_pos, my_vel)
            return dir_to_continuous_action(d)
        # Fallback to random if role mismatch (shouldn't happen under correct wiring)
        return penv.action_space(agent_name).sample()


def parse_policy(arg: str, role: str, baseline: str, extra_kwargs: dict | None = None) -> BasePolicy:
    arg = (arg or '').strip()
    extra = extra_kwargs or {}
    if arg in ("r", "rand", "random"):
        return RandomPolicy(role=role, baseline=baseline)
    if arg in ("h", "heur", "heuristic"):
        return HeuristicPolicy(role=role, baseline=baseline)
    if arg.startswith("custom:"):
        _, mod, cls = arg.split(":", 2)
        module = importlib.import_module(mod)
        cls_obj = getattr(module, cls)
        return cls_obj(role=role, baseline=baseline, **extra)
    raise ValueError(f"Unknown policy spec '{arg}'. Use random|heuristic|custom:module:Class")


# --------- Detection ---------

def detect_tag_event(rewards: Dict[str, float], infos: Dict[str, dict], adversary_keys: set[str]) -> bool:
    for _, info in infos.items():
        if not isinstance(info, dict):
            continue
        if info.get("contact") or info.get("is_caught") or info.get("tagged"):
            return True
    for k in adversary_keys:
        if rewards.get(k, 0.0) > 0.0:
            return True
    return False


# --------- Runner ---------

def run_eval(episodes: int, seed: int, pred_spec: str, prey_spec: str, baseline: str,
             pred_kwargs: dict | None = None, prey_kwargs: dict | None = None) -> Tuple[float, float, int]:
    penv = simple_tag_v3.parallel_env(continuous_actions=True, render_mode=None)
    obs, infos = penv.reset(seed=seed)

    pred_policy = parse_policy(pred_spec, role='pred', baseline=baseline, extra_kwargs=pred_kwargs)
    prey_policy = parse_policy(prey_spec, role='prey', baseline=baseline, extra_kwargs=prey_kwargs)

    adversary_keys = {a for a in penv.agents if ("adversary" in a) or ("pursuer" in a) or ("tagger" in a)}

    catches = 0
    steps_to_first: List[int] = []

    for ep in range(episodes):
        ep_seed = seed + ep
        obs, infos = penv.reset(seed=ep_seed)
        step = 0
        caught = False
        first_step: Optional[int] = None
        while True:
            actions: Dict[str, np.ndarray | int] = {}
            raw = penv.unwrapped
            w = raw.world
            for ag in penv.agents:
                aobj = next(a for a in w.agents if getattr(a, 'name', None) == ag)
                is_pred = getattr(aobj, 'adversary', False)
                if is_pred:
                    actions[ag] = pred_policy.select_action(penv, ag)
                else:
                    actions[ag] = prey_policy.select_action(penv, ag)
            obs, rewards, terms, truncs, infos = penv.step(actions)
            step += 1
            if not caught and detect_tag_event(rewards, infos, adversary_keys):
                caught = True
                first_step = step
            if all(terms.values()) or all(truncs.values()):
                break
        if caught and first_step is not None:
            catches += 1
            steps_to_first.append(first_step)

    catch_rate = catches / float(episodes)
    avg_steps = float(np.mean(steps_to_first)) if steps_to_first else float("nan")
    return catch_rate, avg_steps, catches


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--outdir", type=str, default="hfo_petting_zoo_results")
    parser.add_argument("--baseline", type=str, choices=["research", "enhanced"], default="research")
    parser.add_argument("--pred", type=str, default="heuristic", help="Pred policy: random|heuristic|custom:module:Class")
    parser.add_argument("--prey", type=str, default="random", help="Prey policy: random|heuristic|custom:module:Class")
    parser.add_argument("--pred-kwargs", type=str, default=None, help="JSON dict of kwargs for pred policy class (e.g., '{\"k_rep_wall\":0.0}')")
    parser.add_argument("--prey-kwargs", type=str, default=None, help="JSON dict of kwargs for prey policy class")
    parser.add_argument("--diag-boundary", action="store_true", help="Collect boundary and movement diagnostics (near-wall, min-dists, clipping, OOB checks)")
    parser.add_argument("--diag-boundary-thr", type=float, default=0.98, help="Abs position threshold to count 'near boundary' (default 0.98)")
    parser.add_argument("--diag-close-dist", type=float, default=0.03, help="Distance threshold to consider predators 'close' to prey (default 0.03)")
    args = parser.parse_args()

    run_end = datetime.now(timezone.utc)

    try:
        import pettingzoo as _pz
        pz_ver = getattr(_pz, "__version__", "unknown")
    except Exception:
        pz_ver = "unknown"
    try:
        import gymnasium as _gym
        gym_ver = getattr(_gym, "__version__", "unknown")
    except Exception:
        gym_ver = "unknown"
    try:
        import mpe2 as _mpe2
        mpe2_ver = getattr(_mpe2, "__version__", "unknown")
    except Exception:
        mpe2_ver = "unknown"

    # Optional diagnostics accumulation
    diag = {"enabled": bool(args.diag_boundary)}
    if args.diag_boundary:
        diag.update({
            "prey_near_boundary_steps": 0,
            "prey_total_steps": 0,
            "pred_near_boundary_steps": 0,
            "pred_total_steps": 0,
            # Extended
            "prey_oob_steps": 0,
            "pred_oob_steps": 0,
            "near_boundary_steps": 0,  # steps where prey is near boundary
            "near_boundary_min_dists_sum": 0.0,
            "near_boundary_min_dists_min": float("inf"),
            # Movement clipping (predators)
            "pred_clip_steps": 0,
            "pred_clip_steps_near_boundary": 0,
            "pred_clip_total_checked": 0,
            "pred_clip_total_checked_near_boundary": 0,
        })

    # Parse optional JSON kwargs for policies (used for custom policies)
    try:
        pred_kwargs = json.loads(args.pred_kwargs) if args.pred_kwargs else None
    except Exception:
        pred_kwargs = None
    try:
        prey_kwargs = json.loads(args.prey_kwargs) if args.prey_kwargs else None
    except Exception:
        prey_kwargs = None

    def _accum_diag_pre_step(penv, actions):
        if not args.diag_boundary:
            return
        raw = penv.unwrapped
        w = raw.world
        bound = 1.0
        thr = float(args.diag_boundary_thr)
        # Mark near-boundary and OOB before stepping
        for a in w.agents:
            pos = a.state.p_pos
            near = (abs(pos[0]) >= thr) or (abs(pos[1]) >= thr)
            oob = (abs(pos[0]) > bound + 1e-6) or (abs(pos[1]) > bound + 1e-6)
            if getattr(a, 'adversary', False):
                diag["pred_total_steps"] += 1
                if near:
                    diag["pred_near_boundary_steps"] += 1
                if oob:
                    diag["pred_oob_steps"] += 1
            else:
                diag["prey_total_steps"] += 1
                if near:
                    diag["prey_near_boundary_steps"] += 1
                if oob:
                    diag["prey_oob_steps"] += 1

        # Track movement clipping intent (predators): compare intended vector mag to later delta
        # Store intended movement per agent for the next post-step check
        _intended = {}
        for ag, act in actions.items():
            # action -> effective 2D desired direction
            if isinstance(act, np.ndarray) and act.shape[0] >= 5:
                eff = np.array([float(act[2]) - float(act[1]), float(act[4]) - float(act[3])], dtype=np.float32)
                _intended[ag] = eff
            else:
                _intended[ag] = None
        return _intended

    def _accum_diag_post_step(penv, intended):
        if not args.diag_boundary:
            return
        raw = penv.unwrapped
        w = raw.world
        thr = float(args.diag_boundary_thr)
        close_thr = float(args.diag_close_dist)

        # Min predator-prey distance when prey is near boundary
        prey = [a for a in w.agents if not getattr(a, 'adversary', False)][0]
        prey_pos = prey.state.p_pos.copy()
        prey_near = (abs(prey_pos[0]) >= thr) or (abs(prey_pos[1]) >= thr)
        if prey_near:
            diag["near_boundary_steps"] += 1
            dmin = float("inf")
            for p in [a for a in w.agents if getattr(a, 'adversary', False)]:
                dp = float(np.linalg.norm(prey_pos - p.state.p_pos))
                if dp < dmin:
                    dmin = dp
            diag["near_boundary_min_dists_sum"] += dmin
            if dmin < diag["near_boundary_min_dists_min"]:
                diag["near_boundary_min_dists_min"] = dmin

        # Movement clipping (predators): check ratio of actual displacement vs intended
        for p in [a for a in w.agents if getattr(a, 'adversary', False)]:
            name = getattr(p, 'name', None)
            intend = intended.get(name) if isinstance(intended, dict) else None
            if intend is None:
                continue
            intend_mag = float(np.linalg.norm(intend))
            # Approximate actual step size via velocity magnitude (state has p_vel)
            # Note: better would be delta position, but p_vel reflects applied movement this step
            actual_mag = float(np.linalg.norm(p.state.p_vel))
            near = (abs(p.state.p_pos[0]) >= thr) or (abs(p.state.p_pos[1]) >= thr)
            if intend_mag > 0.1:  # only consider meaningful commands
                diag["pred_clip_total_checked"] += 1
                if near:
                    diag["pred_clip_total_checked_near_boundary"] += 1
                ratio = actual_mag / max(intend_mag, 1e-6)
                if ratio < 0.25:
                    diag["pred_clip_steps"] += 1
                    if near:
                        diag["pred_clip_steps_near_boundary"] += 1

    # Wrap run_eval to inject diagnostics by reusing its loop via a local copy
    def _run_eval_with_diag(episodes: int, seed: int, pred_spec: str, prey_spec: str, baseline: str):
        if not args.diag_boundary:
            return run_eval(episodes, seed, pred_spec, prey_spec, baseline, pred_kwargs=pred_kwargs, prey_kwargs=prey_kwargs)

        from typing import List, Dict, Optional, Tuple
        penv = simple_tag_v3.parallel_env(continuous_actions=True, render_mode=None)
        obs, infos = penv.reset(seed=seed)

        pred_policy = parse_policy(pred_spec, role='pred', baseline=baseline, extra_kwargs=pred_kwargs)
        prey_policy = parse_policy(prey_spec, role='prey', baseline=baseline, extra_kwargs=prey_kwargs)

        adversary_keys = {a for a in penv.agents if ("adversary" in a) or ("pursuer" in a) or ("tagger" in a)}

        catches = 0
        steps_to_first: List[int] = []

        for ep in range(episodes):
            ep_seed = seed + ep
            obs, infos = penv.reset(seed=ep_seed)
            step = 0
            caught = False
            first_step: Optional[int] = None
            while True:
                actions: Dict[str, np.ndarray | int] = {}
                raw = penv.unwrapped
                w = raw.world
                for ag in penv.agents:
                    aobj = next(a for a in w.agents if getattr(a, 'name', None) == ag)
                    is_pred = getattr(aobj, 'adversary', False)
                    if is_pred:
                        actions[ag] = pred_policy.select_action(penv, ag)
                    else:
                        actions[ag] = prey_policy.select_action(penv, ag)
                _intended = _accum_diag_pre_step(penv, actions)
                obs, rewards, terms, truncs, infos = penv.step(actions)
                _accum_diag_post_step(penv, _intended)
                step += 1
                if not caught and detect_tag_event(rewards, infos, adversary_keys):
                    caught = True
                    first_step = step
                if all(terms.values()) or all(truncs.values()):
                    break
            if caught and first_step is not None:
                catches += 1
                steps_to_first.append(first_step)

        catch_rate = catches / float(episodes)
        avg_steps = float(np.mean(steps_to_first)) if steps_to_first else float("nan")
        return catch_rate, avg_steps, catches

    cr, avg, c = _run_eval_with_diag(args.episodes, args.seed, args.pred, args.prey, args.baseline)

    results = {
        "env": "mpe.simple_tag_v3",
        "policies": {
            "pred": args.pred,
            "prey": args.prey,
            "baseline": args.baseline,
        },
        "parameters": {
            "episodes": int(args.episodes),
            "seed": int(args.seed),
            "continuous_actions": True,
        },
        "diagnostics": None if not args.diag_boundary else {
            "prey_near_boundary_frac": (diag["prey_near_boundary_steps"] / diag["prey_total_steps"]) if diag["prey_total_steps"] else None,
            "pred_near_boundary_frac": (diag["pred_near_boundary_steps"] / diag["pred_total_steps"]) if diag["pred_total_steps"] else None,
            "prey_near_boundary_steps": int(diag["prey_near_boundary_steps"]),
            "prey_total_steps": int(diag["prey_total_steps"]),
            "pred_near_boundary_steps": int(diag["pred_near_boundary_steps"]),
            "pred_total_steps": int(diag["pred_total_steps"]),
            "prey_oob_steps": int(diag["prey_oob_steps"]),
            "pred_oob_steps": int(diag["pred_oob_steps"]),
            "near_boundary_steps": int(diag["near_boundary_steps"]),
            "near_boundary_min_dist_avg": (
                (diag["near_boundary_min_dists_sum"] / max(diag["near_boundary_steps"], 1))
                if diag["near_boundary_steps"] else None
            ),
            "near_boundary_min_dist_min": (
                (None if diag["near_boundary_min_dists_min"] == float("inf") else float(diag["near_boundary_min_dists_min"]))
            ),
            "pred_clip_steps": int(diag["pred_clip_steps"]),
            "pred_clip_total_checked": int(diag["pred_clip_total_checked"]),
            "pred_clip_rate": (
                (diag["pred_clip_steps"] / max(diag["pred_clip_total_checked"], 1))
                if diag["pred_clip_total_checked"] else None
            ),
            "pred_clip_steps_near_boundary": int(diag["pred_clip_steps_near_boundary"]),
            "pred_clip_total_checked_near_boundary": int(diag["pred_clip_total_checked_near_boundary"]),
            "pred_clip_rate_near_boundary": (
                (diag["pred_clip_steps_near_boundary"] / max(diag["pred_clip_total_checked_near_boundary"], 1))
                if diag["pred_clip_total_checked_near_boundary"] else None
            ),
            "threshold_abs": float(args.diag_boundary_thr),
            "close_dist_thr": float(args.diag_close_dist),
        },
        "library_versions": {
            "pettingzoo": pz_ver,
            "gymnasium": gym_ver,
            "mpe2": mpe2_ver,
            "numpy": np.__version__,
        },
        "results": {
            "catch_rate": float(cr),
            "avg_steps_to_first_catch": None if np.isnan(avg) else float(avg),
            "caught_episodes": int(c),
            "total_episodes": int(args.episodes),
        },
        "timestamps": {
            "run_end_iso": run_end.isoformat(),
        },
        "host": {
            "python": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            "platform": os.uname().sysname if hasattr(os, "uname") else "unknown",
        },
    }

    os.makedirs(args.outdir, exist_ok=True)
    ts_for_name = run_end.strftime("%Y%m%dT%H%M%SZ")
    pred_tag = args.pred.replace(":", "-").replace("/", "-")
    prey_tag = args.prey.replace(":", "-").replace("/", "-")
    fname = (
        f"simple_tag_v3_eval_{ts_for_name}_seed{args.seed}_eps{args.episodes}_"
        f"pred{pred_tag}_prey{prey_tag}.json"
    )
    fpath = os.path.join(args.outdir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, sort_keys=True)

    avg_str = f"{avg:.2f}" if not np.isnan(avg) else "nan"
    print("simple_tag_v3 eval summary")
    print(f"pred={args.pred}  prey={args.prey}  baseline={args.baseline}")
    print(f"episodes={args.episodes} seed={args.seed}")
    print(f"catch_rate={cr:.3f} avg_steps_to_first_catch={avg_str} caught={c}/{args.episodes}")
    print("JSON saved:", fpath)


if __name__ == "__main__":
    main()
