from __future__ import annotations
from typing import Any, Dict, Optional
from pathlib import Path


def _safe_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _get_query(mission: Dict[str, Any]) -> str:
    q = str((mission.get("research", {}) or {}).get("query") or "").strip()
    if q:
        return q
    # Fallback to a generic phrasing based on mission_id
    return f"Research focus derived from mission {mission.get('mission_id', 'unknown')}"


def perceive_research(*, mission: Dict[str, Any], lane_name: str, model_hint: Optional[str], lane_index: int = 0, lane_dir: Path) -> Dict[str, Any]:
    """Collect initial observations for the research prompt.

    This stub avoids network calls and writes a small observations note to keep costs low.
    """
    query = _get_query(mission)
    notes = [
        f"# Perception Observations — {lane_name}",
        "",
        f"Prompt: {query}",
        "Scope: Capture the immediate framing, known constraints, and key unknowns.",
        "Signals: Establish initial hypotheses and evidence needs for React stage.",
    ]
    obs_path = lane_dir / "perception_observations.md"
    _safe_write(obs_path, "\n".join(notes))
    return {"evidence_refs": [str(obs_path)]}


def react_research(*, mission: Dict[str, Any], lane_name: str, model_hint: Optional[str], lane_index: int = 0, lane_dir: Path) -> Dict[str, Any]:
    query = _get_query(mission)
    plan = [
        f"# React Plan — {lane_name}",
        "",
        f"Goal: Address the research prompt: {query}",
        "Approach:",
        "- Categorize problem space (definition, prior art, constraints)",
        "- Draft outline of deliverables (summary, references, open questions)",
        "- Define acceptance (traceable evidence, structured yield)",
    ]
    plan_path = lane_dir / "react_plan_detail.md"
    _safe_write(plan_path, "\n".join(plan))
    return {"evidence_refs": [str(plan_path)]}


def engage_research(*, mission: Dict[str, Any], lane_name: str, model_hint: Optional[str], lane_index: int = 0) -> Dict[str, Any]:
    # Minimal engage summary—no external calls in this stub.
    query = _get_query(mission)
    metrics = {"notes_created": True, "llm_used": False}
    return {
        "actions": ["shaper_run", "synthesize_notes"],
        "metrics_summary": metrics,
        "llm": {
            "ok": False,
            "model": model_hint,
            "latency_ms": None,
            "status_code": None,
            "error": None,
            "content_preview": f"Synthesis for: {query}"[:120],
            "max_tokens": 0,
            "requested_model_hint": model_hint,
        },
    }


def yield_research(*, mission: Dict[str, Any], lane_name: str, model_hint: Optional[str], lane_index: int = 0, lane_dir: Path) -> Dict[str, Any]:
    query = _get_query(mission)
    summary = [
        f"# Yield Summary — {lane_name}",
        "",
        f"Prompt: {query}",
        "Deliverables:",
        "- Perception observations",
        "- React plan detail",
        "- Engage synthesis (if any)",
    ]
    ypath = lane_dir / "yield_notes.md"
    _safe_write(ypath, "\n".join(summary))
    return {"evidence_refs": [str(ypath)]}
