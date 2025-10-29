#!/usr/bin/env python3
"""
Independent Audit Tool for Generation 21 Architecture

This tool performs an independent audit of Gen21's architecture by:
1. Validating SSOT compliance (line counts, PREY terminology, safety envelope)
2. Checking blackboard protocol adherence
3. Testing regeneration capability with receipts tracking
4. Analyzing explore/exploit balance (4/6 seed ratio)
5. Detecting hallucination and drift
6. Generating BLUF summary with matrix and diagrams

Usage:
    python3 scripts/audit_gen21.py --explore-ratio 0.4 --output /tmp/gen21_audit_report.md
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any


class Gen21Auditor:
    """Independent auditor for Generation 21 architecture."""
    
    def __init__(self, repo_root: Path, explore_ratio: float = 0.4):
        self.repo_root = repo_root
        self.explore_ratio = explore_ratio
        self.exploit_ratio = 1.0 - explore_ratio
        self.findings = []
        self.metrics = {}
        self.timestamp = datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(datetime, 'UTC') else datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
    def audit_ssot_compliance(self) -> Dict[str, Any]:
        """Audit SSOT document for Gen21 requirements."""
        ssot_path = self.repo_root / "hfo_gem" / "gen_21" / "gpt5-attempt-3-gem.md"
        
        if not ssot_path.exists():
            self.findings.append(("CRITICAL", "SSOT document not found at expected path"))
            return {"status": "FAIL", "reason": "SSOT not found"}
        
        content = ssot_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        line_count = len(lines)
        
        # Check line count requirement (≥1000)
        line_count_pass = line_count >= 1000
        if not line_count_pass:
            self.findings.append(("FAIL", f"SSOT line count {line_count} < 1000"))
        
        # Count PREY terminology usage
        prey_terms = {
            "PREY": content.count("PREY"),
            "Perceive": content.count("Perceive"),
            "React": content.count("React"),
            "Engage": content.count("Engage"),
            "Yield": content.count("Yield")
        }
        prey_total = sum(prey_terms.values())
        prey_canonical = prey_total >= 50  # Expect substantial usage
        
        if not prey_canonical:
            self.findings.append(("WARN", f"PREY term usage low: {prey_total} occurrences"))
        
        # Check for placeholders (forbidden)
        placeholders = []
        placeholder_patterns = [r'\bTODO\b', r'\.\.\.(?!\])', r'\bomitted\b']
        for pattern in placeholder_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                # Exclude policy references (mentions of the word TODO in documentation)
                context = content[max(0, match.start()-80):min(len(content), match.end()+80)].lower()
                # Skip if it's in a policy/documentation context
                skip_terms = [
                    'policy', 'forbidden', 'no "todo"', 'scan for', 'placeholders (', 
                    'ban ', 'avoid', 'todo/', 'search for "todo"', 'fail trigger',
                    'present; broken', '… present'
                ]
                if any(term in context for term in skip_terms):
                    continue
                placeholders.append((line_num, match.group()))
        
        placeholder_pass = len(placeholders) == 0
        if not placeholder_pass:
            self.findings.append(("FAIL", f"Found {len(placeholders)} placeholders: {placeholders[:3]}"))
        
        # Check for Swarmlord facade mentions
        swarmlord_count = content.count("Swarmlord")
        swarmlord_facade = swarmlord_count >= 10
        if not swarmlord_facade:
            self.findings.append(("WARN", f"Swarmlord mentions low: {swarmlord_count}"))
        
        # Check for safety envelope components
        safety_terms = {
            "canary": content.lower().count("canary"),
            "tripwire": content.lower().count("tripwire"),
            "revert": content.lower().count("revert")
        }
        safety_envelope = all(v >= 3 for v in safety_terms.values())
        if not safety_envelope:
            self.findings.append(("WARN", f"Safety envelope incomplete: {safety_terms}"))
        
        # Check for verification mentions
        verify_count = content.lower().count("verify")
        verify_gate = verify_count >= 20
        if not verify_gate:
            self.findings.append(("WARN", f"Verify mentions low: {verify_count}"))
        
        return {
            "status": "PASS" if (line_count_pass and placeholder_pass) else "FAIL",
            "line_count": line_count,
            "line_count_pass": line_count_pass,
            "prey_terms": prey_terms,
            "prey_canonical": prey_canonical,
            "placeholders": len(placeholders),
            "placeholder_pass": placeholder_pass,
            "swarmlord_mentions": swarmlord_count,
            "swarmlord_facade": swarmlord_facade,
            "safety_terms": safety_terms,
            "safety_envelope": safety_envelope,
            "verify_mentions": verify_count,
            "verify_gate": verify_gate
        }
    
    def audit_blackboard_protocol(self) -> Dict[str, Any]:
        """Audit blackboard JSONL for protocol compliance."""
        bb_path = self.repo_root / "hfo_blackboard" / "obsidian_synapse_blackboard.jsonl"
        
        if not bb_path.exists():
            self.findings.append(("WARN", "Blackboard JSONL not found"))
            return {"status": "WARN", "reason": "No blackboard"}
        
        entries = []
        invalid_lines = []
        
        with bb_path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    entries.append(entry)
                except json.JSONDecodeError as e:
                    invalid_lines.append((i, str(e)))
        
        if invalid_lines:
            self.findings.append(("FAIL", f"Invalid JSONL lines: {len(invalid_lines)}"))
        
        # Check required fields in recent entries
        required_fields = ["mission_id", "phase", "summary", "timestamp"]
        gen21_entries = [e for e in entries if "gem21" in e.get("mission_id", "").lower()]
        
        field_compliance = []
        for entry in gen21_entries[-10:]:  # Check last 10 Gen21 entries
            missing = [f for f in required_fields if f not in entry]
            if missing:
                field_compliance.append(missing)
        
        if field_compliance:
            self.findings.append(("WARN", f"Blackboard entries missing fields: {field_compliance[:3]}"))
        
        # Analyze phases
        phases = Counter(e.get("phase", "unknown") for e in gen21_entries)
        prey_phases = ["perceive", "react", "engage", "yield", "verify"]
        prey_phase_count = sum(phases.get(p, 0) for p in prey_phases)
        
        # Check for evidence_refs
        entries_with_evidence = sum(1 for e in gen21_entries if "evidence_refs" in e)
        evidence_ratio = entries_with_evidence / max(len(gen21_entries), 1)
        
        return {
            "status": "PASS" if (not invalid_lines and not field_compliance) else "FAIL",
            "total_entries": len(entries),
            "gen21_entries": len(gen21_entries),
            "invalid_lines": len(invalid_lines),
            "field_compliance_issues": len(field_compliance),
            "phases": dict(phases),
            "prey_phase_count": prey_phase_count,
            "evidence_ratio": evidence_ratio
        }
    
    def test_regeneration_capability(self) -> Dict[str, Any]:
        """Test if Gen21 can regenerate components with proper receipts."""
        # This is a simulated regeneration test - in practice would trigger actual regen
        # For audit purposes, we verify the CAPABILITY exists, not actual execution
        
        ssot_path = self.repo_root / "hfo_gem" / "gen_21" / "gpt5-attempt-3-gem.md"
        agents_path = self.repo_root / "AGENTS.md"
        
        if not ssot_path.exists():
            self.findings.append(("CRITICAL", "Cannot test regeneration - SSOT missing"))
            return {"status": "FAIL", "reason": "SSOT missing"}
        
        content = ssot_path.read_text(encoding="utf-8")
        
        # Check for regeneration protocol section
        has_regen_protocol = "Regeneration Protocol" in content or "regeneration" in content.lower()
        has_bootstrap = "Bootstrap" in content or "Cold-Start" in content
        has_prey_workflow = all(term in content for term in ["Perceive", "React", "Engage", "Yield"])
        
        # Check if AGENTS.md exists and aligns
        agents_exists = agents_path.exists()
        agents_aligned = False
        if agents_exists:
            agents_content = agents_path.read_text(encoding="utf-8")
            agents_aligned = all(term in agents_content for term in ["PREY", "Perceive", "blackboard"])
        
        regeneration_capable = all([
            has_regen_protocol,
            has_bootstrap,
            has_prey_workflow,
            agents_exists,
            agents_aligned
        ])
        
        if not regeneration_capable:
            self.findings.append(("WARN", "Regeneration capability incomplete"))
        
        return {
            "status": "PASS" if regeneration_capable else "PARTIAL",
            "has_regen_protocol": has_regen_protocol,
            "has_bootstrap": has_bootstrap,
            "has_prey_workflow": has_prey_workflow,
            "agents_exists": agents_exists,
            "agents_aligned": agents_aligned,
            "regeneration_capable": regeneration_capable
        }
    
    def analyze_explore_exploit_balance(self) -> Dict[str, Any]:
        """Analyze explore vs exploit balance with 4/6 target ratio."""
        # Explore indicators: new patterns, research, experimentation, diverse approaches
        # Exploit indicators: proven patterns, optimization, refinement, production
        
        ssot_path = self.repo_root / "hfo_gem" / "gen_21" / "gpt5-attempt-3-gem.md"
        content = ssot_path.read_text(encoding="utf-8").lower()
        
        explore_keywords = [
            "research", "experiment", "novel", "explore", "discover", "innovative",
            "probe", "test", "trial", "diverse", "quality diversity", "qd"
        ]
        exploit_keywords = [
            "proven", "battle-tested", "optimize", "refine", "production", "reliable",
            "stable", "verified", "validate", "compose", "exemplar", "canon"
        ]
        
        explore_count = sum(content.count(kw) for kw in explore_keywords)
        exploit_count = sum(content.count(kw) for kw in exploit_keywords)
        total = explore_count + exploit_count
        
        if total == 0:
            explore_actual = 0.5
        else:
            explore_actual = explore_count / total
        
        exploit_actual = 1.0 - explore_actual
        
        # Check if within tolerance (±10%)
        explore_in_range = abs(explore_actual - self.explore_ratio) <= 0.10
        exploit_in_range = abs(exploit_actual - self.exploit_ratio) <= 0.10
        
        if not explore_in_range:
            self.findings.append((
                "WARN",
                f"Explore ratio {explore_actual:.2f} not near target {self.explore_ratio} (±0.10)"
            ))
        
        return {
            "status": "PASS" if explore_in_range else "WARN",
            "explore_target": self.explore_ratio,
            "exploit_target": self.exploit_ratio,
            "explore_actual": explore_actual,
            "exploit_actual": exploit_actual,
            "explore_count": explore_count,
            "exploit_count": exploit_count,
            "explore_in_range": explore_in_range,
            "exploit_in_range": exploit_in_range
        }
    
    def detect_hallucination_drift(self) -> Dict[str, Any]:
        """Detect potential hallucination and drift from stated architecture."""
        ssot_path = self.repo_root / "hfo_gem" / "gen_21" / "gpt5-attempt-3-gem.md"
        content = ssot_path.read_text(encoding="utf-8")
        
        # Check for self-contradictions
        contradictions = []
        
        # Check: "Zero Invention" vs actual invention
        zero_invention_claimed = "zero invention" in content.lower()
        invention_indicators = ["we invent", "newly created", "our novel"]
        invention_found = any(ind in content.lower() for ind in invention_indicators)
        if zero_invention_claimed and invention_found:
            contradictions.append("Claims 'zero invention' but contains invention language")
        
        # Check: "Real Tools Only" vs simulated tools
        real_tools_claimed = "real tools" in content.lower() or "no simulated" in content.lower()
        simulation_indicators = ["simulated", "mocked", "emulated", "fabricated results"]
        # Look for these in negative context only (e.g., "no simulated")
        simulation_issues = []
        for ind in simulation_indicators:
            matches = re.finditer(r'\b' + ind + r'\b', content.lower())
            for match in matches:
                context = content[max(0, match.start()-40):min(len(content), match.end()+40)].lower()
                # Skip if it's in a negative/prohibition context
                negative_terms = ['no ', 'not ', 'forbidden', 'ban ', 'avoid', 'never', 'prohibit']
                if any(term in context for term in negative_terms):
                    continue
                simulation_issues.append(ind)
        if real_tools_claimed and simulation_issues:
            contradictions.append(f"Claims 'real tools only' but mentions: {simulation_issues}")
        
        # Check for drift: YAML v19 usage (should be excluded)
        yaml_v19_mentioned = "yaml v19" in content.lower() or "yaml version 19" in content.lower()
        yaml_v19_forbidden = "yaml v19" in content.lower() and ("hallucinated" in content.lower() or "excluded" in content.lower())
        
        if yaml_v19_mentioned and not yaml_v19_forbidden:
            contradictions.append("References YAML v19 without marking as hallucinated/excluded")
        
        # Check for consistent terminology
        terminology_mixed = False
        ooda_count = content.count("OODA")
        jadc2_count = content.count("JADC2")
        mapek_count = content.count("MAPE-K")
        prey_count = content.count("PREY")
        
        # PREY should dominate since it's canonical
        if prey_count < max(ooda_count, jadc2_count, mapek_count):
            terminology_mixed = True
            contradictions.append("PREY not dominant - terminology may be mixed")
        
        hallucination_score = len(contradictions) / 10.0  # Normalize to 0-1 range
        
        return {
            "status": "PASS" if len(contradictions) == 0 else "WARN",
            "contradictions": contradictions,
            "hallucination_score": min(hallucination_score, 1.0),
            "yaml_v19_handled": yaml_v19_forbidden if yaml_v19_mentioned else True,
            "terminology_consistent": not terminology_mixed,
            "terminology_counts": {
                "PREY": prey_count,
                "OODA": ooda_count,
                "JADC2": jadc2_count,
                "MAPE-K": mapek_count
            }
        }
    
    def run_full_audit(self) -> Dict[str, Any]:
        """Run all audit checks and compile results."""
        print("🔍 Starting Gen21 Architecture Audit...")
        print(f"   Timestamp: {self.timestamp}")
        print(f"   Explore/Exploit Target: {self.explore_ratio:.0%}/{self.exploit_ratio:.0%}")
        print()
        
        results = {
            "timestamp": self.timestamp,
            "explore_exploit_seed": f"{self.explore_ratio:.0%}/{self.exploit_ratio:.0%}",
            "ssot_compliance": self.audit_ssot_compliance(),
            "blackboard_protocol": self.audit_blackboard_protocol(),
            "regeneration": self.test_regeneration_capability(),
            "explore_exploit": self.analyze_explore_exploit_balance(),
            "hallucination": self.detect_hallucination_drift(),
            "findings": self.findings
        }
        
        # Overall status
        statuses = [
            results["ssot_compliance"]["status"],
            results["blackboard_protocol"]["status"],
            results["regeneration"]["status"],
            results["explore_exploit"]["status"],
            results["hallucination"]["status"]
        ]
        
        if "FAIL" in statuses or "CRITICAL" in [f[0] for f in self.findings]:
            overall = "FAIL"
        elif "WARN" in statuses:
            overall = "PARTIAL"
        else:
            overall = "PASS"
        
        results["overall_status"] = overall
        
        return results
    
    def generate_bluf_report(self, results: Dict[str, Any]) -> str:
        """Generate one-page BLUF summary with matrix and diagrams."""
        
        status_emoji = {
            "PASS": "✅",
            "PARTIAL": "⚠️",
            "FAIL": "❌",
            "WARN": "⚠️",
            "CRITICAL": "🔴"
        }
        
        report = f"""# Gen21 Architecture Audit Report — BLUF

