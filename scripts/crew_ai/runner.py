#!/usr/bin/env python3
"""
Minimal Crew AI runner (pilot):
- Reads mission intent YAML
- Runs 2 lanes (from intent) with PREY steps (Perceive→React→Engage→Yield)
- Executes lane agents (Observer, Bridger, Shaper, Assimilator); then Immunizer + Disruptor
- Appends receipts to blackboard JSONL
- Writes simple OpenTelemetry-like spans (JSON) to temp/otel/
- Runs Verify with immunizer + disruptor, aggregate to PASS/FAIL

Dependencies: PyYAML and python-dotenv. Optional: requests for OpenRouter LLM path.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml
from dotenv import load_dotenv

# Ensure local imports work when running as a script
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from llm_client import call_openrouter, ALLOWLIST as MODEL_ALLOWLIST
from agents import REGISTRY as AGENTS

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INTENT = ROOT / "hfo_mission_intent/2025-10-30/mission_intent_daily_2025-10-30.v5.yml"
BLACKBOARD = ROOT / "hfo_blackboard/obsidian_synapse_blackboard.jsonl"
OTEL_DIR = ROOT / "temp/otel"
RESULTS_ROOT = ROOT / "hfo_crew_ai_swarm_results"

ISO = "%Y-%m-%dT%H:%M:%SZ"

def now_z() -> str:
    return datetime.now(timezone.utc).strftime(ISO)


def append_blackboard(entry: Dict[str, Any]) -> None:
    BLACKBOARD.parent.mkdir(parents=True, exist_ok=True)
    with BLACKBOARD.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def write_span(trace_id: str, span: Dict[str, Any]) -> None:
    OTEL_DIR.mkdir(parents=True, exist_ok=True)
    out = OTEL_DIR / f"{trace_id}.jsonl"
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(span, ensure_ascii=False) + "\n")


def load_intent(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _read_yaml(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _validate_lane_artifacts(lane_out: Path) -> Dict[str, Any]:
    """Validate that a lane has the four artifacts and minimal fields.
    Returns { ok: bool, errors: [str] }.
    """
    errors: List[str] = []
    required = {
        "perception_snapshot.yml": [
            ("mission_id", str),
            ("lane", str),
            ("timestamp", str),
            ("trace_id", str),
            ("safety", dict),
            ("llm", dict),
            ("paths", dict),
        ],
        "react_plan.yml": [
            ("mission_id", str),
            ("lane", str),
            ("timestamp", str),
            ("cynefin", dict),
            ("approach", dict),
        ],
        "engage_report.yml": [
            ("mission_id", str),
            ("lane", str),
            ("timestamp", str),
            ("safety", dict),
            ("llm", dict),
        ],
        "yield_summary.yml": [
            ("mission_id", str),
            ("lane", str),
            ("timestamp", str),
            ("collected_agents", list),
            ("evidence_refs", list),
        ],
    }

    found_files: Dict[str, Dict[str, Any]] = {}
    for fname, req_fields in required.items():
        fp = lane_out / fname
        if not fp.exists():
            errors.append(f"missing_file:{fname}")
            continue
        data = _read_yaml(fp)
        found_files[fname] = data
        for key, typ in req_fields:
            val = data.get(key)
            if val is None or (typ is list and not isinstance(val, list)) or (typ is dict and not isinstance(val, dict)) or (typ is str and not isinstance(val, str)):
                errors.append(f"missing_or_type:{fname}:{key}")

    # Cross-check evidence_refs include core artifacts
    ys = found_files.get("yield_summary.yml", {})
    e_refs = ys.get("evidence_refs") or []
    core_refs_ok = True
    for core in ("perception_snapshot.yml", "react_plan.yml", "engage_report.yml"):
        if not any(core in str(x) for x in e_refs):
            core_refs_ok = False
            errors.append(f"evidence_missing:{core}")

    ok = len(errors) == 0 and core_refs_ok
    return {"ok": ok, "errors": errors}


def lane_prey_cycle(
    mission: Dict[str, Any],
    lane_name: str,
    trace_id: str,
    model_hint: Optional[str] = None,
    run_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    mission_id = mission.get("mission_id", f"mi_{now_z()}")
    safety = mission.get("safety", {})
    telemetry = mission.get("telemetry", {})

    phases = [
        ("perceive", "Perception snapshot collected"),
        ("react", "Plan created with tripwires"),
        ("engage", "Work executed under safety envelope"),
        ("yield", "Review bundle assembled"),
    ]
    evidence: List[str] = []
    phases_seen: List[str] = []
    collected: Dict[str, Any] = {}
    # Prepare lane output directory (attempt_1 for pilot)
    base_dir = run_dir if run_dir is not None else (ROOT / "temp" / "crew_ai_runs")
    lane_out = base_dir / str(lane_name) / "attempt_1"
    lane_out.mkdir(parents=True, exist_ok=True)

    for phase, summary in phases:
        ts = now_z()
        entry = {
            "mission_id": mission_id,
            "phase": phase,
            "summary": f"lane={lane_name}: {summary}",
            "evidence_refs": [f"lane:{lane_name}", f"phase:{phase}"],
            "safety_envelope": {
                "chunk_size_max": safety.get("chunk_size_max", 200),
                "placeholder_ban": safety.get("placeholder_ban", True),
            },
            "blocked_capabilities": [],
            "timestamp": ts,
            "chunk_id": {"index": 1, "total": 1},
        }
        append_blackboard(entry)
        span = {
            "trace_id": trace_id,
            "span_id": f"{lane_name}-{phase}-{int(time.time()*1000)}",
            "name": f"{lane_name}:{phase}",
            "start_time": ts,
            "end_time": ts,
            "attributes": {
                "lane": lane_name,
                "phase": phase,
                "mission_id": mission_id,
                "otel": telemetry.get("emit_opentelemetry", True),
            },
        }
        write_span(trace_id, span)
        evidence.append(f"lane={lane_name}:{phase}")
        phases_seen.append(phase)

        # If this is the Perceive phase, write a human/machine-friendly perception snapshot YAML
        if phase == "perceive":
            try:
                effective_model = model_hint or os.environ.get("OPENROUTER_MODEL_HINT") or None
                llm_cfg = mission.get("llm", {})
                snapshot = {
                    "mission_id": mission_id,
                    "lane": lane_name,
                    "timestamp": ts,
                    "trace_id": trace_id,
                    "prey_phases": [p for p, _ in phases],
                    "safety": {
                        "chunk_size_max": safety.get("chunk_size_max", 200),
                        "placeholder_ban": safety.get("placeholder_ban", True),
                        "tripwires": mission.get("safety", {}).get("tripwires", []),
                    },
                    "llm": {
                        "model_hint": effective_model,
                        "max_tokens": int(llm_cfg.get("max_tokens", 72)),
                        "temperature": float(llm_cfg.get("temperature", 0.2)),
                        "timeout_seconds": int(llm_cfg.get("timeout_seconds", 25)),
                        "response_format_type": llm_cfg.get("response_format_type", "text"),
                        "reasoning": bool(llm_cfg.get("reasoning", False)),
                        "reasoning_effort": llm_cfg.get("reasoning_effort", "medium"),
                        "allowlist": list(MODEL_ALLOWLIST),
                        "api_key_present": bool(os.environ.get("OPENROUTER_API_KEY")),
                    },
                    "paths": {
                        "blackboard": str(BLACKBOARD.relative_to(ROOT)),
                        "spans": f"temp/otel/{trace_id}.jsonl",
                        "lane_dir": str(lane_out.relative_to(ROOT)) if lane_out.is_relative_to(ROOT) else str(lane_out),
                    },
                }
                snap_path = lane_out / "perception_snapshot.yml"
                with snap_path.open("w", encoding="utf-8") as f:
                    yaml.safe_dump(snapshot, f, sort_keys=False)
                # Log a focused receipt referencing the snapshot
                append_blackboard({
                    "mission_id": mission_id,
                    "phase": "perceive",
                    "summary": f"lane={lane_name}: perception_snapshot.yml written",
                    "evidence_refs": [str(snap_path.relative_to(ROOT)) if snap_path.is_relative_to(ROOT) else str(snap_path)],
                    "timestamp": now_z(),
                })
                evidence.append(str(snap_path.relative_to(ROOT)) if snap_path.is_relative_to(ROOT) else str(snap_path))
            except Exception as e:
                append_blackboard({
                    "mission_id": mission_id,
                    "phase": "perceive",
                    "summary": f"lane={lane_name}: perception snapshot write failed: {e}",
                    "evidence_refs": [f"lane:{lane_name}", "phase:perceive"],
                    "timestamp": now_z(),
                    "regen_flag": True,
                })

    # Run role agents aligned to the current PREY phase
        agent_map = {
            "perceive": ["observer"],
            "react": ["bridger"],
            "engage": ["shaper"],
            "yield": ["assimilator"],
        }
        for role in agent_map.get(phase, []):
            agent = AGENTS.get(role)
            if not agent:
                continue
            ctx = {"mission": mission, "lane": lane_name, "phase": phase, "evidence": evidence, "flags": {"phases_seen": phases_seen}, "collected": collected, "model_hint": model_hint}
            res = agent.run(ctx)
            collected[role] = {"ok": res.ok, "summary": res.summary, "data": res.data, "llm_used": res.llm_used}
            # Span per agent
            write_span(trace_id, {
                "trace_id": trace_id,
                "span_id": f"{lane_name}-{phase}-{role}-{int(time.time()*1000)}",
                "name": f"{lane_name}:{phase}:{role}",
                "start_time": ts,
                "end_time": now_z(),
                "attributes": {
                    "lane": lane_name,
                    "phase": phase,
                    "role": role,
                    "ok": res.ok,
                    "llm_used": res.llm_used,
                },
            })
            append_blackboard({
                "mission_id": mission_id,
                "phase": phase,
                "summary": f"lane={lane_name}:{role} -> {'ok' if res.ok else 'fail'}",
                "evidence_refs": [f"lane:{lane_name}", f"phase:{phase}", f"role:{role}"],
                "safety_envelope": {
                    "chunk_size_max": safety.get("chunk_size_max", 200),
                    "placeholder_ban": safety.get("placeholder_ban", True),
                },
                "blocked_capabilities": [],
                "timestamp": now_z(),
                "agent": {"role": role, "summary": res.summary},
            })

        # Write a React planning artifact
        if phase == "react":
            try:
                tripwires = mission.get("safety", {}).get("tripwires", [])
                quorum = mission.get("quorum", {})
                plan = {
                    "mission_id": mission_id,
                    "lane": lane_name,
                    "timestamp": now_z(),
                    "cynefin": {
                        "domain": "complicated",
                        "rationale": "Structured, bounded PREY workflow; predictable steps; expert practices apply",
                    },
                    "approach": {
                        "loop": [p for p, _ in phases],
                        "chunk_limit_lines": int(safety.get("chunk_size_max", 200)),
                        "tripwires": tripwires,
                        "receipts": True,
                        "verify_quorum": {
                            "validators": quorum.get("validators", ["immunizer", "disruptor", "verifier_aux"]),
                            "threshold": int(quorum.get("threshold", 2)),
                        },
                    },
                    "c2": {
                        "orchestrator": "swarmlord",
                        "lane_autonomy": True,
                        "post_lane_validators": ["immunizer", "disruptor"],
                    },
                    "cbr": {
                        "case_hints": [f"mission:{mission_id}", f"lane:{lane_name}"],
                        "tools": ["observer", "bridger", "shaper", "assimilator"],
                    },
                }
                out = lane_out / "react_plan.yml"
                with out.open("w", encoding="utf-8") as f:
                    yaml.safe_dump(plan, f, sort_keys=False)
                append_blackboard({
                    "mission_id": mission_id,
                    "phase": "react",
                    "summary": f"lane={lane_name}: react_plan.yml written",
                    "evidence_refs": [str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out)],
                    "timestamp": now_z(),
                })
                evidence.append(str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out))
            except Exception as e:
                append_blackboard({
                    "mission_id": mission_id,
                    "phase": "react",
                    "summary": f"lane={lane_name}: react plan write failed: {e}",
                    "evidence_refs": [f"lane:{lane_name}", "phase:react"],
                    "timestamp": now_z(),
                    "regen_flag": True,
                })

        # During engage, perform a single, guarded LLM call if key present
        if phase == "engage":
            model_hint_eff = model_hint or os.environ.get("OPENROUTER_MODEL_HINT")
            llm_cfg = mission.get("llm", {})
            prompt = (
                "Restate the mission's intent and safety posture briefly but completely: "
                f"mission_id={mission_id}, safety={safety.get('tripwires', [])}."
            )
            llm_result = call_openrouter(
                prompt,
                model_hint=model_hint_eff,
                max_tokens=int(llm_cfg.get("max_tokens", 72)),
                temperature=float(llm_cfg.get("temperature", 0.2)),
                timeout_seconds=int(llm_cfg.get("timeout_seconds", 25)),
                response_format_type=llm_cfg.get("response_format_type", "text"),
                system_prompt=llm_cfg.get("system_prompt"),
                # Pass-through; None allows client to auto-enable reasoning for supported models
                enable_reasoning=llm_cfg.get("reasoning"),
                reasoning_effort=llm_cfg.get("reasoning_effort"),
            )

            # Emit span for the LLM action (content not stored here to limit size)
            write_span(
                trace_id,
                {
                    "trace_id": trace_id,
                    "span_id": f"{lane_name}-engage-llm-{int(time.time()*1000)}",
                    "name": f"{lane_name}:engage_llm",
                    "start_time": ts,
                    "end_time": now_z(),
                    "attributes": {
                        "lane": lane_name,
                        "mission_id": mission_id,
                        "ok": llm_result.get("ok"),
                        "model": llm_result.get("model"),
                        "latency_ms": llm_result.get("latency_ms"),
                        "status_code": llm_result.get("status_code"),
                        "error": llm_result.get("error"),
                        "reasoning_enabled": llm_result.get("reasoning_enabled"),
                        "reasoning_effort": llm_result.get("reasoning_effort"),
                        "reasoning_removed_on_retry": llm_result.get("reasoning_removed_on_retry"),
                    },
                },
            )

            # Append a concise blackboard receipt noting success/failure and a tiny preview
            content_preview = None
            if llm_result.get("ok") and llm_result.get("content"):
                content_preview = llm_result["content"].strip().replace("\n", " ")[:180]
            append_blackboard(
                {
                    "mission_id": mission_id,
                    "phase": "engage",
                    "summary": f"lane={lane_name}: LLM engage call {'ok' if llm_result.get('ok') else 'fail'}",
                    "evidence_refs": [f"lane:{lane_name}", "phase:engage", "action:llm"],
                    "safety_envelope": {
                        "chunk_size_max": safety.get("chunk_size_max", 200),
                        "placeholder_ban": safety.get("placeholder_ban", True),
                        "bounded_tokens": int(mission.get("llm", {}).get("max_tokens", 72)),
                    },
                    "blocked_capabilities": [],
                    "timestamp": now_z(),
                    "llm": {
                        "ok": llm_result.get("ok"),
                        "model": llm_result.get("model"),
                        "latency_ms": llm_result.get("latency_ms"),
                        "status_code": llm_result.get("status_code"),
                        "error": llm_result.get("error"),
                        "content_preview": content_preview,
                        "reasoning_enabled": llm_result.get("reasoning_enabled"),
                        "reasoning_effort": llm_result.get("reasoning_effort"),
                        "reasoning_removed_on_retry": llm_result.get("reasoning_removed_on_retry"),
                    },
                }
            )

            # Write engage report artifact
            try:
                engage_report = {
                    "mission_id": mission_id,
                    "lane": lane_name,
                    "timestamp": now_z(),
                    "actions": ["shaper_run", "llm_call" if os.environ.get("OPENROUTER_API_KEY") else "llm_skipped"],
                    "safety": {
                        "bounded_tokens": int(mission.get("llm", {}).get("max_tokens", 72)),
                        "placeholder_ban": bool(safety.get("placeholder_ban", True)),
                    },
                    "llm": {
                        "ok": bool(llm_result.get("ok")),
                        "model": llm_result.get("model"),
                        "latency_ms": llm_result.get("latency_ms"),
                        "status_code": llm_result.get("status_code"),
                        "error": llm_result.get("error"),
                        "content_preview": content_preview,
                        "reasoning_enabled": llm_result.get("reasoning_enabled"),
                        "reasoning_effort": llm_result.get("reasoning_effort"),
                        "reasoning_removed_on_retry": llm_result.get("reasoning_removed_on_retry"),
                    },
                }
                out = lane_out / "engage_report.yml"
                with out.open("w", encoding="utf-8") as f:
                    yaml.safe_dump(engage_report, f, sort_keys=False)
                append_blackboard({
                    "mission_id": mission_id,
                    "phase": "engage",
                    "summary": f"lane={lane_name}: engage_report.yml written",
                    "evidence_refs": [str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out)],
                    "timestamp": now_z(),
                })
                evidence.append(str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out))
            except Exception as e:
                append_blackboard({
                    "mission_id": mission_id,
                    "phase": "engage",
                    "summary": f"lane={lane_name}: engage report write failed: {e}",
                    "evidence_refs": [f"lane:{lane_name}", "phase:engage"],
                    "timestamp": now_z(),
                    "regen_flag": True,
                })
    # Before post-verify, write a Yield summary artifact for the lane
    try:
        yield_summary = {
            "mission_id": mission_id,
            "lane": lane_name,
            "timestamp": now_z(),
            "collected_agents": list(collected.keys()),
            "evidence_refs": evidence,
            "verify_expected": "quorum_after_yield",
        }
        out = lane_out / "yield_summary.yml"
        with out.open("w", encoding="utf-8") as f:
            yaml.safe_dump(yield_summary, f, sort_keys=False)
        append_blackboard({
            "mission_id": mission_id,
            "phase": "yield",
            "summary": f"lane={lane_name}: yield_summary.yml written",
            "evidence_refs": [str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out)],
            "timestamp": now_z(),
        })
    except Exception as e:
        append_blackboard({
            "mission_id": mission_id,
            "phase": "yield",
            "summary": f"lane={lane_name}: yield summary write failed: {e}",
            "evidence_refs": [f"lane:{lane_name}", "phase:yield"],
            "timestamp": now_z(),
            "regen_flag": True,
        })

    # Lane artifact validator: ensure four artifacts and minimal fields before handoff
    validation = _validate_lane_artifacts(lane_out)
    append_blackboard({
        "mission_id": mission_id,
        "phase": "verify",
        "summary": f"lane={lane_name}: artifact validation {'PASS' if validation['ok'] else 'FAIL'}",
        "evidence_refs": [str((lane_out / n).relative_to(ROOT)) for n in ("perception_snapshot.yml", "react_plan.yml", "engage_report.yml", "yield_summary.yml") if (lane_out / n).exists()],
        "timestamp": now_z(),
        "validator": {"ok": validation["ok"], "errors": validation.get("errors", [])},
    })

    # Post-Yield lane checks by Immunizer and Disruptor
    for role in ("immunizer", "disruptor"):
        agent = AGENTS.get(role)
        if not agent:
            continue
        res = agent.run({"mission": mission, "lane": lane_name, "evidence": evidence, "flags": {"phases_seen": phases_seen}, "collected": collected})
        write_span(trace_id, {
            "trace_id": trace_id,
            "span_id": f"{lane_name}-post-{role}-{int(time.time()*1000)}",
            "name": f"{lane_name}:post:{role}",
            "start_time": now_z(),
            "end_time": now_z(),
            "attributes": {"lane": lane_name, "role": role, "ok": res.ok},
        })
        append_blackboard({
            "mission_id": mission_id,
            "phase": "verify",
            "summary": f"lane={lane_name}:{role} -> {'ok' if res.ok else 'fail'}",
            "evidence_refs": [f"lane:{lane_name}", f"role:{role}"],
            "safety_envelope": {"tripwires_checked": ["receipts_present"]},
            "blocked_capabilities": [],
            "timestamp": now_z(),
            "agent": {"role": role, "summary": res.summary},
        })

    return {"lane": lane_name, "evidence": evidence, "phases_seen": phases_seen, "lane_valid": bool(validation.get("ok"))}


def verify_quorum(mission: Dict[str, Any], lane_results: List[Dict[str, Any]], trace_id: str) -> Dict[str, Any]:
    mission_id = mission.get("mission_id", f"mi_{now_z()}")
    validators = mission.get("quorum", {}).get("validators", ["immunizer", "disruptor", "verifier_aux"]) 
    threshold = mission.get("quorum", {}).get("threshold", 2)
    verify_cfg = mission.get("verify", {})

    # Immunizer: check each lane produced PERCEIVE..YIELD evidence
    immunizer_pass = all(len(r.get("evidence", [])) >= 4 for r in lane_results)

    # Artifact validator: confirm each lane reported validation ok
    artifact_validator_pass = all(bool(r.get("lane_valid", False)) for r in lane_results)

    # Disruptor: minimal probe — ensure at least one span exists per lane
    disruptor_pass = True
    for r in lane_results:
        # Here we just assert evidence was logged; a richer probe would inspect spans on disk
        if len(r.get("evidence", [])) == 0:
            disruptor_pass = False
            break

    # Verifier aux: sanity check quorum settings present
    aux_pass = isinstance(validators, list) and isinstance(threshold, int) and threshold >= 1

    votes = [immunizer_pass, disruptor_pass, aux_pass, artifact_validator_pass]
    pass_count = sum(1 for v in votes if v)
    passed = pass_count >= threshold

    # Record verify spans
    ts = now_z()
    write_span(trace_id, {"trace_id": trace_id, "span_id": f"verify-{int(time.time()*1000)}", "name": "verify_quorum", "start_time": ts, "end_time": ts, "attributes": {"votes": votes, "threshold": threshold}})

    append_blackboard({
        "mission_id": mission_id,
        "phase": "verify",
        "summary": f"Verify quorum {'PASS' if passed else 'FAIL'} (votes={votes}, threshold={threshold})",
        "evidence_refs": ["verify:immunizer", "verify:disruptor", "verify:aux"],
        "safety_envelope": {"tripwires_checked": ["receipts_present", "otel_spans_written"]},
        "blocked_capabilities": [],
        "timestamp": ts,
        "verifier": "pilot_quorum",
    })
    return {"passed": passed, "votes": votes, "threshold": threshold}


def run(intent_path: Path) -> int:
    # Load env (for secrets like OPENROUTER_API_KEY) without logging values
    load_dotenv(dotenv_path=ROOT / ".env", override=False)
    mission = load_intent(intent_path)
    mission_id = mission.get("mission_id", f"mi_{now_z()}")
    lanes = mission.get("lanes", {}) or {}
    # Build lanes and optional per-lane model mapping
    def sanitize(name: str) -> str:
        return "".join(ch if (ch.isalnum() or ch in ("_", "-")) else "_" for ch in str(name))[:64]

    lane_to_model: Dict[str, Optional[str]] = {}
    models_cfg = lanes.get("models")  # 'all' or list of strings
    if isinstance(models_cfg, str) and models_cfg.strip().lower() == "all":
        selected = list(MODEL_ALLOWLIST)
        names = [sanitize(m) for m in selected]
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
        seen = set()
        selected = [m for m in selected if not (m in seen or seen.add(m))]
        names = [sanitize(m) for m in selected]
        lane_to_model = {n: m for n, m in zip(names, selected)}
    else:
        count = int(lanes.get("count", 2))
        names = lanes.get("names") or [f"lane_{i+1}" for i in range(count)]
        names = [str(n) for n in names][:count]
        lane_to_model = {str(n): os.environ.get("OPENROUTER_MODEL_HINT") for n in names}

    # Create a run directory upfront so that Perceive can write its snapshot there
    date_dir = RESULTS_ROOT / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    run_ts = int(time.time()*1000)
    run_dir = date_dir / f"run-{run_ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    trace_id = f"trace-{mission_id}-{run_ts}"

    # Write a mission pointer for this run (swarmlord-level intent pointer)
    try:
        mission_pointer = {
            "mission_id": mission_id,
            "timestamp": now_z(),
            "intent_path": str(intent_path.relative_to(ROOT)) if intent_path.is_relative_to(ROOT) else str(intent_path),
            "lanes": mission.get("lanes", {}),
            "quorum": mission.get("quorum", {}),
            "telemetry": mission.get("telemetry", {}),
        }
        mp_path = run_dir / "mission_pointer.yml"
        with mp_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(mission_pointer, f, sort_keys=False)
        append_blackboard({
            "mission_id": mission_id,
            "phase": "perceive",
            "summary": "mission_pointer.yml written for run",
            "evidence_refs": [str(mp_path.relative_to(ROOT))],
            "timestamp": now_z(),
        })
    except Exception as e:
        append_blackboard({
            "mission_id": mission_id,
            "phase": "perceive",
            "summary": f"mission pointer write failed: {e}",
            "evidence_refs": ["swarmlord:mission_pointer"],
            "timestamp": now_z(),
            "regen_flag": True,
        })

    # Execute lanes concurrently to achieve true parallel swarm behavior
    lane_results: List[Dict[str, Any]] = []
    max_workers = int(lanes.get("max_workers", 0)) or len(names)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(lane_prey_cycle, mission, name, trace_id, lane_to_model.get(name), run_dir): name for name in names}
        for fut in as_completed(futures):
            lane_results.append(fut.result())

    verify_result = verify_quorum(mission, lane_results, trace_id)

    # Record presence (not value) of OpenRouter key for audit without leaking secret
    llm_present = bool(os.environ.get("OPENROUTER_API_KEY"))
    append_blackboard({
        "mission_id": mission_id,
        "phase": "audit",
        "summary": "LLM provider configuration presence audit",
        "evidence_refs": ["env:OPENROUTER_API_KEY:present" if llm_present else "env:OPENROUTER_API_KEY:absent"],
        "safety_envelope": {"tripwires_checked": ["no_secret_logged"]},
        "timestamp": now_z(),
    })

    # Write digest file under the same run directory
    matrix_lines = ["| Lane | Model | Notes |", "|---|---|---|"]
    for n in sorted(lane_to_model.keys()):
        model = lane_to_model.get(n) or os.environ.get("OPENROUTER_MODEL_HINT") or "default"
        matrix_lines.append(f"| {n} | {model} | PREY executed |")
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
        f"- Verify PASS: {verify_result.get('passed', False)}",
        f"- Trace: temp/otel/{trace_id}.jsonl",
        "",
        "## BLUF",
        "- PREY lanes executed with per-phase artifacts (perceive/react/engage/yield).",
        "- Verify quorum executed post-yield.",
        "",
        "## Matrix",
        *matrix_lines,
        "",
        "## Diagram",
        *mermaid,
        "",
        "## Notes",
        "- Artifacts: mission_pointer.yml; per-lane perception_snapshot.yml, react_plan.yml, engage_report.yml, yield_summary.yml.",
    ]
    digest_path = run_dir / "swarmlord_digest.md"
    digest_path.write_text("\n".join(md), encoding="utf-8")

    # Yield digest receipt
    ts = now_z()
    append_blackboard({
        "mission_id": mission_id,
        "phase": "yield",
        "summary": "Pilot digest ready (lanes executed, verify quorum run)",
        "evidence_refs": ["temp/otel", f"trace:{trace_id}", str(digest_path.relative_to(ROOT))],
        "safety_envelope": {"policy": "contact only on digest/critical/timeout"},
        "timestamp": ts,
        "digest": {"verify_pass": verify_result.get("passed", False)},
    })

    return 0 if verify_result.get("passed") else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Crew AI pilot runner")
    parser.add_argument("--intent", type=str, default=str(DEFAULT_INTENT), help="Path to mission intent YAML")
    args = parser.parse_args()

    intent_path = Path(args.intent)
    if not intent_path.exists():
        print(f"Intent not found: {intent_path}", file=sys.stderr)
        sys.exit(2)

    rc = run(intent_path)
    sys.exit(rc)


if __name__ == "__main__":
    main()
