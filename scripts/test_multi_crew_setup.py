#!/usr/bin/env python3
"""
Test script to verify multi-crew orchestration setup without API calls.

This validates:
- Dependencies installed correctly
- Module imports work
- Configuration loads
- Blackboard logger functional
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all required imports work."""
    print("Testing imports...")
    
    try:
        from crewai import Agent, Task, Crew, Process
        print("✓ crewai imported successfully")
    except ImportError as e:
        print(f"✗ crewai import failed: {e}")
        return False
    
    try:
        from crewai.tools import tool
        print("✓ crewai.tools imported successfully")
    except ImportError as e:
        print(f"✗ crewai.tools import failed: {e}")
        return False
    
    try:
        from blackboard_logger import append_receipt
        print("✓ blackboard_logger imported successfully")
    except ImportError as e:
        print(f"✗ blackboard_logger import failed: {e}")
        return False
    
    return True


def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from hfo_multi_crew_orchestrator import MissionConfig
        config = MissionConfig.from_env()
        
        print(f"✓ MissionConfig loaded")
        print(f"  - Mission ID: {config.mission_id}")
        print(f"  - Parallel lanes: {config.parallel_lanes}")
        print(f"  - Quorum threshold: {config.quorum_threshold}")
        print(f"  - Chunk size max: {config.chunk_size_max}")
        
        return True
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return False


def test_blackboard():
    """Test blackboard logger."""
    print("\nTesting blackboard logger...")
    
    try:
        from blackboard_logger import append_receipt
        
        receipt_path = append_receipt(
            mission_id="test_setup_verification",
            phase="verify",
            summary="Multi-crew orchestration setup test",
            evidence_refs=["scripts/test_multi_crew_setup.py"],
            safety_envelope={"chunk_size_max": 200},
            blocked_capabilities=[],
        )
        
        print(f"✓ Blackboard receipt logged to {receipt_path}")
        return True
    except Exception as e:
        print(f"✗ Blackboard logging failed: {e}")
        return False


def test_orchestrator_init():
    """Test orchestrator initialization."""
    print("\nTesting orchestrator initialization...")
    
    try:
        from hfo_multi_crew_orchestrator import SwarmlordOrchestrator, MissionConfig
        
        config = MissionConfig.from_env()
        orchestrator = SwarmlordOrchestrator(config)
        
        print(f"✓ SwarmlordOrchestrator initialized")
        print(f"  - Config: {config.mission_id}")
        print(f"  - Safety envelope: {orchestrator.safety_envelope}")
        
        return True
    except Exception as e:
        print(f"✗ Orchestrator initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all setup tests."""
    print("=" * 80)
    print("HFO Multi-Crew Orchestration Setup Test")
    print("=" * 80)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Blackboard Logger", test_blackboard),
        ("Orchestrator Init", test_orchestrator_init),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} test crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 80)
    print("Test Results")
    print("=" * 80)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✓ All setup tests PASSED")
        print("\nNext steps:")
        print("1. Copy .env.example to .env")
        print("2. Add your OPENAI_API_KEY to .env")
        print("3. Run: python scripts/hfo_multi_crew_orchestrator.py")
        return 0
    else:
        print("✗ Some setup tests FAILED")
        print("\nPlease fix the issues above before running the orchestrator.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