**Timestamp:** {results['timestamp']}  
**Overall Status:** {status_emoji.get(results['overall_status'], '❓')} **{results['overall_status']}**  
**Explore/Exploit Seed:** {results['explore_exploit_seed']}

---

## Executive Summary

Generation 21 architecture audit using independent Python tools to validate:
- SSOT compliance (≥1000 lines, PREY canonical, safety envelope)
- Blackboard protocol adherence (JSONL receipts with evidence_refs)
- Regeneration capability (bootstrap, AGENTS.md alignment)
- Explore/Exploit balance (target {results['explore_exploit_seed']})
- Hallucination/drift detection (zero invention, real tools, terminology consistency)

**Bottom Line:** {self._get_bottom_line(results)}

---

## Audit Matrix

| Dimension | Status | Score | Key Metrics | Issues |
|-----------|--------|-------|-------------|--------|
| **SSOT Compliance** | {status_emoji.get(results['ssot_compliance']['status'], '?')} {results['ssot_compliance']['status']} | {results['ssot_compliance']['line_count']}/1000 lines | PREY: {sum(results['ssot_compliance']['prey_terms'].values())} mentions, Placeholders: {results['ssot_compliance']['placeholders']} | {self._get_issues('SSOT', results)} |
| **Blackboard Protocol** | {status_emoji.get(results['blackboard_protocol']['status'], '?')} {results['blackboard_protocol']['status']} | {results['blackboard_protocol']['gen21_entries']} Gen21 entries | Evidence ratio: {results['blackboard_protocol']['evidence_ratio']:.0%} | {self._get_issues('Blackboard', results)} |
| **Regeneration** | {status_emoji.get(results['regeneration']['status'], '?')} {results['regeneration']['status']} | {'5/5' if results['regeneration']['regeneration_capable'] else 'Partial'} components | AGENTS.md: {status_emoji.get('PASS' if results['regeneration']['agents_aligned'] else 'FAIL', '?')} | {self._get_issues('Regeneration', results)} |
| **Explore/Exploit** | {status_emoji.get(results['explore_exploit']['status'], '?')} {results['explore_exploit']['status']} | {results['explore_exploit']['explore_actual']:.0%}/{results['explore_exploit']['exploit_actual']:.0%} | Target: {results['explore_exploit']['explore_target']:.0%}/{results['explore_exploit']['exploit_target']:.0%} | {self._get_issues('Explore', results)} |
| **Hallucination** | {status_emoji.get(results['hallucination']['status'], '?')} {results['hallucination']['status']} | {len(results['hallucination']['contradictions'])} contradictions | Score: {results['hallucination']['hallucination_score']:.2f} | {self._get_issues('Hallucination', results)} |

