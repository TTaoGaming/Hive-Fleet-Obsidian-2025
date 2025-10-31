#!/usr/bin/env python3
"""
OSS transport/format diagnostics for GPT-OSS family.

Probes models with/without response_format, measures empty content rate,
HTTP statuses, and latency. Writes a compact summary.

Usage:
  # default: probe 'openai/gpt-oss-20b' and 'openai/gpt-oss-120b'
  python3 scripts/crew_ai/oss_transport_diag.py --per-model 20

  # set diag log directory for raw events
  OPENROUTER_DIAG_DIR=temp/llm_diag \
    python3 scripts/crew_ai/oss_transport_diag.py --per-model 20
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

import importlib.util

THIS = Path(__file__).resolve()
LLM_PATH = THIS.parent / "llm_client.py"
spec = importlib.util.spec_from_file_location("llm_client", str(LLM_PATH))
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load llm_client module")
llm_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(llm_client)  # type: ignore[arg-type]


def probe(model_hint: str, use_format: bool, n: int) -> Dict[str, Any]:
    ok = 0
    empty = 0
    http_fail = 0
    latencies: List[int] = []
    for i in range(n):
        r = llm_client.call_openrouter(
            "Answer with the letter A only.",
            model_hint=model_hint,
            max_tokens=4,
            temperature=0.0,
            timeout_seconds=20,
            response_format_type=("text" if use_format else None),
            system_prompt="Return exactly one letter.",
            retry_on_empty=True,
            retry_max=1,
            retry_alt_format=True,
        )
        if not r.get("ok"):
            http_fail += 1
        content = r.get("content")
        if content is None or str(content).strip() == "":
            empty += 1
        else:
            ok += 1
        latencies.append(int(r.get("latency_ms") or 0))
    avg_lat = (sum(latencies) / len(latencies)) if latencies else 0.0
    return {"ok": ok, "empty": empty, "http_fail": http_fail, "avg_latency_ms": avg_lat}


def main() -> None:
    ap = argparse.ArgumentParser(description="OSS transport diagnostics")
    ap.add_argument("--models", type=str, default="openai/gpt-oss-20b,openai/gpt-oss-120b")
    ap.add_argument("--per-model", type=int, default=20)
    args = ap.parse_args()

    ROOT = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=ROOT / ".env", override=False)
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("No OPENROUTER_API_KEY found. Set it in .env.")
        return

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    lines = []
    lines.append("# OSS Transport Diagnostics")
    lines.append("")
    lines.append(f"per-model probes: {args.per_model}")
    lines.append("")
    lines.append("| Model | with format: empty/http_fail/ok | avg_lat | without format: empty/http_fail/ok | avg_lat |")
    lines.append("|---|---:|---:|---:|---:|")
    for m in models:
        with_fmt = probe(m, True, args.per_model)
        no_fmt = probe(m, False, args.per_model)
        lines.append(
            f"| {m} | {with_fmt['empty']}/{with_fmt['http_fail']}/{with_fmt['ok']} | {with_fmt['avg_latency_ms']:.0f} | "
            f"{no_fmt['empty']}/{no_fmt['http_fail']}/{no_fmt['ok']} | {no_fmt['avg_latency_ms']:.0f} |"
        )
    out_dir = ROOT / "hfo_crew_ai_swarm_results" / Path.cwd().name if False else ROOT / "hfo_crew_ai_swarm_results"
    date_dir = out_dir / Path(".")
    date_dir = ROOT / "hfo_crew_ai_swarm_results" / os.environ.get("TZ_DATE", "2025-10-30") if False else ROOT / "hfo_crew_ai_swarm_results" / Path(Path().cwd().name)
    # Simplify output path to today's date folder
    from datetime import datetime, timezone
    date_dir = ROOT / "hfo_crew_ai_swarm_results" / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    report_path = date_dir / f"oss_transport_diag_{int(__import__('time').time()*1000)}.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote: {report_path}")


if __name__ == "__main__":
    main()
