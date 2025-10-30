#!/usr/bin/env python3
"""
Analyze OTEL-like JSONL traces written by the Crew AI pilot and report whether
lanes ran in parallel (i.e., overlapping time windows) or sequentially.

Usage:
  python scripts/crew_ai/analyze_traces.py [trace_file_or_dir]
If a directory is passed, analyzes the most recent trace-*.jsonl file.

Outputs a concise report to stdout and exits 0 on success.
"""
from __future__ import annotations
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple

ISO = "%Y-%m-%dT%H:%M:%SZ"


def parse_time(ts: str) -> datetime:
    return datetime.strptime(ts, ISO).replace(tzinfo=timezone.utc)


def load_spans(path: Path) -> List[Dict]:
    spans: List[Dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                spans.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return spans


def pick_latest_trace_file(d: Path) -> Path:
    files = sorted(d.glob("trace-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print(f"No trace files in {d}")
        sys.exit(1)
    return files[0]


def summarize_overlap(spans: List[Dict]) -> Dict:
    # Build lane windows using engage_llm spans if present (longest), else react:bridger spans
    lane_windows: Dict[str, Tuple[datetime, datetime]] = {}
    for s in spans:
        name: str = s.get("name", "")
        attrs = s.get("attributes", {}) or {}
        lane = attrs.get("lane")
        if not lane:
            continue
        # Prefer the LLM engage span as it has real duration
        if name.endswith(":engage_llm") or ":engage_llm" in name:
            start = parse_time(s["start_time"])  # type: ignore[index]
            end = parse_time(s["end_time"])      # type: ignore[index]
            lane_windows[lane] = (start, end)
        elif name.endswith(":react:bridger"):
            # Only set if no engage_llm span was recorded for that lane
            if lane not in lane_windows:
                start = parse_time(s["start_time"])  # type: ignore[index]
                end = parse_time(s["end_time"])      # type: ignore[index]
                lane_windows[lane] = (start, end)

    lanes = sorted(lane_windows.keys())
    overlaps: Dict[str, Dict[str, float]] = {l: {} for l in lanes}
    for i, a in enumerate(lanes):
        for b in lanes[i+1:]:
            a_s, a_e = lane_windows[a]
            b_s, b_e = lane_windows[b]
            latest_start = max(a_s, b_s)
            earliest_end = min(a_e, b_e)
            overlap = (earliest_end - latest_start).total_seconds()
            # Clamp negatives to zero for readability
            if overlap < 0:
                overlap = 0.0
            overlaps[a][b] = overlap
            overlaps[b][a] = overlap

    parallel = any(v > 0 for m in overlaps.values() for v in m.values())
    return {
        "lane_windows": {k: (lane_windows[k][0].strftime(ISO), lane_windows[k][1].strftime(ISO)) for k in lanes},
        "overlaps_seconds": overlaps,
        "parallel": parallel,
    }


def main() -> None:
    arg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("temp/otel")
    trace_file = arg
    if arg.is_dir():
        trace_file = pick_latest_trace_file(arg)
    spans = load_spans(trace_file)
    report = summarize_overlap(spans)

    print("Trace:", trace_file)
    print("Lane windows:")
    for lane, (s, e) in report["lane_windows"].items():
        print(f"  - {lane}: {s} → {e}")
    print("Overlaps (seconds):")
    lanes = sorted(report["lane_windows"].keys())
    for a in lanes:
        row = [f"{report['overlaps_seconds'].get(a, {}).get(b, 0):.2f}" for b in lanes]
        print(f"  {a}: [" + ", ".join(row) + "]")
    print("Parallel detected:", report["parallel"])


if __name__ == "__main__":
    main()
