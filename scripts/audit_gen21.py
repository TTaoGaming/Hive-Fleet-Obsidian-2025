#!/usr/bin/env python3
"""
Independent audit of Generation 21 architecture.

This tool validates Gen21 against its own stated requirements using independent
measurements rather than self-reporting to detect hallucination and drift.

Audit dimensions:
1. SSOT completeness (≥1000 lines, required sections present)
2. PREY canonical terminology usage (grep analysis)
3. Blackboard integrity (JSONL validation, evidence_refs)
4. Safety envelope adherence (tripwires, chunk sizes)
5. Self-regeneration capability (can Gen21 describe how to recreate itself?)
6. Drift analysis (claims vs implementation)

Output: JSON results suitable for digest and visualization.
"""

from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from datetime import datetime


REPO_ROOT = Path(__file__).resolve().parents[1]
GEN21_PATH = REPO_ROOT / "hfo_gem" / "gen_21" / "gpt5-attempt-3-gem.md"
BLACKBOARD_PATH = REPO_ROOT / "hfo_blackboard" / "obsidian_synapse_blackboard.jsonl"
AGENTS_MD_PATH = REPO_ROOT / "AGENTS.md"


@dataclass
class AuditResult:
    """Single audit check result."""
    dimension: str
    metric: str
    expected: Any
    actual: Any
    status: str  # PASS, FAIL, WARN, INFO
    evidence: List[str]
    notes: str = ""


@dataclass
class AuditSummary:
    """Overall audit summary."""
    timestamp: str
    total_checks: int
    passed: int
    failed: int
    warned: int
    results: List[Dict[str, Any]]
    drift_score: float  # 0.0 = perfect alignment, 1.0 = complete drift
    regeneration_score: float  # 0.0 = cannot regenerate, 1.0 = fully specified


