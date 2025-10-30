#!/usr/bin/env python3
"""
Test suite for multi-crew orchestrator.
Tests core components without requiring API keys or CrewAI.
"""
import sys
import json
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from blackboard_logger import append_receipt, ChunkId, Receipt
from hfo_multi_crew_core import (
    MissionConfig, 
    LaneResult, 
    VerificationQuorum
)


def test_mission_config():
    """Test mission configuration."""
    config = MissionConfig(
        mission_id="test_001",
        lane_count=2,
        explore_exploit_ratio=0.2,
        quorum_threshold=2,
        chunk_size_max=200,
        placeholder_ban=True,
        blackboard_path="test_blackboard.jsonl",
        lane_cycle_soft_minutes=5,
        mission_soft_minutes=30,
    )
    
    assert config.mission_id == "test_001"
    assert config.lane_count == 2
    assert config.explore_exploit_ratio == 0.2
    print("✓ MissionConfig test passed")


def test_lane_result():
    """Test lane result creation and serialization."""
    result = LaneResult(
        lane_id="lane_a",
        lane_index=0,
        success=True,
        output="Test output",
        evidence_refs=["test.py:1-10"],
        duration_seconds=1.5,
        errors=None
    )
    
    data = result.to_dict()
    assert data["lane_id"] == "lane_a"
    assert data["success"] is True
    assert data["duration_seconds"] == 1.5
    print("✓ LaneResult test passed")


def test_verification_immunizer():
    """Test immunizer validator."""
    config = MissionConfig(
        mission_id="test_002",
        lane_count=2,
        explore_exploit_ratio=0.2,
        quorum_threshold=2,
        chunk_size_max=200,
        placeholder_ban=True,
        blackboard_path="test_blackboard.jsonl",
        lane_cycle_soft_minutes=5,
        mission_soft_minutes=30,
    )
    
    verifier = VerificationQuorum(config)
    
    # Test with successful results
    good_results = [
        LaneResult("lane_a", 0, True, "output1", ["ref1"], 1.0, None),
        LaneResult("lane_b", 1, True, "output2", ["ref2"], 1.0, None),
    ]
    
    assert verifier._immunizer_check(good_results) is True
    
    # Test with failed result
    bad_results = [
        LaneResult("lane_a", 0, False, "", [], 1.0, ["error"]),
        LaneResult("lane_b", 1, True, "output2", ["ref2"], 1.0, None),
    ]
    
    assert verifier._immunizer_check(bad_results) is False
    print("✓ Immunizer validator test passed")


def test_verification_disruptor():
    """Test disruptor validator."""
    config = MissionConfig(
        mission_id="test_003",
        lane_count=2,
        explore_exploit_ratio=0.2,
        quorum_threshold=2,
        chunk_size_max=200,
        placeholder_ban=True,
        blackboard_path="test_blackboard.jsonl",
        lane_cycle_soft_minutes=5,
        mission_soft_minutes=30,
    )
    
    verifier = VerificationQuorum(config)
    
    # Test with diverse outputs
    good_results = [
        LaneResult("lane_a", 0, True, "output1", ["ref1"], 1.0, None),
        LaneResult("lane_b", 1, True, "output2", ["ref2"], 1.0, None),
    ]
    
    assert verifier._disruptor_probe(good_results) is True
    
    # Test with placeholder
    placeholder_results = [
        LaneResult("lane_a", 0, True, "output with TODO item", ["ref1"], 1.0, None),
        LaneResult("lane_b", 1, True, "output2", ["ref2"], 1.0, None),
    ]
    
    assert verifier._disruptor_probe(placeholder_results) is False
    
    # Test with identical outputs (suspicious)
    identical_results = [
        LaneResult("lane_a", 0, True, "same output", ["ref1"], 1.0, None),
        LaneResult("lane_b", 1, True, "same output", ["ref2"], 1.0, None),
    ]
    
    assert verifier._disruptor_probe(identical_results) is False
    print("✓ Disruptor validator test passed")


def test_verification_verifier_aux():
    """Test auxiliary verifier."""
    config = MissionConfig(
        mission_id="test_004",
        lane_count=2,
        explore_exploit_ratio=0.2,
        quorum_threshold=2,
        chunk_size_max=200,
        placeholder_ban=True,
        blackboard_path="test_blackboard.jsonl",
        lane_cycle_soft_minutes=5,
        mission_soft_minutes=30,
    )
    
    verifier = VerificationQuorum(config)
    
    # Test with good timing
    good_results = [
        LaneResult("lane_a", 0, True, "output1", ["ref1"], 60.0, None),  # 1 min
        LaneResult("lane_b", 1, True, "output2", ["ref2"], 120.0, None),  # 2 min
    ]
    
    assert verifier._verifier_aux(good_results) is True
    
    # Test with timeout
    timeout_results = [
        LaneResult("lane_a", 0, True, "output1", ["ref1"], 400.0, None),  # > 5 min
        LaneResult("lane_b", 1, True, "output2", ["ref2"], 60.0, None),
    ]
    
    assert verifier._verifier_aux(timeout_results) is False
    
    # Test with errors
    error_results = [
        LaneResult("lane_a", 0, True, "output1", ["ref1"], 60.0, ["error1"]),
        LaneResult("lane_b", 1, True, "output2", ["ref2"], 60.0, None),
    ]
    
    assert verifier._verifier_aux(error_results) is False
    print("✓ Verifier aux test passed")


def test_blackboard_receipt():
    """Test blackboard receipt creation."""
    receipt = Receipt(
        mission_id="test_005",
        phase="perceive",
        summary="Test receipt",
        evidence_refs=["test.py:1-10"],
        safety_envelope={"chunk_size_max": 200},
        blocked_capabilities=[],
        chunk_id=ChunkId(index=0, total=2),
        regen_flag=False,
    )
    
    json_str = receipt.to_json()
    data = json.loads(json_str)
    
    assert data["mission_id"] == "test_005"
    assert data["phase"] == "perceive"
    assert data["chunk_id"]["index"] == 0
    assert data["chunk_id"]["total"] == 2
    print("✓ Blackboard receipt test passed")


def test_explore_exploit_ratio():
    """Test explore/exploit lane distribution."""
    # Test 2 lanes with 0.2 ratio (should be 1 explore, 1 exploit)
    config = MissionConfig(
        mission_id="test_006",
        lane_count=2,
        explore_exploit_ratio=0.2,
        quorum_threshold=2,
        chunk_size_max=200,
        placeholder_ban=True,
        blackboard_path="test_blackboard.jsonl",
        lane_cycle_soft_minutes=5,
        mission_soft_minutes=30,
    )
    
    explore_count = max(1, int(config.lane_count * config.explore_exploit_ratio))
    assert explore_count == 1  # 20% of 2 rounds up to 1
    
    # Test 10 lanes with 0.2 ratio (should be 2 explore, 8 exploit)
    config.lane_count = 10
    explore_count = max(1, int(config.lane_count * config.explore_exploit_ratio))
    assert explore_count == 2  # 20% of 10 = 2
    
    print("✓ Explore/exploit ratio test passed")


def run_all_tests():
    """Run all tests."""
    print("🧪 Running multi-crew orchestrator tests...")
    print()
    
    tests = [
        test_mission_config,
        test_lane_result,
        test_verification_immunizer,
        test_verification_disruptor,
        test_verification_verifier_aux,
        test_blackboard_receipt,
        test_explore_exploit_ratio,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1
    
    print()
    print(f"Results: {passed} passed, {failed} failed")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run_all_tests())
