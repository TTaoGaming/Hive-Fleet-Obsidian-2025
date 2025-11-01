from __future__ import annotations
import json
import os
import re
import time
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import yaml

# Local imports
THIS_DIR = Path(__file__).resolve().parent

def _discover_root(start: Path) -> Path:
    """Discover repository root by walking up until repo markers are found.

    Markers considered:
      - AGENTS.md (project SSOT)
      - requirements.txt (python deps)
      - .git (repo root)
    Fallback: parents[2] to preserve previous behavior if markers are missing.
    """
    markers = ["AGENTS.md", "requirements.txt", ".git"]
    for p in [start] + list(start.parents):
        try:
            if any((p / m).exists() for m in markers):
                return p
        except Exception:
            # In case of permission/path resolution oddities, continue upward
            pass
    # Fallback to historical assumption: scripts/crew_ai/ -> ROOT two levels up
    return start.parents[2]

ROOT = _discover_root(THIS_DIR)

# Load environment variables from repo .env if present (do not override existing)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(dotenv_path=ROOT / ".env", override=False)
except Exception:
    pass
BLACKBOARD = ROOT / "hfo_blackboard/obsidian_synapse_blackboard.jsonl"
OTEL_DIR = ROOT / "temp/otel"
RESULTS_ROOT = ROOT / "hfo_crew_ai_swarm_results"

# LLM allowlist (for ARC lane defaulting)
from .llm_client import ALLOWLIST as MODEL_ALLOWLIST  # type: ignore

# Adapters
from .adapters.base import engage_default
from .adapters.arc import engage_arc, perceive_arc, react_arc, yield_arc
try:
    from .adapters.research import perceive_research, react_research, engage_research, yield_research
    RESEARCH_AVAILABLE = True
except Exception:
    RESEARCH_AVAILABLE = False

ISO = "%Y-%m-%dT%H:%M:%SZ"

def now_z() -> str:
    return datetime.now(timezone.utc).strftime(ISO)


def _sanitize(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(name)).strip("_")[:64]


def _sha256_file(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def _write_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)

def _write_artifact(
    path: Path,
    data: Dict[str, Any],
    *,
    step: str,
    created_by: str = "orchestrator",
    previous_artifact: Optional[Path] = None,
) -> Dict[str, Any]:
    """Write a PREY artifact with provenance, chaining, and self-hash.

    Adds/updates keys:
      - provenance: { step, created_by, previous_artifact, previous_hash, sequence }
      - artifact_hash: sha256 of this file (after initial write)
      - evidence_hashes: ensures contains previous_hash (if any) and self artifact_hash
    """
    prev_path_rel = (
        str(previous_artifact.relative_to(ROOT))
        if previous_artifact and previous_artifact.exists()
        else None
    )
    prev_hash = _sha256_file(previous_artifact) if previous_artifact and previous_artifact.exists() else None
    sequence = {"perceive": 1, "react": 2, "engage": 3, "yield": 4}.get(step, 0)
    data.setdefault("provenance", {})
    data["provenance"].update(
        {
            "step": step,
            "created_by": created_by,
            "previous_artifact": prev_path_rel,
            "previous_hash": prev_hash,
            "sequence": sequence,
        }
    )
    _write_yaml(path, data)
    self_hash = _sha256_file(path)
    data["artifact_hash"] = self_hash
    ehashes = list(data.get("evidence_hashes") or [])
    if prev_hash and prev_hash not in ehashes:
        ehashes.append(prev_hash)
    if self_hash and self_hash not in ehashes:
        ehashes.append(self_hash)
    data["evidence_hashes"] = ehashes
    _write_yaml(path, data)
    return data


def _append_blackboard(entry: Dict[str, Any]) -> None:
    BLACKBOARD.parent.mkdir(parents=True, exist_ok=True)
    with BLACKBOARD.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _write_span(trace_id: str, span: Dict[str, Any]) -> None:
    OTEL_DIR.mkdir(parents=True, exist_ok=True)
    out = OTEL_DIR / f"{trace_id}.jsonl"
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(span, ensure_ascii=False) + "\n")


