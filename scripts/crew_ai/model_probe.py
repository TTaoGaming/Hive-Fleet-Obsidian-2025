#!/usr/bin/env python3
"""
Probe all allowlisted OpenRouter models (1–2 questions per model) and emit a concise digest.

Outputs:
- Markdown digest under hfo_crew_ai_swarm_results/YYYY-MM-DD/model_probe_digest.md
- JSON results under hfo_crew_ai_swarm_results/YYYY-MM-DD/model_probe_results.json

Criteria:
- ok: HTTP 200 and non-empty content, and integer parsing succeeds for both probes
- partial: at least one probe succeeds
- fail: both probes fail (empty content or parse fail)
"""
from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple

import sys
from pathlib import Path
import importlib.util
from dotenv import load_dotenv

# Load llm_client.py directly to avoid package import issues
THIS_FILE = Path(__file__).resolve()
LLM_PATH = THIS_FILE.parent / "llm_client.py"
spec = importlib.util.spec_from_file_location("llm_client", str(LLM_PATH))
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load llm_client module")
llm_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(llm_client)  # type: ignore[arg-type]


def _parse_int(s: str) -> Tuple[bool, int | None]:
    if s is None:
        return False, None
    text = s.strip()
    # Extract first integer on the line if present
    num = ""
    neg = False
    i = 0
    if i < len(text) and text[i] in "+-":
        neg = text[i] == "-"
        i += 1
    while i < len(text) and text[i].isdigit():
        num += text[i]
        i += 1
    if not num:
        return False, None
    val = int(num)
    return True, -val if neg else val


def probe_model(model_hint: str) -> Dict[str, Any]:
    questions = [
        ("Answer with only the integer result: 7 + 5 = ?", 12),
        ("Answer with only the integer result: 81 - 39 = ?", 42),
    ]
    results = []
    passes = 0
    for q, expect in questions:
        r = llm_client.call_openrouter(
            q,
            model_hint=model_hint,
            max_tokens=16,
            temperature=0.1,
            timeout_seconds=20,
        )
        ok_http = r.get("ok") and r.get("status_code") == 200
        raw = r.get("content")
        ok_parse, val = _parse_int(raw or "")
        ok = bool(ok_http and ok_parse and val == expect)
        if ok:
            passes += 1
        results.append({
            "http_ok": bool(ok_http),
            "status_code": r.get("status_code"),
            "latency_ms": r.get("latency_ms"),
            "raw": raw,
            "parsed_ok": bool(ok_parse),
            "parsed": val,
            "expect": expect,
        })
    status = "ok" if passes == 2 else ("partial" if passes == 1 else "fail")
    return {"model": r.get("model"), "hint": model_hint, "status": status, "passes": passes, "probes": results}


def main() -> None:
    # Load .env if present
    load_dotenv()

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    out_dir = Path(f"hfo_crew_ai_swarm_results/{date_str}")
    out_dir.mkdir(parents=True, exist_ok=True)

    allowlist = llm_client.ALLOWLIST
    all_results = []
    for hint in allowlist:
        # Set env for downstream systems (also used inside client.select)
        os.environ["OPENROUTER_MODEL_HINT"] = hint
        all_results.append(probe_model(hint))

    # Write JSON
    json_path = out_dir / "model_probe_results.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    # Write Markdown digest
    md_path = out_dir / "model_probe_digest.md"
    lines = []
    lines.append(f"# Model Probe Digest — {date_str}")
    lines.append("")
    lines.append("Summary: quick 2-question integer probes (low token) across allowlisted models. Status=ok|partial|fail.")
    lines.append("")
    lines.append("| Model (hint) | Status | Passes | Notes |")
    lines.append("|---|---:|---:|---|")
    for r in all_results:
        note = []
        for i, p in enumerate(r["probes"], 1):
            tag = "OK" if (p["http_ok"] and p["parsed_ok"] and p["parsed"] == p["expect"]) else "FAIL"
            sym = "✓" if tag == "OK" else "✗"
            raw_short = (p["raw"] or "").replace("\n", " ")
            if len(raw_short) > 60:
                raw_short = raw_short[:57] + "..."
            note.append(f"Q{i}:{sym} http={p['http_ok']} parsed={p['parsed_ok']} got={p['parsed']} exp={p['expect']} raw=‘{raw_short}’")
        lines.append(f"| {r['model']} ({r['hint']}) | {r['status']} | {r['passes']}/2 | {'; '.join(note)} |")
    lines.append("")
    lines.append("Artifacts:")
    lines.append(f"- JSON: {json_path}")
    with md_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote: {md_path}")
    print(f"Wrote: {json_path}")


if __name__ == "__main__":
    main()
