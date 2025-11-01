#!/usr/bin/env python3
"""
Summarize HFO PREY runs for a UTC date or explicit run path.

Outputs per-run, per-lane metrics and presence of per-phase LLM notes, plus quorum/digest.

Examples:
  # Summarize all runs for today's UTC date
  python3 scripts/crew_ai/summarize_runs.py --date $(date -u +%F)

  # Summarize a specific run
  python3 scripts/crew_ai/summarize_runs.py --run hfo_crew_ai_swarm_results/2025-11-01/run-1762005847874

  # JSON output
  python3 scripts/crew_ai/summarize_runs.py --date 2025-11-01 --json-out temp/otel/summary_2025-11-01.json
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

THIS = Path(__file__).resolve()
ROOT = THIS.parents[2]
RESULTS = ROOT / "hfo_crew_ai_swarm_results"


def _read_yaml(p: Path) -> Dict[str, Any]:
    try:
        with p.open("r", encoding="utf-8") as f:
            d = yaml.safe_load(f) or {}
            return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _summarize_run(run_dir: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {"run": str(run_dir.relative_to(ROOT)), "lanes": []}
    digest = run_dir / "swarmlord_digest.md"
    quorum = run_dir / "quorum_report.yml"
    if digest.exists():
        # light probe for PASS
        txt = digest.read_text(encoding="utf-8", errors="ignore")
        out["digest_present"] = True
        out["digest_pass"] = ("Verify PASS: True" in txt)
    else:
        out["digest_present"] = False
        out["digest_pass"] = None
    qr = _read_yaml(quorum) if quorum.exists() else {}
    if qr:
        out["quorum"] = {
            "threshold": qr.get("threshold"),
            "votes": qr.get("votes"),
        }
    # lanes = immediate subdirs with attempt_1
    for lane_dir in sorted([d for d in run_dir.iterdir() if d.is_dir()]):
        a1 = lane_dir / "attempt_1"
        if not a1.exists():
            continue
        er = a1 / "engage_report.yml"
        met = _read_yaml(er)
        metrics = met.get("metrics_summary") or {}
        notes = {
            "perceive": (a1 / "perceive_llm_note.md").exists(),
            "react": (a1 / "react_llm_note.md").exists(),
            "yield": (a1 / "yield_llm_note.md").exists(),
        }
        out["lanes"].append(
            {
                "lane": lane_dir.name,
                "engage_report": str(er.relative_to(ROOT)) if er.exists() else None,
                "metrics": {
                    "total": metrics.get("total"),
                    "correct": metrics.get("correct"),
                    "accuracy": metrics.get("accuracy"),
                    "format_fails": metrics.get("format_fails"),
                    "empty_content": metrics.get("empty_content"),
                    "total_tokens": metrics.get("total_tokens"),
                },
                "notes_present": notes,
            }
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Summarize HFO PREY runs")
    ap.add_argument("--date", help="UTC date YYYY-MM-DD to scan under hfo_crew_ai_swarm_results/")
    ap.add_argument("--run", help="Explicit run directory path")
    ap.add_argument("--json-out", help="Optional JSON output path")
    args = ap.parse_args()

    results: List[Dict[str, Any]] = []

    if args.run:
        rd = Path(args.run)
        if rd.is_dir():
            results.append(_summarize_run(rd))
    elif args.date:
        day = RESULTS / args.date
        if day.is_dir():
            for rd in sorted(day.glob("run-*")):
                results.append(_summarize_run(rd))
    else:
        # Default to today's UTC date folder if present
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day = RESULTS / today
        if day.is_dir():
            for rd in sorted(day.glob("run-*")):
                results.append(_summarize_run(rd))

    if args.json_out:
        outp = Path(args.json_out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Wrote: {outp}")
    else:
        # Pretty print
        for r in results:
            print(f"RUN: {r['run']}")
            print(f"  digest_present: {r.get('digest_present')} pass: {r.get('digest_pass')}")
            if "quorum" in r:
                q = r["quorum"] or {}
                print(f"  quorum threshold: {q.get('threshold')} votes: {len(q.get('votes') or [])}")
            for lane in r.get("lanes", []):
                m = lane.get("metrics") or {}
                n = lane.get("notes_present") or {}
                print(f"  lane: {lane.get('lane')} total={m.get('total')} correct={m.get('correct')} accuracy={m.get('accuracy')} empty={m.get('empty_content')} fmtfail={m.get('format_fails')} tokens={m.get('total_tokens')} notes(p/r/y)={n.get('perceive')}/{n.get('react')}/{n.get('yield')}")
            print()


if __name__ == "__main__":
    main()
