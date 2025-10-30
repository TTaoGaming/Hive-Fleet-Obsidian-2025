#!/usr/bin/env python3
"""
Test script for multi-lane orchestrator - validates structure without API calls.

Tests:
- Module imports
- Lane configuration
- Quorum verification logic
- Blackboard logging
"""
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from hfo_multi_lane_orchestrator import (
    create_lane_configs,
    LaneConfig,
    LaneResult,
    EXPLORE_RATIO,
    PARALLEL_LANES,
)
from hfo_quorum_verifier import run_quorum_verification
from blackboard_logger import append_receipt


def test_lane_configuration():
    """Test lane configuration generation."""
    print("Testing lane configuration...")
    
    lanes = create_lane_configs(4, EXPLORE_RATIO)
    
    assert len(lanes) == 4, f"Expected 4 lanes, got {len(lanes)}"
    
    explore_count = sum(1 for l in lanes if l.mode == "explore")
    exploit_count = sum(1 for l in lanes if l.mode == "exploit")
    
    print(f"  ✓ Created {len(lanes)} lanes")
    print(f"  ✓ Explore: {explore_count}, Exploit: {exploit_count}")
    print(f"  ✓ Ratio: {explore_count/len(lanes):.1%} explore / {exploit_count/len(lanes):.1%} exploit")
    
    # Check that we have at least one of each (with 4 lanes and 40% explore)
    assert explore_count >= 1, "Should have at least 1 explore lane"
    assert exploit_count >= 1, "Should have at least 1 exploit lane"
    
    return True


def test_quorum_verification():
    """Test quorum verification logic."""
    print("\nTesting quorum verification...")
    
    # Create mock lane results
    mock_results = [
        LaneResult(
            lane_id="lane_0",
            lane_name="lane_a",
            success=True,
            output="Good output from lane A with meaningful content and no placeholders",
            evidence_refs=["lane:lane_0", "mode:explore"],
            metrics={"output_length": 60, "mode": "explore"},
        ),
        LaneResult(
            lane_id="lane_1",
            lane_name="lane_b",
            success=True,
            output="Different output from lane B with distinct content",
            evidence_refs=["lane:lane_1", "mode:exploit"],
            metrics={"output_length": 50, "mode": "exploit"},
        ),
    ]
    
    # Run quorum verification
    quorum_result = run_quorum_verification(mock_results, "test_mission_verify", threshold=2)
    
    print(f"  ✓ Validators passed: {quorum_result.validators_passed}/{quorum_result.validators_total}")
    print(f"  ✓ Quorum result: {'PASS' if quorum_result.passed else 'FAIL'}")
    
    # With good mock data, should pass
    assert quorum_result.validators_passed >= 2, "Should pass at least 2 validators"
    assert quorum_result.passed, "Quorum should pass with good data"
    
    return True


def test_quorum_verification_with_failures():
    """Test quorum verification catches problems."""
    print("\nTesting quorum verification with problematic data...")
    
    # Create mock results with issues
    bad_results = [
        LaneResult(
            lane_id="lane_0",
            lane_name="lane_a",
            success=True,
            output="Output with TODO placeholder and ... ellipsis",
            evidence_refs=[],  # Missing evidence
            metrics={},  # Missing metrics
        ),
        LaneResult(
            lane_id="lane_1",
            lane_name="lane_b",
            success=True,
            output="Same output with TODO placeholder and ... ellipsis",  # Duplicate
            evidence_refs=[],
            metrics={},
        ),
    ]
    
    quorum_result = run_quorum_verification(bad_results, "test_mission_fail", threshold=2)
    
    print(f"  ✓ Validators passed: {quorum_result.validators_passed}/{quorum_result.validators_total}")
    print(f"  ✓ Quorum result: {'PASS' if quorum_result.passed else 'FAIL'}")
    
    # Should catch the issues
    assert quorum_result.validators_passed < quorum_result.validators_total, \
        "Should fail at least one validator"
    
    return True


def test_blackboard_logging():
    """Test blackboard receipt logging."""
    print("\nTesting blackboard logging...")
    
    test_path = Path("hfo_blackboard/test_blackboard.jsonl")
    
    # Append a test receipt
    result_path = append_receipt(
        mission_id="test_mission_log",
        phase="verify",
        summary="Test receipt for validation",
        evidence_refs=["test:1", "test:2"],
        safety_envelope={"chunk_size_max": 200},
        blocked_capabilities=[],
        jsonl_path=test_path,
    )
    
    assert result_path.exists(), "Blackboard file should be created"
    
    # Read and verify
    with result_path.open() as f:
        lines = f.readlines()
        last_line = lines[-1]
        
    import json
    receipt = json.loads(last_line)
    
    assert receipt["mission_id"] == "test_mission_log"
    assert receipt["phase"] == "verify"
    assert "test:1" in receipt["evidence_refs"]
    
    print(f"  ✓ Blackboard logging working")
    print(f"  ✓ Receipt written to {test_path}")
    
    # Cleanup
    test_path.unlink()
    
    return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("Multi-Lane Orchestrator Test Suite")
    print("=" * 70)
    
    tests = [
        ("Lane Configuration", test_lane_configuration),
        ("Quorum Verification (Pass)", test_quorum_verification),
        ("Quorum Verification (Fail Detection)", test_quorum_verification_with_failures),
        ("Blackboard Logging", test_blackboard_logging),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"  ✗ {name} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {name} error: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
