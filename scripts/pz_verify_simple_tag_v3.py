#!/usr/bin/env python3
"""
PettingZoo MPE simple_tag_v3 verification: random-vs-random for N episodes.
Outputs:
- catch_rate: fraction of episodes where at least one tag event occurred
- avg_steps_to_first_catch: average number of parallel steps until first tag (only over episodes with a catch)

Usage (optional):
  python scripts/pz_verify_simple_tag_v3.py --episodes 100 --seed 42
"""
from __future__ import annotations

import argparse
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

    print("simple_tag_v3 random-vs-random results")
    print(f"episodes: {total_eps}")
    print(f"catch_rate: {catch_rate:.3f}  (episodes with >=1 tag)")
    if steps_to_first_catch:
        print(f"avg_steps_to_first_catch: {avg_steps:.2f}  (over {len(steps_to_first_catch)} caught episodes)")
    else:
        print("avg_steps_to_first_catch: n/a (no catches)")


if __name__ == "__main__":
    main()
