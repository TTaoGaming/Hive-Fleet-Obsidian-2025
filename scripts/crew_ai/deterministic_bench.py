#!/usr/bin/env python3
"""
Deterministic parallelism benchmark that simulates per-lane work without any LLM calls.
It writes OTEL-like spans compatible with analyze_traces.py by emitting
"{lane}:engage_llm" spans so the existing analyzer can detect overlap.

Usage:
  python scripts/crew_ai/deterministic_bench.py --lanes 10 --work-ms 800

Args:
  --lanes: number of parallel lanes to simulate
  --work-ms: approximate CPU-bound work duration per lane in milliseconds
  --jitter-ms: add +/- jitter to work duration to avoid perfect alignment

Outputs:
  - temp/otel/trace-dbench-<ts>.jsonl: spans with start/end per lane
  - Prints a short summary and hints to run the analyzer
"""
from __future__ import annotations
import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parents[2]
OTEL_DIR = ROOT / "temp/otel"
ISO = "%Y-%m-%dT%H:%M:%SZ"


def now_z() -> str:
    return datetime.now(timezone.utc).strftime(ISO)


def write_span(trace_id: str, span: Dict) -> None:
    OTEL_DIR.mkdir(parents=True, exist_ok=True)
    out = OTEL_DIR / f"{trace_id}.jsonl"
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(span, ensure_ascii=False) + "\n")


@dataclass
class BenchCfg:
    lanes: int
    work_ms: int
    jitter_ms: int


def cpu_burn(ms: int) -> None:
    # Busy loop for ms; do some math to avoid being optimized away.
    end = time.perf_counter() + (ms / 1000.0)
    x = 0.0
    while time.perf_counter() < end:
        x = x * 1.000001 + 3.14159  # harmless floating ops
    # Return a value to keep branch alive (not used)
    if x < -1:  # pragma: no cover - impossible branch
        print("never")


def lane_job(lane_name: str, trace_id: str, cfg: BenchCfg) -> Dict[str, str]:
    # Optional jitter
    jitter = int((cfg.jitter_ms or 0) * (0.5 - (hash(lane_name) % 100) / 100.0))
    work_ms = max(1, cfg.work_ms + jitter)

    start_ts = now_z()
    # Emit a start span with engage_llm name to be analyzer-compatible
    span_id = f"{lane_name}-engage-llm-{int(time.time()*1000)}"
    # Start span entry (we'll write full record after work with updated end_time)
    # Do the work
    cpu_burn(work_ms)
    end_ts = now_z()

    write_span(
        trace_id,
        {
            "trace_id": trace_id,
            "span_id": span_id,
            "name": f"{lane_name}:engage_llm",
            "start_time": start_ts,
            "end_time": end_ts,
            "attributes": {
                "lane": lane_name,
                "mission_id": "dbench",
                "ok": True,
                "model": None,
                "latency_ms": work_ms,
            },
        },
    )
    return {"lane": lane_name, "start": start_ts, "end": end_ts}


def main() -> None:
    ap = argparse.ArgumentParser(description="Deterministic parallelism benchmark (no LLM)")
    ap.add_argument("--lanes", type=int, default=4, help="Number of parallel lanes")
    ap.add_argument("--work-ms", type=int, default=800, help="Work per lane in milliseconds")
    ap.add_argument("--jitter-ms", type=int, default=120, help="Jitter (+/-) to desync lanes")
    args = ap.parse_args()

    cfg = BenchCfg(lanes=max(1, args.lanes), work_ms=max(10, args.work_ms), jitter_ms=max(0, args.jitter_ms))
    trace_id = f"trace-dbench-{int(time.time()*1000)}"

    results: List[Dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=cfg.lanes) as ex:
        futs = {ex.submit(lane_job, f"lane_{i+1}", trace_id, cfg): i for i in range(cfg.lanes)}
        for fut in as_completed(futs):
            results.append(fut.result())

    print(f"Deterministic bench complete: lanes={cfg.lanes}, work_ms≈{cfg.work_ms} (±{cfg.jitter_ms})")
    print(f"Trace written: temp/otel/{trace_id}.jsonl")
    print("Next: analyze it")
    print("  python scripts/crew_ai/analyze_traces.py temp/otel")


if __name__ == "__main__":
    main()
