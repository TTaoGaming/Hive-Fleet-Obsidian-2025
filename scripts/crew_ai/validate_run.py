#!/usr/bin/env python3
"""
Validate a Crew AI PREY run directory produced by scripts/crew_ai/runner.py.

Checks performed (fast, no network):
- Find the most recent run dir under hfo_crew_ai_swarm_results/YYYY-MM-DD/run-<ts>/
  unless --run-dir is provided.
- Ensure mission_pointer.yml exists and parses.
- For each lane/*/attempt_1: verify the four artifacts exist and contain minimal fields:
  perception_snapshot.yml, react_plan.yml, engage_report.yml, yield_summary.yml.
- Ensure yield_summary.evidence_refs references the three core artifacts.
- Scan artifacts and digest for placeholder strings (TODO/omitted) and fail if found.
- Parse swarmlord_digest.md to find the Trace path and verify it exists.
- Optionally assert parallelism by importing analyze_traces and checking report["parallel"].

Exit 0 on PASS, non-zero on first failure with a concise message.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = REPO_ROOT / "hfo_crew_ai_swarm_results"
SCHEMA_PATH = REPO_ROOT / "scripts/crew_ai/schemas/lane_artifacts.schema.yml"
SCHEMA_MP_PATH = REPO_ROOT / "scripts/crew_ai/schemas/mission_pointer.schema.yml"


def find_latest_run_dir() -> Path | None:
    if not RESULTS_ROOT.exists():
        return None
    # Search all date dirs for run-* folders, pick most recent by mtime
    candidates: List[Tuple[float, Path]] = []
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


def read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}


def _load_required_schema() -> Dict[str, List[Tuple[str, type]]]:
    # Default (hard-coded) minimal schema
    default: Dict[str, List[Tuple[str, type]]] = {
        "perception_snapshot.yml": [
            ("mission_id", str), ("lane", str), ("timestamp", str), ("trace_id", str), ("safety", dict), ("llm", dict), ("paths", dict),
        ],
        "react_plan.yml": [
            ("mission_id", str), ("lane", str), ("timestamp", str), ("cynefin", dict), ("approach", dict),
        ],
        "engage_report.yml": [
            ("mission_id", str), ("lane", str), ("timestamp", str), ("safety", dict), ("llm", dict),
        ],
        "yield_summary.yml": [
            ("mission_id", str), ("lane", str), ("timestamp", str), ("collected_agents", list), ("evidence_refs", list),
        ],
    }
    # If a YAML schema file exists, load and map its simple type names to Python types
    if SCHEMA_PATH.exists():
        raw = read_yaml(SCHEMA_PATH)
        mapped: Dict[str, List[Tuple[str, type]]] = {}
        type_map = {"str": str, "dict": dict, "list": list, "int": int, "float": float, "bool": bool}
        for fname, kv in (raw.items() if isinstance(raw, dict) else []):
            req_list: List[Tuple[str, type]] = []
            if isinstance(kv, dict):
                for key, tname in kv.items():
                    py_t = type_map.get(str(tname).strip().lower())
                    if py_t is not None:
                        req_list.append((key, py_t))
            if req_list:
                mapped[fname] = req_list
        # Only override if mapping succeeded
        if mapped:
            return mapped
    return default


def validate_lane_artifacts(lane_dir: Path) -> None:
    required = _load_required_schema()

    for fname, req in required.items():
        fp = lane_dir / fname
        if not fp.exists():
            raise SystemExit(f"Lane artifact missing: {fp}")
        data = read_yaml(fp)
        for key, typ in req:
            val = data.get(key)
            if val is None or not isinstance(val, typ):
                raise SystemExit(f"Lane artifact missing/typed field: {fp}:{key}")

    # Cross-check evidence_refs include core artifacts
    ys = read_yaml(lane_dir / "yield_summary.yml")
    e_refs = ys.get("evidence_refs") or []
    for core in ("perception_snapshot.yml", "react_plan.yml", "engage_report.yml"):
        if not any(core in str(x) for x in e_refs):
            raise SystemExit(f"Yield evidence_refs missing core ref: {lane_dir}/yield_summary.yml -> {core}")


def _validate_against_simple_schema(obj: Dict[str, Any], schema_dict: Dict[str, str], path_label: str) -> None:
    type_map = {"str": str, "dict": dict, "list": list, "int": int, "float": float, "bool": bool}
    for key, tname in schema_dict.items():
        if key not in obj:
            raise SystemExit(f"Missing field in {path_label}: {key}")
        py_t = type_map.get(str(tname).strip().lower())
        if py_t is None:
            continue
        if not isinstance(obj.get(key), py_t):
            raise SystemExit(f"Type mismatch in {path_label}: {key} expected {py_t.__name__}")


def validate_mission_pointer(mp_path: Path) -> None:
    if not mp_path.exists():
        raise SystemExit(f"mission_pointer.yml missing: {mp_path}")
    mp = read_yaml(mp_path)
    # If schema exists, enforce it
    if SCHEMA_MP_PATH.exists():
        raw = read_yaml(SCHEMA_MP_PATH)
        section = raw.get("mission_pointer.yml") if isinstance(raw, dict) else None
        if isinstance(section, dict) and section:
            _validate_against_simple_schema(mp, section, str(mp_path))
    else:
        # Minimal fallback checks
        for key, typ in (
            ("mission_id", str), ("timestamp", str), ("intent_path", str), ("lanes", dict), ("quorum", dict), ("telemetry", dict),
        ):
            val = mp.get(key)
            if val is None or not isinstance(val, typ):
                raise SystemExit(f"mission_pointer.yml missing/typed field: {mp_path}:{key}")


def scan_placeholders(path: Path) -> None:
    bad_terms = ("TODO", "omitted")
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    for term in bad_terms:
        if term.lower() in text.lower():
            raise SystemExit(f"Placeholder found in {path}: contains '{term}'")


def extract_trace_from_digest(digest_path: Path) -> Path | None:
    try:
        text = digest_path.read_text(encoding="utf-8")
    except Exception:
        return None
    trace_rel: str | None = None
    for line in text.splitlines():
        if line.strip().startswith("- Trace:"):
            # format: - Trace: temp/otel/trace-....jsonl
            parts = line.split(":", 1)
            if len(parts) == 2:
                trace_rel = parts[1].strip()
                break
    if not trace_rel:
        return None
    p = (REPO_ROOT / trace_rel).resolve()
    return p if p.exists() else None


def has_mermaid_block(digest_path: Path) -> bool:
    try:
        t = digest_path.read_text(encoding="utf-8")
    except Exception:
        return False
    return "```mermaid" in t


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a Crew AI PREY run directory")
    ap.add_argument("--run-dir", type=str, default="", help="Path to a specific run-<ts> directory to validate")
    ap.add_argument("--require-parallel", action="store_true", help="If set, fail when analyze_traces reports no parallelism")
    ap.add_argument("--fail-on-missing-run", action="store_true", help="If set, fail when no run dir is found")
    args = ap.parse_args()

    run_dir = Path(args.run_dir).resolve() if args.run_dir else find_latest_run_dir()
    if not run_dir:
        msg = "No PREY run found under hfo_crew_ai_swarm_results"
        if args.fail_on_missing_run:
            raise SystemExit(msg)
        print(msg)
        return 0

    if not run_dir.exists():
        raise SystemExit(f"Run directory not found: {run_dir}")

    # 1) Mission pointer (schema-enforced)
    mp = run_dir / "mission_pointer.yml"
    validate_mission_pointer(mp)

    # 2) Lanes and artifacts
    lane_roots = [p for p in run_dir.iterdir() if p.is_dir() and (p / "attempt_1").exists()]
    if not lane_roots:
        raise SystemExit(f"No lane outputs found in {run_dir}")
    for lane_root in lane_roots:
        lane_dir = lane_root / "attempt_1"
        validate_lane_artifacts(lane_dir)
        # placeholder scan
        for fname in ("perception_snapshot.yml", "react_plan.yml", "engage_report.yml", "yield_summary.yml"):
            scan_placeholders(lane_dir / fname)

    # 3) Digest
    digest = run_dir / "swarmlord_digest.md"
    if not digest.exists():
        raise SystemExit(f"Digest missing: {digest}")
    if not has_mermaid_block(digest):
        raise SystemExit(f"Digest mermaid block missing: {digest}")
    scan_placeholders(digest)

    # 4) Trace path from digest and optional parallelism assertion
    trace_path = extract_trace_from_digest(digest)
    if not trace_path:
        raise SystemExit(f"Trace path not found or missing on disk (from digest): {digest}")
    if args.require_parallel:
        # Import analyzer and compute report
        sys.path.insert(0, str((REPO_ROOT / "scripts/crew_ai").resolve()))
        try:
            import analyze_traces  # type: ignore
        except Exception as e:
            raise SystemExit(f"Failed to import analyze_traces: {e}")
        spans = analyze_traces.load_spans(trace_path)
        report = analyze_traces.summarize_overlap(spans)
        if not report.get("parallel"):
            raise SystemExit("Trace analysis reports no parallelism across lanes")

    print(f"PREY run validation PASS: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
