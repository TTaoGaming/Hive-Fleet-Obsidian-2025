#!/usr/bin/env python3
"""
Test Gen21's self-regeneration capability.

This script tests whether Gen21 contains enough information to regenerate itself
by extracting key components and checking completeness.

Test strategy:
1. Extract all section headers and required content
2. Verify bootstrap instructions are executable
3. Check for circular dependencies
4. Test explore/exploit ratio specification
5. Validate that diagrams are complete (no placeholders)
"""

from __future__ import annotations
import re
import json
import sys
from pathlib import Path
from typing import List, Dict, Any


REPO_ROOT = Path(__file__).resolve().parents[1]
GEN21_PATH = REPO_ROOT / "hfo_gem" / "gen_21" / "gpt5-attempt-3-gem.md"


class RegenerationTester:
    """Test Gen21 self-regeneration capability."""
    
    def __init__(self):
        self.content = ""
        self.sections: Dict[str, str] = {}
        self.test_results: List[Dict[str, Any]] = []
        
    def load_gen21(self) -> None:
        """Load Gen21 document."""
        if not GEN21_PATH.exists():
            self.add_test_result("load", False, "Gen21 file not found")
            return
        
        self.content = GEN21_PATH.read_text(encoding="utf-8")
        self.add_test_result("load", True, f"Loaded {len(self.content)} chars")
        
    def extract_sections(self) -> None:
        """Extract all sections from Gen21."""
        # Find section headers
        section_pattern = r'^##\s+(Section \d+:|Appendix [A-Z]:)\s*(.+?)$'
        matches = list(re.finditer(section_pattern, self.content, re.MULTILINE))
        
        for i, match in enumerate(matches):
            section_name = match.group(0).strip()
            start = match.end()
            end = matches[i+1].start() if i+1 < len(matches) else len(self.content)
            section_content = self.content[start:end].strip()
            self.sections[section_name] = section_content
        
        self.add_test_result("extract_sections", len(self.sections) > 0,
                           f"Found {len(self.sections)} sections")
    
    def test_bootstrap_executable(self) -> None:
        """Test if bootstrap instructions are executable."""
        # Look for bootstrap section
        bootstrap_section = None
        for section_name, content in self.sections.items():
            if "bootstrap" in section_name.lower():
                bootstrap_section = content
                break
        
        if not bootstrap_section:
            self.add_test_result("bootstrap_executable", False,
                               "No bootstrap section found")
            return
        
        # Check for numbered steps
        steps = re.findall(r'^\d+\)', bootstrap_section, re.MULTILINE)
        
        # Check for file paths
        file_paths = re.findall(r'`([^`]+\.(md|yml|yaml|jsonl))`', bootstrap_section)
        
        # Check for concrete actions
        action_verbs = ['place', 'create', 'initiate', 'run', 'execute']
        actions_found = [verb for verb in action_verbs 
                        if verb in bootstrap_section.lower()]
        
        success = len(steps) >= 1 and len(file_paths) >= 1 and len(actions_found) >= 1
        
        self.add_test_result("bootstrap_executable", success,
                           f"Steps: {len(steps)}, Paths: {len(file_paths)}, Actions: {actions_found}")
    
    def test_prey_completeness(self) -> None:
        """Test if PREY workflow is completely specified."""
        prey_phases = ["Perceive", "React", "Engage", "Yield"]
        
        missing_specs = []
        for phase in prey_phases:
            # Look for phase definition
            phase_pattern = rf'{phase}\s*\([A-Z]\).*?(?:Purpose:|Outputs:)'
            if not re.search(phase_pattern, self.content, re.DOTALL):
                missing_specs.append(phase)
        
        self.add_test_result("prey_completeness", 
                           len(missing_specs) == 0,
                           f"Missing: {missing_specs}" if missing_specs 
                           else "All PREY phases specified")
    
    def test_diagram_completeness(self) -> None:
        """Test if diagrams are complete (no placeholders)."""
        # Find all mermaid diagrams
        mermaid_blocks = re.findall(r'```mermaid(.*?)```', self.content, re.DOTALL)
        
        placeholder_patterns = [
            r'\.\.\.',
            r'TODO',
            r'TBD',
            r'PLACEHOLDER',
            r'\[insert\s',
        ]
        
        incomplete_diagrams = []
        for i, block in enumerate(mermaid_blocks):
            for pattern in placeholder_patterns:
                if re.search(pattern, block, re.I):
                    incomplete_diagrams.append(f"Diagram {i+1}")
                    break
        
        self.add_test_result("diagram_completeness",
                           len(incomplete_diagrams) == 0,
                           f"Found {len(mermaid_blocks)} diagrams, " +
                           f"{len(incomplete_diagrams)} incomplete")
    
    def test_explore_exploit_spec(self) -> None:
        """Test if explore/exploit ratio is specified."""
        # Look for explore/exploit or quality diversity mentions
        ee_patterns = [
            r'explore.*exploit',
            r'quality.*diversity',
            r'QD',
            r'8/2|80/20',
        ]
        
        found = []
        for pattern in ee_patterns:
            if re.search(pattern, self.content, re.I):
                found.append(pattern)
        
        self.add_test_result("explore_exploit_spec",
                           len(found) > 0,
                           f"Found patterns: {found}")
    
    def test_circular_dependencies(self) -> None:
        """Test for circular dependencies in regeneration."""
        # Check if Gen21 requires something that requires Gen21
        # Simple heuristic: look for "requires" or "depends on"
        
        dependency_pattern = r'(?:require|depend).*?(?:Gen.*?21|this document)'
        dependencies = re.findall(dependency_pattern, self.content, re.I)
        
        # Self-reference is OK, but not circular dependencies
        # For now, just flag if there are too many
        self.add_test_result("circular_dependencies",
                           len(dependencies) < 10,
                           f"Found {len(dependencies)} dependency mentions")
    
    def test_evidence_discipline(self) -> None:
        """Test if evidence discipline is specified."""
        # Look for evidence_refs specification
        evidence_patterns = [
            r'evidence_refs',
            r'blackboard.*receipt',
            r'append.*jsonl',
        ]
        
        found = sum(1 for pattern in evidence_patterns 
                   if re.search(pattern, self.content, re.I))
        
        self.add_test_result("evidence_discipline",
                           found >= 2,
                           f"Found {found}/3 evidence patterns")
    
    def test_safety_envelope_spec(self) -> None:
        """Test if safety envelope is fully specified."""
        safety_components = {
            "canary": r'\bcanary\b',
            "tripwires": r'\btripwire',
            "revert": r'\brevert\b',
        }
        
        found = {name: bool(re.search(pattern, self.content, re.I))
                for name, pattern in safety_components.items()}
        
        all_present = all(found.values())
        
        self.add_test_result("safety_envelope_spec", all_present,
                           f"Components: {found}")
    
    def add_test_result(self, test_name: str, passed: bool, 
                       details: str) -> None:
        """Add a test result."""
        self.test_results.append({
            "test": test_name,
            "status": "PASS" if passed else "FAIL",
            "details": details
        })
    
    def run_tests(self) -> Dict[str, Any]:
        """Run all regeneration tests."""
        self.load_gen21()
        
        if self.content:
            self.extract_sections()
            self.test_bootstrap_executable()
            self.test_prey_completeness()
            self.test_diagram_completeness()
            self.test_explore_exploit_spec()
            self.test_circular_dependencies()
            self.test_evidence_discipline()
            self.test_safety_envelope_spec()
        
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        total = len(self.test_results)
        
        regeneration_score = passed / total if total > 0 else 0.0
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "regeneration_score": regeneration_score,
            "test_results": self.test_results
        }


def main() -> int:
    """Run regeneration tests."""
    tester = RegenerationTester()
    results = tester.run_tests()
    
    print(json.dumps(results, indent=2))
    
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
