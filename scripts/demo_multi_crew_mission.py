#!/usr/bin/env python3
"""
Demo mission for multi-crew orchestration system.

This demonstrates the disperse-converge pattern with a simple goal
that can be achieved without making actual LLM API calls.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from blackboard_logger import append_receipt


def demo_prey_lane(lane_id: str, mission_goal: str, mode: str = "explore") -> Dict[str, Any]:
    """
    Simulate a PREY lane without LLM calls.
    
    In production, this would use CrewAI agents.
    For demo, we simulate the PREY cycle outputs.
    """
    mission_id = "demo_mission_2025-10-30"
    safety = {"chunk_size_max": 200, "line_target_min": 0}
    
    # Perceive
    append_receipt(
        mission_id=mission_id,
        phase="perceive",
        summary=f"Lane {lane_id} ({mode}): Sensing mission context",
        evidence_refs=[f"lane:{lane_id}", "mission_goal.txt"],
        safety_envelope=safety,
        blocked_capabilities=[],
    )
    
    perception = {
        "context": f"Lane {lane_id} analyzing: {mission_goal[:50]}...",
        "mode": mode,
        "constraints": ["chunk_limit:200", "placeholder_ban", "canary_first"],
    }
    
    # React
    append_receipt(
        mission_id=mission_id,
        phase="react",
        summary=f"Lane {lane_id} ({mode}): Planning approach",
        evidence_refs=[f"lane:{lane_id}", "plan.json"],
        safety_envelope=safety,
        blocked_capabilities=[],
    )
    
    plan = {
        "approach": "explore diverse solutions" if mode == "explore" else "exploit proven patterns",
        "chunks": 2,
        "tripwires": ["line_count", "placeholder_scan", "tests_green"],
    }
    
    # Engage
    append_receipt(
        mission_id=mission_id,
        phase="engage",
        summary=f"Lane {lane_id} ({mode}): Executing within safety envelope",
        evidence_refs=[f"lane:{lane_id}", "output.txt:1-50"],
        safety_envelope=safety,
        blocked_capabilities=[],
    )
    
    execution = {
        "actions": [
            f"Analyzed repository structure" if mode == "explore" else "Applied standard pattern",
            f"Generated {mode}-focused approach",
        ],
        "metrics": {
            "lines_written": 45,
            "tests_added": 2 if mode == "explore" else 1,
            "tripwires_hit": 0,
        },
    }
    
    # Yield
    append_receipt(
        mission_id=mission_id,
        phase="yield",
        summary=f"Lane {lane_id} ({mode}): Review bundle ready",
        evidence_refs=[f"lane:{lane_id}", "review_bundle.json"],
        safety_envelope=safety,
        blocked_capabilities=[],
    )
    
    return {
        "lane_id": lane_id,
        "mode": mode,
        "perception": perception,
        "plan": plan,
        "execution": execution,
        "success": True,
    }


def demo_verify_quorum(lane_results: List[Dict[str, Any]]) -> bool:
    """
    Simulate verification quorum without LLM calls.
    
    Checks:
    - All lanes completed successfully
    - Evidence present
    - Safety envelope respected
    """
    mission_id = "demo_mission_2025-10-30"
    safety = {"chunk_size_max": 200, "line_target_min": 0}
    
    # Immunizer check
    immunizer_pass = all(r["success"] for r in lane_results)
    append_receipt(
        mission_id=mission_id,
        phase="verify",
        summary=f"Immunizer: {'PASS' if immunizer_pass else 'FAIL'} - All lanes successful",
        evidence_refs=["immunizer_report.json"],
        safety_envelope=safety,
        blocked_capabilities=[],
    )
    
    # Disruptor probe
    disruptor_pass = all(
        r["execution"]["metrics"]["tripwires_hit"] == 0
        for r in lane_results
    )
    append_receipt(
        mission_id=mission_id,
        phase="verify",
        summary=f"Disruptor: {'PASS' if disruptor_pass else 'FAIL'} - No tripwires hit",
        evidence_refs=["disruptor_report.json"],
        safety_envelope=safety,
        blocked_capabilities=[],
    )
    
    # Verifier auxiliary
    verifier_pass = all(
        r["execution"]["metrics"]["lines_written"] <= 200
        for r in lane_results
    )
    append_receipt(
        mission_id=mission_id,
        phase="verify",
        summary=f"Verifier Aux: {'PASS' if verifier_pass else 'FAIL'} - Chunk limits respected",
        evidence_refs=["verifier_aux_report.json"],
        safety_envelope=safety,
        blocked_capabilities=[],
    )
    
    # Quorum: 2 of 3 must pass
    votes = [immunizer_pass, disruptor_pass, verifier_pass]
    quorum_met = sum(votes) >= 2
    
    append_receipt(
        mission_id=mission_id,
        phase="verify",
        summary=f"Quorum: {'PASS' if quorum_met else 'FAIL'} ({sum(votes)}/3 validators approved)",
        evidence_refs=["quorum_aggregate.json"],
        safety_envelope=safety,
        blocked_capabilities=[],
    )
    
    return quorum_met


def main():
    """Run demo mission."""
    print("=" * 80)
    print("HFO Multi-Crew Orchestration Demo Mission")
    print("=" * 80)
    
    mission_goal = """
    Demonstrate multi-crew parallel orchestration with:
    - Disperse-converge pattern
    - 8/2 explore/exploit ratio
    - Quorum verification (2/3)
    - Stigmergy via blackboard JSONL
    """
    
    print(f"\nMission Goal: {mission_goal.strip()}\n")
    print("-" * 80)
    
    # Configuration
    parallel_lanes = 2
    explore_ratio = 0.8
    num_explore = int(parallel_lanes * explore_ratio)
    num_exploit = parallel_lanes - num_explore
    
    print(f"Configuration:")
    print(f"  - Parallel lanes: {parallel_lanes}")
    print(f"  - Explore/Exploit: {num_explore}/{num_exploit}")
    print(f"  - Quorum threshold: 2/3")
    print(f"\n" + "-" * 80)
    
    # Disperse phase
    print("\n[DISPERSE] Running parallel lanes...\n")
    
    lane_results = []
    
    # Explore lanes
    for i in range(num_explore):
        lane_id = f"explore_{i}"
        print(f"  ▸ Lane {lane_id} starting...")
        result = demo_prey_lane(lane_id, mission_goal, mode="explore")
        lane_results.append(result)
        print(f"    ✓ Lane {lane_id} completed: {result['execution']['metrics']}")
    
    # Exploit lanes
    for i in range(num_exploit):
        lane_id = f"exploit_{i}"
        print(f"  ▸ Lane {lane_id} starting...")
        result = demo_prey_lane(lane_id, mission_goal, mode="exploit")
        lane_results.append(result)
        print(f"    ✓ Lane {lane_id} completed: {result['execution']['metrics']}")
    
    # Converge phase
    print(f"\n[CONVERGE] Aggregating {len(lane_results)} lane results...\n")
    
    print(f"  ▸ Verification quorum starting...")
    quorum_pass = demo_verify_quorum(lane_results)
    
    # Digest
    print("\n" + "-" * 80)
    print(f"\n[DIGEST] Mission Result: {'PASS' if quorum_pass else 'FAIL'}\n")
    
    if quorum_pass:
        print("✓ Quorum verification passed (2/3 validators)")
        print("✓ All lanes completed successfully")
        print("✓ Evidence logged to blackboard JSONL")
        print("\nDigest Summary:")
        for result in lane_results:
            print(f"  • Lane {result['lane_id']} ({result['mode']}): {result['execution']['metrics']}")
    else:
        print("✗ Quorum verification failed")
        print("✗ Would retry with narrower scope")
    
    print("\n" + "=" * 80)
    print("Demo Complete")
    print("=" * 80)
    
    print("\nBlackboard receipts logged to:")
    print("  hfo_blackboard/obsidian_synapse_blackboard.jsonl")
    
    print("\nTo view receipts:")
    print("  cat hfo_blackboard/obsidian_synapse_blackboard.jsonl | grep demo_mission")
    
    print("\nFor production use with real LLM agents:")
    print("  1. Copy .env.example to .env")
    print("  2. Add your OPENAI_API_KEY")
    print("  3. Run: python scripts/hfo_multi_crew_orchestrator.py")
    
    return 0 if quorum_pass else 1


if __name__ == "__main__":
    sys.exit(main())
