#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from typing import Dict

import numpy as np

from hfo_petting_zoo_mas.policy_base import RandomPolicy
from hfo_petting_zoo_mas.heuristics import HeuristicChasePolicy, PreyFleePolicy
from hfo_petting_zoo_mas.simple_tag_runner import run_episodes


CELLS = ("RvsR", "HvsR", "RvsH", "HvsH")


def run_cell(cell: str, episodes: int, seed: int) -> Dict[str, float | int | None]:
    if cell == "RvsR":
        preds = [RandomPolicy(), RandomPolicy(), RandomPolicy()]
        prey = RandomPolicy()
    elif cell == "HvsR":
        preds = [HeuristicChasePolicy(), HeuristicChasePolicy(), HeuristicChasePolicy()]
        prey = RandomPolicy()
    elif cell == "RvsH":
        preds = [RandomPolicy(), RandomPolicy(), RandomPolicy()]
        prey = PreyFleePolicy()
    elif cell == "HvsH":
        preds = [HeuristicChasePolicy(), HeuristicChasePolicy(), HeuristicChasePolicy()]
        prey = PreyFleePolicy()
    else:
        raise ValueError(f"unknown cell {cell}")

    res = run_episodes(
        episodes=episodes,
        seed=seed,
        predator_policies=preds,
        prey_policies=prey,
        continuous_actions=True,
        coordinator=None,
    )

    return {
        "catch_rate": float(res["catch_rate"]),
        "avg_steps_to_first_catch": res["avg_steps_to_first_catch"],
        "caught_episodes": int(res["caught_episodes"]),
        "total_episodes": int(res["episodes"]),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--outdir", type=str, default="hfo_petting_zoo_results")
    args = ap.parse_args()

    t_end = datetime.now(timezone.utc)

    results = {}
    for cell in CELLS:
        r = run_cell(cell, args.episodes, args.seed)
        avg = r["avg_steps_to_first_catch"]
        avg_str = f"{avg:.2f}" if isinstance(avg, (int, float)) and not np.isnan(avg) else "nan"
        print(f"{cell}: catch_rate={r['catch_rate']:.3f}, avg_steps={avg_str} caught={r['caught_episodes']}/{r['total_episodes']}")
        results[cell] = r

    cr_rvr = results.get("RvsR", {}).get("catch_rate", float("nan"))
    cr_hvr = results.get("HvsR", {}).get("catch_rate", float("nan"))
    cr_rvh = results.get("RvsH", {}).get("catch_rate", float("nan"))

    checks = {
        "HvsR_ge_RvsR": bool(cr_hvr >= cr_rvr),
        "RvsH_le_RvsR": bool(cr_rvh <= cr_rvr),
    }

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
        },
        "library_versions": {
            "pettingzoo": pz_ver,
            "gymnasium": gym_ver,
            "numpy": np.__version__,
        },
        "results": results,
        "verification": {
            "expected_ordering": checks,
            "passed": bool(all(checks.values())),
            "episodes_per_cell": int(args.episodes),
            "seed": int(args.seed),
        },
        "timestamps": {
            "run_end_iso": t_end.isoformat(),
        },
        "host": {
            "python": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            "platform": os.uname().sysname if hasattr(os, "uname") else "unknown",
        },
    }

    os.makedirs(args.outdir, exist_ok=True)
    ts = t_end.strftime("%Y%m%dT%H%M%SZ")
    fname = f"simple_tag_v3_matrix_{ts}_seed{args.seed}_eps{args.episodes}.json"
    fpath = os.path.join(args.outdir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)

    print("Matrix results written:", fpath)


if __name__ == "__main__":
    main()
