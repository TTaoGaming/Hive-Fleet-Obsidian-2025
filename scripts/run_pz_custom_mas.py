#!/usr/bin/env python3
from __future__ import annotations

import argparse
from typing import List

from hfo_petting_zoo_mas.policy_base import RandomPolicy, FnPolicy
from hfo_petting_zoo_mas.heuristics import HeuristicChasePolicy
from hfo_petting_zoo_mas.controllers import Coordinator
from hfo_petting_zoo_mas.simple_tag_runner import run_episodes


def parse_args():
    p = argparse.ArgumentParser(description="Run PettingZoo simple_tag_v3 with custom MAS hooks.")
    p.add_argument("--episodes", type=int, default=5)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--continuous", action="store_true", help="Use continuous actions (default)")
    p.add_argument("--discrete", action="store_true", help="Use discrete actions")
    p.add_argument("--pred-policies", type=str, default="random",
                   help="Comma-separated list of predator policies. Only 'random' is built-in; you can extend via code.")
    p.add_argument("--prey-policy", type=str, default="random",
                   help="Single prey policy name (default: random)")
    return p.parse_args()


def build_policy_list(spec: str) -> List[RandomPolicy]:
    # Built-ins: random, heuristic_chase
    names = [s.strip() for s in spec.split(',') if s.strip()]
    out = []
    for name in names:
        if name == 'random':
            out.append(RandomPolicy())
        elif name in ('heuristic', 'heuristic_chase', 'chase'):
            out.append(HeuristicChasePolicy())
        else:
            raise ValueError(f"Unknown policy name: {name}")
    return out


class PrintCoordinator(Coordinator):
    # Example: you can override hooks to coordinate predators
    def before_episode(self, episode, shared):
        shared["formation"] = "none"  # user-extensible


def main():
    args = parse_args()
    continuous = True
    if args.discrete:
        continuous = False
    if args.continuous:
        continuous = True

    pred_policies = build_policy_list(args.pred_policies)
    prey_policy = build_policy_list(args.prey_policy)[0]

    res = run_episodes(
        episodes=args.episodes,
        seed=args.seed,
        predator_policies=pred_policies,
        prey_policies=prey_policy,
        continuous_actions=continuous,
        coordinator=PrintCoordinator(),
    )

    print("Episodes:", res["episodes"])
    print("Seed:", res["seed"])
    print("Caught:", f"{res['caught_episodes']}/{res['episodes']}")
    print("Catch rate:", f"{res['catch_rate']:.3f}")
    print("Avg steps to first catch:", res["avg_steps_to_first_catch"])  # may be None if no catches


if __name__ == "__main__":
    main()
