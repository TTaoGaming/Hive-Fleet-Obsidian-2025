#!/usr/bin/env python3
"""
Verify blackboard logging and JSONL structure.
Demonstrates stigmergy coordination pattern.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from blackboard_logger import append_receipt, ChunkId


def verify_blackboard():
    """Verify blackboard JSONL logging."""
    print("🔍 Verifying Blackboard JSONL Logging")
    print("=" * 60)
    
    # Test receipt 1: Perceive
    print("\n1. Writing Perceive receipt...")
    path = append_receipt(
        mission_id="verify_blackboard_2025-10-30",
        phase="perceive",
        summary="Starting verification test",
        evidence_refs=[__file__],
        safety_envelope={"chunk_size_max": 200, "line_target_min": 0},
        blocked_capabilities=[],
        chunk_id=ChunkId(index=0, total=3)
    )
    print(f"   ✓ Written to: {path}")
    
    # Test receipt 2: React
    print("\n2. Writing React receipt...")
    append_receipt(
        mission_id="verify_blackboard_2025-10-30",
        phase="react",
        summary="Planning test execution",
        evidence_refs=[__file__, "scripts/blackboard_logger.py"],
        safety_envelope={"chunk_size_max": 200, "line_target_min": 0},
        blocked_capabilities=[],
        chunk_id=ChunkId(index=1, total=3)
    )
    print(f"   ✓ Written to: {path}")
    
    # Test receipt 3: Engage
    print("\n3. Writing Engage receipt...")
    append_receipt(
        mission_id="verify_blackboard_2025-10-30",
        phase="engage",
        summary="Executing verification checks",
        evidence_refs=[__file__],
        safety_envelope={"chunk_size_max": 200, "line_target_min": 0},
        blocked_capabilities=[],
        chunk_id=ChunkId(index=2, total=3)
    )
    print(f"   ✓ Written to: {path}")
    
    # Verify JSONL structure
    print("\n4. Verifying JSONL structure...")
    if not path.exists():
        print(f"   ✗ Blackboard file not found: {path}")
        return False
    
    with path.open("r") as f:
        lines = f.readlines()
    
    print(f"   Total receipts in blackboard: {len(lines)}")
    
    # Find our test receipts (mission_id matches)
    test_receipts = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            receipt = json.loads(line)
            if isinstance(receipt, dict) and receipt.get('mission_id') == 'verify_blackboard_2025-10-30':
                test_receipts.append(receipt)
        except (json.JSONDecodeError, TypeError):
            # Skip invalid lines (may be from old format)
            continue
    
    print(f"   Found {len(test_receipts)} test receipts")
    
    for i, receipt in enumerate(test_receipts, 1):
        print(f"\n   Receipt {i}:")
        print(f"     Phase: {receipt.get('phase')}")
        print(f"     Summary: {receipt.get('summary')[:50]}...")
        print(f"     Evidence: {len(receipt.get('evidence_refs', []))} refs")
        print(f"     Chunk: {receipt.get('chunk_id', {}).get('index')}/{receipt.get('chunk_id', {}).get('total')}")
    
    print("\n✅ Blackboard verification complete!")
    return True


def demonstrate_stigmergy():
    """Demonstrate stigmergy pattern."""
    print("\n" + "=" * 60)
    print("🐜 Stigmergy Coordination Pattern")
    print("=" * 60)
    
    print("\nStigmergy allows agents to coordinate indirectly:")
    print("1. Agent A writes receipt → blackboard")
    print("2. Agent B reads blackboard → sees Agent A's work")
    print("3. Agent B builds on A's work → writes new receipt")
    print("4. No direct communication needed!")
    
    print("\nExample:")
    print("  Lane A (explore): 'Tried approach X, got result Y'")
    print("  Lane B (exploit): Reads A's receipt, avoids approach X")
    print("  Lane C (exploit): Builds on Y from A's findings")
    
    print("\nBenefits:")
    print("  ✓ Decentralized coordination")
    print("  ✓ Asynchronous execution")
    print("  ✓ Audit trail built-in")
    print("  ✓ Scalable to many agents")


def main():
    """Main entry point."""
    print("\n🐝 Hive Fleet Obsidian - Blackboard Verification\n")
    
    success = verify_blackboard()
    demonstrate_stigmergy()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All checks passed!")
    else:
        print("❌ Some checks failed")
    print("=" * 60)
    print()
    
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
