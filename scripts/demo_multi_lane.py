#!/usr/bin/env python3
"""
Demo script for multi-lane orchestrator - shows architecture without API calls.

This demonstrates the structure and flow without requiring API keys.
For actual execution with CrewAI agents, use hfo_multi_lane_orchestrator.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from hfo_multi_lane_orchestrator import (
    create_lane_configs,
    LaneResult,
    EXPLORE_RATIO,
)
from hfo_quorum_verifier import run_quorum_verification
from blackboard_logger import append_receipt


MISSION_ID = "demo_multi_lane_2025-10-30"


def simulate_lane_execution(lane_config):
    """Simulate a lane execution without actual CrewAI calls."""
    # Simulate different outputs based on mode
    if lane_config.mode == "explore":
        output = (
            f"Lane {lane_config.lane_name} explored novel approaches:\n"
            "1. Investigated alternative architectures\n"
            "2. Tested experimental patterns\n"
            "3. Gathered diverse evidence\n"
            "Result: Discovered 2 promising directions"
        )
    else:
        output = (
            f"Lane {lane_config.lane_name} executed proven workflow:\n"
            "1. Applied established patterns\n"
            "2. Validated against known benchmarks\n"
            "3. Confirmed stability\n"
            "Result: Completed with 100% reliability"
        )
    
    return LaneResult(
        lane_id=lane_config.lane_id,
        lane_name=lane_config.lane_name,
        success=True,
        output=output,
        evidence_refs=[
            f"lane:{lane_config.lane_id}",
            f"mode:{lane_config.mode}",
            f"output_len:{len(output)}",
        ],
        metrics={
            "output_length": len(output),
            "mode": lane_config.mode,
            "simulated": True,
        },
    )


def main():
    """Run demo of multi-lane orchestrator."""
    print("=" * 70)
    print("Multi-Lane Orchestrator Demo")
    print("=" * 70)
    print(f"Mission ID: {MISSION_ID}")
    print(f"Explore/Exploit Ratio: {EXPLORE_RATIO}/{1-EXPLORE_RATIO}")
    print("=" * 70)
    
    # Log perceive
    append_receipt(
        mission_id=MISSION_ID,
        phase="perceive",
        summary="Demo orchestrator starting",
        evidence_refs=[__file__],
        safety_envelope={"chunk_size_max": 200},
        blocked_capabilities=[],
    )
    
    # Create lane configurations
    num_lanes = 2
    lane_configs = create_lane_configs(num_lanes, EXPLORE_RATIO)
    
    print(f"\nCreated {len(lane_configs)} lane configurations:")
    for config in lane_configs:
        print(f"  - {config.lane_name}: {config.mode} mode")
    
    # Log react
    append_receipt(
        mission_id=MISSION_ID,
        phase="react",
        summary=f"Created {len(lane_configs)} lane configurations",
        evidence_refs=[f"lanes:{num_lanes}", f"explore_ratio:{EXPLORE_RATIO}"],
        safety_envelope={"chunk_size_max": 200},
        blocked_capabilities=[],
    )
    
    # Simulate lane execution (DISPERSE)
    print(f"\n{'='*70}")
    print("DISPERSE: Simulating parallel lane execution...")
    print(f"{'='*70}")
    
    lane_results = []
    for config in lane_configs:
        print(f"\nExecuting {config.lane_name} ({config.mode} mode)...")
        result = simulate_lane_execution(config)
        lane_results.append(result)
        print(f"  ✓ {config.lane_name} completed")
        
        # Log engage
        append_receipt(
            mission_id=MISSION_ID,
            phase="engage",
            summary=f"Lane {config.lane_name} simulated execution",
            evidence_refs=result.evidence_refs,
            safety_envelope={"chunk_size_max": 200},
            blocked_capabilities=[],
        )
    
    # Show outputs
    print(f"\n{'='*70}")
    print("Lane Outputs:")
    print(f"{'='*70}")
    for result in lane_results:
        print(f"\n{result.lane_name} ({result.metrics['mode']}):")
        print("-" * 70)
        print(result.output)
    
    # Quorum verification (CONVERGE)
    print(f"\n{'='*70}")
    print("CONVERGE: Running quorum verification...")
    print(f"{'='*70}")
    
    quorum_result = run_quorum_verification(lane_results, MISSION_ID, threshold=2)
    
    print(f"\n{quorum_result.summary}")
    
    if quorum_result.passed:
        print(f"\n✅ QUORUM VERIFICATION PASSED")
    else:
        print(f"\n❌ QUORUM VERIFICATION FAILED")
    
    # Show validator details
    print(f"\nValidator Details:")
    for val_result in quorum_result.individual_results:
        status = "✓" if val_result.passed else "✗"
        print(f"  {status} {val_result.validator_name}: {val_result.confidence:.2%}")
        for finding in val_result.findings[:2]:
            print(f"      - {finding}")
    
    # Log digest
    append_receipt(
        mission_id=MISSION_ID,
        phase="digest",
        summary=f"Demo complete - Quorum: {'PASS' if quorum_result.passed else 'FAIL'}",
        evidence_refs=[
            f"lanes:{len(lane_results)}",
            f"quorum_passed:{quorum_result.passed}",
            f"validators_passed:{quorum_result.validators_passed}",
        ],
        safety_envelope={"chunk_size_max": 200},
        blocked_capabilities=[],
    )
    
    print(f"\n{'='*70}")
    print("Demo complete. Check hfo_blackboard/obsidian_synapse_blackboard.jsonl")
    print("for receipts showing PREY cycle: perceive → react → engage → verify → digest")
    print(f"{'='*70}\n")
    
    return 0 if quorum_result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
