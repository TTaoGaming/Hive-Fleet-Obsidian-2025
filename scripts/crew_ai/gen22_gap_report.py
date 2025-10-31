#!/usr/bin/env python3
"""
Gen22 Gap Report — Check a PREY run directory against the Gen22 SSOT contracts

What this does (read-only):
- Finds a run directory (or use --run-dir) under hfo_crew_ai_swarm_results/YYYY-MM-DD/run-<ts>/
- Inspects lane artifacts and run-level files for Gen22-required traceability and artifacts
- Prints a concise human-readable report with PASS/FAIL per check and concrete gaps

Scope: non-destructive, no network calls, fast. Uses PyYAML only.

Checks (aligning to Gen22 SSOT):
1) Traceability fields on all lane artifacts: trace_id, parent_refs, evidence_hashes, context_notes (>=3 lines)
2) Lane artifact content: required presence per file (perception/react/engage/yield)
3) Engage has booleans: tests_green, tripwires_passed, evidence_refs_present
4) Yield evidence_refs includes the other three artifacts
5) Run-level quorum_report.yml exists with validators, threshold, votes
6) Digest includes a validation checklist flags line (parser-safe scan)

Note: This reports gaps only — it does not fail with a non-zero exit unless --strict is used.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = ROOT / "hfo_crew_ai_swarm_results"


def _find_latest_run_dir() -> Path | None:
    if not RESULTS_ROOT.exists():
        return None
    candidates: List[tuple[float, Path]] = []
    for day in sorted(RESULTS_ROOT.glob("*/")):
        for run in day.glob("run-*/"):
            try:
                mt = (run / "swarmlord_digest.md").stat().st_mtime if (run / "swarmlord_digest.md").exists() else run.stat().st_mtime
                candidates.append((mt, run))
            except Exception:
                continue
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _read_yaml(p: Path) -> Dict[str, Any]:
    try:
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _has_min_context_notes(obj: Dict[str, Any]) -> bool:
    notes = obj.get("context_notes")
    if isinstance(notes, str):
        # multi-line string acceptable
        return len([ln for ln in notes.splitlines() if ln.strip()]) >= 3
    if isinstance(notes, list):
        return len([ln for ln in notes if isinstance(ln, str) and ln.strip()]) >= 3
    return False


def check_lane_dir(lane_dir: Path) -> List[str]:
    gaps: List[str] = []
    # Required files
    req_files = [
        "perception_snapshot.yml",
        "react_plan.yml",
        "engage_report.yml",
        "yield_summary.yml",
    ]
    present = {n: (lane_dir / n) for n in req_files if (lane_dir / n).exists()}
    for n in req_files:
        if n not in present:
            gaps.append(f"missing_file:{lane_dir.name}/{n}")

    # Traceability checks per file
    for n, p in present.items():
        obj = _read_yaml(p)
        # 1) trace_id
        if not isinstance(obj.get("trace_id"), str) or not obj.get("trace_id"):  # perception may pass in pilot; Gen22 requires all
            gaps.append(f"traceability_missing:{lane_dir.name}/{n}:trace_id")
        # 2) parent_refs
        pr = obj.get("parent_refs")
        if not (isinstance(pr, list) and pr):
            gaps.append(f"traceability_missing:{lane_dir.name}/{n}:parent_refs")
        # 3) evidence_hashes
        eh = obj.get("evidence_hashes")
        if not (isinstance(eh, list) and eh):
            gaps.append(f"traceability_missing:{lane_dir.name}/{n}:evidence_hashes")
        # 4) context_notes (>=3 lines)
        if not _has_min_context_notes(obj):
            gaps.append(f"traceability_missing:{lane_dir.name}/{n}:context_notes>=3")

    # Engage booleans
    er = _read_yaml(lane_dir / "engage_report.yml")
    for key in ("tests_green", "tripwires_passed", "evidence_refs_present"):
        if key not in er:
            gaps.append(f"engage_report_missing:{lane_dir.name}/engage_report.yml:{key}")

    # Yield evidence completeness
    ys = _read_yaml(lane_dir / "yield_summary.yml")
    e_refs = ys.get("evidence_refs") or []
    core = {"perception_snapshot.yml", "react_plan.yml", "engage_report.yml"}
    for k in core:
        if not any(k in str(x) for x in e_refs):
            gaps.append(f"yield_evidence_missing:{lane_dir.name}/yield_summary.yml->{k}")

    return gaps


def check_run_level(run_dir: Path) -> List[str]:
    gaps: List[str] = []
    # quorum_report.yml must exist with validators, threshold, votes
    qr = run_dir / "quorum_report.yml"
    if not qr.exists():
        gaps.append("missing_run_artifact:quorum_report.yml")
    else:
        obj = _read_yaml(qr)
        if not isinstance(obj.get("validators"), list) or not obj.get("validators"):
            gaps.append("quorum_report_missing:validators")
        if not isinstance(obj.get("threshold"), int):
            gaps.append("quorum_report_missing:threshold")
        votes = obj.get("votes")
        if not (isinstance(votes, list) and votes):
            gaps.append("quorum_report_missing:votes")

    # digest checklist
    digest = run_dir / "swarmlord_digest.md"
    if not digest.exists():
        gaps.append("missing_run_artifact:swarmlord_digest.md")
    else:
        try:
            t = digest.read_text(encoding="utf-8")
        except Exception:
            t = ""
        if "Validation checklist" not in t and "checklist" not in t.lower():
            gaps.append("digest_missing:validation_checklist")
    return gaps


def main() -> int:
    ap = argparse.ArgumentParser(description="Gen22 gap report for a PREY run")
    ap.add_argument("--run-dir", type=str, default="", help="Path to run-<ts> directory; defaults to latest")
    ap.add_argument("--strict", action="store_true", help="Exit non-zero when gaps are found")
    args = ap.parse_args()

    run_dir = Path(args.run_dir).resolve() if args.run_dir else _find_latest_run_dir()
    if not run_dir or not run_dir.exists():
        print("No run directory found under hfo_crew_ai_swarm_results.")
        return 0

    print(f"Gen22 gap report for: {run_dir}")
    lane_roots = [p for p in run_dir.iterdir() if p.is_dir() and (p / "attempt_1").exists()]
    all_gaps: List[str] = []
    for lane_root in sorted(lane_roots):
        lane_dir = lane_root / "attempt_1"
        gaps = check_lane_dir(lane_dir)
        if gaps:
            print(f"- Lane {lane_root.name}: {len(gaps)} gap(s)")
            for g in gaps:
                print(f"  • {g}")
        else:
            print(f"- Lane {lane_root.name}: PASS (traceability + content)")
        all_gaps.extend(gaps)

    run_gaps = check_run_level(run_dir)
    if run_gaps:
        print(f"- Run-level: {len(run_gaps)} gap(s)")
        for g in run_gaps:
            print(f"  • {g}")
    else:
        print("- Run-level: PASS (quorum_report + digest checklist)")
    all_gaps.extend(run_gaps)

    if not all_gaps:
        print("\nOverall: PASS — Run appears Gen22-compliant for the checks implemented.")
        return 0
    else:
        print(f"\nOverall: {len(all_gaps)} gap(s) found. See bullets above.")
        return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
