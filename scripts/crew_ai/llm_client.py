#!/usr/bin/env python3
"""
Minimal OpenRouter LLM client with cost and safety guards.

Design goals:
- Never log secrets (only audit presence externally)
- Default to cheap/fast models via allowlist and env hint
- Bounded responses with configurable limits (env or mission overrides)
- Timeouts and clear error paths (no raise unless critical)

Environment variables:
- OPENROUTER_API_KEY: required to actually call the API
- OPENROUTER_BASE_URL: optional, defaults to https://openrouter.ai/api/v1
- OPENROUTER_MODEL_HINT: optional, used to select a model from ALLOWLIST
- OPENROUTER_MAX_TOKENS: optional int, overrides max_tokens if set
- OPENROUTER_TEMPERATURE: optional float, overrides temperature if set
- OPENROUTER_TIMEOUT_SECONDS: optional int, overrides timeout if set
"""
from __future__ import annotations
import os
import time
from typing import Any, Dict, Optional, List

import requests

DEFAULT_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Strict allowlist (user-defined)
# Note: Only these models can be selected. Hints outside this set will fall back to the first entry.
# Order reflects priority. You can override selection with OPENROUTER_MODEL_HINT.
ALLOWLIST = [
    # Preferred, modern, reasoning-capable or fast models
    "openai/gpt-5-mini",
    "x-ai/grok-4-fast",
    "minimax/minimax-m2",
    "deepseek/deepseek-v3.2-exp",
    "deepseek/deepseek-v3.1-terminus",
    # Existing backups and test models
    "deepseek/deepseek-chat-v3-0324",
    "qwen/qwen3-235b-a22b-2507",
    "x-ai/grok-code-fast-1",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]

# Models that support a reasoning parameter (best-effort list)
REASONING_MODELS = {
    "openai/gpt-5-mini",
    "x-ai/grok-4-fast",
    "deepseek/deepseek-v3.2-exp",
    "deepseek/deepseek-v3.1-terminus",
    "minimax/minimax-m2",
}


def _select_model(model_hint: Optional[str]) -> str:
    if model_hint:
        # Prefer explicit hint if present in allowlist (case-insensitive contains)
        hint = model_hint.lower()
        for m in ALLOWLIST:
            if hint in m.lower():
                return m
    # Fallback to first allowlisted model
    return ALLOWLIST[0]


def _coerce_int(val: Optional[str], default: int) -> int:
    try:
        return int(val) if val is not None else default
    except Exception:
        return default


def _coerce_float(val: Optional[str], default: float) -> float:
    try:
        return float(val) if val is not None else default
    except Exception:
        return default


def _extract_content(data: Dict[str, Any]) -> str:
    """
    Robustly extract assistant text from an OpenRouter /chat/completions response.
    Tries multiple shapes observed across providers and OSS models.
    """
    try:
        choices = data.get("choices", []) or []
        if not choices:
            return ""
        c0 = choices[0] or {}
        # 1) OpenAI-standard: choices[0].message.content as string
        msg = c0.get("message", {}) or {}
        content = msg.get("content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()
        # 2) Some providers return content as a list of parts
        if isinstance(content, list):
            parts: List[str] = []
            for part in content:
                if isinstance(part, str) and part.strip():
                    parts.append(part.strip())
                elif isinstance(part, dict):
                    # Common keys: text, content, output_text
                    for key in ("text", "content", "output_text"):
                        val = part.get(key)
                        if isinstance(val, str) and val.strip():
                            parts.append(val.strip())
                            break
            if parts:
                return "\n".join(parts).strip()
        # 3) Some OSS models place text under choices[0].text
        txt = c0.get("text")
        if isinstance(txt, str) and txt.strip():
            return txt.strip()
        # 4) Some providers mirror under choices[0].content
        alt = c0.get("content")
        if isinstance(alt, str) and alt.strip():
            return alt.strip()
    except Exception:
        return ""
    return ""


def call_openrouter(
    prompt: str,
    *,
    model_hint: Optional[str] = None,
    max_tokens: int = 96,
    temperature: float = 0.2,
    timeout_seconds: int = 25,
    response_format_type: Optional[str] = "text",
    system_prompt: Optional[str] = None,
    enable_reasoning: Optional[bool] = None,
    reasoning_effort: Optional[str] = None,
    # Transport resilience
    retry_on_empty: bool = False,
    retry_max: int = 1,
    retry_alt_format: bool = True,
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

    # Allow environment overrides for limits
    max_tokens = _coerce_int(os.environ.get("OPENROUTER_MAX_TOKENS"), max_tokens)
    temperature = _coerce_float(os.environ.get("OPENROUTER_TEMPERATURE"), temperature)
    timeout_seconds = _coerce_int(os.environ.get("OPENROUTER_TIMEOUT_SECONDS"), timeout_seconds)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Identify this client conservatively (optional but helpful)
        "HTTP-Referer": "https://github.com/tommytai3/HiveFleetObsidian",
        "X-Title": "HFO Crew AI Pilot",
    }
    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": (system_prompt or "You are a helpful assistant. Be clear and accurate.")},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    # Hint to prefer plain text when supported; gracefully ignored otherwise
    if response_format_type:
        payload["response_format"] = {"type": response_format_type}

    # Reasoning controls: enable when requested and model is in supported set
    if enable_reasoning is None:
        # Allow env override: OPENROUTER_REASONING=true/false, OPENROUTER_REASONING_EFFORT
        env_reason = os.environ.get("OPENROUTER_REASONING")
        enable_reasoning = (str(env_reason).lower() in {"1", "true", "yes"}) if env_reason is not None else False
    if reasoning_effort is None:
        reasoning_effort = os.environ.get("OPENROUTER_REASONING_EFFORT", "medium")
    if enable_reasoning and any(m in model for m in REASONING_MODELS):
        payload["reasoning"] = {"effort": reasoning_effort}

    attempts = 0
    last_error: Optional[str] = None
    total_latency = 0
    while True:
        attempts += 1
        t0 = time.time()
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout_seconds)
            latency_ms = int((time.time() - t0) * 1000)
            total_latency += latency_ms
        except requests.RequestException as e:
            last_error = f"request_error: {type(e).__name__}"
            if attempts <= retry_max:
                # Retry on transport errors too
                if retry_alt_format:
                    payload.pop("response_format", None)
                continue
            return {
                "ok": False,
                "model": model,
                "latency_ms": total_latency,
                "content": None,
                "error": last_error,
                "status_code": None,
            }

        if resp.status_code != 200:
            last_error = f"http_{resp.status_code}"
            if attempts <= retry_max:
                if retry_alt_format:
                    payload.pop("response_format", None)
                continue
            return {
                "ok": False,
                "model": model,
                "latency_ms": total_latency,
                "content": None,
                "error": last_error,
                "status_code": resp.status_code,
            }

        usage = None
        try:
            data = resp.json()
            content = _extract_content(data)
            usage = data.get("usage") if isinstance(data, dict) else None
        except Exception:
            content = ""
            usage = None

        # If content is empty and retry is allowed, try once more (possibly without response_format)
        if (content is None or not str(content).strip()) and retry_on_empty and attempts <= retry_max:
            if retry_alt_format:
                payload.pop("response_format", None)
            # slight jitter via no-op sleep avoided to keep fast
            continue

        return {
            "ok": True,
            "model": model,
            "latency_ms": total_latency if attempts > 1 else latency_ms,
            "content": content,
            "error": None,
            "status_code": resp.status_code,
            "usage": usage,
        }
