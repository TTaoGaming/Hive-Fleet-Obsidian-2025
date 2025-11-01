from __future__ import annotations
from typing import Any, Dict, Optional

# Base adapter interface: implement engage() returning metrics and llm fields
# Contract
# inputs: mission (dict), lane_name (str), model_hint (str|None), lane_index (int)
# outputs: {
#   actions: [str],
#   metrics_summary: dict,
#   llm: dict,  # ok, model, latency_ms, status_code, error, content_preview, max_tokens
# }

def engage_default(*, mission: Dict[str, Any], lane_name: str, model_hint: Optional[str], lane_index: int = 0) -> Dict[str, Any]:
    # No-op default engage: avoid remote calls if not needed
    llm_cfg = mission.get("llm", {}) or {}
    engage_stage_cfg = (llm_cfg.get("per_stage_defaults", {}) or {}).get("engage", {})
    try:
        engage_tokens = int(engage_stage_cfg.get("max_tokens", llm_cfg.get("max_tokens", 72)))
    except Exception:
        engage_tokens = int(llm_cfg.get("max_tokens", 72))
    return {
        "actions": ["shaper_run", "llm_skipped"],
        "metrics_summary": {},
        "llm": {
            "ok": False,
            "model": model_hint,
            "latency_ms": None,
            "status_code": None,
            "error": None,
            "content_preview": None,
            "max_tokens": int(engage_tokens),
            "requested_model_hint": model_hint,
        },
    }
