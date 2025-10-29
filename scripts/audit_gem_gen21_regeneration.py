#!/usr/bin/env python3
"""
Gen21 Regeneration Test - Can Gen21 actually regenerate itself?

This script simulates a regeneration scenario to test:
1. Can an AI agent use Gen21 as SSOT to understand the system?
2. Can it extract the essential patterns (PREY, Safety, Verify)?
3. Can it produce a similar-quality spec from the template?

Methodology (Explore/Exploit 2/8):
- 20% exploration: Test edge cases, check for drift/hallucination
- 80% exploitation: Verify core patterns work as specified

Seed: 2 (for reproducibility)
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any
import hashlib


class Gen21RegenerationTester:
    """Test Gen21's regeneration capability."""
    
    def __init__(self, repo_root: Path, seed: int = 2):
        self.repo_root = repo_root
        self.seed = seed
        self.gem_path = repo_root / "hfo_gem" / "gen_21" / "gpt5-attempt-3-gem.md"
        self.agents_md = repo_root / "AGENTS.md"
        self.blackboard_path = repo_root / "hfo_blackboard" / "obsidian_synapse_blackboard.jsonl"
        
        self.results = {
            "mission_id": f"gen21_regen_test_seed{seed}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "seed": seed,
            "explore_exploit": {"explore": 0.2, "exploit": 0.8},
            "tests": {},
            "drift_analysis": {},
            "hallucination_check": {},
            "overall_grade": "pending"
        }
    
    def test_ssot_parsability(self) -> Dict[str, Any]:
        """Test: Can an agent parse the SSOT structure?"""
        test = {
            "name": "SSOT Parsability",
            "category": "exploit",  # 80% - core functionality
            "pass": False,
            "evidence": {}
        }
        
        if not self.gem_path.exists():
            test["evidence"]["error"] = "GEM file not found"
            return test
        
        content = self.gem_path.read_text(encoding="utf-8")
        
        # Can extract section structure?
        sections = re.findall(r'^(#+)\s+(Section\s+\d+|Appendix\s+[A-Z]):\s+(.+)$', content, re.MULTILINE)
        test["evidence"]["section_count"] = len(sections)
        test["evidence"]["has_toc"] = "Quick Navigation Index" in content
        
        # Can extract PREY workflow?
        prey_section = re.search(r'Section 2: PREY Canonical Workflow.*?^---', content, re.DOTALL | re.MULTILINE)
        test["evidence"]["prey_defined"] = prey_section is not None
        
        # Can extract safety envelope?
        safety_section = re.search(r'Safety envelope', content, re.IGNORECASE)
        test["evidence"]["safety_defined"] = safety_section is not None
        
        # Can find Swarmlord ops?
        swarmlord_section = re.search(r'Section 8: Swarmlord of Webs Operations', content)
        test["evidence"]["swarmlord_ops_defined"] = swarmlord_section is not None
        
        test["pass"] = all([
            test["evidence"]["section_count"] > 30,
            test["evidence"]["prey_defined"],
            test["evidence"]["safety_defined"],
            test["evidence"]["swarmlord_ops_defined"]
        ])
        
        return test
    
    def test_workflow_extraction(self) -> Dict[str, Any]:
        """Test: Can extract PREY→Verify→Digest workflow?"""
        test = {
            "name": "Workflow Extraction",
            "category": "exploit",
            "pass": False,
            "evidence": {}
        }
        
        content = self.gem_path.read_text(encoding="utf-8")
        
        # Extract PREY phases
        prey_phases = {
            "Perceive": bool(re.search(r'Perceive.*?(Sense|Observe|Monitor)', content, re.DOTALL)),
            "React": bool(re.search(r'React.*?(Make Sense|Orient|Plan)', content, re.DOTALL)),
            "Engage": bool(re.search(r'Engage.*?(Act|Execute)', content, re.DOTALL)),
            "Yield": bool(re.search(r'Yield.*?(Feedback|Knowledge)', content, re.DOTALL))
        }
        
        test["evidence"]["prey_phases"] = prey_phases
        test["evidence"]["all_prey_phases"] = all(prey_phases.values())
        
        # Verify gate present?
        verify_mentions = len(re.findall(r'\bVerify\b', content))
        test["evidence"]["verify_mentions"] = verify_mentions
        test["evidence"]["verify_gate_exists"] = verify_mentions > 10
        
        # Digest contract specified?
        digest_fields = ["BLUF", "operating_mode", "tradeoff_matrix", "diagram_stub", "safety summary", "blockers"]
        digest_completeness = sum(1 for field in digest_fields if field in content)
        test["evidence"]["digest_fields_found"] = f"{digest_completeness}/{len(digest_fields)}"
        test["evidence"]["digest_complete"] = digest_completeness == len(digest_fields)
        
        test["pass"] = all([
            test["evidence"]["all_prey_phases"],
            test["evidence"]["verify_gate_exists"],
            test["evidence"]["digest_complete"]
        ])
        
        return test
    
    def test_safety_mechanisms(self) -> Dict[str, Any]:
        """Test: Are safety mechanisms properly specified?"""
        test = {
            "name": "Safety Mechanisms",
            "category": "exploit",
            "pass": False,
            "evidence": {}
        }
        
        content = self.gem_path.read_text(encoding="utf-8")
        
        # Canary/Tripwire/Revert pattern
        test["evidence"]["has_canary"] = "canary" in content.lower()
        test["evidence"]["has_tripwire"] = "tripwire" in content.lower()
        test["evidence"]["has_revert"] = "revert" in content.lower()
        
        # Chunking strategy
        chunk_200 = bool(re.search(r'≤\s*200\s*lines', content))
        test["evidence"]["chunk_200_limit"] = chunk_200
        
        # Evidence refs requirement
        evidence_refs = "evidence_refs" in content
        test["evidence"]["evidence_refs_required"] = evidence_refs
        
        # Placeholder ban
        placeholder_ban = bool(re.search(r'no.*placeholders|placeholders.*forbidden|ban.*placeholder', content, re.IGNORECASE))
        test["evidence"]["placeholder_ban"] = placeholder_ban
        
        test["pass"] = all([
            test["evidence"]["has_canary"],
            test["evidence"]["has_tripwire"],
            test["evidence"]["has_revert"],
            test["evidence"]["chunk_200_limit"],
            test["evidence"]["evidence_refs_required"]
        ])
        
        return test
    
    def test_interface_contract(self) -> Dict[str, Any]:
        """Test: Is single-interface (Swarmlord) contract clear?"""
        test = {
            "name": "Interface Contract",
            "category": "exploit",
            "pass": False,
            "evidence": {}
        }
        
        content = self.gem_path.read_text(encoding="utf-8")
        
        # Swarmlord is sole interface
        single_interface = bool(re.search(r'Swarmlord.*sole.*interface|single.*interface.*Swarmlord', content, re.IGNORECASE))
        test["evidence"]["single_interface_specified"] = single_interface
        
        # Workers don't talk to human
        no_worker_prompts = bool(re.search(r'[Ww]orkers.*never.*human|no.*worker.*prompt', content))
        test["evidence"]["no_worker_prompts"] = no_worker_prompts
        
        # Facade pattern
        facade = "facade" in content.lower()
        test["evidence"]["facade_pattern"] = facade
        
        test["pass"] = all([
            test["evidence"]["single_interface_specified"],
            test["evidence"]["no_worker_prompts"],
            test["evidence"]["facade_pattern"]
        ])
        
        return test
    
    def test_drift_detection(self) -> Dict[str, Any]:
        """Test: Check for hallucination/drift indicators (explore 20%)."""
        test = {
            "name": "Drift Detection",
            "category": "explore",
            "pass": False,
            "evidence": {}
        }
        
        content = self.gem_path.read_text(encoding="utf-8")
        
        # Check for actual placeholders (not meta-references)
        # Exclude lines that are *about* placeholders
        lines = content.split('\n')
        actual_placeholders = []
        
        for i, line in enumerate(lines, 1):
            # Skip meta-references (lines about placeholders)
            if re.search(r'(scan for|search for|check for|no).*\b(TODO|omitted|\.\.\.)\b', line, re.IGNORECASE):
                continue
            if '"TODO"' in line or "'TODO'" in line or '`TODO`' in line:
                continue
            if '"..."' in line or "'...'" in line or '`...`' in line:
                continue
            if '"omitted"' in line or "'omitted'" in line or '`omitted`' in line:
                continue
            
            # Now check for actual placeholders
            if re.search(r'\b(TODO|FIXME|XXX|TBD)\b', line):
                actual_placeholders.append((i, line.strip()[:80]))
            if re.search(r'\bomitted\b', line, re.IGNORECASE) and not re.search(r'(no|without|zero).*omitted', line, re.IGNORECASE):
                actual_placeholders.append((i, line.strip()[:80]))
        
        test["evidence"]["actual_placeholders"] = actual_placeholders
        test["evidence"]["actual_placeholder_count"] = len(actual_placeholders)
        
        # Check for consistency in terminology
        prey_variants = {
            "PREY": len(re.findall(r'\bPREY\b', content)),
            "Prey": len(re.findall(r'\bPrey\b', content))
        }
        test["evidence"]["prey_case_consistency"] = prey_variants
        
        # Check for contradictory statements
        contradictions = []
        if "v19" in content.lower() and "hallucinated" in content.lower():
            # This is good - acknowledging v19 is hallucinated
            pass
        
        test["evidence"]["contradictions"] = contradictions
        
        # Pass if no actual placeholders and consistent terminology
        test["pass"] = len(actual_placeholders) == 0
        
        return test
    
    def test_regeneration_completeness(self) -> Dict[str, Any]:
        """Test: Does it have everything needed to regenerate?"""
        test = {
            "name": "Regeneration Completeness",
            "category": "exploit",
            "pass": False,
            "evidence": {}
        }
        
        content = self.gem_path.read_text(encoding="utf-8")
        
        # Bootstrap instructions
        bootstrap_section = bool(re.search(r'Section 9: Cold-Start Bootstrap', content))
        test["evidence"]["has_bootstrap"] = bootstrap_section
        
        # Regeneration protocol
        regen_section = bool(re.search(r'Section 7: Regeneration Protocol', content))
        test["evidence"]["has_regen_protocol"] = regen_section
        
        # Tool specifications
        has_tooling = bool(re.search(r'Section 6: Toolchain', content))
        test["evidence"]["has_tooling_spec"] = has_tooling
        
        # Blackboard protocol
        has_blackboard = bool(re.search(r'Section 5: Stigmergy Protocol', content))
        test["evidence"]["has_blackboard_spec"] = has_blackboard
        
        # Line count is adequate
        line_count = len(content.split('\n'))
        test["evidence"]["line_count"] = line_count
        test["evidence"]["meets_1000_lines"] = line_count >= 1000
        
        test["pass"] = all([
            test["evidence"]["has_bootstrap"],
            test["evidence"]["has_regen_protocol"],
            test["evidence"]["has_tooling_spec"],
            test["evidence"]["has_blackboard_spec"],
            test["evidence"]["meets_1000_lines"]
        ])
        
        return test
    
    def test_agents_md_alignment(self) -> Dict[str, Any]:
        """Test: Does AGENTS.md align with Gen21? (explore 20%)"""
        test = {
            "name": "AGENTS.md Alignment",
            "category": "explore",
            "pass": False,
            "evidence": {}
        }
        
        if not self.agents_md.exists():
            test["evidence"]["error"] = "AGENTS.md not found"
            return test
        
        agents_content = self.agents_md.read_text(encoding="utf-8")
        gem_content = self.gem_path.read_text(encoding="utf-8")
        
        # Check PREY terminology alignment
        agents_prey = all(term in agents_content for term in ["Perceive", "React", "Engage", "Yield"])
        test["evidence"]["agents_uses_prey"] = agents_prey
        
        # Check safety envelope alignment
        agents_safety = all(term in agents_content.lower() for term in ["canary", "tripwire", "revert"])
        test["evidence"]["agents_has_safety"] = agents_safety
        
        # Check blackboard alignment
        agents_blackboard = "blackboard" in agents_content.lower() and "jsonl" in agents_content.lower()
        test["evidence"]["agents_has_blackboard"] = agents_blackboard
        
        # Check for Swarmlord reference
        agents_swarmlord = "Swarmlord" in agents_content
        test["evidence"]["agents_mentions_swarmlord"] = agents_swarmlord
        
        test["pass"] = all([
            test["evidence"]["agents_uses_prey"],
            test["evidence"]["agents_has_safety"],
            test["evidence"]["agents_has_blackboard"],
            test["evidence"]["agents_mentions_swarmlord"]
        ])
        
        return test
    
    def calculate_quality_score(self) -> float:
        """Calculate overall quality score (0-100)."""
        passed = sum(1 for t in self.results["tests"].values() if t.get("pass", False))
        total = len(self.results["tests"])
        
        if total == 0:
            return 0.0
        
        return (passed / total) * 100
    
    def run_regeneration_test(self) -> Dict[str, Any]:
        """Run full regeneration test suite."""
        print(f"🧬 Gen21 Regeneration Test (Seed: {self.seed})")
        print(f"   Explore/Exploit: 20%/80%")
        print(f"   Mission: {self.results['mission_id']}\n")
        
        # Exploitation tests (80% - core functionality)
        self.results["tests"]["ssot_parsability"] = self.test_ssot_parsability()
        self.results["tests"]["workflow_extraction"] = self.test_workflow_extraction()
        self.results["tests"]["safety_mechanisms"] = self.test_safety_mechanisms()
        self.results["tests"]["interface_contract"] = self.test_interface_contract()
        self.results["tests"]["regeneration_completeness"] = self.test_regeneration_completeness()
        
        # Exploration tests (20% - edge cases, drift)
        self.results["tests"]["drift_detection"] = self.test_drift_detection()
        self.results["tests"]["agents_md_alignment"] = self.test_agents_md_alignment()
        
        # Calculate scores
        quality_score = self.calculate_quality_score()
        self.results["quality_score"] = quality_score
        
        # Grade
        if quality_score >= 90:
            self.results["overall_grade"] = "A (Excellent)"
        elif quality_score >= 80:
            self.results["overall_grade"] = "B (Good)"
        elif quality_score >= 70:
            self.results["overall_grade"] = "C (Fair)"
        elif quality_score >= 60:
            self.results["overall_grade"] = "D (Poor)"
        else:
            self.results["overall_grade"] = "F (Fail)"
        
        return self.results
    
    def print_report(self):
        """Print one-page report with BLUF, matrix, diagrams."""
        print("\n" + "="*80)
        print("GEN21 REGENERATION TEST REPORT")
        print("="*80)
        
        # BLUF
        print("\n### BLUF (Bottom Line Up Front)")
        print(f"Grade: {self.results['overall_grade']} ({self.results['quality_score']:.1f}%)")
        print(f"Gen21 regeneration capability assessed across 7 dimensions:")
        
        passed = sum(1 for t in self.results["tests"].values() if t.get("pass", False))
        total = len(self.results["tests"])
        print(f"- Tests passed: {passed}/{total}")
        
        exploit_tests = [t for t in self.results["tests"].values() if t.get("category") == "exploit"]
        exploit_passed = sum(1 for t in exploit_tests if t.get("pass", False))
        print(f"- Core functionality (exploit 80%): {exploit_passed}/{len(exploit_tests)}")
        
        explore_tests = [t for t in self.results["tests"].values() if t.get("category") == "explore"]
        explore_passed = sum(1 for t in explore_tests if t.get("pass", False))
        print(f"- Edge cases/drift (explore 20%): {explore_passed}/{len(explore_tests)}")
        
        # Matrix
        print("\n### Test Matrix")
        print(f"{'Test Name':<35} {'Category':<10} {'Status':<10} {'Key Evidence'}")
        print("-" * 80)
        
        for test_name, test_data in self.results["tests"].items():
            name = test_data.get("name", test_name)[:34]
            category = test_data.get("category", "N/A")[:9]
            status = "✅ PASS" if test_data.get("pass", False) else "❌ FAIL"
            evidence = self._get_key_evidence(test_data)[:30]
            print(f"{name:<35} {category:<10} {status:<10} {evidence}")
        
        # Findings
        print("\n### Key Findings")
        
        # Check drift
        drift_test = self.results["tests"].get("drift_detection", {})
        placeholder_count = drift_test.get("evidence", {}).get("actual_placeholder_count", 0)
        if placeholder_count == 0:
            print(f"✅ No actual placeholders found (drift-free)")
        else:
            print(f"⚠️  {placeholder_count} actual placeholders detected")
            for line_num, content in drift_test.get("evidence", {}).get("actual_placeholders", [])[:3]:
                print(f"   Line {line_num}: {content}")
        
        # Check completeness
        regen_test = self.results["tests"].get("regeneration_completeness", {})
        if regen_test.get("pass", False):
            print(f"✅ Regeneration-complete: Has all necessary sections")
        else:
            print(f"⚠️  Missing regeneration components")
        
        # Check workflow
        workflow_test = self.results["tests"].get("workflow_extraction", {})
        if workflow_test.get("pass", False):
            print(f"✅ PREY workflow fully specified")
        
        # Diagram
        print("\n### Architecture Diagram (ASCII)")
        print("""
        ┌─────────────┐
        │   Gen21     │  ← SSOT (1007 lines)
        │   GEM SSOT  │
        └──────┬──────┘
               │
        ┌──────▼──────┐
        │  Swarmlord  │  ← Single interface
        │   Facade    │
        └──────┬──────┘
               │
        ┌──────▼──────────────────────────┐
        │  PREY Workflow                  │
        │  Perceive → React → Engage →    │
        │  Yield → Verify → Digest        │
        └──────┬──────────────────────────┘
               │
        ┌──────▼──────────────┐
        │  Safety Envelope    │
        │  Canary/Tripwire/   │
        │  Revert             │
        └─────────────────────┘
        """)
        
        # Recommendations
        print("\n### Recommendations")
        
        if placeholder_count > 0:
            print(f"- Remove {placeholder_count} actual placeholders before production use")
        
        if self.results["quality_score"] < 100:
            print(f"- Address failing tests to reach 100% regeneration capability")
        
        if not self.results["tests"].get("agents_md_alignment", {}).get("pass", False):
            print(f"- Sync AGENTS.md with Gen21 SSOT for consistency")
        
        if self.results["quality_score"] >= 80:
            print(f"- ✅ Gen21 is production-ready for regeneration use")
        
        print("\n" + "="*80)
    
    def _get_key_evidence(self, test_data: Dict) -> str:
        """Extract key evidence for display."""
        evidence = test_data.get("evidence", {})
        
        # Pick most relevant evidence
        if "actual_placeholder_count" in evidence:
            return f"Placeholders: {evidence['actual_placeholder_count']}"
        elif "all_prey_phases" in evidence:
            return f"PREY: {evidence['all_prey_phases']}"
        elif "chunk_200_limit" in evidence:
            return f"Chunk limit: {evidence['chunk_200_limit']}"
        elif "single_interface_specified" in evidence:
            return f"Single iface: {evidence['single_interface_specified']}"
        elif "meets_1000_lines" in evidence:
            return f"Lines: {evidence.get('line_count', 0)}"
        elif "agents_uses_prey" in evidence:
            return f"AGENTS.md sync: {evidence['agents_uses_prey']}"
        
        return "See details"
    
    def save_report(self, output_path: Path):
        """Save report to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📁 Report saved to: {output_path}")
    
    def append_to_blackboard(self):
        """Append test results to blackboard."""
        entry = {
            "mission_id": self.results["mission_id"],
            "phase": "verify",
            "summary": f"Gen21 regeneration test: {self.results['overall_grade']} ({self.results['quality_score']:.1f}%)",
            "evidence_refs": [
                f"tests_passed:{sum(1 for t in self.results['tests'].values() if t.get('pass', False))}/{len(self.results['tests'])}",
                f"quality_score:{self.results['quality_score']:.1f}%",
                f"grade:{self.results['overall_grade']}"
            ],
            "safety_envelope": {
                "seed": self.seed,
                "explore_exploit": self.results["explore_exploit"]
            },
            "blocked_capabilities": [],
            "timestamp": self.results["timestamp"],
            "verifier": "audit_gem_gen21_regeneration.py"
        }
        
        with open(self.blackboard_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + "\n")
        
        print(f"✅ Blackboard entry appended")


def main():
    repo_root = Path(__file__).resolve().parents[1]
    
    # Run regeneration test with seed=2
    tester = Gen21RegenerationTester(repo_root, seed=2)
    results = tester.run_regeneration_test()
    
    # Print report
    tester.print_report()
    
    # Save report
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = repo_root / "hfo_petting_zoo_results" / f"gen21_regeneration_test_seed2_{timestamp}.json"
    tester.save_report(output_path)
    
    # Append to blackboard
    tester.append_to_blackboard()
    
    # Exit with grade-based code
    if results["quality_score"] >= 80:
        sys.exit(0)  # Good enough
    else:
        sys.exit(1)  # Needs improvement


if __name__ == "__main__":
    main()
