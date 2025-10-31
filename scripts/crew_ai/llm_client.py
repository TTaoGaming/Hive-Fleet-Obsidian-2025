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
DIAG_DIR = os.environ.get("OPENROUTER_DIAG_DIR")  # optional: where to write diag logs

# Strict allowlist (user-defined)
# Note: Only these models can be selected. Hints outside this set will fall back to the first entry.
# Order reflects priority. You can override selection with OPENROUTER_MODEL_HINT.
ALLOWLIST = [
    # Requested, tightened allowlist (order = priority)
    "openai/gpt-5-mini",           # gpt 5 mini (reasoning high)
    "minimax/minimax-m2",          # minimax m2
    "openai/gpt-oss-120b",         # gpt oss 120b
    "openai/gpt-oss-20b",          # gpt oss 20b
    "x-ai/grok-4-fast",            # grok 4 fast
    "deepseek/deepseek-v3.2-exp",  # deepseek v3.2
    "qwen/qwen3-235b-a22b-2507",   # Qwen3 235B A22B Instruct 2507
]

# Models that support a reasoning parameter (best-effort list)
REASONING_MODELS = {
    "openai/gpt-5-mini",
    "x-ai/grok-4-fast",
    "deepseek/deepseek-v3.2-exp",
    "minimax/minimax-m2",
    "qwen/qwen3-235b-a22b-2507",
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


def _should_force_no_response_format(model: str) -> bool:
    """Return True if env OPENROUTER_FORCE_NO_RESPONSE_FORMAT_MODELS matches this model.
    Accepts comma-separated substrings (case-insensitive).
    """
    raw = os.environ.get("OPENROUTER_FORCE_NO_RESPONSE_FORMAT_MODELS", "")
    if not raw.strip():
        return False
    filters = [s.strip().lower() for s in raw.split(",") if s.strip()]
    m = model.lower()
    return any(f in m for f in filters)


def _diag_write(event: dict) -> None:
    if not DIAG_DIR:
        return
    try:
        import json, time
        from pathlib import Path
        p = Path(DIAG_DIR)
        p.mkdir(parents=True, exist_ok=True)
        fn = p / f"diag_{int(time.time()*1000)}.jsonl"
        with fn.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


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
    # Force-drop response_format for specific models if instructed by env
    if response_format_type and not _should_force_no_response_format(model):
        payload["response_format"] = {"type": response_format_type}

    # Reasoning controls: auto-enable 'high' when supported unless explicitly overridden by mission/env
    env_reason = os.environ.get("OPENROUTER_REASONING")
    env_effort = os.environ.get("OPENROUTER_REASONING_EFFORT")

    if enable_reasoning is None:
        if env_reason is not None:
            enable_reasoning = (str(env_reason).lower() in {"1", "true", "yes"})
        else:
            enable_reasoning = any(m in model for m in REASONING_MODELS)

    if reasoning_effort is None:
        if env_effort is not None:
            reasoning_effort = env_effort
        else:
            reasoning_effort = "high" if (enable_reasoning and any(m in model for m in REASONING_MODELS)) else "medium"

    if enable_reasoning and any(m in model for m in REASONING_MODELS):
        payload["reasoning"] = {"effort": reasoning_effort}

    attempts = 0
    last_error: Optional[str] = None
    total_latency = 0
    reasoning_removed_on_retry = False
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
                # Also drop reasoning on retry to maximize compatibility
                if "reasoning" in payload:
                    payload.pop("reasoning", None)
                    reasoning_removed_on_retry = True
                continue
            return {
                "ok": False,
                "model": model,
                "latency_ms": total_latency,
                "content": None,
                "error": last_error,
                "status_code": None,
                "reasoning_enabled": False,
                "reasoning_effort": None,
                "reasoning_removed_on_retry": reasoning_removed_on_retry,
            }

        if resp.status_code != 200:
            last_error = f"http_{resp.status_code}"
            if attempts <= retry_max:
                if retry_alt_format:
                    payload.pop("response_format", None)
                # If the provider rejects unknown fields, remove reasoning and retry once
                if "reasoning" in payload:
                    payload.pop("reasoning", None)
                    reasoning_removed_on_retry = True
                continue
            return {
                "ok": False,
                "model": model,
                "latency_ms": total_latency,
                "content": None,
                "error": last_error,
                "status_code": resp.status_code,
                "reasoning_enabled": False,
                "reasoning_effort": None,
                "reasoning_removed_on_retry": reasoning_removed_on_retry,
            }

        usage = None
        raw_len = None
        try:
            data = resp.json()
            content = _extract_content(data)
            usage = data.get("usage") if isinstance(data, dict) else None
            try:
                import json as _json
                raw_len = len(_json.dumps(data))
            except Exception:
                raw_len = None
        except Exception:
            content = ""
            usage = None

        # optional diagnostic log
        _diag_write({
            "model": model,
            "attempt": attempts,
            "status_code": resp.status_code,
            "latency_ms": latency_ms,
            "total_latency_ms": total_latency,
            "has_usage": bool(usage),
            "content_len": len(content or "") if content is not None else None,
            "raw_json_len": raw_len,
            "empty_content": not bool(str(content or "").strip()),
        })

        # If content is empty and retry is allowed, try once more (possibly without response_format)
        if (content is None or not str(content).strip()) and retry_on_empty and attempts <= retry_max:
            if retry_alt_format:
                payload.pop("response_format", None)
            if "reasoning" in payload:
                payload.pop("reasoning", None)
                reasoning_removed_on_retry = True
            # slight jitter via no-op sleep avoided to keep fast
            continue

        # Reasoning metadata for audit
        used_reasoning_block = payload.get("reasoning") if isinstance(payload, dict) else None
        reasoning_enabled_flag = bool(used_reasoning_block)
        reasoning_effort_used = None
        if isinstance(used_reasoning_block, dict):
            effort_val = used_reasoning_block.get("effort")
            reasoning_effort_used = effort_val if isinstance(effort_val, str) else None

        return {
            "ok": True,
            "model": model,
            "latency_ms": total_latency if attempts > 1 else latency_ms,
            "content": content,
            "error": None,
            "status_code": resp.status_code,
            "usage": usage,
            "reasoning_enabled": reasoning_enabled_flag,
            "reasoning_effort": reasoning_effort_used,
            "reasoning_removed_on_retry": reasoning_removed_on_retry,
        }