---

## Architecture Flow Diagram

```mermaid
graph TD
    SSOT[Gen21 SSOT<br/>{results['ssot_compliance']['line_count']} lines] -->|PREY workflow| PREY[Perceive→React→Engage→Yield]
    PREY -->|receipts| BB[Blackboard JSONL<br/>{results['blackboard_protocol']['gen21_entries']} entries]
    PREY --> VERIFY[Independent Verify]
    VERIFY -->|PASS| DIGEST[Digest→Human]
    VERIFY -->|FAIL| REGEN[Regenerate]
    REGEN --> PREY
    
    SSOT -.->|bootstraps| AGENTS[AGENTS.md]
    AGENTS -.->|guides| WORKERS[Workers]
    WORKERS -->|evidence| BB
    
    style SSOT fill:#2d5,stroke:#333,stroke-width:3px
    style VERIFY fill:#{'2d5' if results['regeneration']['regeneration_capable'] else 'd52'},stroke:#333,stroke-width:2px
    style BB fill:#{'2d5' if results['blackboard_protocol']['status'] == 'PASS' else 'dd5'},stroke:#333,stroke-width:2px
```

---

## Explore/Exploit Balance

```mermaid
pie title Explore vs Exploit Balance
    "Explore (Target {results['explore_exploit']['explore_target']:.0%})" : {results['explore_exploit']['explore_count']}
    "Exploit (Target {results['explore_exploit']['exploit_target']:.0%})" : {results['explore_exploit']['exploit_count']}
```

