#!/usr/bin/env python3
"""
Tiny math benchmark using the shared OpenRouter client.
Keeps token/cost low and produces a simple accuracy summary.

Usage:
  OPENROUTER_MODEL_HINT=openai/gpt-oss-120b python scripts/crew_ai/math_bench.py
"""
from __future__ import annotations
import re
from typing import List, Tuple
import os
from pathlib import Path
from dotenv import load_dotenv

try:
    from .llm_client import call_openrouter
except Exception:  # pragma: no cover - fallback for direct run
    from llm_client import call_openrouter  # type: ignore

PROBLEMS: List[Tuple[str, int]] = [
    ("12 + 7 = ?", 19),
    ("8 * 9 = ?", 72),
    ("144 / 12 = ?", 12),
    ("(3 + 5) * 2 = ?", 16),
    ("2^5 = ?", 32),
    ("100 - 77 = ?", 23),
    ("15 * 0 = ?", 0),
    ("7 * 13 = ?", 91),
    ("81^(1/2) = ?", 9),
    ("(10 + 2) / 4 = ? (integer)", 3),
]


def extract_int(s: str) -> int | None:
    m = re.search(r"-?\d+", s)
    if not m:
        return None
    try:
        return int(m.group(0))
    except ValueError:
        return None


def main() -> None:
    # Load API key from repo .env if present
    ROOT = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=ROOT / ".env", override=False)
    correct = 0
    total = len(PROBLEMS)
    model_hint = os.environ.get("OPENROUTER_MODEL_HINT")
    for q, ans in PROBLEMS:
        res = call_openrouter(
            f"Answer with just the integer. {q}",
            model_hint=model_hint,
            max_tokens=12,
            temperature=0.0,
        )
        got = None
        if res.get("ok") and res.get("content"):
            got = extract_int(res["content"])  # type: ignore[index]
        is_ok = got == ans
        if is_ok:
            correct += 1
        print(f"Q: {q} -> model={res.get('model')} got={got} expected={ans} ok={is_ok}")
    acc = correct / total if total else 0.0
    print(f"Accuracy: {correct}/{total} = {acc:.2%}")


if __name__ == "__main__":
    main()
