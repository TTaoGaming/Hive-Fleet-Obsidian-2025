"""
Blackboard utilities for append-only JSONL coordination.

Implements stigmergy pattern for multi-agent communication
following AGENTS.md protocol.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class BlackboardManager:
    """Manages append-only JSONL blackboard for agent coordination."""
    
    def __init__(self, blackboard_path: str = "hfo_blackboard/obsidian_synapse_blackboard.jsonl"):
        """Initialize blackboard manager.
        
        Args:
            blackboard_path: Path to blackboard JSONL file
        """
        self.blackboard_path = Path(blackboard_path)
        self.blackboard_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.blackboard_path.exists():
            self.blackboard_path.touch()
    
    def append_receipt(
        self,
        mission_id: str,
        phase: str,
        summary: str,
        evidence_refs: List[str],
        safety_envelope: Optional[Dict[str, Any]] = None,
        blocked_capabilities: Optional[List[str]] = None,
        chunk_id: Optional[Dict[str, int]] = None,
        regen_flag: bool = False,
        **extra_fields
    ) -> None:
        """Append a receipt to the blackboard.
        
        Args:
            mission_id: Mission identifier
            phase: PREY phase (perceive, react, engage, yield, verify, digest)
            summary: Human-readable description
            evidence_refs: List of evidence references (paths, hashes, etc)
            safety_envelope: Safety parameters and tripwire status
            blocked_capabilities: List of blocked capabilities
            chunk_id: Chunk tracking info {index, total}
            regen_flag: True if regenerating after failure
            **extra_fields: Additional optional fields
        """
        receipt = {
            "mission_id": mission_id,
            "phase": phase,
            "summary": summary,
            "evidence_refs": evidence_refs,
            "safety_envelope": safety_envelope or {},
            "blocked_capabilities": blocked_capabilities or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if chunk_id is not None:
            receipt["chunk_id"] = chunk_id
        
        if regen_flag:
            receipt["regen_flag"] = regen_flag
        
        receipt.update(extra_fields)
        
        with open(self.blackboard_path, "a") as f:
            # Ensure previous entry ends with newline if file exists and is non-empty
            if self.blackboard_path.exists() and self.blackboard_path.stat().st_size > 0:
                # Check if last character is newline
                with open(self.blackboard_path, "rb") as rf:
                    rf.seek(-1, 2)  # Seek to last byte
                    last_char = rf.read(1)
                    if last_char != b'\n':
                        f.write("\n")
            
            f.write(json.dumps(receipt) + "\n")
    
    def read_receipts(
        self,
        mission_id: Optional[str] = None,
        phase: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Read receipts from blackboard.
        
        Args:
            mission_id: Filter by mission ID
            phase: Filter by phase
            limit: Maximum number of receipts to return (most recent)
            
        Returns:
            List of receipt dictionaries
        """
        receipts = []
        
        if not self.blackboard_path.exists():
            return receipts
        
        with open(self.blackboard_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Handle concatenated JSON on same line (malformed entries)
                # Try to extract valid JSON objects
                try:
                    receipt = json.loads(line)
                    
                    # Ensure receipt is a dict, not a string
                    if not isinstance(receipt, dict):
                        continue
                    
                    if mission_id and receipt.get("mission_id") != mission_id:
                        continue
                    
                    if phase and receipt.get("phase") != phase:
                        continue
                    
                    receipts.append(receipt)
                except json.JSONDecodeError:
                    # Try to extract first valid JSON object from line
                    try:
                        # Find first { and matching }
                        start = line.find('{')
                        if start >= 0:
                            brace_count = 0
                            for i, char in enumerate(line[start:], start=start):
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        # Found complete JSON object
                                        json_str = line[start:i+1]
                                        receipt = json.loads(json_str)
                                        
                                        if not isinstance(receipt, dict):
                                            continue
                                        
                                        if mission_id and receipt.get("mission_id") != mission_id:
                                            continue
                                        
                                        if phase and receipt.get("phase") != phase:
                                            continue
                                        
                                        receipts.append(receipt)
                                        break
                    except:
                        continue
        
        if limit:
            receipts = receipts[-limit:]
        
        return receipts
    
    def get_latest_receipt(
        self,
        mission_id: Optional[str] = None,
        phase: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent receipt.
        
        Args:
            mission_id: Filter by mission ID
            phase: Filter by phase
            
        Returns:
            Most recent receipt or None
        """
        receipts = self.read_receipts(mission_id=mission_id, phase=phase, limit=1)
        return receipts[0] if receipts else None
