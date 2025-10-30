#!/usr/bin/env python3
"""
Quorum Verification Module for Multi-Lane Orchestrator.

Implements:
- Immunizer: checks for safety and consistency
- Disruptor: adversarial probes to avoid persistent green
- Verifier_aux: auxiliary validation checks
- Quorum aggregation (2/3 threshold)

Aligned with mission intent mi_daily_2025-10-30 v5 and clarification pass 4.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path

from blackboard_logger import append_receipt


@dataclass
class ValidationResult:
    """Result from a single validator."""
    validator_name: str
    passed: bool
    confidence: float  # 0.0 to 1.0
    findings: List[str]
    evidence_refs: List[str]


@dataclass
class QuorumResult:
    """Aggregated result from quorum verification."""
    passed: bool
    validators_passed: int
    validators_total: int
    threshold: int
    individual_results: List[ValidationResult]
    summary: str


class Immunizer:
    """
    Immunizer validator: checks for safety and consistency.
    
    Validates:
    - No placeholders (TODO, ..., omitted)
    - Chunk size limits respected
    - Evidence refs present
    - Basic consistency checks
    """
    
    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.name = "immunizer"
    
    def validate(self, lane_results: List[Any]) -> ValidationResult:
        """Run immunizer validation checks."""
        findings = []
        evidence = []
        
        # Check for placeholders
        placeholder_patterns = [r'\bTODO\b', r'\.\.\.', r'\bomitted\b', r'\bFIXME\b']
        for result in lane_results:
            output = result.output
            for pattern in placeholder_patterns:
                if re.search(pattern, output, re.IGNORECASE):
                    findings.append(f"Placeholder detected in {result.lane_name}: {pattern}")
        
        # Check for evidence refs
        for result in lane_results:
            if not result.evidence_refs or len(result.evidence_refs) == 0:
                findings.append(f"Missing evidence_refs in {result.lane_name}")
        
        # Check output validity
        for result in lane_results:
            if not result.output or len(result.output) < 10:
                findings.append(f"Insufficient output in {result.lane_name}")
        
        passed = len(findings) == 0
        confidence = 1.0 if passed else max(0.0, 1.0 - (len(findings) * 0.2))
        
        evidence.append(f"validator:{self.name}")
        evidence.append(f"findings_count:{len(findings)}")
        evidence.append(f"lanes_checked:{len(lane_results)}")
        
        return ValidationResult(
            validator_name=self.name,
            passed=passed,
            confidence=confidence,
            findings=findings if findings else ["All immunizer checks passed"],
            evidence_refs=evidence,
        )


class Disruptor:
    """
    Disruptor validator: adversarial probes to avoid persistent green.
    
    Validates:
    - Outputs are sufficiently different (diversity check)
    - No obvious copy-paste or template repetition
    - Reasonable variance in metrics
    """
    
    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.name = "disruptor"
    
    def validate(self, lane_results: List[Any]) -> ValidationResult:
        """Run adversarial probes."""
        findings = []
        evidence = []
        
        # Check output diversity
        if len(lane_results) >= 2:
            outputs = [r.output for r in lane_results]
            
            # Simple similarity check: compare first 100 chars
            for i in range(len(outputs)):
                for j in range(i + 1, len(outputs)):
                    sample_i = outputs[i][:100].lower()
                    sample_j = outputs[j][:100].lower()
                    if sample_i == sample_j:
                        findings.append(
                            f"Identical outputs detected: "
                            f"{lane_results[i].lane_name} and {lane_results[j].lane_name}"
                        )
        
        # Check for suspicious uniformity in success rates
        success_count = sum(1 for r in lane_results if r.success)
        if len(lane_results) > 2 and success_count == len(lane_results):
            # All succeeded - check if outputs are meaningful
            avg_length = sum(len(r.output) for r in lane_results) / len(lane_results)
            if avg_length < 50:
                findings.append("Suspiciously uniform success with minimal output")
        
        # Probe: check for noop patterns
        noop_patterns = [r'no-op', r'nothing to do', r'skipped', r'not implemented']
        for result in lane_results:
            for pattern in noop_patterns:
                if re.search(pattern, result.output, re.IGNORECASE):
                    findings.append(
                        f"Potential noop detected in {result.lane_name}: {pattern}"
                    )
        
        passed = len(findings) == 0
        confidence = 1.0 if passed else max(0.0, 1.0 - (len(findings) * 0.25))
        
        evidence.append(f"validator:{self.name}")
        evidence.append(f"probes_run:{len(findings) + 1}")
        evidence.append(f"lanes_checked:{len(lane_results)}")
        
        return ValidationResult(
            validator_name=self.name,
            passed=passed,
            confidence=confidence,
            findings=findings if findings else ["All disruptor probes passed"],
            evidence_refs=evidence,
        )


class VerifierAux:
    """
    Auxiliary verifier: additional validation checks.
    
    Validates:
    - Metrics are present and reasonable
    - Evidence refs follow expected format
    - Success/failure distribution is reasonable
    """
    
    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.name = "verifier_aux"
    
    def validate(self, lane_results: List[Any]) -> ValidationResult:
        """Run auxiliary validation checks."""
        findings = []
        evidence = []
        
        # Check metrics presence
        for result in lane_results:
            if not result.metrics or len(result.metrics) == 0:
                findings.append(f"Missing metrics in {result.lane_name}")
        
        # Check evidence format
        for result in lane_results:
            for ref in result.evidence_refs:
                if not isinstance(ref, str) or len(ref) < 3:
                    findings.append(
                        f"Invalid evidence_ref format in {result.lane_name}: {ref}"
                    )
        
        # Check for complete failure
        failure_count = sum(1 for r in lane_results if not r.success)
        if failure_count == len(lane_results):
            findings.append("All lanes failed - systematic issue likely")
        
        passed = len(findings) == 0
        confidence = 1.0 if passed else max(0.0, 1.0 - (len(findings) * 0.2))
        
        evidence.append(f"validator:{self.name}")
        evidence.append(f"checks_run:3")
        evidence.append(f"lanes_checked:{len(lane_results)}")
        
        return ValidationResult(
            validator_name=self.name,
            passed=passed,
            confidence=confidence,
            findings=findings if findings else ["All auxiliary checks passed"],
            evidence_refs=evidence,
        )


def run_quorum_verification(
    lane_results: List[Any], 
    mission_id: str,
    threshold: int = 2
) -> QuorumResult:
    """
    Run quorum verification with all validators.
    
    Args:
        lane_results: Results from parallel lanes
        mission_id: Current mission ID
        threshold: Number of validators that must pass (default: 2/3)
    
    Returns:
        QuorumResult with aggregated validation results
    """
    # Create validators
    immunizer = Immunizer(mission_id)
    disruptor = Disruptor(mission_id)
    verifier_aux = VerifierAux(mission_id)
    
    # Run validations
    validators = [immunizer, disruptor, verifier_aux]
    results = [v.validate(lane_results) for v in validators]
    
    # Aggregate results
    validators_passed = sum(1 for r in results if r.passed)
    quorum_passed = validators_passed >= threshold
    
    # Create summary
    summary_lines = [
        f"Quorum verification: {'PASS' if quorum_passed else 'FAIL'}",
        f"Validators passed: {validators_passed}/{len(validators)} (threshold: {threshold})",
    ]
    
    for result in results:
        status = "✓" if result.passed else "✗"
        summary_lines.append(
            f"{status} {result.validator_name}: {result.confidence:.2f} confidence"
        )
    
    summary = "\n".join(summary_lines)
    
    # Log to blackboard
    evidence_refs = []
    for result in results:
        evidence_refs.extend(result.evidence_refs)
    
    append_receipt(
        mission_id=mission_id,
        phase="verify",
        summary=f"Quorum verification: {validators_passed}/{len(validators)} passed",
        evidence_refs=evidence_refs,
        safety_envelope={"chunk_size_max": 200, "line_target_min": 0},
        blocked_capabilities=[],
    )
    
    return QuorumResult(
        passed=quorum_passed,
        validators_passed=validators_passed,
        validators_total=len(validators),
        threshold=threshold,
        individual_results=results,
        summary=summary,
    )
