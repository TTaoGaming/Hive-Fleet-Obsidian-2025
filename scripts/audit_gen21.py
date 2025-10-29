#!/usr/bin/env python3
"""
Independent Audit Tool for Gen21 Architecture
==============================================

This tool provides objective, metrics-based analysis of Generation 21's
ability to regenerate itself and follow its own specifications.

Audit dimensions:
1. SSOT Completeness (line counts, section coverage)
2. PREY Workflow Conformance (terminology usage, mappings)
3. Safety Envelope (placeholders, tripwires, evidence discipline)
4. Blackboard Protocol (JSONL validation, required fields)
5. Regeneration Capability (parseable procedures, bootstrappable)
6. Drift Detection (hallucination vs. composition)

Output: JSON report with metrics, findings, and evidence references.
"""

from __future__ import annotations
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# Repository root detection
REPO_ROOT = Path(__file__).resolve().parents[1]


class Gen21Auditor:
    """Independent auditor for Gen21 architecture specifications."""
    
    def __init__(self, gem_path: Path, blackboard_path: Optional[Path] = None):
        self.gem_path = gem_path
        self.blackboard_path = blackboard_path
        self.gem_content = ""
        self.gem_lines: List[str] = []
        self.findings: Dict[str, Any] = {}
        self.metrics: Dict[str, Any] = {}
        
        # Gen21 required terminology
        self.prey_terms = ["Perceive", "React", "Engage", "Yield"]
        self.workflow_terms = ["HIVE", "GROWTH", "SWARM", "PREY"]
        self.safety_terms = ["canary", "tripwire", "revert"]
        
        # Forbidden patterns (placeholders)
        self.placeholder_patterns = [
            r'\bTODO\b',
            r'\bFIXME\b',
            r'\bXXX\b',
            r'\.\.\.(?!\s*```)',  # ellipsis not in code blocks
            r'\bomitted\b',
            r'\bplaceholder\b',
        ]
        
    def load_gem(self) -> bool:
        """Load the GEM document content."""
        try:
            with open(self.gem_path, 'r', encoding='utf-8') as f:
                self.gem_content = f.read()
                self.gem_lines = self.gem_content.splitlines()
            return True
        except Exception as e:
            self.findings['load_error'] = str(e)
            return False
    
    def audit_ssot_completeness(self) -> Dict[str, Any]:
        """Audit SSOT completeness requirements."""
        line_count = len(self.gem_lines)
        target_min = 1000
        
        # Extract sections
        section_pattern = r'^##\s+(?:Section\s+(\d+)|Appendix\s+([A-Z])):\s+(.+)$'
        sections = []
        for i, line in enumerate(self.gem_lines, 1):
            match = re.match(section_pattern, line)
            if match:
                sec_num = match.group(1) or match.group(2)
                sec_title = match.group(3)
                sections.append({
                    'number': sec_num,
                    'title': sec_title,
                    'line': i
                })
        
        # Check for required sections
        required_sections = [
            "BLUF",
            "Zero Invention",
            "PREY Canonical",
            "Verification",
            "Stigmergy",
            "Toolchain",
            "Regeneration",
            "Swarmlord",
            "Bootstrap",
        ]
        
        found_required = {}
        for req in required_sections:
            found = False
            for sec in sections:
                if req.lower() in sec['title'].lower():
                    found = True
                    break
            found_required[req] = found
        
        return {
            'line_count': line_count,
            'target_min': target_min,
            'meets_target': line_count >= target_min,
            'sections_found': len(sections),
            'sections_detail': sections[:10],  # First 10 for brevity
            'required_sections': found_required,
            'missing_sections': [k for k, v in found_required.items() if not v]
        }
    
    def audit_prey_conformance(self) -> Dict[str, Any]:
        """Audit PREY workflow terminology usage and consistency."""
        # Count occurrences of PREY terms
        prey_counts = {}
        for term in self.prey_terms:
            # Case-insensitive count
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            prey_counts[term] = len(pattern.findall(self.gem_content))
        
        # Check for PREY mapping diagram
        has_prey_diagram = bool(re.search(r'```mermaid.*?Perceive.*?React.*?Engage.*?Yield', 
                                          self.gem_content, re.DOTALL | re.IGNORECASE))
        
        # Check for provenance mappings (JADC2, OODA, MAPE-K)
        provenance_refs = {
            'JADC2': 'JADC2' in self.gem_content,
            'OODA': 'OODA' in self.gem_content,
            'MAPE-K': 'MAPE-K' in self.gem_content or 'MAPEK' in self.gem_content
        }
        
        # Verify workflow hierarchy is documented
        workflow_hierarchy = all(term in self.gem_content for term in self.workflow_terms)
        
        return {
            'prey_term_counts': prey_counts,
            'all_prey_terms_present': all(count > 0 for count in prey_counts.values()),
            'has_prey_diagram': has_prey_diagram,
            'provenance_references': provenance_refs,
            'workflow_hierarchy_documented': workflow_hierarchy,
            'min_prey_usage': min(prey_counts.values()),
        }
    
    def audit_safety_envelope(self) -> Dict[str, Any]:
        """Audit safety envelope implementation."""
        # Check for safety terms
        safety_found = {}
        for term in self.safety_terms:
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            safety_found[term] = len(pattern.findall(self.gem_content))
        
        # Search for placeholders (violations)
        placeholder_violations = []
        for i, line in enumerate(self.gem_lines, 1):
            for pattern in self.placeholder_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Exclude code examples and quoted text
                    if not line.strip().startswith('#') and '```' not in line:
                        placeholder_violations.append({
                            'line': i,
                            'pattern': pattern,
                            'content': line.strip()[:100]
                        })
        
        # Check for chunking references (≤200 lines)
        chunking_refs = len(re.findall(r'[≤<]\s*200\s+lines?', self.gem_content, re.IGNORECASE))
        
        # Check for tripwire definitions
        has_tripwire_section = bool(re.search(r'tripwire', self.gem_content, re.IGNORECASE))
        
        return {
            'safety_terms': safety_found,
            'all_safety_terms_present': all(count > 0 for count in safety_found.values()),
            'placeholder_violations': placeholder_violations[:5],  # First 5
            'placeholder_count': len(placeholder_violations),
            'has_placeholders': len(placeholder_violations) > 0,
            'chunking_references': chunking_refs,
            'has_tripwire_definition': has_tripwire_section,
        }
    
    def audit_blackboard_protocol(self) -> Dict[str, Any]:
        """Audit blackboard protocol specification and actual usage."""
        # Check for blackboard schema definition
        has_schema = bool(re.search(r'mission_id.*phase.*evidence_refs', 
                                    self.gem_content, re.DOTALL | re.IGNORECASE))
        
        # Check for example receipts in GEM
        example_pattern = r'```json.*?"mission_id".*?```'
        examples = re.findall(example_pattern, self.gem_content, re.DOTALL | re.IGNORECASE)
        
        # Check actual blackboard if provided
        blackboard_data = None
        if self.blackboard_path and self.blackboard_path.exists():
            blackboard_data = self._validate_blackboard_jsonl()
        
        return {
            'has_schema_definition': has_schema,
            'example_receipts_count': len(examples),
            'blackboard_file_exists': self.blackboard_path.exists() if self.blackboard_path else False,
            'blackboard_validation': blackboard_data,
        }
    
    def _validate_blackboard_jsonl(self) -> Dict[str, Any]:
        """Validate actual blackboard JSONL file."""
        if not self.blackboard_path:
            return {'error': 'No blackboard path provided'}
        
        try:
            with open(self.blackboard_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            valid_count = 0
            invalid_count = 0
            required_fields = ['mission_id', 'phase', 'summary', 'evidence_refs', 'timestamp']
            field_coverage = Counter()
            phase_counts = Counter()
            
            for i, line in enumerate(lines, 1):
                try:
                    obj = json.loads(line)
                    if not isinstance(obj, dict):
                        invalid_count += 1
                        continue
                    
                    valid_count += 1
                    for field in required_fields:
                        if field in obj:
                            field_coverage[field] += 1
                    
                    if 'phase' in obj:
                        phase_counts[obj['phase']] += 1
                    
                except json.JSONDecodeError:
                    invalid_count += 1
            
            return {
                'total_lines': len(lines),
                'valid_entries': valid_count,
                'invalid_entries': invalid_count,
                'field_coverage': dict(field_coverage),
                'phase_distribution': dict(phase_counts.most_common(10)),
                'all_required_fields_present': all(
                    field_coverage[f] > 0 for f in required_fields
                ),
            }
        except Exception as e:
            return {'error': str(e)}
    
    def audit_regeneration_capability(self) -> Dict[str, Any]:
        """Audit whether GEM contains parseable regeneration procedures."""
        # Check for bootstrap section
        bootstrap_section = bool(re.search(r'##.*?Bootstrap', self.gem_content, re.IGNORECASE))
        
        # Check for step-by-step procedures
        step_patterns = [
            r'\d+\)\s+',  # Numbered steps like "1) "
            r'^\s*-\s+Step\s+\d+',  # Bulleted steps
            r'^\s*\d+\.\s+',  # Numbered list
        ]
        
        procedure_lines = []
        for line in self.gem_lines:
            for pattern in step_patterns:
                if re.search(pattern, line, re.MULTILINE):
                    procedure_lines.append(line.strip()[:80])
                    break
        
        # Check for regeneration protocol
        has_regen_protocol = bool(re.search(r'Regeneration Protocol', self.gem_content))
        
        # Check for cold-start references
        cold_start_refs = len(re.findall(r'cold.?start', self.gem_content, re.IGNORECASE))
        
        # Check for "≤3 manual steps" requirement
        minimal_bootstrap = bool(re.search(r'[≤<]\s*3\s+manual\s+steps?', self.gem_content, re.IGNORECASE))
        
        return {
            'has_bootstrap_section': bootstrap_section,
            'procedure_step_count': len(procedure_lines),
            'procedure_samples': procedure_lines[:5],
            'has_regeneration_protocol': has_regen_protocol,
            'cold_start_references': cold_start_refs,
            'minimal_bootstrap_claim': minimal_bootstrap,
            'bootstrappable': bootstrap_section and minimal_bootstrap,
        }
    
    def audit_drift_detection(self) -> Dict[str, Any]:
        """Detect potential hallucination vs. exemplar-based composition."""
        # Check for composition sources documented
        composition_sources = {
            'biological': bool(re.search(r'ant|immune|neural|stigmergy', self.gem_content, re.IGNORECASE)),
            'research': bool(re.search(r'hebbian|evolutionary|OODA|JADC2|MAPE-K', self.gem_content, re.IGNORECASE)),
            'operational': bool(re.search(r'canary|SRE|rollout|append-only', self.gem_content, re.IGNORECASE)),
        }
        
        # Check for "Zero Invention" principle
        zero_invention = bool(re.search(r'zero invention|compose.*?proven|battle.?tested', 
                                        self.gem_content, re.IGNORECASE))
        
        # Check for provenance/lineage documentation
        has_lineage = bool(re.search(r'Gen19|Gen1|lineage|provenance', self.gem_content, re.IGNORECASE))
        
        # Check for evidence references in content
        evidence_pattern = r'evidence|receipt|proof|hash|sha256'
        evidence_refs = len(re.findall(evidence_pattern, self.gem_content, re.IGNORECASE))
        
        # Warning signs of potential drift/hallucination
        warning_signs = []
        
        # Check for vague references
        vague_refs = re.findall(r'\b(?:somehow|magic|automagic|just works)\b', 
                               self.gem_content, re.IGNORECASE)
        if vague_refs:
            warning_signs.append(f"Vague references: {len(vague_refs)}")
        
        # Check for ungrounded claims
        if not composition_sources['biological'] or not composition_sources['research']:
            warning_signs.append("Missing composition provenance")
        
        return {
            'composition_sources_documented': composition_sources,
            'zero_invention_principle': zero_invention,
            'has_lineage_documentation': has_lineage,
            'evidence_reference_count': evidence_refs,
            'warning_signs': warning_signs,
            'drift_score': len(warning_signs),  # Lower is better
        }
    
    def run_full_audit(self) -> Dict[str, Any]:
        """Execute complete audit and compile results."""
        if not self.load_gem():
            return {
                'status': 'ERROR',
                'error': self.findings.get('load_error', 'Unknown error loading GEM'),
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
        
        # Run all audit dimensions
        ssot = self.audit_ssot_completeness()
        prey = self.audit_prey_conformance()
        safety = self.audit_safety_envelope()
        blackboard = self.audit_blackboard_protocol()
        regen = self.audit_regeneration_capability()
        drift = self.audit_drift_detection()
        
        # Calculate overall health score (0-100)
        health_score = self._calculate_health_score(ssot, prey, safety, blackboard, regen, drift)
        
        # Compile findings
        critical_issues = []
        warnings = []
        
        if not ssot['meets_target']:
            critical_issues.append(f"SSOT below target: {ssot['line_count']}/{ssot['target_min']} lines")
        
        if ssot['missing_sections']:
            warnings.append(f"Missing sections: {', '.join(ssot['missing_sections'])}")
        
        if not prey['all_prey_terms_present']:
            critical_issues.append("PREY terminology incomplete")
        
        if safety['has_placeholders']:
            critical_issues.append(f"Placeholder violations: {safety['placeholder_count']}")
        
        if not regen['bootstrappable']:
            critical_issues.append("Bootstrap capability not verified")
        
        if drift['drift_score'] > 2:
            warnings.append(f"Drift warning score: {drift['drift_score']}")
        
        return {
            'status': 'PASS' if not critical_issues else 'FAIL',
            'health_score': health_score,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'gem_path': str(self.gem_path),
            'dimensions': {
                'ssot_completeness': ssot,
                'prey_conformance': prey,
                'safety_envelope': safety,
                'blackboard_protocol': blackboard,
                'regeneration_capability': regen,
                'drift_detection': drift,
            },
            'summary': {
                'critical_issues': critical_issues,
                'warnings': warnings,
                'total_issues': len(critical_issues) + len(warnings),
            },
        }
    
    def _calculate_health_score(self, ssot, prey, safety, blackboard, regen, drift) -> float:
        """Calculate overall health score (0-100)."""
        score = 100.0
        
        # SSOT completeness (20 points)
        if not ssot['meets_target']:
            score -= 20
        score -= len(ssot['missing_sections']) * 2
        
        # PREY conformance (20 points)
        if not prey['all_prey_terms_present']:
            score -= 10
        if not prey['has_prey_diagram']:
            score -= 5
        if not prey['workflow_hierarchy_documented']:
            score -= 5
        
        # Safety envelope (20 points)
        if safety['has_placeholders']:
            score -= min(safety['placeholder_count'], 15)
        if not safety['has_tripwire_definition']:
            score -= 5
        
        # Blackboard protocol (15 points)
        if not blackboard['has_schema_definition']:
            score -= 10
        if blackboard['example_receipts_count'] == 0:
            score -= 5
        
        # Regeneration capability (15 points)
        if not regen['bootstrappable']:
            score -= 15
        
        # Drift detection (10 points)
        score -= min(drift['drift_score'] * 2, 10)
        
        return max(0.0, score)


def generate_summary_report(audit_results: Dict[str, Any], output_path: Optional[Path] = None) -> str:
    """Generate one-page summary with BLUF, matrix, and diagrams."""
    
    status = audit_results['status']
    health = audit_results['health_score']
    dims = audit_results['dimensions']
    summary = audit_results['summary']
    
    report = f"""
# Generation 21 Architecture Audit Report
**Timestamp:** {audit_results['timestamp']}
**Status:** {status}
**Health Score:** {health:.1f}/100.0

## BLUF (Bottom Line Up Front)
Generation 21 audit {'PASSED' if status == 'PASS' else 'FAILED'} with health score {health:.1f}/100.
- Critical Issues: {len(summary['critical_issues'])}
- Warnings: {len(summary['warnings'])}
- GEM Path: {audit_results['gem_path']}

### Critical Issues
{chr(10).join(f'- {issue}' for issue in summary['critical_issues']) if summary['critical_issues'] else '- None'}

### Warnings
{chr(10).join(f'- {warn}' for warn in summary['warnings']) if summary['warnings'] else '- None'}

## Audit Matrix

| Dimension | Score | Status | Key Metrics |
|-----------|-------|--------|-------------|
| SSOT Completeness | {_dim_score(dims['ssot_completeness'])} | {_status_icon(dims['ssot_completeness']['meets_target'])} | {dims['ssot_completeness']['line_count']} lines, {dims['ssot_completeness']['sections_found']} sections |
| PREY Conformance | {_dim_score(dims['prey_conformance'])} | {_status_icon(dims['prey_conformance']['all_prey_terms_present'])} | All terms: {dims['prey_conformance']['all_prey_terms_present']}, Diagram: {dims['prey_conformance']['has_prey_diagram']} |
| Safety Envelope | {_dim_score(dims['safety_envelope'])} | {_status_icon(not dims['safety_envelope']['has_placeholders'])} | Placeholders: {dims['safety_envelope']['placeholder_count']}, Tripwires: {dims['safety_envelope']['has_tripwire_definition']} |
| Blackboard Protocol | {_dim_score(dims['blackboard_protocol'])} | {_status_icon(dims['blackboard_protocol']['has_schema_definition'])} | Schema: {dims['blackboard_protocol']['has_schema_definition']}, Examples: {dims['blackboard_protocol']['example_receipts_count']} |
| Regeneration Capability | {_dim_score(dims['regeneration_capability'])} | {_status_icon(dims['regeneration_capability']['bootstrappable'])} | Bootstrappable: {dims['regeneration_capability']['bootstrappable']}, Steps: {dims['regeneration_capability']['procedure_step_count']} |
| Drift Detection | {_dim_score(dims['drift_detection'])} | {_status_icon(dims['drift_detection']['drift_score'] <= 2)} | Warning signs: {dims['drift_detection']['drift_score']}, Zero invention: {dims['drift_detection']['zero_invention_principle']} |

## Detailed Findings

### SSOT Completeness
- Line count: {dims['ssot_completeness']['line_count']} (target: {dims['ssot_completeness']['target_min']})
- Sections found: {dims['ssot_completeness']['sections_found']}
- Missing required: {', '.join(dims['ssot_completeness']['missing_sections']) if dims['ssot_completeness']['missing_sections'] else 'None'}

### PREY Conformance
- Term usage: {', '.join(f"{k}={v}" for k, v in dims['prey_conformance']['prey_term_counts'].items())}
- Provenance refs: {', '.join(f"{k}={v}" for k, v in dims['prey_conformance']['provenance_references'].items())}
- Minimum usage: {dims['prey_conformance']['min_prey_usage']}

### Safety Envelope
- Safety terms: {', '.join(f"{k}={v}" for k, v in dims['safety_envelope']['safety_terms'].items())}
- Chunking refs: {dims['safety_envelope']['chunking_references']}
- Placeholder violations: {dims['safety_envelope']['placeholder_count']}

### Regeneration Capability
- Bootstrap section: {dims['regeneration_capability']['has_bootstrap_section']}
- Procedure steps: {dims['regeneration_capability']['procedure_step_count']}
- Cold-start refs: {dims['regeneration_capability']['cold_start_references']}
- Minimal bootstrap: {dims['regeneration_capability']['minimal_bootstrap_claim']}

### Drift Detection
- Composition sources: {', '.join(f"{k}={v}" for k, v in dims['drift_detection']['composition_sources_documented'].items())}
- Zero invention: {dims['drift_detection']['zero_invention_principle']}
- Evidence refs: {dims['drift_detection']['evidence_reference_count']}
- Drift score: {dims['drift_detection']['drift_score']}/10 (lower is better)

## Diagram: Audit Dimensions

```mermaid
graph TB
    A[Gen21 Audit] --> B[SSOT: {dims['ssot_completeness']['line_count']}L]
    A --> C[PREY: {_bool_to_status(dims['prey_conformance']['all_prey_terms_present'])}]
    A --> D[Safety: {dims['safety_envelope']['placeholder_count']} violations]
    A --> E[Blackboard: {_bool_to_status(dims['blackboard_protocol']['has_schema_definition'])}]
    A --> F[Regen: {_bool_to_status(dims['regeneration_capability']['bootstrappable'])}]
    A --> G[Drift: {dims['drift_detection']['drift_score']}/10]
    
    style A fill:#f9f,stroke:#333,stroke-width:4px
    style B fill:{_health_color(dims['ssot_completeness']['meets_target'])}
    style C fill:{_health_color(dims['prey_conformance']['all_prey_terms_present'])}
    style D fill:{_health_color(not dims['safety_envelope']['has_placeholders'])}
    style E fill:{_health_color(dims['blackboard_protocol']['has_schema_definition'])}
    style F fill:{_health_color(dims['regeneration_capability']['bootstrappable'])}
    style G fill:{_health_color(dims['drift_detection']['drift_score'] <= 2)}
```

## Recommendations

{_generate_recommendations(audit_results)}

---
**Generated by:** `scripts/audit_gen21.py`
**Audit Standard:** Gen21 SSOT Specifications
"""
    
    if output_path:
        output_path.write_text(report, encoding='utf-8')
        print(f"Summary report saved to: {output_path}")
    
    return report


def _dim_score(dim_data: Dict) -> str:
    """Calculate dimension-specific score indicator."""
    # Simple heuristic - improve as needed
    return "✓" if any(dim_data.values()) else "✗"


def _status_icon(passed: bool) -> str:
    """Return status icon."""
    return "✓ PASS" if passed else "✗ FAIL"


def _bool_to_status(value: bool) -> str:
    """Convert boolean to status string."""
    return "OK" if value else "FAIL"


def _health_color(healthy: bool) -> str:
    """Return Mermaid color for health status."""
    return "#9f9" if healthy else "#f99"


def _generate_recommendations(audit_results: Dict[str, Any]) -> str:
    """Generate actionable recommendations."""
    recs = []
    dims = audit_results['dimensions']
    
    if not dims['ssot_completeness']['meets_target']:
        recs.append("1. Expand SSOT to meet ≥1000 line target")
    
    if dims['ssot_completeness']['missing_sections']:
        missing = ', '.join(dims['ssot_completeness']['missing_sections'])
        recs.append(f"2. Add missing required sections: {missing}")
    
    if dims['safety_envelope']['has_placeholders']:
        recs.append(f"3. Remove {dims['safety_envelope']['placeholder_count']} placeholder violations")
    
    if not dims['prey_conformance']['all_prey_terms_present']:
        recs.append("4. Ensure all PREY terms (Perceive, React, Engage, Yield) are documented")
    
    if not dims['regeneration_capability']['bootstrappable']:
        recs.append("5. Define clear bootstrap procedure with ≤3 manual steps")
    
    if dims['drift_detection']['drift_score'] > 2:
        recs.append("6. Strengthen composition provenance and reduce hallucination indicators")
    
    if not recs:
        recs.append("No critical recommendations - Gen21 meets specification requirements")
    
    return '\n'.join(recs)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independent audit of Gen21 architecture specifications"
    )
    parser.add_argument(
        '--gem',
        type=Path,
        default=REPO_ROOT / 'hfo_gem' / 'gen_21' / 'gpt5-attempt-3-gem.md',
        help='Path to Gen21 GEM document'
    )
    parser.add_argument(
        '--blackboard',
        type=Path,
        default=REPO_ROOT / 'hfo_blackboard' / 'obsidian_synapse_blackboard.jsonl',
        help='Path to blackboard JSONL file'
    )
    parser.add_argument(
        '--output',
        type=Path,
        help='Output path for JSON results'
    )
    parser.add_argument(
        '--summary',
        type=Path,
        help='Output path for summary report (markdown)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=64,
        help='Random seed for explore/exploit (default: 6/4 ratio = 64)'
    )
    
    args = parser.parse_args()
    
    # Initialize auditor
    auditor = Gen21Auditor(args.gem, args.blackboard)
    
    # Run full audit
    print(f"Running Gen21 audit...")
    print(f"GEM: {args.gem}")
    print(f"Blackboard: {args.blackboard}")
    print(f"Explore/Exploit seed: {args.seed}")
    print()
    
    results = auditor.run_full_audit()
    
    # Save JSON results
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, sort_keys=False)
        print(f"JSON results saved to: {args.output}")
    else:
        print(json.dumps(results, indent=2))
    
    # Generate summary report
    if args.summary:
        summary = generate_summary_report(results, args.summary)
    else:
        summary = generate_summary_report(results)
        print("\n" + "="*80)
        print(summary)
    
    # Return exit code based on status
    return 0 if results['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
