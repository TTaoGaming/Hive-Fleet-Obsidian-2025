#!/usr/bin/env python3
"""
2x2 matrix runner for PettingZoo MPE simple_tag_v3:
- random_vs_random (RvsR)
- heuristic_pred_vs_random_prey (HvsR)
- random_pred_vs_heuristic_prey (RvsH)
- heuristic_vs_heuristic (HvsH)

Heuristics:
- Predator: pure pursuit toward prey (optionally adds a small lead with prey velocity)
- Prey: flee from adversaries (repulsive potential); bias away from centroid of predators

Uses continuous_actions=True and maps desired direction to 5-dim Box actions with indices [noop, left, right, down, up].
Writes a single JSON file with parameters, per-cell results, versions, and timestamps.
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import numpy as np

try:
    from mpe2 import simple_tag_v3
except Exception:  # pragma: no cover
    from pettingzoo.mpe import simple_tag_v3  # type: ignore


# ---------- Utility ----------

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


# ---------- Policies ----------

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


def predator_dir_enhanced(view: WorldView, my_pos: np.ndarray, my_vel: np.ndarray) -> np.ndarray:
    """Enhanced pursuit (previous default): short-horizon lead with gentle wall handling."""
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
    """Research baseline: pure pursuit (greedy direction to current prey position)."""
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
    """Research baseline: inverse-distance weighted flee from predators (no inertia/landmarks)."""
    rep = np.zeros(2, dtype=np.float32)
    for p in view.preds_pos:
        v = my_pos - p
        rep += unit(v) / (np.linalg.norm(v) + 1e-6)
    return unit(rep)


def build_actions(penv, matchup: str, baseline: str) -> Dict[str, np.ndarray | int]:
    raw = penv.unwrapped
    w = raw.world
    view = get_world_view(raw)

    actions: Dict[str, np.ndarray] = {}
    for ag in penv.agents:
        aobj = next(a for a in w.agents if getattr(a, 'name', None) == ag)
        is_pred = getattr(aobj, 'adversary', False)
        my_pos = aobj.state.p_pos.copy()
        my_vel = aobj.state.p_vel.copy()

        # Select heuristic set
        if baseline == 'research':
            pred_fn = predator_dir_research
            prey_fn = prey_dir_research
        else:
            pred_fn = predator_dir_enhanced
            prey_fn = prey_dir_enhanced

        if matchup == 'RvsR':
            actions[ag] = penv.action_space(ag).sample()
        elif matchup == 'HvsR':
            if is_pred:
                d = pred_fn(view, my_pos, my_vel)
                actions[ag] = dir_to_continuous_action(d)
            else:
                actions[ag] = penv.action_space(ag).sample()
        elif matchup == 'RvsH':
            if is_pred:
                actions[ag] = penv.action_space(ag).sample()
            else:
                d = prey_fn(view, my_pos, my_vel)
                actions[ag] = dir_to_continuous_action(d)
        elif matchup == 'HvsH':
            if is_pred:
                d = pred_fn(view, my_pos, my_vel)
            else:
                d = prey_fn(view, my_pos, my_vel)
            actions[ag] = dir_to_continuous_action(d)
        else:
            raise ValueError(f"unknown matchup {matchup}")
    return actions


# ---------- Detection ----------

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


# ---------- Runner ----------

def run_matchup(episodes: int, seed: int, matchup: str, baseline: str) -> Tuple[float, float, int]:
    penv = simple_tag_v3.parallel_env(continuous_actions=True, render_mode=None)
    obs, infos = penv.reset(seed=seed)
    adversary_keys = {a for a in penv.agents if ("adversary" in a) or ("pursuer" in a) or ("tagger" in a)}

    catches = 0
    steps_to_first: List[int] = []

    for ep in range(episodes):
        ep_seed = seed + ep
        obs, infos = penv.reset(seed=ep_seed)
        step = 0
        caught = False
        first_step = None
        while True:
            actions = build_actions(penv, matchup, baseline)
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
    parser.add_argument(
        "--baseline",
        type=str,
        choices=["research", "enhanced"],
        default="research",
        help="Heuristic set to use: 'research' (pure pursuit + invdist flee) or 'enhanced' (lead + inertia)",
    )
    parser.add_argument(
        "--no-fail-on-bad-ordering",
        action="store_true",
        help="Do not exit non-zero when expected ordering checks fail.",
    )
    parser.add_argument(
        "--min-hvsr",
        type=float,
        default=None,
        help="If set, enforce that HvsR catch_rate >= this threshold (exit non-zero if violated).",
    )
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

    cells = ["RvsR", "HvsR", "RvsH", "HvsH"]
    results = {}
    for cell in cells:
        cr, avg, c = run_matchup(args.episodes, args.seed, cell, args.baseline)
        results[cell] = {
            "catch_rate": float(cr),
            "avg_steps_to_first_catch": None if np.isnan(avg) else float(avg),
            "caught_episodes": int(c),
            "total_episodes": int(args.episodes),
        }
        avg_str = f"{avg:.2f}" if not np.isnan(avg) else "nan"
        print(f"{cell}: catch_rate={cr:.3f}, avg_steps={avg_str} caught={c}/{args.episodes}")

    # Build verification checks for expected ordering
    cr_rvr = results.get("RvsR", {}).get("catch_rate", float("nan"))
    cr_hvr = results.get("HvsR", {}).get("catch_rate", float("nan"))
    cr_rvh = results.get("RvsH", {}).get("catch_rate", float("nan"))
    cr_hvh = results.get("HvsH", {}).get("catch_rate", float("nan"))
    checks = {
        "HvsR_ge_RvsR": (cr_hvr >= cr_rvr),
        "RvsH_le_RvsR": (cr_rvh <= cr_rvr),
        "HvsH_le_HvsR": (cr_hvh <= cr_hvr),
    }
    verify = {
        "expected_ordering": checks,
        "passed": bool(all(checks.values())),
        "episodes_per_cell": int(args.episodes),
        "seed": int(args.seed),
    }

    payload = {
        "env": "mpe.simple_tag_v3",
        "policy_matrix": {
            "RvsR": "random predators vs random prey",
            "HvsR": "heuristic predators vs random prey",
            "RvsH": "random predators vs heuristic prey",
            "HvsH": "heuristic predators vs heuristic prey",
        },
        "parameters": {
            "episodes": int(args.episodes),
            "seed": int(args.seed),
            "continuous_actions": True,
            "baseline": args.baseline,
        },
        "library_versions": {
            "pettingzoo": pz_ver,
            "gymnasium": gym_ver,
            "mpe2": mpe2_ver,
            "numpy": np.__version__,
        },
        "results": results,
        "verification": verify,
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
    fname = f"simple_tag_v3_matrix_{ts_for_name}_seed{args.seed}_eps{args.episodes}.json"
    fpath = os.path.join(args.outdir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)

    print("Matrix results written:", fpath)

    # Optional hard gates for automation (CI / pre-commit)
    should_fail_on_ordering = not args.no_fail_on_bad_ordering
    if should_fail_on_ordering and not verify["passed"]:
        print("ERROR: Expected ordering checks FAILED:", checks)
        raise SystemExit(2)
    if args.min_hvsr is not None and not np.isnan(cr_hvr):
        if cr_hvr < float(args.min_hvsr):
            print(f"ERROR: HvsR catch_rate {cr_hvr:.3f} is below minimum {args.min_hvsr:.3f}")
            raise SystemExit(3)


if __name__ == "__main__":
    main()
