#!/usr/bin/env python3
"""
Blackboard JSONL receipt logger aligned with AGENTS.md.

Append-only protocol (one JSON object per line) with required fields:
- mission_id: str
- phase: str (perceive|react|engage|yield|verify|digest)
- summary: str
- evidence_refs: list[str]
- safety_envelope: dict (chunk_size_max, line_target_min, tripwire_status?)
- blocked_capabilities: list[str]
- timestamp: ISO 8601 Z

Optional:
- chunk_id: { index:int, total:int }
- regen_flag: bool

Usage:
  from blackboard_logger import append_receipt
  append_receipt(mission_id, phase, summary, evidence_refs=[...])
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


BLACKBOARD_JSONL = Path("hfo_blackboard/obsidian_synapse_blackboard.jsonl")


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class ChunkId:
    index: int
    total: int


@dataclass
class Receipt:
    mission_id: str
    phase: str
    summary: str
    evidence_refs: List[str]
    safety_envelope: Dict[str, Any] = field(default_factory=dict)
    blocked_capabilities: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=now_utc)
    chunk_id: Optional[ChunkId] = None
    regen_flag: Optional[bool] = None

    def to_json(self) -> str:
        obj = asdict(self)
        # Convert nested dataclass if present
        if self.chunk_id is not None:
            obj["chunk_id"] = asdict(self.chunk_id)
        # Enforce evidence_refs as list and presence of required keys
        if not isinstance(obj.get("evidence_refs"), list):
            raise ValueError("evidence_refs must be a list")
        return json.dumps(obj, ensure_ascii=False)


def append_receipt(
    mission_id: str,
    phase: str,
    summary: str,
    evidence_refs: Optional[List[str]] = None,
    safety_envelope: Optional[Dict[str, Any]] = None,
    blocked_capabilities: Optional[List[str]] = None,
    chunk_id: Optional[ChunkId] = None,
    regen_flag: Optional[bool] = None,
    jsonl_path: Path | str = BLACKBOARD_JSONL,
) -> Path:
    """Append a receipt line to the blackboard JSONL and return the path.

    This never edits prior lines; it only appends a new JSON object line.
    """
    jsonl_path = Path(jsonl_path)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    receipt = Receipt(
        mission_id=mission_id,
        phase=phase,
        summary=summary,
        evidence_refs=evidence_refs or [],
        safety_envelope=safety_envelope or {},
        blocked_capabilities=blocked_capabilities or [],
        chunk_id=chunk_id,
        regen_flag=regen_flag,
    )

    line = receipt.to_json()
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(line)
        f.write("\n")
    return jsonl_path


if __name__ == "__main__":
    # Tiny self-test append (commented by default)
    # append_receipt(
    #     mission_id="selftest_000",
    #     phase="verify",
    #     summary="blackboard_logger self-test (no-op)",
    #     evidence_refs=["blackboard_logger.py:1-200"],
    #     safety_envelope={"chunk_size_max": 200, "line_target_min": 0},
    # )
    print("blackboard_logger module ready")
