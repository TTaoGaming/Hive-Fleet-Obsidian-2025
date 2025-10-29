# Generation 21 Architecture Audit Tools

This directory contains independent audit tools for validating Generation 21's architecture and self-regeneration capabilities.

## Quick Start

Run the comprehensive audit:
```bash
python3 scripts/generate_audit_summary.py
```

This will:
1. Run all audit checks
2. Generate a one-page summary with BLUF, matrix, and diagrams
3. Save results to `temp/GEN21_AUDIT_SUMMARY.md`

## Individual Tools

### `audit_gen21.py`
Independent architecture integrity audit.

**Checks**:
- SSOT completeness (≥1000 lines, required sections)
- PREY canonical terminology usage
- Blackboard JSONL integrity
- Safety envelope adherence (canary/tripwires/revert)
- Drift analysis (claims vs implementation)

**Usage**:
```bash
python3 scripts/audit_gen21.py
```

**Output**: JSON with detailed results

### `test_gen21_regeneration.py`
Self-regeneration capability tests.

**Tests**:
- Bootstrap executability
- PREY workflow completeness
- Diagram completeness (no placeholders)
- Circular dependency detection
- Evidence discipline specification

**Usage**:
```bash
python3 scripts/test_gen21_regeneration.py
```

**Output**: JSON with regeneration score (0.0-1.0)

### `test_explore_exploit.py`
Explore/Exploit 8/2 ratio validation.

**Tests**:
- Quality Diversity (QD) architecture
- Mutation mechanisms
- Portfolio diversity
- Risk management
- 8/2 ratio simulation (with seed)

**Usage**:
```bash
python3 scripts/test_explore_exploit.py [seed]
```

**Default seed**: 42

**Output**: JSON with explore/exploit support score

### `generate_audit_summary.py`
Comprehensive report generator.

Combines all audit results into a one-page markdown report with:
- BLUF (Bottom Line Up Front)
- Audit matrix
- Mermaid diagrams
- Detailed findings
- Recommendations

**Usage**:
```bash
python3 scripts/generate_audit_summary.py
```

**Output**: 
- Console output with full report
- `temp/gen21_audit_report_<timestamp>.md`
- `temp/GEN21_AUDIT_SUMMARY.md` (latest)

## Audit Methodology

All tools use **independent validation** rather than self-reporting:
- Parse actual Gen21 document (not claims)
- Validate blackboard JSONL (not in-memory state)
- Grep/regex for terminology (not assumptions)
- Measure against stated requirements

This approach detects hallucination and architectural drift.

## Example Results

**Overall Health**: 90.7%
- Architecture Integrity: 82% (9/11 checks)
- Self-Regeneration: 100% (9/9 tests)
- Explore/Exploit: 93% (8/9 tests)
- Drift: 9% (low)

## Files Audited

- Gen21 SSOT: `hfo_gem/gen_21/gpt5-attempt-3-gem.md`
- Blackboard: `hfo_blackboard/obsidian_synapse_blackboard.jsonl`
- AGENTS.md: `AGENTS.md`

## Dependencies

Standard library only:
- `json`
- `re`
- `subprocess`
- `pathlib`
- `dataclasses`

## Evidence Discipline

All audit results include:
- `evidence`: File paths, line ranges, or specific findings
- `timestamp`: ISO 8601 UTC
- `status`: PASS/WARN/FAIL
- `score`: Quantitative measure (0.0-1.0)

## Integration with PREY Loop

These tools support the Gen21 PREY loop:
- **Perceive**: Audit current state
- **React**: Identify issues and plan fixes
- **Engage**: Apply fixes
- **Yield**: Re-audit and verify

Run audits before and after changes to measure improvement.

## Next Steps

1. Run audit regularly (daily/weekly)
2. Track drift over time
3. Address warnings before they become failures
4. Update Gen21 SSOT based on findings
5. Validate fixes with independent verification
