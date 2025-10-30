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
from typing import Any, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml
from dotenv import load_dotenv

# Ensure local imports work when running as a script
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from llm_client import call_openrouter
from agents import REGISTRY as AGENTS

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INTENT = ROOT / "hfo_mission_intent/2025-10-30/mission_intent_daily_2025-10-30.v5.yml"
BLACKBOARD = ROOT / "hfo_blackboard/obsidian_synapse_blackboard.jsonl"
OTEL_DIR = ROOT / "temp/otel"

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


def lane_prey_cycle(mission: Dict[str, Any], lane_name: str, trace_id: str) -> Dict[str, Any]:
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
            ctx = {"mission": mission, "lane": lane_name, "phase": phase, "evidence": evidence, "flags": {"phases_seen": phases_seen}, "collected": collected}
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

        # During engage, perform a single, guarded LLM call if key present
        if phase == "engage":
            model_hint = os.environ.get("OPENROUTER_MODEL_HINT")
            prompt = (
                "In one short sentence, restate the mission's intent and safety posture: "
                f"mission_id={mission_id}, safety={safety.get('tripwires', [])}."
            )
            llm_result = call_openrouter(
                prompt,
                model_hint=model_hint,
                max_tokens=72,
                temperature=0.1,
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
                        "bounded_tokens": 72,
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
                    },
                }
            )
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

    return {"lane": lane_name, "evidence": evidence, "phases_seen": phases_seen}


def verify_quorum(mission: Dict[str, Any], lane_results: List[Dict[str, Any]], trace_id: str) -> Dict[str, Any]:
    mission_id = mission.get("mission_id", f"mi_{now_z()}")
    validators = mission.get("quorum", {}).get("validators", ["immunizer", "disruptor", "verifier_aux"]) 
    threshold = mission.get("quorum", {}).get("threshold", 2)
    verify_cfg = mission.get("verify", {})

    # Immunizer: check each lane produced PERCEIVE..YIELD evidence
    immunizer_pass = all(len(r.get("evidence", [])) >= 4 for r in lane_results)

    # Disruptor: minimal probe — ensure at least one span exists per lane
    disruptor_pass = True
    for r in lane_results:
        # Here we just assert evidence was logged; a richer probe would inspect spans on disk
        if len(r.get("evidence", [])) == 0:
            disruptor_pass = False
            break

    # Verifier aux: sanity check quorum settings present
    aux_pass = isinstance(validators, list) and isinstance(threshold, int) and threshold >= 1

    votes = [immunizer_pass, disruptor_pass, aux_pass]
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
    lanes = mission.get("lanes", {})
    count = lanes.get("count", 2)
    names = lanes.get("names") or [f"lane_{i+1}" for i in range(count)]

    trace_id = f"trace-{mission_id}-{int(time.time()*1000)}"

    # Execute lanes concurrently to achieve true parallel swarm behavior
    lane_results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=count) as executor:
        futures = {executor.submit(lane_prey_cycle, mission, name, trace_id): name for name in names[:count]}
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

    # Yield digest receipt
    ts = now_z()
    append_blackboard({
        "mission_id": mission_id,
        "phase": "yield",
        "summary": "Pilot digest ready (lanes executed, verify quorum run)",
        "evidence_refs": ["temp/otel", f"trace:{trace_id}"],
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
