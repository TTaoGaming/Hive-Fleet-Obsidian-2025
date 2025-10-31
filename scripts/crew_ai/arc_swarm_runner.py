#!/usr/bin/env python3
"""
ARC-Challenge swarm runner:
- Runs ARC-Challenge (validation) in parallel across all allowlisted models
- Writes a Swarmlord-style digest summarizing per-model accuracy and latency

Usage:
  python3 scripts/crew_ai/arc_swarm_runner.py --limit 200

Notes:
- Requires OPENROUTER_API_KEY in .env. Uses your llm_client.ALLOWLIST.
- Limit defaults to 200 for cost control; use --limit 0 for full split.
"""
from __future__ import annotations
import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
import re

import importlib.util

ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = ROOT / "hfo_crew_ai_swarm_results"
BLACKBOARD = ROOT / "hfo_blackboard/obsidian_synapse_blackboard.jsonl"


def now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_blackboard(entry: Dict[str, Any]) -> None:
    BLACKBOARD.parent.mkdir(parents=True, exist_ok=True)
    with BLACKBOARD.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# Load sibling modules
THIS = Path(__file__).resolve()
LLM_PATH = THIS.parent / "llm_client.py"
EVAL_PATH = THIS.parent / "arc_challenge_eval.py"
spec_llm = importlib.util.spec_from_file_location("llm_client", str(LLM_PATH))
spec_eval = importlib.util.spec_from_file_location("arc_challenge_eval", str(EVAL_PATH))
if spec_llm is None or spec_llm.loader is None or spec_eval is None or spec_eval.loader is None:
    raise RuntimeError("Unable to load required modules")
import sys as _sys
llm_client = importlib.util.module_from_spec(spec_llm)
_sys.modules[spec_llm.name] = llm_client  # ensure visible during exec
spec_llm.loader.exec_module(llm_client)  # type: ignore[arg-type]
arc_eval = importlib.util.module_from_spec(spec_eval)
_sys.modules[spec_eval.name] = arc_eval  # ensure visible during exec
spec_eval.loader.exec_module(arc_eval)  # type: ignore[arg-type]


def _sanitize_model_env_key(model: str) -> str:
    # OPENROUTER_PRICE_<SANITIZED>_PER_1K
    key = re.sub(r"[^A-Za-z0-9]+", "_", str(model)).upper().strip("_")
    return f"OPENROUTER_PRICE_{key}_PER_1K"


def _price_per_1k(model: str) -> float | None:
    # Env-based pricing; avoids inventing numbers. Use OPENROUTER_PRICE_DEFAULT_PER_1K for fallback.
    specific = os.environ.get(_sanitize_model_env_key(model))
    if specific:
        try:
            return float(specific)
        except Exception:
            pass
    default = os.environ.get("OPENROUTER_PRICE_DEFAULT_PER_1K")
    if default:
        try:
            return float(default)
        except Exception:
            pass
    return None


