#!/usr/bin/env python
"""
Demo script showing HFO Crew Parallel system setup and validation.

This validates the infrastructure without requiring full CrewAI installation.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hfo_crew_parallel.blackboard import BlackboardManager
from hfo_crew_parallel.safety import SafetyEnvelope
from hfo_crew_parallel.config import CrewConfig, MissionIntent


def main():
    """Run demo validation."""
    print("=" * 80)
    print("HFO Crew Parallel - Infrastructure Validation")
    print("=" * 80)
    
    # Test 1: Blackboard
    print("\n[1/4] Testing Blackboard...")
    bb = BlackboardManager()
    bb.append_receipt(
        mission_id="demo_validation",
        phase="perceive",
        summary="Infrastructure validation started",
        evidence_refs=["demo_validate.py"]
    )
    receipts = bb.read_receipts(mission_id="demo_validation")
    print(f"  ✓ Blackboard operational: {len(receipts)} receipt(s) logged")
    
    # Test 2: Safety Envelope
    print("\n[2/4] Testing Safety Envelope...")
    safety = SafetyEnvelope(chunk_size_max=200)
    
    test_content = "\n".join([f"line {i}" for i in range(50)])
    passed, count = safety.check_line_count(test_content)
    print(f"  ✓ Line count check: {count} lines (passed={passed})")
    
    passed, found = safety.check_placeholders("clean code without placeholders")
    print(f"  ✓ Placeholder scan: passed={passed}")
    
    chunks = safety.chunk_content(test_content, max_lines=20)
    print(f"  ✓ Chunking: {len(chunks)} chunk(s) created")
    
    # Test 3: Configuration
    print("\n[3/4] Testing Configuration...")
    config = CrewConfig()
    print(f"  ✓ Model: {config.model_name}")
    print(f"  ✓ Temperature: {config.temperature}")
    print(f"  ✓ Explore/Exploit: {config.explore_ratio}/{config.exploit_ratio}")
    print(f"  ✓ API Key: {'set' if config.openai_api_key else 'NOT SET'}")
    
    # Test 4: Mission Intent
    print("\n[4/4] Testing Mission Intent...")
    mission = MissionIntent()
    print(f"  ✓ Mission ID: {mission.mission_id}")
    print(f"  ✓ Lanes: {mission.lanes_count} ({', '.join(mission.lane_names)})")
    print(f"  ✓ Quorum: {mission.quorum_threshold}/{len(mission.quorum_validators)} validators")
    print(f"  ✓ Chunk size max: {mission.chunk_size_max}")
    print(f"  ✓ Placeholder ban: {mission.placeholder_ban}")
    
    # Summary
    print("\n" + "=" * 80)
    print("Validation Summary")
    print("=" * 80)
    
    all_tests_passed = True
    
    if not config.openai_api_key:
        print("\n⚠️  WARNING: OPENAI_API_KEY not set")
        print("   To use the full system, create a .env file with:")
        print("   OPENAI_API_KEY=sk-your-key-here")
        all_tests_passed = False
    else:
        print("\n✓ All infrastructure components validated")
    
    print("\nCore Infrastructure:")
    print(f"  ✓ Blackboard: {bb.blackboard_path}")
    print(f"  ✓ Safety Envelope: chunk_max={safety.chunk_size_max}")
    print(f"  ✓ Mission Intent: {mission.mission_id}")
    
    print("\nNext Steps:")
    if not config.openai_api_key:
        print("  1. Set OPENAI_API_KEY in .env file")
        print("  2. Run: python hfo_crew_parallel/demo_validate.py")
        print("  3. Run: python -m hfo_crew_parallel.cli 'Your mission'")
    else:
        print("  1. Install CrewAI: pip install crewai")
        print("  2. Run: python -m hfo_crew_parallel.cli 'Your mission context'")
    
    print("\n" + "=" * 80)
    
    return 0 if all_tests_passed else 1


if __name__ == '__main__':
    sys.exit(main())
