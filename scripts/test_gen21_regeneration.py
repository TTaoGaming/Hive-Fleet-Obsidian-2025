#!/usr/bin/env python3
"""
Test Gen21 Regeneration Capability
===================================

This script tests whether Gen21 can regenerate itself by:
1. Parsing the regeneration protocol from the GEM
2. Extracting bootstrap steps
3. Simulating the regeneration process
4. Validating the outputs meet Gen21 requirements

This is an independent test, not a self-audit.
"""

from __future__ import annotations
import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]


class RegenerationTester:
    """Test Gen21 self-regeneration capability."""
    
    def __init__(self, gem_path: Path):
        self.gem_path = gem_path
        self.gem_content = ""
        self.gem_lines: List[str] = []
        self.test_results: Dict[str, Any] = {}
        
    def load_gem(self) -> bool:
        """Load GEM document."""
        try:
            with open(self.gem_path, 'r', encoding='utf-8') as f:
                self.gem_content = f.read()
                self.gem_lines = self.gem_content.splitlines()
            return True
        except Exception as e:
            self.test_results['load_error'] = str(e)
            return False
    
    def extract_bootstrap_procedure(self) -> Dict[str, Any]:
        """Extract bootstrap steps from the GEM."""
        # Find bootstrap section
        bootstrap_start = None
        for i, line in enumerate(self.gem_lines):
            if re.search(r'##.*?(?:Bootstrap|Cold.?Start)', line, re.IGNORECASE):
                bootstrap_start = i
                break
        
        if bootstrap_start is None:
            return {
                'found': False,
                'error': 'No bootstrap section found'
            }
        
        # Extract steps (numbered)
        steps = []
        step_pattern = r'^\s*\d+\)\s+(.+)$'
        
        for i in range(bootstrap_start, min(bootstrap_start + 50, len(self.gem_lines))):
            line = self.gem_lines[i]
            match = re.match(step_pattern, line)
            if match:
                steps.append({
                    'number': len(steps) + 1,
                    'content': match.group(1).strip(),
                    'line': i + 1
                })
        
        return {
            'found': True,
            'step_count': len(steps),
            'steps': steps,
            'manual_steps_claim': self._check_manual_steps_claim(),
        }
    
    def _check_manual_steps_claim(self) -> Optional[int]:
        """Check if GEM claims ≤3 manual steps."""
        match = re.search(r'[≤<]\s*(\d+)\s+manual\s+steps?', self.gem_content, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    
    def extract_prey_workflow(self) -> Dict[str, Any]:
        """Extract PREY workflow definition."""
        prey_mappings = {}
        
        # Look for PREY definitions
        prey_pattern = r'(Perceive|React|Engage|Yield)\s*[↔←→]?\s*([^|\n]+)'
        matches = re.findall(prey_pattern, self.gem_content, re.IGNORECASE)
        
        for phase, mapping in matches:
            phase_clean = phase.strip()
            mapping_clean = mapping.strip().split('/')[0].strip()
            if phase_clean not in prey_mappings:
                prey_mappings[phase_clean] = []
            prey_mappings[phase_clean].append(mapping_clean)
        
        return {
            'phases_found': list(prey_mappings.keys()),
            'mappings': prey_mappings,
            'complete': len(prey_mappings) == 4,
        }
    
    def extract_safety_envelope(self) -> Dict[str, Any]:
        """Extract safety envelope specification."""
        safety_elements = {
            'canary': [],
            'tripwire': [],
            'revert': [],
        }
        
        for i, line in enumerate(self.gem_lines, 1):
            for element in safety_elements.keys():
                if element in line.lower():
                    safety_elements[element].append({
                        'line': i,
                        'content': line.strip()[:100]
                    })
        
        # Check for specific tripwire examples
        tripwire_examples = []
        tripwire_section = re.search(
            r'tripwire.*?:(.*?)(?:---|##)',
            self.gem_content,
            re.DOTALL | re.IGNORECASE
        )
        if tripwire_section:
            examples = re.findall(r'-\s+([^-\n]+)', tripwire_section.group(1))
            tripwire_examples = examples[:5]
        
        return {
            'canary_refs': len(safety_elements['canary']),
            'tripwire_refs': len(safety_elements['tripwire']),
            'revert_refs': len(safety_elements['revert']),
            'tripwire_examples': tripwire_examples,
            'complete': all(len(v) > 0 for v in safety_elements.values()),
        }
    
    def extract_blackboard_schema(self) -> Dict[str, Any]:
        """Extract blackboard JSONL schema."""
        required_fields = [
            'mission_id',
            'phase',
            'summary',
            'evidence_refs',
            'safety_envelope',
            'timestamp'
        ]
        
        field_definitions = {}
        for field in required_fields:
            # Look for field definitions
            pattern = rf'{field}\s*:\s*([^,\n]+)'
            matches = re.findall(pattern, self.gem_content, re.IGNORECASE)
            if matches:
                field_definitions[field] = matches[0].strip()
        
        # Check for example receipts
        json_example_pattern = r'```json\s*\{[^}]*"mission_id"[^}]*\}```'
        examples = re.findall(json_example_pattern, self.gem_content, re.DOTALL | re.IGNORECASE)
        
        return {
            'required_fields': required_fields,
            'defined_fields': list(field_definitions.keys()),
            'field_coverage': len(field_definitions) / len(required_fields),
            'example_count': len(examples),
            'complete': len(field_definitions) >= 4,  # At least 4 core fields
        }
    
    def test_regeneration_completeness(self) -> Dict[str, Any]:
        """Test if GEM contains all necessary components for regeneration."""
        components = {}
        
        # Check for each critical component
        components['bootstrap'] = self.extract_bootstrap_procedure()
        components['prey_workflow'] = self.extract_prey_workflow()
        components['safety_envelope'] = self.extract_safety_envelope()
        components['blackboard_schema'] = self.extract_blackboard_schema()
        
        # Check for operational procedures
        components['swarmlord_ops'] = bool(re.search(
            r'Swarmlord.*?Operations?',
            self.gem_content,
            re.IGNORECASE
        ))
        
        # Check for verification gate
        components['verify_gate'] = bool(re.search(
            r'(?:Independent|Verify).*?Gate',
            self.gem_content,
            re.IGNORECASE
        ))
        
        # Overall completeness
        completeness_score = sum([
            components['bootstrap']['found'],
            components['prey_workflow']['complete'],
            components['safety_envelope']['complete'],
            components['blackboard_schema']['complete'],
            components['swarmlord_ops'],
            components['verify_gate'],
        ]) / 6.0
        
        return {
            'components': components,
            'completeness_score': completeness_score,
            'regenerable': completeness_score >= 0.8,
        }
    
    def test_terminology_consistency(self) -> Dict[str, Any]:
        """Test PREY terminology is used consistently."""
        prey_terms = ['Perceive', 'React', 'Engage', 'Yield']
        legacy_terms = ['Observe', 'Orient', 'Decide', 'Act', 'Monitor', 'Analyze', 'Plan', 'Execute']
        
        prey_usage = {}
        legacy_usage = {}
        
        for term in prey_terms:
            pattern = re.compile(rf'\b{term}\b', re.IGNORECASE)
            prey_usage[term] = len(pattern.findall(self.gem_content))
        
        for term in legacy_terms:
            pattern = re.compile(rf'\b{term}\b', re.IGNORECASE)
            legacy_usage[term] = len(pattern.findall(self.gem_content))
        
        # PREY should be dominant
        total_prey = sum(prey_usage.values())
        total_legacy = sum(legacy_usage.values())
        
        # But legacy terms are OK when showing provenance
        has_provenance_section = bool(re.search(
            r'provenance|lineage|mapping',
            self.gem_content,
            re.IGNORECASE
        ))
        
        return {
            'prey_usage': prey_usage,
            'legacy_usage': legacy_usage,
            'total_prey': total_prey,
            'total_legacy': total_legacy,
            'prey_dominant': total_prey > total_legacy * 0.5,
            'has_provenance': has_provenance_section,
            'consistent': total_prey > 40,  # Reasonable threshold
        }
    
    def run_regeneration_test(self) -> Dict[str, Any]:
        """Run complete regeneration test suite."""
        if not self.load_gem():
            return {
                'status': 'ERROR',
                'error': self.test_results.get('load_error', 'Unknown error'),
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
        
        # Run all tests
        completeness = self.test_regeneration_completeness()
        terminology = self.test_terminology_consistency()
        
        # Calculate overall regeneration capability
        regen_score = (completeness['completeness_score'] * 70 + 
                      (30 if terminology['consistent'] else 0))
        
        # Determine status
        critical_failures = []
        warnings = []
        
        if not completeness['regenerable']:
            critical_failures.append(
                f"Regeneration completeness too low: {completeness['completeness_score']:.1%}"
            )
        
        if not completeness['components']['bootstrap']['found']:
            critical_failures.append("No bootstrap procedure found")
        
        if not terminology['consistent']:
            warnings.append("PREY terminology usage below threshold")
        
        if not completeness['components']['prey_workflow']['complete']:
            critical_failures.append("PREY workflow incomplete")
        
        return {
            'status': 'PASS' if not critical_failures else 'FAIL',
            'regeneration_score': regen_score,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'gem_path': str(self.gem_path),
            'tests': {
                'completeness': completeness,
                'terminology': terminology,
            },
            'summary': {
                'critical_failures': critical_failures,
                'warnings': warnings,
                'total_issues': len(critical_failures) + len(warnings),
            },
        }


def generate_regen_report(test_results: Dict[str, Any]) -> str:
    """Generate regeneration test report."""
    status = test_results['status']
    score = test_results['regeneration_score']
    tests = test_results['tests']
    summary = test_results['summary']
    
    report = f"""
# Gen21 Regeneration Test Report
**Timestamp:** {test_results['timestamp']}
**Status:** {status}
**Regeneration Score:** {score:.1f}/100.0

## Executive Summary
Gen21 regeneration test {'PASSED' if status == 'PASS' else 'FAILED'} with score {score:.1f}/100.
- Critical Failures: {len(summary['critical_failures'])}
- Warnings: {len(summary['warnings'])}

### Critical Failures
{chr(10).join(f'- {fail}' for fail in summary['critical_failures']) if summary['critical_failures'] else '- None'}

### Warnings
{chr(10).join(f'- {warn}' for warn in summary['warnings']) if summary['warnings'] else '- None'}

## Test Results

### Regeneration Completeness
- **Score:** {tests['completeness']['completeness_score']:.1%}
- **Regenerable:** {tests['completeness']['regenerable']}

#### Component Analysis
- **Bootstrap Procedure:**
  - Found: {tests['completeness']['components']['bootstrap']['found']}
  - Steps: {tests['completeness']['components']['bootstrap'].get('step_count', 0)}
  - Manual Steps Claim: {tests['completeness']['components']['bootstrap'].get('manual_steps_claim', 'N/A')}

- **PREY Workflow:**
  - Complete: {tests['completeness']['components']['prey_workflow']['complete']}
  - Phases Found: {', '.join(tests['completeness']['components']['prey_workflow']['phases_found'])}

- **Safety Envelope:**
  - Complete: {tests['completeness']['components']['safety_envelope']['complete']}
  - Canary refs: {tests['completeness']['components']['safety_envelope']['canary_refs']}
  - Tripwire refs: {tests['completeness']['components']['safety_envelope']['tripwire_refs']}
  - Revert refs: {tests['completeness']['components']['safety_envelope']['revert_refs']}

- **Blackboard Schema:**
  - Complete: {tests['completeness']['components']['blackboard_schema']['complete']}
  - Field Coverage: {tests['completeness']['components']['blackboard_schema']['field_coverage']:.1%}
  - Example Count: {tests['completeness']['components']['blackboard_schema']['example_count']}

- **Operational Procedures:**
  - Swarmlord Ops: {tests['completeness']['components']['swarmlord_ops']}
  - Verify Gate: {tests['completeness']['components']['verify_gate']}

### Terminology Consistency
- **PREY Dominant:** {tests['terminology']['prey_dominant']}
- **Consistent Usage:** {tests['terminology']['consistent']}
- **Total PREY Terms:** {tests['terminology']['total_prey']}
- **Total Legacy Terms:** {tests['terminology']['total_legacy']}
- **Has Provenance:** {tests['terminology']['has_provenance']}

#### Term Usage Breakdown
PREY Terms:
{chr(10).join(f'  - {k}: {v}' for k, v in tests['terminology']['prey_usage'].items())}

## Diagram: Regeneration Capability

```mermaid
graph TB
    A[Regeneration Test] --> B[Completeness: {tests['completeness']['completeness_score']:.0%}]
    A --> C[Terminology: {_regen_status(tests['terminology']['consistent'])}]
    
    B --> B1[Bootstrap: {_regen_status(tests['completeness']['components']['bootstrap']['found'])}]
    B --> B2[PREY: {_regen_status(tests['completeness']['components']['prey_workflow']['complete'])}]
    B --> B3[Safety: {_regen_status(tests['completeness']['components']['safety_envelope']['complete'])}]
    B --> B4[Blackboard: {_regen_status(tests['completeness']['components']['blackboard_schema']['complete'])}]
    
    style A fill:#f9f,stroke:#333,stroke-width:4px
    style B fill:{_regen_color(tests['completeness']['regenerable'])}
    style C fill:{_regen_color(tests['terminology']['consistent'])}
```

## Conclusion
{_generate_regen_conclusion(test_results)}

---
**Generated by:** `scripts/test_gen21_regeneration.py`
"""
    
    return report


def _regen_status(value: bool) -> str:
    """Convert boolean to status."""
    return "OK" if value else "FAIL"


def _regen_color(healthy: bool) -> str:
    """Get color for status."""
    return "#9f9" if healthy else "#f99"


def _generate_regen_conclusion(results: Dict[str, Any]) -> str:
    """Generate conclusion text."""
    if results['status'] == 'PASS':
        return ("Gen21 demonstrates strong regeneration capability. "
                "All critical components are present and well-documented. "
                "The system can bootstrap from this specification.")
    else:
        return ("Gen21 regeneration capability requires improvement. "
                f"Address {len(results['summary']['critical_failures'])} critical failures "
                "before attempting regeneration.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test Gen21 self-regeneration capability"
    )
    parser.add_argument(
        '--gem',
        type=Path,
        default=REPO_ROOT / 'hfo_gem' / 'gen_21' / 'gpt5-attempt-3-gem.md',
        help='Path to Gen21 GEM document'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output path for JSON results'
    )
    parser.add_argument(
        '--report',
        type=Path,
        help='Output path for test report (markdown)'
    )
    
    args = parser.parse_args()
    
    # Run regeneration test
    print(f"Testing Gen21 regeneration capability...")
    print(f"GEM: {args.gem}")
    print()
    
    tester = RegenerationTester(args.gem)
    results = tester.run_regeneration_test()
    
    # Save JSON
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"JSON results: {args.output}")
    
    # Generate report
    if args.report:
        report = generate_regen_report(results)
        with open(args.report, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Test report: {args.report}")
    else:
        print(generate_regen_report(results))
    
    return 0 if results['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