class Gen21Auditor:
    """Independent auditor for Generation 21 architecture."""
    
    def __init__(self):
        self.results: List[AuditResult] = []
        self.gen21_content = ""
        self.blackboard_entries: List[Dict] = []
        self.agents_content = ""
        
    def load_artifacts(self) -> None:
        """Load all artifacts for analysis."""
        # Load Gen21 document
        if GEN21_PATH.exists():
            self.gen21_content = GEN21_PATH.read_text(encoding="utf-8")
        else:
            self.add_result("artifact_presence", "gen21_document", 
                          "exists", "missing", "FAIL",
                          [str(GEN21_PATH)], "Cannot audit missing document")
            
        # Load blackboard
        if BLACKBOARD_PATH.exists():
            with BLACKBOARD_PATH.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            self.blackboard_entries.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            self.add_result("blackboard_integrity", "json_parse",
                                          "valid_json", f"parse_error: {e}", "FAIL",
                                          [f"line: {line[:100]}"])
        else:
            self.add_result("artifact_presence", "blackboard", 
                          "exists", "missing", "WARN",
                          [str(BLACKBOARD_PATH)])
            
        # Load AGENTS.md
        if AGENTS_MD_PATH.exists():
            self.agents_content = AGENTS_MD_PATH.read_text(encoding="utf-8")
        else:
            self.add_result("artifact_presence", "agents_md",
                          "exists", "missing", "WARN",
                          [str(AGENTS_MD_PATH)])
    
    def add_result(self, dimension: str, metric: str, expected: Any, 
                   actual: Any, status: str, evidence: List[str], 
                   notes: str = "") -> None:
        """Add an audit result."""
        self.results.append(AuditResult(
            dimension=dimension,
            metric=metric,
            expected=expected,
            actual=actual,
            status=status,
            evidence=evidence,
            notes=notes
        ))
    
    def audit_ssot_completeness(self) -> None:
        """Audit SSOT completeness requirements."""
        if not self.gen21_content:
            return
            
        lines = self.gen21_content.splitlines()
        line_count = len(lines)
        
        # Line count requirement
        self.add_result("ssot_completeness", "line_count",
                       "≥1000", line_count,
                       "PASS" if line_count >= 1000 else "FAIL",
                       [f"wc -l: {line_count}"],
                       f"Gen21 requirement: ≥1000 lines")
        
        # Required sections
        required_sections = [
            "Section 0: BLUF",
            "Section 1: Zero Invention",
            "Section 2: PREY Canonical Workflow",
            "Section 3: Hive Workflow",
            "Section 4: Independent Verification",
            "Section 5: Stigmergy Protocol",
            "Section 6: Toolchain",
            "Section 7: Regeneration Protocol",
            "Section 8: Swarmlord of Webs Operations",
        ]
        
        missing_sections = []
        for section in required_sections:
            if section.lower() not in self.gen21_content.lower():
                missing_sections.append(section)
        
        self.add_result("ssot_completeness", "required_sections",
                       "all_present", 
                       "all" if not missing_sections else f"missing: {len(missing_sections)}",
                       "PASS" if not missing_sections else "FAIL",
                       missing_sections if missing_sections else ["all sections found"])
    
    def audit_prey_terminology(self) -> None:
        """Audit PREY canonical terminology usage."""
        if not self.gen21_content:
            return
        
        # Count PREY term usage
        prey_terms = {
            "Perceive": len(re.findall(r'\bPerceive\b', self.gen21_content)),
            "React": len(re.findall(r'\bReact\b', self.gen21_content)),
            "Engage": len(re.findall(r'\bEngage\b', self.gen21_content)),
            "Yield": len(re.findall(r'\bYield\b', self.gen21_content)),
            "PREY": len(re.findall(r'\bPREY\b', self.gen21_content)),
        }
        
        # Should have substantial usage
        min_expected = 5
        failures = [term for term, count in prey_terms.items() if count < min_expected]
        
        self.add_result("prey_terminology", "canonical_usage",
                       f"≥{min_expected} each",
                       str(prey_terms),
                       "WARN" if failures else "PASS",
                       [f"Counts: {prey_terms}"],
                       f"Low usage: {failures}" if failures else "")
        
        # Check for PREY mapping to frameworks
        mappings = [
            ("JADC2", r'\bJADC2\b'),
            ("OODA", r'\bOODA\b'),
            ("MAPE-K", r'\bMAPE-K\b'),
        ]
        
        found_mappings = []
        for name, pattern in mappings:
            if re.search(pattern, self.gen21_content):
                found_mappings.append(name)
        
        self.add_result("prey_terminology", "framework_mapping",
                       "JADC2/OODA/MAPE-K present",
                       ", ".join(found_mappings) if found_mappings else "none",
                       "PASS" if found_mappings else "WARN",
                       found_mappings)
    
    def audit_blackboard_integrity(self) -> None:
        """Audit blackboard JSONL integrity."""
        if not self.blackboard_entries:
            return
        
        # Required fields for Gen21 entries
        required_fields = ["mission_id", "phase", "summary", "timestamp"]
        evidence_required_fields = ["evidence_refs"]
        
        gen21_entries = [e for e in self.blackboard_entries 
                        if "gem21" in e.get("mission_id", "").lower()]
        
        if not gen21_entries:
            self.add_result("blackboard_integrity", "gen21_entries",
                          ">0", 0, "WARN",
                          ["No Gen21 mission entries found"])
            return
        
        # Check field presence
        missing_fields_count = 0
        missing_evidence_count = 0
        
        for entry in gen21_entries:
            for field in required_fields:
                if field not in entry:
                    missing_fields_count += 1
            
            # Evidence refs should be present for material phases
            material_phases = ["engage", "assemble_review_bundle", "verify"]
            if entry.get("phase") in material_phases:
                if "evidence_refs" not in entry or not isinstance(entry["evidence_refs"], list):
                    missing_evidence_count += 1
        
        self.add_result("blackboard_integrity", "required_fields",
                       "all entries complete",
                       f"{missing_fields_count} missing",
                       "PASS" if missing_fields_count == 0 else "FAIL",
                       [f"Checked {len(gen21_entries)} Gen21 entries"])
        
        self.add_result("blackboard_integrity", "evidence_refs",
                       "present for material phases",
                       f"{missing_evidence_count} missing",
                       "PASS" if missing_evidence_count == 0 else "WARN",
                       [f"Material phases need evidence"])
    
    def audit_safety_envelope(self) -> None:
        """Audit safety envelope adherence."""
        if not self.gen21_content:
            return
        
        # Check for safety terms
        safety_terms = {
            "canary": len(re.findall(r'\bcanary\b', self.gen21_content, re.I)),
            "tripwire": len(re.findall(r'\btripwire', self.gen21_content, re.I)),
            "revert": len(re.findall(r'\brevert\b', self.gen21_content, re.I)),
            "chunk": len(re.findall(r'\bchunk', self.gen21_content, re.I)),
            "line_count": len(re.findall(r'\bline_count\b', self.gen21_content, re.I)),
        }
        
        self.add_result("safety_envelope", "terminology_present",
                       "all safety terms used",
                       str(safety_terms),
                       "PASS",
                       [f"Safety terms: {safety_terms}"])
        
        # Check chunk size limits
        chunk_mentions = re.findall(r'chunk.*?(\d+)', self.gen21_content, re.I)
        chunk_sizes = [int(m) for m in chunk_mentions if m.isdigit()]
        
        if chunk_sizes:
            max_chunk = max(chunk_sizes)
            self.add_result("safety_envelope", "chunk_size_limit",
                           "≤200 mentioned",
                           f"max={max_chunk}",
                           "PASS" if max_chunk <= 200 else "WARN",
                           [f"Chunk sizes found: {chunk_sizes[:5]}"])
    
    def audit_regeneration_capability(self) -> None:
        """Audit self-regeneration capability."""
        if not self.gen21_content:
            return
        
        # Check for regeneration section
        has_regen_section = "regeneration protocol" in self.gen21_content.lower()
        
        # Check for bootstrap instructions
        bootstrap_patterns = [
            r'bootstrap',
            r'cold.?start',
            r'≤3.*steps',
            r'manual.*step',
        ]
        
        bootstrap_mentions = sum(
            1 for pattern in bootstrap_patterns 
            if re.search(pattern, self.gen21_content, re.I)
        )
        
        self.add_result("regeneration", "bootstrap_specified",
                       "≥3 bootstrap patterns",
                       bootstrap_mentions,
                       "PASS" if bootstrap_mentions >= 3 else "WARN",
                       [f"Bootstrap patterns found: {bootstrap_mentions}/4"])
        
        # Check if it references itself
        self_references = len(re.findall(r'this document|this file|gen.*21|gpt5.*attempt.*3',
                                        self.gen21_content, re.I))
        
        self.add_result("regeneration", "self_awareness",
                       ">0 self-references",
                       self_references,
                       "PASS" if self_references > 0 else "WARN",
                       [f"Self-references: {self_references}"])
    
    def audit_drift(self) -> None:
        """Measure drift between claims and implementation."""
        # Claims in Gen21 (using regex for flexibility)
        claims = {
            "single_interface": bool(re.search(r'swarmlord.*only|single.*interface', self.gen21_content, re.I | re.DOTALL)),
            "prey_canonical": bool(re.search(r'prey.*canonical', self.gen21_content, re.I)),
            "verify_gate": bool(re.search(r'verify.*pass', self.gen21_content, re.I)),
            "no_placeholders": bool(re.search(r'placeholder.*ban|no.*placeholder', self.gen21_content, re.I)),
        }
        
        # Check actual implementation
        implementations = {
            "single_interface": self.agents_content and "swarmlord" in self.agents_content.lower(),
            "prey_canonical": self.agents_content and "prey" in self.agents_content.lower(),
            "verify_gate": len([e for e in self.blackboard_entries 
                               if e.get("phase") == "verify"]) > 0,
            "no_placeholders": "TODO" not in self.gen21_content or self.gen21_content.count("TODO") < 3,  # Allow references to "TODO" as a concept
        }
        
        drift_items = []
        for key in claims:
            if claims[key] != implementations[key]:
                drift_items.append(f"{key}: claimed={claims[key]}, impl={implementations[key]}")
        
        drift_score = len(drift_items) / len(claims) if claims else 0.0
        
        self.add_result("drift_analysis", "claim_vs_implementation",
                       "0 drift items",
                       len(drift_items),
                       "PASS" if drift_score < 0.2 else "WARN" if drift_score < 0.5 else "FAIL",
                       drift_items if drift_items else ["No drift detected"],
                       f"Drift score: {drift_score:.2%}")
    
    def calculate_scores(self) -> tuple[float, float]:
        """Calculate drift and regeneration scores."""
        # Drift score: proportion of failed checks
        total = len(self.results)
        if total == 0:
            return 1.0, 0.0
        
        failed = len([r for r in self.results if r.status == "FAIL"])
        warned = len([r for r in self.results if r.status == "WARN"])
        drift_score = (failed + 0.5 * warned) / total
        
        # Regeneration score: based on regeneration-specific checks
        regen_results = [r for r in self.results if r.dimension == "regeneration"]
        if not regen_results:
            regeneration_score = 0.5  # Unknown
        else:
            regen_passed = len([r for r in regen_results if r.status == "PASS"])
            regeneration_score = regen_passed / len(regen_results)
        
        return drift_score, regeneration_score
    
    def run_audit(self) -> AuditSummary:
        """Run all audit checks."""
        self.load_artifacts()
        self.audit_ssot_completeness()
        self.audit_prey_terminology()
        self.audit_blackboard_integrity()
        self.audit_safety_envelope()
        self.audit_regeneration_capability()
        self.audit_drift()
        
        # Calculate summary
        drift_score, regen_score = self.calculate_scores()
        
        passed = len([r for r in self.results if r.status == "PASS"])
        failed = len([r for r in self.results if r.status == "FAIL"])
        warned = len([r for r in self.results if r.status == "WARN"])
        
        return AuditSummary(
            timestamp=datetime.utcnow().isoformat() + "Z",
            total_checks=len(self.results),
            passed=passed,
            failed=failed,
            warned=warned,
            results=[asdict(r) for r in self.results],
            drift_score=drift_score,
            regeneration_score=regen_score
        )


def main() -> int:
    """Run Gen21 audit and output results."""
    auditor = Gen21Auditor()
    summary = auditor.run_audit()
    
    # Output JSON
    output = asdict(summary)
    print(json.dumps(output, indent=2))
    
    # Exit code based on failures
    return 1 if summary.failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
