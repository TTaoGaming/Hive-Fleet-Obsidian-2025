#!/usr/bin/env python3
"""
Low-cost hallucination sanity: small, verifiable prompts with exact answers.
Runs in parallel to exercise lane concurrency and reports accuracy + consistency.

If no OPENROUTER_API_KEY is present, it will skip LLM calls and print guidance.

Usage:
  OPENROUTER_MODEL_HINT=openai/gpt-oss-120b python scripts/crew_ai/hallucination_sanity.py --concurrency 4 --repeat 1
"""
from __future__ import annotations
import argparse
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Optional
from pathlib import Path
from dotenv import load_dotenv

try:
    from .llm_client import call_openrouter
except Exception:  # pragma: no cover
    from llm_client import call_openrouter  # type: ignore

# Tiny, synthetic set of problems with unique, numeric answers
PROBLEMS: List[Tuple[str, int]] = [
    ("If you have 3 boxes with 5 apples each, how many apples total?", 15),
    ("What is 7 times 8?", 56),
    ("A train travels 60 km in 1 hour. How far in 2.5 hours?", 150),
    ("John had 120 stickers, gave away 45. How many left?", 75),
    ("Compute (12 + 18) / 6", 5),
    ("Area of rectangle 7 by 9?", 63),
    ("If x=4, evaluate 3x^2", 48),
    ("Convert 0.75 to percent (integer)", 75),
    ("What is 9 squared?", 81),
    ("If you split 84 equally among 7 people, each gets?", 12),
]


def extract_int(s: str) -> Optional[int]:
    m = re.search(r"-?\d+", s or "")
    if not m:
        return None
    try:
        return int(m.group(0))
    except ValueError:
        return None


def ask(q: string, model_hint: Optional[str]) -> Tuple[bool, Optional[int], str]:  # type: ignore[name-defined]
    res = call_openrouter(
        f"Answer with just the integer. {q}",
        model_hint=model_hint,
        max_tokens=12,
        temperature=0.0,
    )
    got = extract_int(res.get("content") or "") if res.get("ok") else None
    return res.get("ok", False), got, (res.get("model") or "")


def main() -> None:
    ap = argparse.ArgumentParser(description="Hallucination sanity: numeric, verifiable prompts")
    ap.add_argument("--concurrency", type=int, default=2, help="Parallel requests")
    ap.add_argument("--repeat", type=int, default=1, help="Repeat each prompt (self-consistency)")
    args = ap.parse_args()

    ROOT = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=ROOT / ".env", override=False)
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("No OPENROUTER_API_KEY found. Skipping LLM calls. Set it in .env to run this sanity check.")
        return

    model_hint = os.environ.get("OPENROUTER_MODEL_HINT")
    correct = 0
    total = 0
    model_used = None

    tasks: List[Tuple[str, int]] = []
    for q, ans in PROBLEMS:
        for _ in range(max(1, args.repeat)):
            tasks.append((q, ans))

    def job(item: Tuple[str, int]):
        q, ans = item
        ok, got, model = ask(q, model_hint)
        return q, ans, ok, got, model

    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as ex:
        futs = [ex.submit(job, t) for t in tasks]
        for fut in as_completed(futs):
            q, ans, ok, got, model = fut.result()
            model_used = model_used or model
            total += 1
            is_correct = (got == ans)
            correct += 1 if is_correct else 0
            print(f"Q: {q} -> model={model} got={got} expected={ans} ok={ok} correct={is_correct}")

    acc = (correct / total) if total else 0.0
    print(f"Model: {model_used}")
    print(f"Accuracy: {correct}/{total} = {acc:.2%}")


if __name__ == "__main__":
    main()
