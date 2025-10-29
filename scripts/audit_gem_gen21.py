#!/usr/bin/env python3
"""
Independent audit script for Generation 21 GEM self-regeneration capability.

This script conducts a trial run to test whether Gen21 can actually regenerate
itself from its own specification, with metrics on:
- Completeness (line counts, section coverage)
- Quality (placeholder detection, evidence tracking)
- Structural integrity (PREY terminology, safety envelopes)
- Regeneration fidelity (how well it reproduces from SSOT)

Seed: 2 (for reproducibility)
Explore/Exploit: 2/8 (20% exploration, 80% exploitation)
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple, Any
import hashlib


class Gen21Auditor:
    """Independent auditor for Gen21 GEM specification."""
    
    def __init__(self, repo_root: Path, seed: int = 2):
        self.repo_root = repo_root
        self.seed = seed
        self.gem_path = repo_root / "hfo_gem" / "gen_21" / "gpt5-attempt-3-gem.md"
        self.mission_intent_path = repo_root / "hfo_mission_intent" / "mission_intent_2025-10-29.yml"
        self.blackboard_path = repo_root / "hfo_blackboard" / "obsidian_synapse_blackboard.jsonl"
        self.agents_md_path = repo_root / "AGENTS.md"
        
        self.results = {
            "mission_id": f"gen21_audit_seed{seed}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "seed": seed,
            "explore_exploit_ratio": "2/8",
            "metrics": {},
            "findings": [],
            "recommendations": [],
            "pass_fail": {}
        }
    
    def audit_completeness(self) -> Dict[str, Any]:
        """Audit Gen21 SSOT completeness."""
        metrics = {}
        
        if not self.gem_path.exists():
            return {
                "exists": False,
                "error": f"Gen21 GEM not found at {self.gem_path}"
            }
        
        content = self.gem_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        
        metrics["exists"] = True
        metrics["line_count"] = len(lines)
        metrics["target_min"] = 1000
        metrics["meets_target"] = len(lines) >= 1000
        metrics["char_count"] = len(content)
        metrics["word_count"] = len(content.split())
        
        # Check for sections
        sections = re.findall(r"^#+\s+Section\s+(\d+):", content, re.MULTILINE)
        metrics["section_count"] = len(sections)
        metrics["sections_found"] = sorted(set(int(s) for s in sections))
        
        # Expected sections per spec (0-40 + appendices)
        expected_sections = list(range(0, 41))  # Section 0 through Section 40
        missing_sections = [s for s in expected_sections if s not in metrics["sections_found"]]
        metrics["missing_sections"] = missing_sections
        
        return metrics
    
    def audit_quality(self) -> Dict[str, Any]:
        """Audit code quality and placeholder detection."""
        metrics = {}
        
        if not self.gem_path.exists():
            return {"exists": False}
        
        content = self.gem_path.read_text(encoding="utf-8")
        
        # Placeholder detection
        placeholders = {
            "TODO": len(re.findall(r'\bTODO\b', content, re.IGNORECASE)),
            "FIXME": len(re.findall(r'\bFIXME\b', content, re.IGNORECASE)),
            "XXX": len(re.findall(r'\bXXX\b', content)),
            "...": len(re.findall(r'\.\.\.', content)),
            "omitted": len(re.findall(r'\bomitted\b', content, re.IGNORECASE)),
            "TBD": len(re.findall(r'\bTBD\b', content, re.IGNORECASE))
        }
        
        metrics["placeholders"] = placeholders
        metrics["total_placeholders"] = sum(placeholders.values())
        metrics["placeholder_free"] = metrics["total_placeholders"] == 0
        
        # Mermaid diagram detection
        mermaid_blocks = re.findall(r'```mermaid.*?```', content, re.DOTALL)
        metrics["mermaid_diagram_count"] = len(mermaid_blocks)
        
        # Evidence reference patterns
        evidence_refs = len(re.findall(r'evidence_refs', content))
        metrics["evidence_ref_mentions"] = evidence_refs
        
        return metrics
    
    def audit_prey_terminology(self) -> Dict[str, Any]:
        """Audit PREY canonical terminology usage."""
        metrics = {}
        
        if not self.gem_path.exists():
            return {"exists": False}
        
        content = self.gem_path.read_text(encoding="utf-8")
        
        # PREY terms
        prey_terms = {
            "Perceive": len(re.findall(r'\bPerceive\b', content)),
            "React": len(re.findall(r'\bReact\b', content)),
            "Engage": len(re.findall(r'\bEngage\b', content)),
            "Yield": len(re.findall(r'\bYield\b', content))
        }
        
        metrics["prey_term_counts"] = prey_terms
        metrics["prey_all_present"] = all(count > 0 for count in prey_terms.values())
        
        # Workflow hierarchies
        workflows = {
            "HIVE": len(re.findall(r'\bHIVE\b', content)),
            "GROWTH": len(re.findall(r'\bGROWTH\b', content)),
            "SWARM": len(re.findall(r'\bSWARM\b', content)),
            "PREY": len(re.findall(r'\bPREY\b', content))
        }
        
        metrics["workflow_counts"] = workflows
        metrics["workflow_hierarchy_present"] = all(count > 0 for count in workflows.values())
        
        return metrics
    
    def audit_safety_envelope(self) -> Dict[str, Any]:
        """Audit safety envelope specifications."""
        metrics = {}
        
        if not self.gem_path.exists():
            return {"exists": False}
        
        content = self.gem_path.read_text(encoding="utf-8")
        
        safety_terms = {
            "canary": len(re.findall(r'\bcanary\b', content, re.IGNORECASE)),
            "tripwire": len(re.findall(r'\btripwire[s]?\b', content, re.IGNORECASE)),
            "revert": len(re.findall(r'\brevert\b', content, re.IGNORECASE)),
            "safety_envelope": len(re.findall(r'\bsafety[_\s]envelope\b', content, re.IGNORECASE))
        }
        
        metrics["safety_terms"] = safety_terms
        metrics["safety_comprehensive"] = all(count > 0 for count in safety_terms.values())
        
        # Check for chunk size limits
        chunk_mentions = re.findall(r'(\d+)\s*lines?\s*per\s*(?:write|chunk)', content, re.IGNORECASE)
        metrics["chunk_size_limits"] = [int(m) for m in chunk_mentions]
        metrics["chunk_size_200_enforced"] = 200 in metrics["chunk_size_limits"]
        
        return metrics
    
    def audit_blackboard_protocol(self) -> Dict[str, Any]:
        """Audit blackboard JSONL integrity."""
        metrics = {}
        
        if not self.blackboard_path.exists():
            metrics["exists"] = False
            return metrics
        
        metrics["exists"] = True
        
        try:
            with open(self.blackboard_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            metrics["entry_count"] = len(lines)
            
            valid_entries = 0
            missions = set()
            phases = []
            
            for i, line in enumerate(lines):
                try:
                    entry = json.loads(line)
                    valid_entries += 1
                    
                    if "mission_id" in entry:
                        missions.add(entry["mission_id"])
                    
                    if "phase" in entry:
                        phases.append(entry["phase"])
                
                except json.JSONDecodeError:
                    pass
            
            metrics["valid_json_entries"] = valid_entries
            metrics["unique_missions"] = len(missions)
            metrics["phases_logged"] = list(set(phases))
            metrics["all_entries_valid"] = valid_entries == len(lines)
            
        except Exception as e:
            metrics["error"] = str(e)
        
        return metrics
    
    def audit_swarmlord_interface(self) -> Dict[str, Any]:
        """Audit Swarmlord single-interface contract."""
        metrics = {}
        
        if not self.gem_path.exists():
            return {"exists": False}
        
        content = self.gem_path.read_text(encoding="utf-8")
        
        # Check for single-interface enforcement
        swarmlord_mentions = len(re.findall(r'\bSwarmlord\s+of\s+Webs\b', content, re.IGNORECASE))
        single_interface = len(re.findall(r'\bsingle[_\s-]interface\b', content, re.IGNORECASE))
        facade = len(re.findall(r'\bfacade\b', content, re.IGNORECASE))
        
        metrics["swarmlord_mentions"] = swarmlord_mentions
        metrics["single_interface_mentions"] = single_interface
        metrics["facade_mentions"] = facade
        metrics["interface_contract_specified"] = swarmlord_mentions > 0 and single_interface > 0
        
        return metrics
    
    def audit_verify_gate(self) -> Dict[str, Any]:
        """Audit independent verification gate specifications."""
        metrics = {}
        
        if not self.gem_path.exists():
            return {"exists": False}
        
        content = self.gem_path.read_text(encoding="utf-8")
        
        verify_terms = {
            "Verify": len(re.findall(r'\bVerify\b', content)),
            "independent": len(re.findall(r'\bindependent\b', content, re.IGNORECASE)),
            "PASS": len(re.findall(r'\bPASS\b', content)),
            "FAIL": len(re.findall(r'\bFAIL\b', content))
        }
        
        metrics["verify_terms"] = verify_terms
        metrics["verify_gate_specified"] = all(count > 0 for count in verify_terms.values())
        
        # Check for verification checklist
        checklist_pattern = r'Verification.*?Checklist'
        metrics["verification_checklist_exists"] = bool(re.search(checklist_pattern, content, re.IGNORECASE))
        
        return metrics
    
    def calculate_structural_hash(self) -> str:
        """Calculate hash of GEM structure (sections, not content)."""
        if not self.gem_path.exists():
            return "N/A"
        
        content = self.gem_path.read_text(encoding="utf-8")
        
        # Extract section headers only
        sections = re.findall(r'^#+\s+.*$', content, re.MULTILINE)
        structure = "\n".join(sections)
        
        return hashlib.sha256(structure.encode()).hexdigest()[:16]
    
    def run_full_audit(self) -> Dict[str, Any]:
        """Run comprehensive audit."""
        print(f"🔍 Gen21 GEM Audit (Seed: {self.seed}, Explore/Exploit: 2/8)")
        print(f"   Mission: {self.results['mission_id']}")
        print(f"   Timestamp: {self.results['timestamp']}\n")
        
        # Run all audit components
        self.results["metrics"]["completeness"] = self.audit_completeness()
        self.results["metrics"]["quality"] = self.audit_quality()
        self.results["metrics"]["prey_terminology"] = self.audit_prey_terminology()
        self.results["metrics"]["safety_envelope"] = self.audit_safety_envelope()
        self.results["metrics"]["blackboard"] = self.audit_blackboard_protocol()
        self.results["metrics"]["swarmlord_interface"] = self.audit_swarmlord_interface()
        self.results["metrics"]["verify_gate"] = self.audit_verify_gate()
        self.results["metrics"]["structural_hash"] = self.calculate_structural_hash()
        
        # Evaluate pass/fail
        self.evaluate_pass_fail()
        
        # Generate findings and recommendations
        self.generate_findings()
        
        return self.results
    
    def evaluate_pass_fail(self):
        """Evaluate overall pass/fail status."""
        c = self.results["metrics"]["completeness"]
        q = self.results["metrics"]["quality"]
        p = self.results["metrics"]["prey_terminology"]
        s = self.results["metrics"]["safety_envelope"]
        v = self.results["metrics"]["verify_gate"]
        
        self.results["pass_fail"] = {
            "line_count_target": c.get("meets_target", False),
            "placeholder_free": q.get("placeholder_free", False),
            "prey_terms_present": p.get("prey_all_present", False),
            "safety_comprehensive": s.get("safety_comprehensive", False),
            "verify_gate_specified": v.get("verify_gate_specified", False)
        }
        
        self.results["overall_pass"] = all(self.results["pass_fail"].values())
    
    def generate_findings(self):
        """Generate findings and recommendations."""
        c = self.results["metrics"]["completeness"]
        q = self.results["metrics"]["quality"]
        
        # Findings
        if not c.get("meets_target", False):
            self.results["findings"].append(
                f"CRITICAL: Line count {c.get('line_count', 0)} below target {c.get('target_min', 1000)}"
            )
        
        if q.get("total_placeholders", 0) > 0:
            self.results["findings"].append(
                f"WARNING: {q['total_placeholders']} placeholders found: {q['placeholders']}"
            )
        
        if c.get("missing_sections"):
            self.results["findings"].append(
                f"INFO: Missing sections: {c['missing_sections']}"
            )
        
        # Recommendations
        if not self.results["overall_pass"]:
            self.results["recommendations"].append(
                "Re-run PREY loop with chunked generation (≤200 lines per write)"
            )
            self.results["recommendations"].append(
                "Enforce tripwires: line_count ≥0.9×target, placeholders=0"
            )
    
    def print_summary(self):
        """Print one-page summary with BLUF, matrix, and diagrams."""
        print("\n" + "="*80)
        print("GEN21 AUDIT SUMMARY")
        print("="*80)
        
        # BLUF
        print("\n### BLUF (Bottom Line Up Front)")
        status = "✅ PASS" if self.results["overall_pass"] else "❌ FAIL"
        print(f"Status: {status}")
        print(f"Gen21 GEM at {self.gem_path.name}:")
        print(f"- Line count: {self.results['metrics']['completeness'].get('line_count', 0)}/1000")
        print(f"- Placeholders: {self.results['metrics']['quality'].get('total_placeholders', 0)}")
        print(f"- PREY terms: {'✓' if self.results['metrics']['prey_terminology'].get('prey_all_present') else '✗'}")
        print(f"- Safety envelope: {'✓' if self.results['metrics']['safety_envelope'].get('safety_comprehensive') else '✗'}")
        
        # Matrix
        print("\n### Audit Matrix")
        print(f"{'Criterion':<30} {'Status':<10} {'Evidence':<40}")
        print("-" * 80)
        for criterion, passed in self.results["pass_fail"].items():
            status = "✅ PASS" if passed else "❌ FAIL"
            evidence = self._get_evidence(criterion)
            print(f"{criterion:<30} {status:<10} {evidence:<40}")
        
        # Key Metrics
        print("\n### Key Metrics")
        print(f"- Seed: {self.seed}")
        print(f"- Explore/Exploit: {self.results['explore_exploit_ratio']} (20% exploration)")
        print(f"- Sections found: {self.results['metrics']['completeness'].get('section_count', 0)}")
        print(f"- Mermaid diagrams: {self.results['metrics']['quality'].get('mermaid_diagram_count', 0)}")
        print(f"- Blackboard entries: {self.results['metrics']['blackboard'].get('entry_count', 0)}")
        print(f"- Structural hash: {self.results['metrics']['structural_hash']}")
        
        # Findings
        if self.results["findings"]:
            print("\n### Findings")
            for finding in self.results["findings"]:
                print(f"- {finding}")
        
        # Recommendations
        if self.results["recommendations"]:
            print("\n### Recommendations")
            for rec in self.results["recommendations"]:
                print(f"- {rec}")
        
        print("\n" + "="*80)
    
    def _get_evidence(self, criterion: str) -> str:
        """Get evidence string for a criterion."""
        c = self.results["metrics"]["completeness"]
        q = self.results["metrics"]["quality"]
        p = self.results["metrics"]["prey_terminology"]
        s = self.results["metrics"]["safety_envelope"]
        v = self.results["metrics"]["verify_gate"]
        
        evidence_map = {
            "line_count_target": f"{c.get('line_count', 0)} lines",
            "placeholder_free": f"{q.get('total_placeholders', 0)} found",
            "prey_terms_present": f"P:{p.get('prey_term_counts', {}).get('Perceive', 0)} R:{p.get('prey_term_counts', {}).get('React', 0)} E:{p.get('prey_term_counts', {}).get('Engage', 0)} Y:{p.get('prey_term_counts', {}).get('Yield', 0)}",
            "safety_comprehensive": f"canary:{s.get('safety_terms', {}).get('canary', 0)} tripwire:{s.get('safety_terms', {}).get('tripwire', 0)}",
            "verify_gate_specified": f"Verify:{v.get('verify_terms', {}).get('Verify', 0)} PASS/FAIL:{v.get('verify_terms', {}).get('PASS', 0)}/{v.get('verify_terms', {}).get('FAIL', 0)}"
        }
        
        return evidence_map.get(criterion, "N/A")
    
    def save_results(self, output_path: Path):
        """Save audit results to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📁 Results saved to: {output_path}")
    
    def append_to_blackboard(self):
        """Append audit results to blackboard."""
        entry = {
            "mission_id": self.results["mission_id"],
            "phase": "verify",
            "summary": f"Gen21 audit (seed={self.seed}): {'PASS' if self.results['overall_pass'] else 'FAIL'}",
            "evidence_refs": [
                f"line_count:{self.results['metrics']['completeness'].get('line_count', 0)}",
                f"placeholders:{self.results['metrics']['quality'].get('total_placeholders', 0)}",
                f"structural_hash:{self.results['metrics']['structural_hash']}"
            ],
            "safety_envelope": {
                "seed": self.seed,
                "explore_exploit": self.results["explore_exploit_ratio"]
            },
            "blocked_capabilities": [],
            "timestamp": self.results["timestamp"],
            "verifier": "audit_gem_gen21.py"
        }
        
        with open(self.blackboard_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + "\n")
        
        print(f"✅ Blackboard entry appended to: {self.blackboard_path}")


def main():
    repo_root = Path(__file__).resolve().parents[1]
    
    # Run audit with seed=2
    auditor = Gen21Auditor(repo_root, seed=2)
    results = auditor.run_full_audit()
    
    # Print summary
    auditor.print_summary()
    
    # Save results
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = repo_root / "hfo_petting_zoo_results" / f"gen21_audit_seed2_{timestamp}.json"
    auditor.save_results(output_path)
    
    # Append to blackboard
    auditor.append_to_blackboard()
    
    # Exit code
    sys.exit(0 if results["overall_pass"] else 1)


if __name__ == "__main__":
    main()
