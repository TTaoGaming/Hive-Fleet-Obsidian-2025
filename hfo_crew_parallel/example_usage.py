#!/usr/bin/env python
"""
Example usage of HFO Crew Parallel system.

This demonstrates how to use the parallel crew orchestrator programmatically.
"""

import sys
from pathlib import Path

# Ensure we can import from parent directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from hfo_crew_parallel.config import CrewConfig, MissionIntent
from hfo_crew_parallel.blackboard import BlackboardManager


def example_basic_usage():
    """Example: Basic usage without running full crews."""
    print("=" * 80)
    print("Example 1: Basic Infrastructure Usage")
    print("=" * 80)
    
    # Load configuration
    config = CrewConfig()
    print(f"\n✓ Configuration loaded:")
    print(f"  Model: {config.model_name}")
    print(f"  Temperature: {config.temperature}")
    print(f"  Explore/Exploit: {config.explore_ratio}/{config.exploit_ratio}")
    
    # Load mission intent
    mission = MissionIntent()
    print(f"\n✓ Mission intent loaded:")
    print(f"  Mission ID: {mission.mission_id}")
    print(f"  Lanes: {mission.lanes_count}")
    print(f"  Quorum threshold: {mission.quorum_threshold}")
    
    # Use blackboard
    bb = BlackboardManager()
    bb.append_receipt(
        mission_id="example_basic",
        phase="perceive",
        summary="Example infrastructure demonstration",
        evidence_refs=["example_usage.py"],
        safety_envelope={"chunk_size_max": 200}
    )
    print(f"\n✓ Blackboard receipt logged")
    
    # Read back
    receipts = bb.read_receipts(mission_id="example_basic")
    print(f"  Found {len(receipts)} receipt(s) for this mission")


def example_with_orchestrator():
    """Example: Using the orchestrator (requires API key and CrewAI)."""
    print("\n" + "=" * 80)
    print("Example 2: Full Orchestrator Usage (requires API key)")
    print("=" * 80)
    
    try:
        from hfo_crew_parallel.swarmlord import SwarmlordOrchestrator
        
        config = CrewConfig()
        
        if not config.openai_api_key:
            print("\n⚠️  Skipping: OPENAI_API_KEY not set")
            print("   Set it in .env file to run full crews")
            return
        
        mission = MissionIntent()
        orchestrator = SwarmlordOrchestrator(config=config, mission_intent=mission)
        
        print(f"\n✓ Orchestrator initialized:")
        print(f"  Mission: {orchestrator.mission_id}")
        print(f"  Lanes: {orchestrator.mission.lanes_count}")
        
        print("\n  To execute a mission:")
        print("  result = orchestrator.execute_mission('Your mission context')")
        print("  print(result['status'])")
        
    except ImportError as e:
        print(f"\n⚠️  Cannot import orchestrator: {e}")
        print("   Install CrewAI: pip install crewai")


def example_blackboard_patterns():
    """Example: Common blackboard patterns."""
    print("\n" + "=" * 80)
    print("Example 3: Blackboard Patterns")
    print("=" * 80)
    
    bb = BlackboardManager()
    mission_id = "example_patterns"
    
    # PREY phases
    for phase in ["perceive", "react", "engage", "yield", "verify"]:
        bb.append_receipt(
            mission_id=mission_id,
            phase=phase,
            summary=f"Example {phase} phase",
            evidence_refs=[f"{phase}.log"]
        )
    
    print(f"\n✓ Logged PREY workflow receipts")
    
    # Read by phase
    verify_receipts = bb.read_receipts(mission_id=mission_id, phase="verify")
    print(f"  Found {len(verify_receipts)} verify receipt(s)")
    
    # Get latest
    latest = bb.get_latest_receipt(mission_id=mission_id)
    if latest:
        print(f"  Latest phase: {latest['phase']}")
        print(f"  Latest summary: {latest['summary']}")


def main():
    """Run all examples."""
    print("\n🚀 HFO Crew Parallel - Example Usage\n")
    
    try:
        example_basic_usage()
        example_with_orchestrator()
        example_blackboard_patterns()
        
        print("\n" + "=" * 80)
        print("✅ Examples completed successfully")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Set OPENAI_API_KEY in .env file")
        print("2. Run: python -m hfo_crew_parallel.cli 'Your mission'")
        print("3. Check blackboard: hfo_blackboard/obsidian_synapse_blackboard.jsonl")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
