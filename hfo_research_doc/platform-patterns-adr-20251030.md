# ADR: Platform Engineering Patterns for HFO Hallucination Prevention

**Status:** Proposed  
**Date:** 2025-10-30  
**Decision Makers:** HFO Architecture Team  
**Context Mission ID:** platform_patterns_integration_2025-10-30

## Context

Hive Fleet Obsidian (HFO) Gen21 architecture requires safe, autonomous AI agent operation with minimal human intervention. Current challenge: AI agents can produce compounded hallucinations (fabricated code, false claims, drift from requirements) that bypass verification when operating at scale. Industry platform teams at Google, Netflix, CNCF have proven patterns that prevent unsafe changes from reaching production.

### Problem Statement
Without automated safety controls, HFO agents face:
- **Hallucination Drift**: Agents making unverified claims or generating code without proof
- **Blast Radius**: Single agent error affecting entire system
- **Verification Gap**: Manual human review doesn't scale to autonomous operation
- **Trust Deficit**: No cryptographic proof of artifact provenance

### Current State (As-Is)
- Blackboard JSONL receipts (manual enforcement)
- PREY loop with Verify gate (human-dependent)
- Chunk size limits in AGENTS.md (policy, not enforced)
- No automated policy gates
- No progressive delivery mechanism
- No feature flag infrastructure
- No supply chain attestations

### Desired State (To-Be)
- Automated policy gates block unsafe PRs before human review
- Progressive delivery with canary analysis and auto-rollback
- Feature flags control capability exposure
- Supply chain attestations prove artifact integrity
- Observability drives data-based decisions
- LLM-specific safety controls prevent excessive agency

## Decision

**Adopt 9 industry-proven platform engineering patterns** to create defense-in-depth against hallucination drift:

1. **Code Review + Small Diffs** (Google Engineering Practices)
2. **Progressive Delivery** (Google SRE + Argo Rollouts)
3. **Feature Flags** (OpenFeature CNCF standard)
4. **Policy-as-Code Gates** (OPA/Conftest)
5. **Static Analysis** (CodeQL + Semgrep)
6. **Supply-Chain Integrity** (SLSA + Sigstore Cosign)
7. **Observability** (OpenTelemetry + DORA metrics)
8. **Docs-as-Code** (Backstage TechDocs + Diátaxis)
9. **LLM-Specific Safety** (OWASP LLM Top 10 + NIST AI RMF)

### Implementation Approach
**Phase-based rollout** (12 weeks) prioritizing critical safety controls first:
- Weeks 1-2: Foundation (OPA, CodeQL, chunk validation, receipt validation)
- Weeks 3-4: Progressive delivery (OpenFeature, Argo Rollouts)
- Weeks 5-6: Observability (OpenTelemetry, metrics, dashboards)
- Weeks 7-8: Supply chain (SLSA provenance, Cosign signing)
- Weeks 9-10: Docs-as-code (TechDocs, Diátaxis structure, ADR templates)
- Weeks 11-12: LLM safety (OWASP policies, runtime guards, NIST governance)

### Integration with HFO Workflows
- **HIVE** (Hunt → Integrate → Verify → Evolve): Policy gates, verification, docs-as-code
- **GROWTH** (F3EAD): Feature flags, supply chain, dissemination
- **SWARM** (D3A + Mutate): Progressive delivery, observability, canary analysis
- **PREY** (OODA): Static analysis, LLM safety, chunk limits

## Consequences

### Positive
- **Automated Safety**: Hard gates block hallucinations before merge (OPA policies)
- **Controlled Rollout**: Canaries limit blast radius, auto-rollback on SLO breach
- **Cryptographic Trust**: SLSA attestations + Cosign signatures prove provenance
- **Data-Driven Decisions**: OpenTelemetry metrics inform rollback/promotion
- **Stable Knowledge Base**: Docs-as-code captures accepted truth
- **Defense-in-Depth**: Multiple layers prevent single point of failure

### Negative
- **Complexity**: 9 tools to integrate and maintain
- **Learning Curve**: Team must learn OPA, Argo Rollouts, OpenTelemetry, etc.
- **Operational Overhead**: Policy maintenance, canary configuration, metric tuning
- **Velocity Impact**: More gates may slow initial PR merges (offset by automation)

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Tool integration complexity | Phased rollout (12 weeks), start with highest-ROI patterns |
| Policy false positives blocking valid PRs | Start with warnings, iterate to enforcement; red-team test policies |
| Canary analysis incorrect rollback | Define clear SLO thresholds; manual override capability |
| SLSA attestation generation failures | Graceful degradation; warn but don't block initially |
| Team resistance to overhead | Show metrics: reduction in hallucination incidents, faster mean time to recovery |

