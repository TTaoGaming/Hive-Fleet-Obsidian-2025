#!/usr/bin/env python3
"""
Param sweep for openai/gpt-oss-120b to characterize conditions that work vs fail.

Dimensions:
- prompts: integer_only | json_answer | bare_number
- response_format: text | none
- max_tokens: 16 | 64
- temperature: 0.0 | 0.2

Each config runs 2 probes: 7+5 and 81-39.

Outputs:
- JSON results under hfo_crew_ai_swarm_results/YYYY-MM-DD/oss_120b_sweep_<ts>.json
- Markdown digest under the same folder.
"""
from __future__ import annotations
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
import importlib.util


def load_llm_client():
    here = Path(__file__).resolve()
    llm_path = here.parent / "llm_client.py"
    spec = importlib.util.spec_from_file_location("llm_client", str(llm_path))
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load llm_client module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[arg-type]
    return mod


def make_prompt(kind: str, a: int, b: int, op: str) -> Tuple[str, int]:
    if op == "+":
        expect = a + b
    else:
        expect = a - b
    if kind == "integer_only":
        return (f"Answer with only the integer result: {a} {op} {b} = ?", expect)
    if kind == "json_answer":
        return (f"Return a JSON object {{\"answer\": <int>}} only. Question: {a} {op} {b}.", expect)
    if kind == "bare_number":
        return (f"Just output the number for {a} {op} {b}.", expect)
    return (f"Answer with only the integer result: {a} {op} {b} = ?", expect)


def parse_int(s: str) -> Tuple[bool, int | None]:
    if s is None:
        return False, None
    t = s.strip()
    # Simple integer parse from start of string
    i = 0
    neg = False
    if i < len(t) and t[i] in "+-":
        neg = t[i] == "-"
        i += 1
    num = ""
    while i < len(t) and t[i].isdigit():
        num += t[i]
        i += 1
    if not num:
        # try json
        try:
            obj = json.loads(t)
            if isinstance(obj, dict) and isinstance(obj.get("answer"), int):
                return True, int(obj["answer"])  # type: ignore[index]
        except Exception:
            pass
        return False, None
    val = int(num)
    return True, -val if neg else val


def run_config(llm_client, prompt_kind: str, resp_fmt: str | None, max_tokens: int, temperature: float) -> Dict[str, Any]:
    q1, e1 = make_prompt(prompt_kind, 7, 5, "+")
    q2, e2 = make_prompt(prompt_kind, 81, 39, "-")
    results: List[Dict[str, Any]] = []
    passes = 0
    for q, exp in [(q1, e1), (q2, e2)]:
        r = llm_client.call_openrouter(
            q,
            model_hint="openai/gpt-oss-120b",
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=20,
            response_format_type=resp_fmt,
        )
        http_ok = bool(r.get("ok") and r.get("status_code") == 200)
        raw = r.get("content") or ""
        ok_parse, val = parse_int(raw)
        ok = bool(http_ok and ok_parse and val == exp)
        if ok:
            passes += 1
        results.append({
            "http_ok": http_ok,
            "status_code": r.get("status_code"),
            "latency_ms": r.get("latency_ms"),
            "raw": raw,
            "parsed_ok": ok_parse,
            "parsed": val,
            "expect": exp,
        })
    status = "ok" if passes == 2 else ("partial" if passes == 1 else "fail")
    return {
        "prompt": prompt_kind,
        "response_format": resp_fmt or "none",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "status": status,
        "passes": passes,
        "probes": results,
    }


def main() -> None:
    load_dotenv()
    os.environ["OPENROUTER_MODEL_HINT"] = "openai/gpt-oss-120b"
    llm_client = load_llm_client()

    prompt_kinds = ["integer_only", "json_answer", "bare_number"]
    resp_formats = ["text", None]
    max_tokens_list = [16, 64]
    temps = [0.0, 0.2]

    configs: List[Dict[str, Any]] = []
    for pk in prompt_kinds:
        for rf in resp_formats:
            for mt in max_tokens_list:
                for t in temps:
                    configs.append(run_config(llm_client, pk, rf, mt, t))

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    ts = int(time.time() * 1000)
    out_dir = Path(f"hfo_crew_ai_swarm_results/{date_str}")
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"oss_120b_sweep_{ts}.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(configs, f, indent=2)

    md_path = out_dir / f"oss_120b_sweep_{ts}.md"
    lines = []
    lines.append(f"# OSS-120B Sweep — {date_str} ({ts})")
    lines.append("")
    lines.append("Prompt × response_format × max_tokens × temperature; each row runs 2 probes.")
    lines.append("")
    lines.append("| prompt | resp_format | max_tokens | temp | status | passes | notes |")
    lines.append("|---|---|---:|---:|---|---:|---|")
    for c in configs:
        notes: List[str] = []
        for i, p in enumerate(c["probes"], 1):
            sym = "✓" if (p["http_ok"] and p["parsed_ok"] and p["parsed"] == p["expect"]) else "✗"
            raw_short = (p["raw"] or "").replace("\n", " ")
            if len(raw_short) > 40:
                raw_short = raw_short[:37] + "..."
            notes.append(f"Q{i}:{sym} http={p['http_ok']} parsed={p['parsed_ok']} got={p['parsed']} exp={p['expect']} raw='{raw_short}'")
        lines.append(f"| {c['prompt']} | {c['response_format']} | {c['max_tokens']} | {c['temperature']} | {c['status']} | {c['passes']}/2 | {'; '.join(notes)} |")
    with md_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote: {md_path}")
    print(f"Wrote: {json_path}")


if __name__ == "__main__":
    main()
