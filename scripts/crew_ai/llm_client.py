#!/usr/bin/env python3
"""
Minimal OpenRouter LLM client with cost and safety guards.

Design goals:
- Never log secrets (only audit presence externally)
- Default to cheap/fast models via allowlist and env hint
- Small, bounded responses (low max_tokens) to control cost
- Timeouts and clear error paths (no raise unless critical)

Environment variables:
- OPENROUTER_API_KEY: required to actually call the API
- OPENROUTER_BASE_URL: optional, defaults to https://openrouter.ai/api/v1
- OPENROUTER_MODEL_HINT: optional, used to select a model from ALLOWLIST
"""
from __future__ import annotations
import os
import time
from typing import Any, Dict, Optional

import requests

DEFAULT_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Strict allowlist (user-defined)
# Note: Only these models can be selected. Hints outside this set will fall back to the first entry.
ALLOWLIST = [
    # Default priority: use OSS 120B unless a different allowed hint is provided
    "openai/gpt-oss-120b",
    # Remaining models are available for testing/backup
    "deepseek/deepseek-chat-v3-0324",
    "qwen/qwen3-235b-a22b-2507",
    "x-ai/grok-code-fast-1",
    "openai/gpt-oss-20b",
]


def _select_model(model_hint: Optional[str]) -> str:
    if model_hint:
        # Prefer explicit hint if present in allowlist (case-insensitive contains)
        hint = model_hint.lower()
        for m in ALLOWLIST:
            if hint in m.lower():
                return m
    # Fallback to first allowlisted model
    return ALLOWLIST[0]


def call_openrouter(
    prompt: str,
    *,
    model_hint: Optional[str] = None,
    max_tokens: int = 96,
    temperature: float = 0.2,
    timeout_seconds: int = 25,
) -> Dict[str, Any]:
    """
    Make a single, bounded LLM call. Returns a result dict with shape:
    {
      "ok": bool,
      "model": str,
      "latency_ms": int,
      "content": str | None,
      "error": str | None,
      "status_code": int | None,
    }
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return {
            "ok": False,
            "model": _select_model(model_hint),
            "latency_ms": 0,
            "content": None,
            "error": "missing_api_key",
            "status_code": None,
        }

    url = f"{DEFAULT_BASE_URL.rstrip('/')}/chat/completions"
    model = _select_model(model_hint)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Identify this client conservatively (optional but helpful)
        "HTTP-Referer": "https://github.com/tommytai3/HiveFleetObsidian",
        "X-Title": "HFO Crew AI Pilot",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise, cautious assistant. Keep answers short."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    t0 = time.time()
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout_seconds)
        latency_ms = int((time.time() - t0) * 1000)
    except requests.RequestException as e:
        return {
            "ok": False,
            "model": model,
            "latency_ms": int((time.time() - t0) * 1000),
            "content": None,
            "error": f"request_error: {type(e).__name__}",
            "status_code": None,
        }

    if resp.status_code != 200:
        return {
            "ok": False,
            "model": model,
            "latency_ms": latency_ms,
            "content": None,
            "error": f"http_{resp.status_code}",
            "status_code": resp.status_code,
        }

    try:
        data = resp.json()
        # OpenAI-compatible shape
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
    except Exception:
        content = ""

    return {
        "ok": True,
        "model": model,
        "latency_ms": latency_ms,
        "content": content,
        "error": None,
        "status_code": resp.status_code,
    }