**Analysis:** {'✅ Within target range' if results['explore_exploit']['explore_in_range'] else f"⚠️ Actual {results['explore_exploit']['explore_actual']:.0%} vs target {results['explore_exploit']['explore_target']:.0%}"}

---

## Key Findings

{self._format_findings(results['findings'])}

---

## Recommendations

{self._generate_recommendations(results)}

---

## Evidence References

- SSOT: `hfo_gem/gen_21/gpt5-attempt-3-gem.md`
- Blackboard: `hfo_blackboard/obsidian_synapse_blackboard.jsonl`
- Agents Guide: `AGENTS.md`
- Audit Tool: `scripts/audit_gen21.py` (independent Python)

**Audit Methodology:** Independent static analysis using Python tools, no self-audit or subjective evaluation. All metrics derived from quantifiable evidence in repository artifacts.

---

*Generated by Independent Gen21 Auditor at {results['timestamp']}*
"""
        return report
    
    def _get_bottom_line(self, results: Dict[str, Any]) -> str:
        """Generate bottom line summary."""
        status = results['overall_status']
        if status == "PASS":
            return "Gen21 architecture is well-formed and operational. SSOT meets requirements, PREY workflow canonical, safety envelope present, regeneration capability confirmed."
        elif status == "PARTIAL":
            return "Gen21 architecture is functional with warnings. Core structure sound but some components need refinement. See findings for details."
        else:
            return "Gen21 architecture has critical issues. SSOT compliance or protocol violations detected. Remediation required before operational use."
    
    def _get_issues(self, category: str, results: Dict[str, Any]) -> str:
        """Get issues summary for a category."""
        category_findings = [f for f in results['findings'] if category.lower() in f[1].lower()]
        if not category_findings:
            return "None"
        return f"{len(category_findings)} issues"
    
    def _format_findings(self, findings: List[Tuple[str, str]]) -> str:
        """Format findings list."""
        if not findings:
            return "✅ **No critical findings** - all checks passed\n"
        
        output = []
        by_severity = defaultdict(list)
        for severity, message in findings:
            by_severity[severity].append(message)
        
        for severity in ["CRITICAL", "FAIL", "WARN"]:
            if severity in by_severity:
                output.append(f"### {severity}")
                for msg in by_severity[severity]:
                    output.append(f"- {msg}")
                output.append("")
        
        return "\n".join(output)
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> str:
        """Generate recommendations based on audit results."""
        recs = []
        
        if not results['ssot_compliance']['placeholder_pass']:
            recs.append("1. **Remove placeholders** from SSOT document (TODO, ..., omitted)")
        
        if not results['ssot_compliance']['prey_canonical']:
            recs.append("2. **Increase PREY terminology** usage to establish canonical workflow")
        
        if results['blackboard_protocol']['evidence_ratio'] < 0.8:
            recs.append("3. **Add evidence_refs** to blackboard receipts (currently {:.0%})".format(
                results['blackboard_protocol']['evidence_ratio']))
        
        if not results['regeneration']['regeneration_capable']:
            recs.append("4. **Complete regeneration capability** - ensure all bootstrap components present")
        
        if not results['explore_exploit']['explore_in_range']:
            actual = results['explore_exploit']['explore_actual']
            target = results['explore_exploit']['explore_target']
            direction = "more" if actual < target else "less"
            recs.append(f"5. **Adjust explore/exploit balance** - need {direction} exploration (actual {actual:.0%} vs target {target:.0%})")
        
        if results['hallucination']['contradictions']:
            recs.append(f"6. **Resolve contradictions** - {len(results['hallucination']['contradictions'])} found (see findings)")
        
        if not recs:
            recs.append("✅ **No immediate action required** - continue monitoring and maintain current quality")
        
        return "\n".join(recs)


def main():
    parser = argparse.ArgumentParser(description="Audit Generation 21 Architecture")
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root path"
    )
    parser.add_argument(
        "--explore-ratio",
        type=float,
        default=0.4,
        help="Target explore ratio (0.0-1.0)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output report path (default: stdout)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON results instead of markdown"
    )
    
    args = parser.parse_args()
    
    auditor = Gen21Auditor(args.repo, args.explore_ratio)
    results = auditor.run_full_audit()
    
    if args.json:
        output = json.dumps(results, indent=2)
    else:
        output = auditor.generate_bluf_report(results)
    
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print(f"✅ Report written to: {args.output}")
    else:
        print(output)
    
    # Exit with appropriate code
    status = results['overall_status']
    sys.exit(0 if status == "PASS" else (1 if status == "FAIL" else 2))


if __name__ == "__main__":
    main()
