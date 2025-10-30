#!/usr/bin/env python3
"""
Demo script for multi-crew orchestrator.
Shows the system working with mock agents (no API key required).
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from blackboard_logger import append_receipt, ChunkId
from hfo_multi_crew_core import MissionConfig, LaneResult, VerificationQuorum


def demo_configuration():
    """Demo 1: Show configuration."""
    print("=" * 60)
    print("DEMO 1: Mission Configuration")
    print("=" * 60)
    
    config = MissionConfig(
        mission_id="demo_multi_crew_2025-10-30",
        lane_count=2,
        explore_exploit_ratio=0.2,  # 20% explore, 80% exploit
        quorum_threshold=2,  # 2 out of 3 validators
        chunk_size_max=200,
        placeholder_ban=True,
        blackboard_path="hfo_blackboard/obsidian_synapse_blackboard.jsonl",
        lane_cycle_soft_minutes=5,
        mission_soft_minutes=30,
    )
    
    print(f"Mission ID: {config.mission_id}")
    print(f"Lanes: {config.lane_count}")
    print(f"Explore/Exploit: {config.explore_exploit_ratio} (20% explore, 80% exploit)")
    print(f"Quorum Threshold: {config.quorum_threshold}/3 validators")
    print(f"Chunk Size Max: {config.chunk_size_max} lines")
    print(f"Placeholder Ban: {config.placeholder_ban}")
    print()
    
    return config


def demo_lane_results():
    """Demo 2: Show lane result creation."""
    print("=" * 60)
    print("DEMO 2: Lane Results (Simulated)")
    print("=" * 60)
    
    results = [
        LaneResult(
            lane_id="lane_a",
            lane_index=0,
            success=True,
            output="Explore mode: Analyzed mission context and identified 3 key patterns.",
            evidence_refs=["mission_intent.yml:1-100", "AGENTS.md:1-50"],
            duration_seconds=45.2,
            errors=None
        ),
        LaneResult(
            lane_id="lane_b",
            lane_index=1,
            success=True,
            output="Exploit mode: Applied proven template to generate solution.",
            evidence_refs=["scripts/blackboard_logger.py:1-100"],
            duration_seconds=38.7,
            errors=None
        )
    ]
    
    for result in results:
        print(f"\n{result.lane_id.upper()} ({'explore' if result.lane_index == 0 else 'exploit'} mode):")
        print(f"  Success: {result.success}")
        print(f"  Duration: {result.duration_seconds}s")
        print(f"  Output: {result.output[:60]}...")
        print(f"  Evidence: {', '.join(result.evidence_refs)}")
    
    print()
    return results


def demo_verification(config, results):
    """Demo 3: Show quorum verification."""
    print("=" * 60)
    print("DEMO 3: Quorum Verification")
    print("=" * 60)
    
    verifier = VerificationQuorum(config)
    
    # Run verification
    quorum_pass, summary, evidence = verifier.verify(results)
    
    print("\nValidator Results:")
    for ev in evidence:
        parts = ev.split("=", 1)
        if len(parts) == 2:
            validator_name, status = parts
            print(f"  {validator_name:15} : {status}")
        else:
            print(f"  {ev}")  # Fallback if format is unexpected
    
    print(f"\n{summary}")
    print(f"\nFinal Result: {'✅ PASS' if quorum_pass else '❌ FAIL'}")
    print()
    
    return quorum_pass


def demo_explore_exploit_distribution():
    """Demo 4: Show explore/exploit lane distribution."""
    print("=" * 60)
    print("DEMO 4: Explore/Exploit Distribution")
    print("=" * 60)
    
    test_cases = [
        (2, 0.2),  # 2 lanes, 20% explore
        (4, 0.2),  # 4 lanes, 20% explore
        (10, 0.2), # 10 lanes, 20% explore
    ]
    
    for lane_count, ratio in test_cases:
        explore_count = max(1, int(lane_count * ratio))
        exploit_count = lane_count - explore_count
        
        print(f"\n{lane_count} lanes with {ratio} ratio:")
        print(f"  Explore: {explore_count} lane(s) ({explore_count/lane_count*100:.0f}%)")
        print(f"  Exploit: {exploit_count} lane(s) ({exploit_count/lane_count*100:.0f}%)")
    
    print()


def demo_adversarial_detection():
    """Demo 5: Show disruptor adversarial detection."""
    print("=" * 60)
    print("DEMO 5: Adversarial Detection (Disruptor)")
    print("=" * 60)
    
    config = MissionConfig(
        mission_id="demo_adversarial",
        lane_count=2,
        explore_exploit_ratio=0.2,
        quorum_threshold=2,
        chunk_size_max=200,
        placeholder_ban=True,
        blackboard_path="test.jsonl",
        lane_cycle_soft_minutes=5,
        mission_soft_minutes=30,
    )
    
    verifier = VerificationQuorum(config)
    
    # Test 1: Good results (diverse outputs)
    good_results = [
        LaneResult("lane_a", 0, True, "output1", ["ref1"], 60, None),
        LaneResult("lane_b", 1, True, "output2", ["ref2"], 60, None),
    ]
    
    print("\n1. Diverse outputs (good):")
    print(f"   Result: {'✅ PASS' if verifier._disruptor_probe(good_results) else '❌ FAIL'}")
    
    # Test 2: Placeholder detected
    placeholder_results = [
        LaneResult("lane_a", 0, True, "output with TODO item", ["ref1"], 60, None),
        LaneResult("lane_b", 1, True, "output2", ["ref2"], 60, None),
    ]
    
    print("\n2. Placeholder detected (TODO):")
    print(f"   Result: {'✅ PASS' if verifier._disruptor_probe(placeholder_results) else '❌ FAIL (expected)'}")
    
    # Test 3: Identical outputs (suspicious)
    identical_results = [
        LaneResult("lane_a", 0, True, "same output", ["ref1"], 60, None),
        LaneResult("lane_b", 1, True, "same output", ["ref2"], 60, None),
    ]
    
    print("\n3. Identical outputs (suspicious):")
    print(f"   Result: {'✅ PASS' if verifier._disruptor_probe(identical_results) else '❌ FAIL (expected)'}")
    
    print()


def demo_blackboard_receipt():
    """Demo 6: Show blackboard receipt structure."""
    print("=" * 60)
    print("DEMO 6: Blackboard Receipt Structure")
    print("=" * 60)
    
    print("\nExample receipt (JSON):")
    
    receipt = {
        "mission_id": "demo_multi_crew_2025-10-30",
        "phase": "engage",
        "summary": "[lane_a] PREY execution complete",
        "evidence_refs": ["lane_a:result_len=1234"],
        "safety_envelope": {
            "chunk_size_max": 200,
            "line_target_min": 0,
            "tripwire_status": "green"
        },
        "blocked_capabilities": [],
        "timestamp": "2025-10-30T16:00:00Z",
        "chunk_id": {"index": 0, "total": 2}
    }
    
    print(json.dumps(receipt, indent=2))
    print()


def main():
    """Run all demos."""
    print("\n🐝 Hive Fleet Obsidian - Multi-Crew Orchestrator Demo")
    print("     (No API key required)\n")
    
    # Demo 1: Configuration
    config = demo_configuration()
    
    # Demo 2: Lane results
    results = demo_lane_results()
    
    # Demo 3: Verification
    quorum_pass = demo_verification(config, results)
    
    # Demo 4: Explore/exploit distribution
    demo_explore_exploit_distribution()
    
    # Demo 5: Adversarial detection
    demo_adversarial_detection()
    
    # Demo 6: Blackboard receipt
    demo_blackboard_receipt()
    
    print("=" * 60)
    print("✅ Demo Complete!")
    print("=" * 60)
    print("\nTo run with real agents:")
    print("1. Copy .env.template to .env")
    print("2. Add your OPENAI_API_KEY")
    print("3. Run: bash scripts/run_multi_crew.sh")
    print()
    
    return 0 if quorum_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
