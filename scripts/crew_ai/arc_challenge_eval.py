#!/usr/bin/env python3
"""
ARC-Challenge evaluation harness (research-grade, lightweight):
- Loads the official AI2 ARC-Challenge dataset from Hugging Face datasets
- Uses multiple-choice (validation split) and scores accuracy
- Prompts LLM to output only the choice letter and parses strictly

Usage examples:
  # default: validation split, limit 0 (=all), uses env OPENROUTER_MODEL_HINT if set
  python3 scripts/crew_ai/arc_challenge_eval.py --limit 200

  # select a specific model
  OPENROUTER_MODEL_HINT=deepseek/deepseek-chat-v3-0324 \
    python3 scripts/crew_ai/arc_challenge_eval.py --limit 0

  # write JSON results
  python3 scripts/crew_ai/arc_challenge_eval.py --limit 200 --output temp/evals/arc_challenge_results.json
"""
from __future__ import annotations
import argparse
import json
import os
import re
from dataclasses import dataclass
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from datasets import load_dataset

import importlib.util

# Load sibling llm_client robustly
THIS = Path(__file__).resolve()
LLM_PATH = THIS.parent / "llm_client.py"
spec = importlib.util.spec_from_file_location("llm_client", str(LLM_PATH))
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load llm_client module")
llm_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(llm_client)  # type: ignore[arg-type]
call_openrouter = getattr(llm_client, "call_openrouter")


def _extract_letter(s: str) -> Optional[str]:
    t = (s or "").strip()
    m = re.search(r"[A-Za-z]", t)
    return m.group(0).upper() if m else None


def _format_prompt(question: str, choices: List[Tuple[str, str]]) -> str:
    # choices: list of (label, text), labels like 'A','B','C','D'
    lines = [f"Question: {question}", "", "Options:"]
    # Sort choices by label letter to keep consistent order
    for label, text in sorted(choices, key=lambda x: x[0]):
        lines.append(f"{label}) {text}")
    lines.append("")
    lines.append("Answer with the letter only (A, B, C, D, ...).")
    return "\n".join(lines)


@dataclass
class ARCResult:
    model: str
    total: int
    correct: int
    format_fails: int
    avg_latency_ms: float
    details: List[Dict[str, Any]]
    total_tokens: int
    empty_content: int


def run_eval(
    *,
    model_hint: Optional[str],
    split: str = "validation",
    limit: int = 0,
    offset: int = 0,
    seed: Optional[int] = None,
    max_tokens: int = 12,
    temperature: float = 0.0,
    timeout_seconds: int = 25,
) -> ARCResult:
    ds = load_dataset("ai2_arc", "ARC-Challenge", split=split)
    records = list(ds)
    if seed is not None:
        rnd = random.Random(int(seed))
        rnd.shuffle(records)
    if offset and offset > 0:
        records = records[offset:]
    if limit and limit > 0:
        records = records[: limit]

    total = 0
    correct = 0
    format_fails = 0
    latencies: List[int] = []
    details: List[Dict[str, Any]] = []
    total_tokens = 0
    empty_content = 0
    model_used: Optional[str] = None

    for rec in records:
        total += 1
        q = rec.get("question")
        ans_key = str(rec.get("answerKey")).strip().upper()
        # choices: {'text': [...], 'label': [...]}
        ch = rec.get("choices") or {}
        labels = list(ch.get("label") or [])
        texts = list(ch.get("text") or [])
        pairs: List[Tuple[str, str]] = [(str(l).upper(), str(t)) for l, t in zip(labels, texts)]
        prompt = _format_prompt(q, pairs)

        res = call_openrouter(
            prompt,
            model_hint=model_hint,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            response_format_type="text",
            system_prompt="Answer with the letter only. Be exact.",
        )
        model_used = model_used or res.get("model")
        content = res.get("content") if res.get("ok") else None
        if content is None or str(content).strip() == "":
            empty_content += 1
        got_letter = _extract_letter(content or "") if res.get("ok") else None
        ok = (got_letter == ans_key)
        correct += 1 if ok else 0
        format_fails += 1 if got_letter is None else 0
        latencies.append(int(res.get("latency_ms") or 0))
        usage = res.get("usage") or {}
        try:
            total_tokens += int(usage.get("total_tokens") or 0)
        except Exception:
            pass
        details.append({
            "id": rec.get("id"),
            "ok": ok,
            "got": got_letter,
            "expect": ans_key,
            "latency_ms": res.get("latency_ms"),
            "raw": res.get("content"),
            "usage_total_tokens": (usage or {}).get("total_tokens"),
        })

    avg_latency = float(sum(latencies) / len(latencies)) if latencies else 0.0
    return ARCResult(
        model=model_used or (model_hint or "unknown"),
        total=total,
        correct=correct,
        format_fails=format_fails,
        avg_latency_ms=avg_latency,
        details=details,
        total_tokens=total_tokens,
        empty_content=empty_content,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="ARC-Challenge (validation) evaluation")
    ap.add_argument("--limit", type=int, default=200, help="Limit number of items (0 = all)")
    ap.add_argument("--split", type=str, default="validation", choices=["train", "validation", "test"])
    ap.add_argument("--max-tokens", type=int, default=12)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--timeout-seconds", type=int, default=25)
    ap.add_argument("--output", type=str, default="", help="Optional JSON output path")
    args = ap.parse_args()

    # Load env for key and model hint
    ROOT = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=ROOT / ".env", override=False)
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("No OPENROUTER_API_KEY found. Set it in .env to run ARC-Challenge eval.")
        return
    model_hint = os.environ.get("OPENROUTER_MODEL_HINT")

    result = run_eval(
        model_hint=model_hint,
        split=args.split,
        limit=args.limit,
        offset=0,
        seed=None,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        timeout_seconds=args.timeout_seconds,
    )
    acc = (result.correct / result.total) if result.total else 0.0
    print(f"Model: {result.model}")
    print(f"ARC-Challenge[{args.split}] limit={args.limit or 'ALL'} -> Accuracy: {result.correct}/{result.total} = {acc:.2%}; avg_latency={result.avg_latency_ms:.0f} ms; empty_content={result.empty_content}; tokens={result.total_tokens}")

    if args.output:
        outp = Path(args.output)
        outp.parent.mkdir(parents=True, exist_ok=True)
        with outp.open("w", encoding="utf-8") as f:
            json.dump({
                "model": result.model,
                "split": args.split,
                "limit": args.limit,
                "total": result.total,
                "correct": result.correct,
                "accuracy": acc,
                "format_fails": result.format_fails,
                "avg_latency_ms": result.avg_latency_ms,
                "details": result.details,
            }, f, indent=2)
        print(f"Wrote: {outp}")


if __name__ == "__main__":
    main()
