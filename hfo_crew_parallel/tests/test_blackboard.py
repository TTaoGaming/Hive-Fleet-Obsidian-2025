"""
Tests for blackboard utilities.
"""

import json
import tempfile
from pathlib import Path

from hfo_crew_parallel.blackboard import BlackboardManager


def test_blackboard_append_receipt():
    """Test appending receipts to blackboard."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bb_path = Path(tmpdir) / "test_blackboard.jsonl"
        bb = BlackboardManager(str(bb_path))
        
        bb.append_receipt(
            mission_id="test_mission",
            phase="perceive",
            summary="Test receipt",
            evidence_refs=["test.py:1-10"],
            safety_envelope={"chunk_size_max": 200}
        )
        
        assert bb_path.exists()
        
        with open(bb_path) as f:
            line = f.readline()
            receipt = json.loads(line)
            
            assert receipt["mission_id"] == "test_mission"
            assert receipt["phase"] == "perceive"
            assert receipt["summary"] == "Test receipt"
            assert "test.py:1-10" in receipt["evidence_refs"]


def test_blackboard_read_receipts():
    """Test reading receipts from blackboard."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bb_path = Path(tmpdir) / "test_blackboard.jsonl"
        bb = BlackboardManager(str(bb_path))
        
        bb.append_receipt(
            mission_id="mission1",
            phase="engage",
            summary="First",
            evidence_refs=["a.py"]
        )
        
        bb.append_receipt(
            mission_id="mission2",
            phase="verify",
            summary="Second",
            evidence_refs=["b.py"]
        )
        
        all_receipts = bb.read_receipts()
        assert len(all_receipts) == 2
        
        mission1_receipts = bb.read_receipts(mission_id="mission1")
        assert len(mission1_receipts) == 1
        assert mission1_receipts[0]["mission_id"] == "mission1"
        
        verify_receipts = bb.read_receipts(phase="verify")
        assert len(verify_receipts) == 1
        assert verify_receipts[0]["phase"] == "verify"


def test_blackboard_get_latest():
    """Test getting latest receipt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        bb_path = Path(tmpdir) / "test_blackboard.jsonl"
        bb = BlackboardManager(str(bb_path))
        
        bb.append_receipt(
            mission_id="mission1",
            phase="perceive",
            summary="First",
            evidence_refs=["a.py"]
        )
        
        bb.append_receipt(
            mission_id="mission1",
            phase="engage",
            summary="Second",
            evidence_refs=["b.py"]
        )
        
        latest = bb.get_latest_receipt(mission_id="mission1")
        assert latest is not None
        assert latest["phase"] == "engage"
        assert latest["summary"] == "Second"