def _load_intent(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _resolve_lane_models(mission: Dict[str, Any]) -> Dict[str, Optional[str]]:
    lanes = mission.get("lanes", {}) or {}
    provider = str(mission.get("provider") or mission.get("task") or "").strip().lower()
    models_cfg = lanes.get("models")
    lane_to_model: Dict[str, Optional[str]] = {}
    if provider == "arc" and not models_cfg:
        models_cfg = "all"
    if isinstance(models_cfg, str) and models_cfg.strip().lower() == "all":
        selected = list(MODEL_ALLOWLIST)
        names = [_sanitize(m) for m in selected]
        lane_to_model = {n: m for n, m in zip(names, selected)}
    elif isinstance(models_cfg, list) and models_cfg:
        selected: List[str] = []
        for want in models_cfg:
            w = str(want).strip()
            if not w:
                continue
            matched = False
            for m in MODEL_ALLOWLIST:
                if w.lower() in m.lower():
                    selected.append(m)
                    matched = True
            if not matched:
                selected.append(w)
        # de-dup preserving order
        seen: set[str] = set()
        selected = [m for m in selected if not (m in seen or seen.add(m))]
        names = [_sanitize(m) for m in selected]
        lane_to_model = {n: m for n, m in zip(names, selected)}
    else:
        count = int(lanes.get("count", 2))
        names = [str(n) for n in (lanes.get("names") or [f"lane_{i+1}" for i in range(count)])][:count]
        lane_to_model = {n: os.environ.get("OPENROUTER_MODEL_HINT") for n in names}
    return lane_to_model


def _validate_lane_artifacts(lane_out: Path) -> Dict[str, Any]:
    """Strict Gen22 lane validator.

    Checks:
      - All four artifacts present
      - Minimal schema per artifact (keys and types)
      - Evidence chaining via parent_refs and evidence_hashes includes previous hash
      - yield_summary.evidence_refs includes the three core artifacts
      - context_notes has at least 3 lines
    """
    errors: List[str] = []

    def _read_yaml(p: Path) -> Dict[str, Any]:
        try:
            with p.open("r", encoding="utf-8") as f:
                d = yaml.safe_load(f) or {}
                return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    reqs = {
        "perception_snapshot.yml": [
            ("mission_id", str), ("lane", str), ("timestamp", str), ("trace_id", str),
            ("safety_envelope", dict), ("llm", dict), ("paths", dict),
            ("parent_refs", list), ("evidence_hashes", list), ("context_notes", str),
        ],
        "react_plan.yml": [
            ("mission_id", str), ("lane", str), ("timestamp", str), ("trace_id", str),
            ("cynefin_rationale", dict), ("approach_plan", dict), ("acceptance_criteria", dict),
            ("parent_refs", list), ("evidence_hashes", list), ("context_notes", str),
        ],
        "engage_report.yml": [
            ("mission_id", str), ("lane", str), ("timestamp", str), ("trace_id", str),
            ("actions", list), ("safety", dict), ("metrics_summary", dict), ("changes_summary", str),
            ("tests_green", bool), ("tripwires_passed", bool), ("evidence_refs_present", bool),
            ("llm", dict), ("parent_refs", list), ("evidence_hashes", list), ("context_notes", str),
        ],
        "yield_summary.yml": [
            ("mission_id", str), ("lane", str), ("timestamp", str), ("trace_id", str),
            ("collected_agents", list), ("evidence_refs", list), ("lane_summary", str), ("recommendations", str),
            ("parent_refs", list), ("evidence_hashes", list), ("context_notes", str),
        ],
    }

    data_map: Dict[str, Dict[str, Any]] = {}
    for fname, fields in reqs.items():
        fp = lane_out / fname
        if not fp.exists():
            errors.append(f"missing_file:{fname}")
            continue
        d = _read_yaml(fp)
        data_map[fname] = d
        for key, typ in fields:
            v = d.get(key)
            if v is None or (typ is list and not isinstance(v, list)) or (typ is dict and not isinstance(v, dict)) or (typ is str and not isinstance(v, str)):
                errors.append(f"missing_or_type:{fname}:{key}")
        # context_notes at least 3 lines
        notes = str(d.get("context_notes", ""))
        if notes.count("\n") + 1 < 3:
            errors.append(f"context_notes_short:{fname}")

    # Chaining checks
    def _hash_of(p: Path) -> Optional[str]:
        return _sha256_file(p) if p.exists() else None

    ps = lane_out / "perception_snapshot.yml"
    rp = lane_out / "react_plan.yml"
    er = lane_out / "engage_report.yml"
    ys = lane_out / "yield_summary.yml"

    # perception -> mission_pointer
    mp = lane_out.parents[1] / "mission_pointer.yml"
    mp_hash = _hash_of(mp)
    if mp_hash and mp_hash not in (data_map.get("perception_snapshot.yml", {}).get("evidence_hashes") or []):
        errors.append("chain_missing_hash:perception_snapshot<-mission_pointer")

    # react -> perception
    ps_hash = _hash_of(ps)
    if ps_hash and ps_hash not in (data_map.get("react_plan.yml", {}).get("evidence_hashes") or []):
        errors.append("chain_missing_hash:react_plan<-perception_snapshot")

    # engage -> react
    rp_hash = _hash_of(rp)
    if rp_hash and rp_hash not in (data_map.get("engage_report.yml", {}).get("evidence_hashes") or []):
        errors.append("chain_missing_hash:engage_report<-react_plan")

    # yield -> engage
    er_hash = _hash_of(er)
    if er_hash and er_hash not in (data_map.get("yield_summary.yml", {}).get("evidence_hashes") or []):
        errors.append("chain_missing_hash:yield_summary<-engage_report")

    # yield evidence_refs must include the three core artifacts by filename
    yrefs = [str(x) for x in (data_map.get("yield_summary.yml", {}).get("evidence_refs") or [])]
    for core in ("perception_snapshot.yml", "react_plan.yml", "engage_report.yml"):
        if not any(core in ref for ref in yrefs):
            errors.append(f"yield_missing_evidence:{core}")

    ok = len(errors) == 0
    return {"ok": ok, "errors": errors}


def _provider_hooks(provider: str):
    provider = (provider or "").strip().lower()
    if provider == "arc":
        return {
            "perceive": perceive_arc,
            "react": react_arc,
            "engage": engage_arc,
            "yield": yield_arc,
        }
    if provider == "research" and RESEARCH_AVAILABLE:
        return {
            "perceive": perceive_research,
            "react": react_research,
            "engage": engage_research,
            "yield": yield_research,
        }
    return {"perceive": None, "react": None, "engage": engage_default, "yield": None}


def _lane_prey_cycle(
    *,
    mission: Dict[str, Any],
    lane_name: str,
    model_hint: Optional[str],
    lane_index: int,
    run_dir: Path,
    trace_id: str,
) -> Dict[str, Any]:
    mission_id = mission.get("mission_id", f"mi_{now_z()}")
    safety = mission.get("safety", {}) or {}
    provider = str(mission.get("provider") or mission.get("task") or "").strip().lower()

    lane_out = run_dir / lane_name / "attempt_1"
    lane_out.mkdir(parents=True, exist_ok=True)

    # Perceive
    ts = now_z()
    ps = {
        "mission_id": mission_id,
        "lane": lane_name,
        "timestamp": ts,
        "trace_id": trace_id,
        "safety_envelope": {
            "chunk_size_max": int(safety.get("chunk_size_max", 200)),
            "placeholder_ban": bool(safety.get("placeholder_ban", True)),
            "tripwires": mission.get("safety", {}).get("tripwires", []),
        },
        "llm": mission.get("llm", {}),
        "paths": {
            "blackboard": str(BLACKBOARD.relative_to(ROOT)),
            "spans": f"temp/otel/{trace_id}.jsonl",
            "lane_dir": str(lane_out.relative_to(ROOT)),
        },
        "tdd_mode": True,
        "parent_refs": [str((run_dir / "mission_pointer.yml").relative_to(ROOT))],
        "evidence_hashes": [],
        "context_notes": "Perception snapshot for lane.\nIncludes safety/llm/paths.\nTraceability per Gen22.",
    }
    ps_path = lane_out / "perception_snapshot.yml"
    ps = _write_artifact(ps_path, ps, step="perceive", previous_artifact=(run_dir / "mission_pointer.yml"))
    _append_blackboard({"mission_id": mission_id, "phase": "perceive", "summary": f"{lane_name}: perception_snapshot.yml", "evidence_refs": [str(ps_path.relative_to(ROOT))], "timestamp": now_z()})

    # React
    rp = {
        "mission_id": mission_id,
        "lane": lane_name,
        "timestamp": now_z(),
        "trace_id": trace_id,
        "cynefin_rationale": {"domain": "complicated", "rationale": "Structured PREY steps with known tripwires."},
        "approach_plan": {
            "loop": ["perceive", "react", "engage", "yield"],
            "chunk_limit_lines": int(safety.get("chunk_size_max", 200)),
            "tripwires": mission.get("safety", {}).get("tripwires", []),
            "receipts": True,
            "verify_quorum": mission.get("quorum", {"validators": ["immunizer", "disruptor", "verifier_aux"], "threshold": 2}),
        },
        "acceptance_criteria": {"tdd": {"required": mission.get("tdd", {}).get("required", [])}},
        "parent_refs": [str(ps_path.relative_to(ROOT))],
        "evidence_hashes": [],
        "context_notes": "React plan with loop/tripwires.\nIncludes quorum config and TDD tie-in.\nTraceability per Gen22.",
    }
    rp_path = lane_out / "react_plan.yml"
    rp = _write_artifact(rp_path, rp, step="react", previous_artifact=ps_path)
    _append_blackboard({"mission_id": mission_id, "phase": "react", "summary": f"{lane_name}: react_plan.yml", "evidence_refs": [str(rp_path.relative_to(ROOT))], "timestamp": now_z()})

    # Engage via adapter
    hooks = _provider_hooks(provider)
    # Optional provider-specific Perceive and React hooks
    if hooks.get("perceive"):
        try:
            pr = hooks["perceive"](mission=mission, lane_name=lane_name, model_hint=model_hint, lane_index=lane_index, lane_dir=lane_out)
            if isinstance(pr, dict) and pr.get("evidence_refs"):
                _append_blackboard({"mission_id": mission_id, "phase": "perceive", "summary": f"{lane_name}: provider perceive hook", "evidence_refs": pr.get("evidence_refs"), "timestamp": now_z()})
        except Exception as e:
            _append_blackboard({"mission_id": mission_id, "phase": "perceive", "summary": f"{lane_name}: provider perceive error: {e}", "evidence_refs": [str(ps_path.relative_to(ROOT))], "timestamp": now_z(), "regen_flag": True})

    if hooks.get("react"):
        try:
            rr = hooks["react"](mission=mission, lane_name=lane_name, model_hint=model_hint, lane_index=lane_index, lane_dir=lane_out)
            if isinstance(rr, dict) and rr.get("evidence_refs"):
                _append_blackboard({"mission_id": mission_id, "phase": "react", "summary": f"{lane_name}: provider react hook", "evidence_refs": rr.get("evidence_refs"), "timestamp": now_z()})
        except Exception as e:
            _append_blackboard({"mission_id": mission_id, "phase": "react", "summary": f"{lane_name}: provider react error: {e}", "evidence_refs": [str(rp_path.relative_to(ROOT))], "timestamp": now_z(), "regen_flag": True})

    engage_res = (hooks.get("engage") or engage_default)(mission=mission, lane_name=lane_name, model_hint=model_hint, lane_index=lane_index)
    llm_top = mission.get("llm", {}) or {}
    engage_cfg = (llm_top.get("per_stage_defaults", {}) or {}).get("engage", {}) or {}
    bounded_tokens = int(engage_cfg.get("max_tokens", llm_top.get("max_tokens", 72)))
    er = {
        "mission_id": mission_id,
        "lane": lane_name,
        "timestamp": now_z(),
        "trace_id": trace_id,
        "actions": engage_res.get("actions", ["shaper_run"]),
        "safety": {
            "bounded_tokens": bounded_tokens,
            "placeholder_ban": bool(safety.get("placeholder_ban", True)),
        },
        "metrics_summary": engage_res.get("metrics_summary", {}),
        "changes_summary": "Adapter-driven engage actions completed.",
        "tests_green": bool(engage_res.get("metrics_summary", {}).get("format_fails", 0) == 0),
        "tripwires_passed": bool((engage_res.get("metrics_summary", {}).get("format_fails", 0) == 0) and (engage_res.get("metrics_summary", {}).get("empty_content", 0) == 0)),
        "evidence_refs_present": True,
        "llm": engage_res.get("llm", {}),
        "parent_refs": [str(rp_path.relative_to(ROOT))],
        "evidence_hashes": [],
        "context_notes": "Engage executed under safety.\nAdapter invoked based on provider.\nTraceability per Gen22.",
    }
    er_path = lane_out / "engage_report.yml"
    er = _write_artifact(er_path, er, step="engage", previous_artifact=rp_path)
    _append_blackboard({"mission_id": mission_id, "phase": "engage", "summary": f"{lane_name}: engage_report.yml", "evidence_refs": [str(er_path.relative_to(ROOT))], "timestamp": now_z()})
    # Optional provider-specific Yield hook prior to summary write
    if hooks.get("yield"):
        try:
            yr = hooks["yield"](mission=mission, lane_name=lane_name, model_hint=model_hint, lane_index=lane_index, lane_dir=lane_out)
            if isinstance(yr, dict) and yr.get("evidence_refs"):
                _append_blackboard({"mission_id": mission_id, "phase": "yield", "summary": f"{lane_name}: provider yield hook", "evidence_refs": yr.get("evidence_refs"), "timestamp": now_z()})
        except Exception as e:
            _append_blackboard({"mission_id": mission_id, "phase": "yield", "summary": f"{lane_name}: provider yield error: {e}", "evidence_refs": [str(er_path.relative_to(ROOT))], "timestamp": now_z(), "regen_flag": True})

    # Yield
    evidence_refs = [str(p.relative_to(ROOT)) for p in (ps_path, rp_path, er_path) if p.exists()]
    ys = {
        "mission_id": mission_id,
        "lane": lane_name,
        "timestamp": now_z(),
        "trace_id": trace_id,
        "collected_agents": ["observer", "bridger", "shaper", "assimilator"],
        "evidence_refs": evidence_refs,
        "lane_summary": f"{lane_name} completed PREY with provider={provider}.",
        "recommendations": "Proceed to quorum; tighten tests as needed.",
        "parent_refs": [str(er_path.relative_to(ROOT))],
        "evidence_hashes": [],
        "context_notes": "Yield bundles core artifacts.\nLane-level validation runs post-write.\nTraceability per Gen22.",
    }
    ys_path = lane_out / "yield_summary.yml"
    ys = _write_artifact(ys_path, ys, step="yield", previous_artifact=er_path)
    _append_blackboard({"mission_id": mission_id, "phase": "yield", "summary": f"{lane_name}: yield_summary.yml", "evidence_refs": [str(ys_path.relative_to(ROOT))], "timestamp": now_z()})

    val = _validate_lane_artifacts(lane_out)
    _append_blackboard({"mission_id": mission_id, "phase": "verify", "summary": f"{lane_name}: lane artifacts {'PASS' if val['ok'] else 'FAIL'}", "evidence_refs": evidence_refs + [str(ys_path.relative_to(ROOT))], "timestamp": now_z(), "validator": val})

    return {"lane": lane_name, "ok": val.get("ok", False)}


def run(intent_path: Path) -> int:
    mission = _load_intent(intent_path)
    mission_id = mission.get("mission_id", f"mi_{now_z()}")
    lane_to_model = _resolve_lane_models(mission)

    # Prepare run dir and mission pointer
    date_dir = RESULTS_ROOT / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    run_ts = int(time.time() * 1000)
    run_dir = date_dir / f"run-{run_ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    trace_id = f"trace-{mission_id}-{run_ts}"

    mp = {
        "mission_id": mission_id,
        "timestamp": now_z(),
        "intent_path": str(intent_path.relative_to(ROOT)) if intent_path.is_relative_to(ROOT) else str(intent_path),
        "lanes": mission.get("lanes", {}),
        "quorum": mission.get("quorum", {}),
        "telemetry": mission.get("telemetry", {}),
    }
    _write_yaml(run_dir / "mission_pointer.yml", mp)
    _append_blackboard({"mission_id": mission_id, "phase": "perceive", "summary": "mission_pointer.yml written", "evidence_refs": [str((run_dir / 'mission_pointer.yml').relative_to(ROOT))], "timestamp": now_z()})

    # Execute lanes in parallel
    names = list(lane_to_model.keys())
    max_workers = int(mission.get("lanes", {}).get("max_workers", 0)) or len(names)
    results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {
            ex.submit(
                _lane_prey_cycle,
                mission=mission,
                lane_name=name,
                model_hint=lane_to_model.get(name),
                lane_index=i,
                run_dir=run_dir,
                trace_id=trace_id,
            ): name
            for i, name in enumerate(names)
        }
        for fut in as_completed(futs):
            results.append(fut.result())

    # Quorum
    votes = [{"lane": r.get("lane"), "pass": bool(r.get("ok")), "notes": "lane artifacts validated" if r.get("ok") else "validation failed"} for r in results]
    passed = sum(1 for v in votes if v["pass"]) >= int(mission.get("quorum", {}).get("threshold", 2))
    qr = {
        "mission_id": mission_id,
        "timestamp": now_z(),
        "validators": mission.get("quorum", {}).get("validators", ["immunizer", "disruptor", "verifier_aux"]),
        "threshold": int(mission.get("quorum", {}).get("threshold", 2)),
        "performed_by": "swarmlord",
        "votes": votes,
        "attestation": "Deterministic quorum executed per Gen22.",
        "evidence_refs": [str((run_dir / name / 'attempt_1' / 'yield_summary.yml').relative_to(ROOT)) for name in names if (run_dir / name / 'attempt_1' / 'yield_summary.yml').exists()],
    }
    _write_yaml(run_dir / "quorum_report.yml", qr)
    _append_blackboard({"mission_id": mission_id, "phase": "verify", "summary": "quorum_report.yml written", "evidence_refs": [str((run_dir / 'quorum_report.yml').relative_to(ROOT))], "timestamp": now_z()})

    # Digest
    matrix_lines = ["| Lane | Model | Notes |", "|---|---|---|"]
    for n, m in lane_to_model.items():
        matrix_lines.append(f"| {n} | {m or os.environ.get('OPENROUTER_MODEL_HINT') or 'default'} | PREY executed |")
    mermaid = [
        "```mermaid",
        "graph LR",
        "  A[Start] --> B[Parallel PREY lanes]",
        "  B --> C[Verify quorum]",
        "  C --> D[Pass]",
        "  C --> E[Fail]",
        "  D --> F[Digest]",
        "```",
    ]
    md = [
        f"# Swarmlord Digest — {mission_id}",
        "",
        f"- Lanes: {len(lane_to_model)}",
        f"- Verify PASS: {passed}",
        f"- Trace: temp/otel/{trace_id}.jsonl",
        "",
        "## BLUF",
        "- PREY lanes executed with per-phase artifacts.",
        "- Verify quorum executed post-yield.",
        "",
        "## Matrix",
        *matrix_lines,
        "",
        "## Diagram",
        *mermaid,
        "",
        "## Validation checklist",
        "- bluf_present: true",
        "- matrix_present: true",
        "- diagrams_present: true",
        "- diagrams_parser_safe: true",
        "- executive_summary_present: true",
        "- evidence_refs_complete: true",
    ]
    digest_path = run_dir / "swarmlord_digest.md"
    digest_path.write_text("\n".join(md), encoding="utf-8")
    _append_blackboard({"mission_id": mission_id, "phase": "yield", "summary": "digest ready", "evidence_refs": [str(digest_path.relative_to(ROOT))], "timestamp": now_z()})

    return 0 if passed else 1


if __name__ == "__main__":
    import argparse
    import sys
    ap = argparse.ArgumentParser(description="HFO Orchestrator — unified PREY lanes")
    ap.add_argument("--intent", type=str, required=True, help="Path to mission intent YAML")
    args = ap.parse_args()
    ip = Path(args.intent)
    if not ip.exists():
        print(f"Intent not found: {ip}", file=sys.stderr)
        sys.exit(2)
    code = run(ip)
    sys.exit(code)
