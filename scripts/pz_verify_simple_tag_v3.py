#!/usr/bin/env python3
"""
PettingZoo MPE simple_tag_v3 verification: random-vs-random for N episodes.
Outputs printed to stdout and saved as JSON in hfo_petting_zoo_results/ by default.

Metrics:
- catch_rate: fraction of episodes where at least one tag event occurred
- avg_steps_to_first_catch: average number of parallel steps until first tag (only over episodes with a catch)

Usage (optional):
    python scripts/pz_verify_simple_tag_v3.py --episodes 100 --seed 42 \
            --outdir hfo_petting_zoo_results
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
import random
from typing import Dict, Optional

import numpy as np
# Prefer mpe2 if available (PettingZoo MPE has been migrated). Fallback to legacy path.
try:
    from mpe2 import simple_tag_v3  # type: ignore
except Exception:
    from pettingzoo.mpe import simple_tag_v3  # type: ignore


def detect_tag_event(rewards: Dict[str, float], infos: Dict[str, dict], adversary_keys: set[str]) -> bool:
    """Heuristic to detect a tag event in simple_tag_v3.

    Preference order:
    1) If info contains an explicit contact/is_caught flag for any agent
    2) Else, if any adversary received a positive reward this step
    """
    # Check common info flags first
    for k, info in infos.items():
        if not isinstance(info, dict):
            continue
        # Possible keys seen across versions
        if info.get("contact") or info.get("is_caught") or info.get("tagged"):
            return True
    # Fallback to reward-based heuristic for adversaries
    for k in adversary_keys:
        if rewards.get(k, 0.0) > 0.0:
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=100, help="Number of episodes to run")
    parser.add_argument("--seed", type=int, default=42, help="Base RNG seed")
    parser.add_argument(
        "--outdir",
        type=str,
        default="hfo_petting_zoo_results",
        help="Directory to write JSON results (created if missing)",
    )
    args = parser.parse_args()

    # Seed Python & NumPy
    random.seed(args.seed)
    np.random.seed(args.seed)

    # Parallel env is simpler for random policies and step counting
    env = simple_tag_v3.parallel_env(render_mode=None)

    total_eps = args.episodes
    catches = 0
    steps_to_first_catch: list[int] = []

    # Precompute adversary ids (naming varies but includes 'adversary' in simple_tag)
    env.reset(seed=args.seed)
    adversary_keys = {a for a in env.agents if ("adversary" in a) or ("pursuer" in a) or ("tagger" in a)}

    for ep in range(total_eps):
        # Diverse seeds per episode for better coverage
        ep_seed = args.seed + ep
        obs, infos = env.reset(seed=ep_seed, options=None)

        done = False
        step = 0
        caught_in_ep = False
        first_catch_step: Optional[int] = None

        while True:
            # Random action for every live agent
            actions = {a: env.action_space(a).sample() for a in env.agents}

            obs, rewards, terminations, truncations, infos = env.step(actions)
            step += 1

            # Detect a tag event
            if not caught_in_ep and detect_tag_event(rewards, infos, adversary_keys):
                caught_in_ep = True
                first_catch_step = step

            # Parallel episode ends when all agents are terminated or truncated
            if all(terminations.values()) or all(truncations.values()):
                break

        if caught_in_ep and first_catch_step is not None:
            catches += 1
            steps_to_first_catch.append(first_catch_step)

    catch_rate = catches / float(total_eps)
    avg_steps = float(np.mean(steps_to_first_catch)) if steps_to_first_catch else float("nan")

    # Compose metadata and results for JSON
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

    results = {
        "env": "mpe.simple_tag_v3",
        "policy": "random_vs_random",
        "parameters": {
            "episodes": int(total_eps),
            "seed": int(args.seed),
            "render_mode": None,
        },
        "library_versions": {
            "pettingzoo": pz_ver,
            "gymnasium": gym_ver,
            "mpe2": mpe2_ver,
            "numpy": np.__version__,
        },
        "results": {
            "catch_rate": float(catch_rate),
            "caught_episodes": int(catches),
            "total_episodes": int(total_eps),
            "avg_steps_to_first_catch": None if np.isnan(avg_steps) else float(avg_steps),
        },
        "timestamps": {
            "run_start_iso": run_end.isoformat(),  # simple single timestamp if start not tracked separately
            "run_end_iso": run_end.isoformat(),
        },
        "host": {
            "python": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            "platform": os.uname().sysname if hasattr(os, "uname") else "unknown",
        },
    }

    # Ensure outdir exists and write JSON file
    os.makedirs(args.outdir, exist_ok=True)
    ts_for_name = run_end.strftime("%Y%m%dT%H%M%SZ")
    fname = f"simple_tag_v3_random-vs-random_{ts_for_name}_seed{args.seed}_eps{total_eps}.json"
    fpath = os.path.join(args.outdir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, sort_keys=True)

    # Also print human-readable summary and file path
    print("simple_tag_v3 random-vs-random results")
    print(f"episodes: {total_eps}")
    print(f"catch_rate: {catch_rate:.3f}  (episodes with >=1 tag)")
    if steps_to_first_catch:
        print(f"avg_steps_to_first_catch: {avg_steps:.2f}  (over {len(steps_to_first_catch)} caught episodes)")
    else:
        print("avg_steps_to_first_catch: n/a (no catches)")
    print(f"JSON saved: {fpath}")


if __name__ == "__main__":
    main()