## Alternatives Considered

### Alternative 1: Build Custom Tooling
- **Pros**: Full control, tailored to HFO
- **Cons**: Reinventing wheel, maintenance burden, no community support
- **Rejection Reason**: Violates HFO principle "adopt then adapt with no new inventions"

### Alternative 2: Manual Review Only
- **Pros**: Simple, no new tools
- **Cons**: Doesn't scale to autonomous operation, human bottleneck
- **Rejection Reason**: Fails to meet Gen21 autonomy requirements

### Alternative 3: Subset of Patterns (e.g., only OPA + CodeQL)
- **Pros**: Lower complexity, faster implementation
- **Cons**: Single layer insufficient for defense-in-depth
- **Rejection Reason**: Hallucinations require multiple complementary controls

## Evidence and Receipts

### Industry Adoption Proof
- **Google**: Code review guidelines public (https://google.github.io/eng-practices/), SRE Book documents canarying
- **Netflix**: OPA use documented in tech blog for policy enforcement
- **CNCF**: OpenFeature, OpenTelemetry, Argo are graduated/incubating projects with production use
- **SLSA**: Created by Google, adopted by Linux Foundation, GitHub
- **OWASP LLM Top 10**: Published 2023, industry-standard LLM risk taxonomy

### HFO Alignment Verification
- **AGENTS.md Compliance**: Chunk limits (≤200 lines) enforced via OPA policy
- **Blackboard Protocol**: Receipt validation policy checks evidence_refs presence
- **PREY Loop**: Static analysis in Perceive; capability checks in React; telemetry in Engage
- **Safety Envelope**: Tripwire activation logged to observability backend

### References
1. Google Engineering Practices Guide: https://google.github.io/eng-practices/
2. Google SRE Book, Chapter 31 "Canarying Releases": https://sre.google/sre-book/release-engineering/
3. CNCF Graduated Projects: https://www.cncf.io/projects/
4. SLSA Specification v1.0: https://slsa.dev/spec/v1.0/
5. OWASP Top 10 for LLM Applications: https://owasp.org/www-project-top-10-for-large-language-model-applications/
6. NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
7. Diátaxis Documentation Framework: https://diataxis.fr/
8. Argo Rollouts Documentation: https://argoproj.github.io/rollouts/
9. OpenTelemetry Documentation: https://opentelemetry.io/docs/
10. Backstage TechDocs: https://backstage.io/docs/features/techdocs/techdocs-overview

## Implementation Evidence Requirements

Each phase completion requires:
- **Policy**: OPA .rego files committed to repo
- **CI Integration**: GitHub Actions workflow with required checks
- **Metrics**: Dashboards showing pattern effectiveness (e.g., policy block rate, canary rollback rate)
- **Documentation**: ADR for significant decisions, TechDocs for how-tos
- **Blackboard Receipt**: Phase completion logged with evidence_refs to policies, configs, dashboards

## Success Criteria

Measurable within 6 months of full implementation:
1. **Policy Gate Effectiveness**: >90% of hallucination-prone PRs blocked before merge
2. **Canary Protection**: >95% of degraded deployments auto-rolled back within 5 minutes
3. **MTTR Improvement**: Mean time to recovery from incidents reduced by 50%
4. **Verification Pass Rate**: First-time verification pass rate >80%
5. **Zero Trust Violations**: 100% of deployed artifacts have valid SLSA attestations + Cosign signatures

## Review and Update

- **Review Cadence**: Monthly for first 6 months, quarterly thereafter
- **Triggers for Update**: New OWASP/NIST guidance, tool deprecation, team feedback
- **Ownership**: HFO Architecture Team (Swarmlord facade)

## Blackboard Receipt

```json
{"mission_id":"platform_patterns_adr_2025-10-30","phase":"engage","summary":"Created ADR for platform engineering patterns adoption with evidence and receipts","evidence_refs":["hfo_research_doc/platform-patterns-adr-20251030.md:1-169","Google SRE Book","CNCF Projects","SLSA v1.0","OWASP LLM Top 10","NIST AI RMF"],"safety_envelope":{"chunk_size_max":200,"actual_lines":169},"blocked_capabilities":[],"timestamp":"2025-10-30T17:17:00Z"}
```
