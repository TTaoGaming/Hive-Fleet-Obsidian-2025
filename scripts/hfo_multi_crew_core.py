#!/usr/bin/env python3
"""
Core data structures for multi-crew orchestrator (no CrewAI dependency).
Extracted for testing.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional


@dataclass
class MissionConfig:
    """Mission configuration from environment and mission intent."""
    mission_id: str
    lane_count: int
    explore_exploit_ratio: float
    quorum_threshold: int
    chunk_size_max: int
    placeholder_ban: bool
    blackboard_path: str
    lane_cycle_soft_minutes: int
    mission_soft_minutes: int


@dataclass
class LaneResult:
    """Result from a PREY lane execution."""
    lane_id: str
    lane_index: int
    success: bool
    output: str
    evidence_refs: List[str]
    duration_seconds: float
    errors: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VerificationQuorum:
    """Quorum-based verification with immunizer, disruptor, verifier_aux."""
    
    def __init__(self, config: MissionConfig):
        self.config = config
        self.validators = ["immunizer", "disruptor", "verifier_aux"]
    
    def verify(self, lane_results: List[LaneResult]) -> tuple[bool, str, List[str]]:
        """Run quorum verification on lane results."""
        votes = []
        evidence = []
        
        # Immunizer check
        immunizer_pass = self._immunizer_check(lane_results)
        votes.append(immunizer_pass)
        evidence.append(f"immunizer={'PASS' if immunizer_pass else 'FAIL'}")
        
        # Disruptor probe
        disruptor_pass = self._disruptor_probe(lane_results)
        votes.append(disruptor_pass)
        evidence.append(f"disruptor={'PASS' if disruptor_pass else 'FAIL'}")
        
        # Verifier auxiliary
        verifier_pass = self._verifier_aux(lane_results)
        votes.append(verifier_pass)
        evidence.append(f"verifier_aux={'PASS' if verifier_pass else 'FAIL'}")
        
        # Quorum decision
        pass_count = sum(votes)
        quorum_pass = pass_count >= self.config.quorum_threshold
        
        summary = (
            f"Verification quorum: {pass_count}/{len(votes)} validators passed. "
            f"Threshold: {self.config.quorum_threshold}. "
            f"Result: {'PASS' if quorum_pass else 'FAIL'}"
        )
        
        return quorum_pass, summary, evidence
    
    def _immunizer_check(self, results: List[LaneResult]) -> bool:
        """Check for basic health and consistency."""
        if not results:
            return False
        
        # All lanes should succeed
        all_success = all(r.success for r in results)
        
        # Evidence refs should be present
        has_evidence = all(r.evidence_refs for r in results)
        
        return all_success and has_evidence
    
    def _disruptor_probe(self, results: List[LaneResult]) -> bool:
        """Adversarial probe - look for suspicious patterns."""
        if not results:
            return False
        
        # Check for placeholder ban compliance
        if self.config.placeholder_ban:
            for result in results:
                output_lower = result.output.lower()
                if any(p in output_lower for p in ["todo", "...", "omitted", "placeholder"]):
                    return False
        
        # Check output diversity (avoid identical results)
        if len(results) > 1:
            outputs = [r.output for r in results]
            if len(set(outputs)) == 1:
                # All outputs identical - suspicious
                return False
        
        return True
    
    def _verifier_aux(self, results: List[LaneResult]) -> bool:
        """Auxiliary verification - timing and structure checks."""
        if not results:
            return False
        
        # Check timing constraints
        for result in results:
            max_seconds = self.config.lane_cycle_soft_minutes * 60
            if result.duration_seconds > max_seconds:
                return False
        
        # Check for error presence
        has_errors = any(r.errors for r in results)
        
        return not has_errors
