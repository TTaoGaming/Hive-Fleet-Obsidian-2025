from __future__ import annotations
from typing import Any, Dict, Optional
from pathlib import Path
import sys as _sys
import importlib.util

# Lazy-load arc_challenge_eval to avoid hard dependency outside ARC runs
_THIS = Path(__file__).resolve()
_ARC_EVAL_PATH = _THIS.parent.parent / "arc_challenge_eval.py"
_spec = importlib.util.spec_from_file_location("arc_challenge_eval", str(_ARC_EVAL_PATH))
if _spec is None or _spec.loader is None:
    raise RuntimeError("arc_challenge_eval module not found")
arc_eval = importlib.util.module_from_spec(_spec)
_sys.modules[_spec.name] = arc_eval  # ensure module is registered for decorators/imports
_spec.loader.exec_module(arc_eval)  # type: ignore[arg-type]

# Load llm_client robustly (sibling file)
_LLM_PATH = _THIS.parent.parent / "llm_client.py"
_llm_spec = importlib.util.spec_from_file_location("llm_client", str(_LLM_PATH))
if _llm_spec is None or _llm_spec.loader is None:
    raise RuntimeError("llm_client module not found")
llm_client = importlib.util.module_from_spec(_llm_spec)
_llm_spec.loader.exec_module(llm_client)  # type: ignore[arg-type]
call_openrouter = getattr(llm_client, "call_openrouter")


def engage_arc(*, mission: Dict[str, Any], lane_name: str, model_hint: Optional[str], lane_index: int = 0) -> Dict[str, Any]:
    llm_cfg = mission.get("llm", {}) or {}
    engage_stage_cfg = (llm_cfg.get("per_stage_defaults", {}) or {}).get("engage", {})
    try:
        engage_tokens = int(engage_stage_cfg.get("max_tokens", llm_cfg.get("max_tokens", 400)))
    except Exception:
        engage_tokens = int(llm_cfg.get("max_tokens", 400))

    arc_cfg = mission.get("arc", {}) or {}
    split = str(arc_cfg.get("split", "validation"))
    limit = int(arc_cfg.get("limit", 50))
    seed = int(arc_cfg.get("seed", 42)) + int(lane_index)
    offset = (limit * max(0, int(lane_index))) if limit > 0 else 0

    res = arc_eval.run_eval(
        model_hint=model_hint,
        split=split,
        limit=limit,
        offset=offset,
        seed=seed,
        max_tokens=engage_tokens,
        temperature=float(llm_cfg.get("temperature", 0.0)),
        timeout_seconds=int(llm_cfg.get("timeout_seconds", 25)),
    )

    acc = (res.correct / res.total) if res.total else 0.0
    metrics = {
        "total": res.total,
        "correct": res.correct,
        "accuracy": acc,
        "format_fails": res.format_fails,
        "avg_latency_ms": res.avg_latency_ms,
        "empty_content": res.empty_content,
        "total_tokens": res.total_tokens,
    }
    return {
        "actions": ["shaper_run", "arc_eval"],
        "metrics_summary": metrics,
        "llm": {
            "ok": True,
            "model": getattr(res, "model", model_hint),
            "latency_ms": res.avg_latency_ms,
            "status_code": None,
            "error": None,
            "content_preview": None,
            "max_tokens": int(engage_tokens),
            "requested_model_hint": model_hint,
        },
    }


def _phase_llm_call(
    *,
    phase: str,
    mission: Dict[str, Any],
    lane_name: str,
    model_hint: Optional[str],
    lane_index: int,
    lane_dir: Path,
) -> Dict[str, Any]:
    """Perform a small, bounded LLM call for a phase and write a note file.

    Returns a dict with evidence_refs to the note file if successful.
    """
    llm_cfg = mission.get("llm", {}) or {}
    per_stage = (llm_cfg.get("per_stage_defaults", {}) or {}).get(phase, {})
    max_tokens = int(per_stage.get("max_tokens", llm_cfg.get("max_tokens", 200)))
    temperature = float(llm_cfg.get("temperature", 0.2))
    timeout_seconds = int(llm_cfg.get("timeout_seconds", 20))

    prompts = {
        "perceive": "Summarize the mission context briefly (1-2 lines).",
        "react": "State the plan to approach ARC evaluation in one or two concise bullets.",
        "yield": "Provide a one-line lane summary and a brief recommendation.",
    }
    prompt = prompts.get(phase, f"Phase {phase}: provide a brief note.")
    res = call_openrouter(
        prompt,
        model_hint=model_hint,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
        response_format_type="text",
        retry_on_empty=True,
        retry_max=1,
        retry_alt_format=True,
    )

    content = res.get("content") if res.get("ok") else None
    note_name = f"{phase}_llm_note.md"
    note_path = lane_dir / note_name
    try:
        lane_dir.mkdir(parents=True, exist_ok=True)
        with note_path.open("w", encoding="utf-8") as f:
            f.write(f"# {phase.title()} LLM Note\n\n")
            f.write((content or "<no content>") + "\n")
            f.write("\n---\n")
            f.write(f"model: {res.get('model')}\n")
            f.write(f"latency_ms: {res.get('latency_ms')}\n")
            f.write(f"max_tokens: {max_tokens}\n")
    except Exception:
        pass

    if note_path.exists():
        return {"evidence_refs": [str(note_path)]}
    return {"evidence_refs": []}


def perceive_arc(*, mission: Dict[str, Any], lane_name: str, model_hint: Optional[str], lane_index: int = 0, lane_dir: Path | None = None) -> Dict[str, Any]:
    if lane_dir is None:
        return {}
    return _phase_llm_call(phase="perceive", mission=mission, lane_name=lane_name, model_hint=model_hint, lane_index=lane_index, lane_dir=lane_dir)


def react_arc(*, mission: Dict[str, Any], lane_name: str, model_hint: Optional[str], lane_index: int = 0, lane_dir: Path | None = None) -> Dict[str, Any]:
    if lane_dir is None:
        return {}
    return _phase_llm_call(phase="react", mission=mission, lane_name=lane_name, model_hint=model_hint, lane_index=lane_index, lane_dir=lane_dir)


def yield_arc(*, mission: Dict[str, Any], lane_name: str, model_hint: Optional[str], lane_index: int = 0, lane_dir: Path | None = None) -> Dict[str, Any]:
    if lane_dir is None:
        return {}
    return _phase_llm_call(phase="yield", mission=mission, lane_name=lane_name, model_hint=model_hint, lane_index=lane_index, lane_dir=lane_dir)