def run_for_model(model_hint: str, limit: int, split: str, max_tokens: int, temperature: float, timeout_seconds: int, *, lane_index: int = 0, seed_base: int = 1234) -> Dict[str, Any]:
    # Set env to propagate hint (client also accepts direct hint)
    os.environ["OPENROUTER_MODEL_HINT"] = model_hint
    res = arc_eval.run_eval(
        model_hint=model_hint,
        split=split,
        limit=limit,
        offset=limit * lane_index if limit > 0 else 0,
        seed=seed_base + lane_index,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
    )
    acc = (res.correct / res.total) if res.total else 0.0
    price = _price_per_1k(res.model)
    est_cost = None
    if price is not None and res.total_tokens:
        est_cost = (res.total_tokens / 1000.0) * price
    return {
        "model": res.model,
        "limit": limit,
        "total": res.total,
        "correct": res.correct,
        "accuracy": acc,
        "format_fails": res.format_fails,
        "avg_latency_ms": res.avg_latency_ms,
        "empty_content": res.empty_content,
        "total_tokens": res.total_tokens,
        "price_per_1k": price,
        "est_cost": est_cost,
        "lane_index": lane_index,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="ARC-Challenge swarm runner across allowlisted models")
    ap.add_argument("--limit", type=int, default=200, help="Limit items per lane (0 = all; requires --allow-full)")
    ap.add_argument("--lanes-per-model", type=int, default=2, help="Parallel lanes per model")
    ap.add_argument("--split", type=str, default="validation", choices=["train", "validation", "test"])
    ap.add_argument("--max-tokens", type=int, default=12)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--timeout-seconds", type=int, default=25)
    ap.add_argument("--models", type=str, default="", help="Comma-separated substrings to filter allowlisted models (e.g., 'gpt-oss,deepseek')")
    ap.add_argument("--allow-full", action="store_true", help="Explicitly allow full-dataset run when --limit 0 is set")
    args = ap.parse_args()

    load_dotenv(dotenv_path=ROOT / ".env", override=False)
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("No OPENROUTER_API_KEY found. Set it in .env to run the swarm.")
        return

    # Guard: prevent accidental full-dataset runs unless explicitly allowed
    env_allow_full = str(os.environ.get("ALLOW_FULL_ARC", "")).lower() in ("1", "true", "yes", "y")
    if args.limit is None:
        args.limit = 200
    if args.limit <= 0 and not (args.allow_full or env_allow_full):
        print("Guard: --limit 0 (full) requires --allow-full or ALLOW_FULL_ARC=1. For budgeted runs, use --limit 200.")
        _sys.exit(2)
    if args.limit < 0:
        print("Guard: --limit must be >= 0 (0 only with --allow-full).")
        _sys.exit(2)

    allowlist = list(llm_client.ALLOWLIST)
    if args.models.strip():
        filters = [s.strip().lower() for s in args.models.split(",") if s.strip()]
        allowlist = [m for m in allowlist if any(f in m.lower() for f in filters)]
    mission_id = f"arc_challenge_swarm_{int(time.time()*1000)}"

    date_dir = RESULTS_ROOT / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_dir = date_dir / f"run-{int(time.time()*1000)}"
    run_dir.mkdir(parents=True, exist_ok=True)

    append_blackboard({
        "mission_id": mission_id,
        "phase": "perceive",
        "summary": f"ARC swarm start: models={len(allowlist)} split={args.split} limit={args.limit}",
        "evidence_refs": ["dataset:ai2_arc:ARC-Challenge", f"split:{args.split}"],
        "safety_envelope": {"bounded_tokens": args.max_tokens, "temperature": args.temperature},
        "blocked_capabilities": [],
        "timestamp": now_z(),
    })

    results: List[Dict[str, Any]] = []
    lanes = []
    for m in allowlist:
        for ln in range(max(1, args.lanes_per_model)):
            lanes.append((m, ln))

    with ThreadPoolExecutor(max_workers=len(lanes)) as ex:
        futs = {
            ex.submit(
                run_for_model,
                m,
                args.limit,
                args.split,
                args.max_tokens,
                args.temperature,
                args.timeout_seconds,
                lane_index=ln,
            ): (m, ln)
            for (m, ln) in lanes
        }
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            append_blackboard({
                "mission_id": mission_id,
                "phase": "engage",
                "summary": f"Lane done: {r['model']} lane={r['lane_index']} acc={r['accuracy']:.3f} limit={r['limit']}",
                "evidence_refs": ["dataset:ai2_arc:ARC-Challenge", f"model:{r['model']}", f"lane:{r['lane_index']}"]
                ,
                "timestamp": now_z(),
            })

    # Sort by accuracy desc, then avg_latency asc
    # Aggregate lanes per model
    agg: Dict[str, Dict[str, Any]] = {}
    for r in results:
        key = r["model"]
        a = agg.setdefault(key, {
            "model": key,
            "total": 0,
            "correct": 0,
            "sum_latency": 0.0,
            "n": 0,
            "format_fails": 0,
            "empty_content": 0,
            "total_tokens": 0,
            "price_per_1k": r.get("price_per_1k"),
        })
        a["total"] += r["total"]
        a["correct"] += r["correct"]
        a["sum_latency"] += float(r["avg_latency_ms"]) if r.get("avg_latency_ms") is not None else 0.0
        a["n"] += 1
        a["format_fails"] += int(r.get("format_fails") or 0)
        a["empty_content"] += int(r.get("empty_content") or 0)
        a["total_tokens"] += int(r.get("total_tokens") or 0)

    results_agg: List[Dict[str, Any]] = []
    for key, a in agg.items():
        acc = (a["correct"] / a["total"]) if a["total"] else 0.0
        avg_lat = (a["sum_latency"] / a["n"]) if a["n"] else 0.0
        price = a.get("price_per_1k")
        est_cost = (a["total_tokens"] / 1000.0) * price if (price is not None and a["total_tokens"]) else None
        results_agg.append({
            "model": key,
            "accuracy": acc,
            "correct": a["correct"],
            "total": a["total"],
            "avg_latency_ms": avg_lat,
            "format_fails": a["format_fails"],
            "empty_content": a["empty_content"],
            "total_tokens": a["total_tokens"],
            "price_per_1k": price,
            "est_cost": est_cost,
            "lanes": a["n"],
        })

    results_sorted = sorted(results_agg, key=lambda x: (-x["accuracy"], x["avg_latency_ms"]))
    best = results_sorted[0] if results_sorted else None

    # Write digest
    lines = []
    lines.append(f"# Swarmlord Digest — {mission_id}")
    lines.append("")
    lines.append(f"- Dataset: ai2_arc / ARC-Challenge [{args.split}] limit={args.limit or 'ALL'}")
    lines.append(f"- Models: {len(results_sorted)}")
    if best:
        lines.append(f"- Best: {best['model']} — acc={best['accuracy']:.2%}, avg_latency={best['avg_latency_ms']:.0f} ms")
    lines.append("")
    lines.append("## Results (aggregated across lanes)")
    lines.append("| Rank | Model | Accuracy | Correct/Total | Avg latency (ms) | Format fails | Empty content | Tokens | Price/1K | Est. cost |")
    lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for i, r in enumerate(results_sorted, 1):
        price_str = f"{r['price_per_1k']:.4f}" if r.get("price_per_1k") is not None else "n/a"
        cost_str = f"${r['est_cost']:.4f}" if r.get("est_cost") is not None else "n/a"
        lines.append(
            f"| {i} | {r['model']} | {r['accuracy']:.2%} | {r['correct']}/{r['total']} | {r['avg_latency_ms']:.0f} | {r['format_fails']} | {r['empty_content']} | {r['total_tokens']} | {price_str} | {cost_str} |"
        )
    md_path = run_dir / "swarmlord_digest.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")

    # Combined JSON
    json_path = run_dir / "arc_swarm_results.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump({
            "mission_id": mission_id,
            "split": args.split,
            "limit": args.limit,
            "lanes_per_model": args.lanes_per_model,
            "per_lane_results": results,
            "aggregated_results": results_sorted,
        }, f, indent=2)

    append_blackboard({
        "mission_id": mission_id,
        "phase": "yield",
        "summary": f"ARC swarm digest ready; best={best['model'] if best else 'n/a'}",
        "evidence_refs": [str(md_path.relative_to(ROOT)), str(json_path.relative_to(ROOT))],
        "timestamp": now_z(),
    })

    print(f"Wrote: {md_path}")
    print(f"Wrote: {json_path}")


if __name__ == "__main__":
    main()
