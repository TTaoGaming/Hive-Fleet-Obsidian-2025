# ADR-001: Integration of Policy-as-Code and Progressive Delivery for HFO Safety

**Status:** Proposed  
**Date:** 2025-10-30  
**Authors:** HFO Research Team  
**Deciders:** Mission Lead  
**Technical Story:** Prevent compounded hallucinations in AI agent systems through proven platform engineering patterns

## Context and Problem Statement

Hive Fleet Obsidian (HFO) is a multi-agent AI system using the PREY workflow (Perceive → React → Engage → Yield). As AI agents generate code and configurations, there is a critical risk of **compounded hallucinations**—where AI-generated errors propagate through the system, creating cascading failures that are difficult to detect and remedy.

Current HFO Gen21 has safety measures (canary, tripwires, revert, Independent Verify gate, blackboard receipts), but lacks the automated enforcement mechanisms used by top platform teams to prevent unsafe changes from reaching production or even human review.

**Core Question:** How can we adopt industry-proven safety patterns to prevent compounded hallucinations while maintaining HFO's architectural principles (PREY workflow, Swarmlord facade, Zero Invention)?

## Decision Drivers

* **Risk Mitigation:** Prevent low-quality or hallucinated code from reaching humans or production
* **Automation:** Reduce manual review burden through automated gates and rollback
* **Provenance:** Ensure all artifacts have cryptographic proof of origin and integrity
* **Observability:** Enable data-driven decisions about agent behavior quality
* **Alignment:** Must integrate seamlessly with existing HFO Gen21 architecture
* **Proven Patterns:** Zero Invention principle requires using battle-tested approaches
* **Developer Experience:** Cannot significantly slow down legitimate development

## Considered Options

### Option 1: Status Quo (Manual Review Only)
Continue with current Gen21 safety envelope (canary, tripwires, revert) and manual Independent Verify gate.

**Pros:**
- No new dependencies or infrastructure
- Simple to understand and maintain
- Full human control over decisions

**Cons:**
- Manual review is slow and error-prone
- Humans cannot catch all subtle hallucinations
- No automated rollback on quality degradation
- Lacks cryptographic provenance
- Does not scale with agent complexity

### Option 2: Lightweight Static Analysis Only
Add CodeQL and Semgrep as required CI checks.

**Pros:**
- Easy to integrate (GitHub native)
- Catches common security/quality issues
- Low operational overhead

**Cons:**
- No runtime safety (only pre-merge)
- No progressive rollout capability
- No supply chain integrity
- Limited to pattern-based detection
- Cannot catch semantic hallucinations

### Option 3: Full Platform Engineering Stack (CHOSEN)
Integrate the complete stack: Policy-as-Code (OPA/Conftest), Static Analysis (CodeQL/Semgrep), Feature Flags (OpenFeature), Progressive Delivery (Argo Rollouts), Supply Chain Integrity (SLSA/Cosign), Observability (OpenTelemetry), Docs-as-Code (TechDocs), and LLM-specific controls (OWASP LLM Top-10).

**Pros:**
- Defense in depth with multiple safety layers
- Automated enforcement reduces human burden
- Progressive rollout limits blast radius
- Cryptographic provenance prevents supply chain attacks
- Data-driven rollback on quality degradation
- All patterns are battle-tested (Google, Netflix, CNCF)
- Aligns with HFO's Zero Invention principle

**Cons:**
- Highest implementation complexity
- Requires new infrastructure (K8s for Argo, metrics backend for OTel)
- Learning curve for team
- Potential for over-engineering in early phases

### Option 4: Hybrid Approach (Gates + Observability Only)
Implement policy-as-code gates and observability, defer progressive delivery and supply chain.

**Pros:**
- Balances automation with complexity
- Can run without Kubernetes
- Faster to implement initially

**Cons:**
- Lacks runtime safety (canary/rollback)
- No supply chain integrity
- Still requires eventual migration to full stack
- Partial solution may create false confidence

## Decision Outcome

**Chosen option: Option 3 (Full Platform Engineering Stack)**, because it provides comprehensive defense against compounded hallucinations while using only proven patterns (satisfying Zero Invention principle).

Implementation will be **phased over 12 weeks** to manage complexity:

1. **Phase 1-2 (Weeks 1-4):** Policy gates + Static analysis (hard blockers)
2. **Phase 3-4 (Weeks 5-8):** Observability + Progressive delivery (runtime safety)
3. **Phase 5-6 (Weeks 9-12):** Supply chain + Docs-as-code + LLM controls (completeness)

### Positive Consequences

* **Hard Gates Block Bad PRs:** OPA/Conftest prevents merges missing tests, receipts, or containing placeholders
* **Static Analysis Catches Variants:** CodeQL/Semgrep find security issues and HFO-specific violations
* **Progressive Delivery Limits Risk:** Feature flags + canaries constrain blast radius; auto-rollback on SLO breach
* **Provenance Prevents Tampering:** SLSA attestations + Cosign signing ensure artifact integrity
* **Observability Enables Data-Driven Decisions:** OpenTelemetry metrics drive canary analysis and DORA tracking
* **Docs-as-Code Creates Stable Substrate:** TechDocs ensures agents read verified documentation
* **LLM Controls Prevent Specific Risks:** OWASP LLM Top-10 policies block prompt injection, excessive agency

### Negative Consequences

* **Infrastructure Requirements:** Need Kubernetes for Argo Rollouts, metrics backend for OpenTelemetry
* **Initial Slowdown:** First PRs will be slower as policies are refined
* **Operational Complexity:** More moving parts to monitor and maintain
* **Team Learning Curve:** Requires training on OPA, Argo, OpenFeature, etc.

## Validation

Success will be measured by:

1. **Quantitative Metrics:**
   - **Policy Gate Effectiveness:** % of PRs blocked for missing requirements (target: <5% false positives after tuning)
   - **Static Analysis Coverage:** % of code scanned (target: 100%)
   - **Canary Success Rate:** % of canary deployments that pass analysis (target: >95%)
   - **DORA Four Keys:**
     - Deployment frequency (increase expected)
     - Lead time for changes (may increase initially, then decrease)
     - Change failure rate (should decrease significantly)
     - Time to restore service (should decrease with auto-rollback)

2. **Qualitative Outcomes:**
   - Reduced incidents of hallucinated code reaching production
   - Increased confidence in agent-generated artifacts
   - Faster Independent Verify gate (automated checks reduce manual effort)
   - Better traceability (provenance chain)

3. **Safety Validation:**
   - **Cold Start Test:** Can new developer set up HFO with safety stack in ≤1 hour?
   - **Fault Injection:** Can system detect and rollback deliberately introduced hallucinations?
   - **Audit Trail:** Can we reconstruct full provenance of any artifact?

## Implementation Receipts

### Phase 1: Policy Gates (Evidence Required Before PASS)

**OPA/Conftest Integration:**
- File: `.conftest/policy/hfo_merge_requirements.rego`
- Required checks: tests exist, blackboard receipts present, chunk size ≤200, no placeholders
- CI integration: GitHub Actions workflow `.github/workflows/policy-check.yml`
- Evidence: Policy test results in CI logs + blackboard receipt

**CodeQL Integration:**
- File: `.github/workflows/codeql.yml`
- Queries: Default security queries + HFO custom queries
- Evidence: CodeQL dashboard showing scan results

**Semgrep Integration:**
- File: `.semgrep/hfo_rules.yml`
- Rules: `no-direct-human-prompt`, `require-evidence-refs`, `enforce-prey-terminology`
- Evidence: Semgrep scan results in CI logs

### Phase 2: Progressive Delivery (Evidence Required Before PASS)

**OpenFeature Integration:**
- File: `src/feature_flags/openfeature_client.py`
- Flags: `enable_aggressive_mutation`, `enable_experimental_verify`, `enable_new_stigmergy`
- Provider: File-based provider for local dev, LaunchDarkly/Flagsmith for production
- Evidence: Feature flag evaluation logs in blackboard

**Argo Rollouts (if K8s available):**
- File: `k8s/rollouts/hfo-swarmlord-rollout.yml`
- Strategy: Canary with 10%/50%/100% steps
- Analysis: `success-rate` template querying verify pass rate
- Evidence: Argo dashboard showing rollout history

### Phase 3: Observability (Evidence Required Before PASS)

**OpenTelemetry Instrumentation:**
- File: `src/observability/otel_config.py`
- Spans: `prey_loop`, `perceive`, `react`, `engage`, `yield`, `verify`
- Metrics: `hfo_verify_pass_total`, `hfo_verify_total`, `hfo_chunk_size`, `hfo_tripwire_hits`
- Evidence: Trace IDs in blackboard receipts, Prometheus metrics endpoint

**DORA Metrics Dashboard:**
- File: `dashboards/hfo_dora_metrics.json`
- Metrics: Deployment frequency, lead time, change failure rate, time to restore
- Evidence: Dashboard screenshot showing metrics over time

### Phase 4: Supply Chain (Evidence Required Before PASS)

**SLSA Attestations:**
- File: `.github/workflows/build-and-attest.yml`
- Provenance: SLSA level 2 minimum (hermetic builds for level 3)
- Evidence: Attestation JSON files in release artifacts

**Cosign Signing:**
- File: `.github/workflows/sign-artifacts.yml`
- Keyless signing using GitHub OIDC
- Evidence: Signature files (.sig) alongside artifacts

### Phase 5: Docs-as-Code (Evidence Required Before PASS)

**TechDocs Setup:**
- File: `mkdocs.yml`
- Structure: Diátaxis (tutorials, how-to, reference, explanation)
- CI: Build docs on every merge
- Evidence: Published docs site URL in blackboard receipt

**ADR Template:**
- File: `docs/adr/template.md`
- Required fields: Status, Date, Context, Decision, Consequences, Validation
- Evidence: This ADR (ADR-001) as exemplar

### Phase 6: LLM Safety (Evidence Required Before PASS)

**OWASP LLM Controls:**
- File: `.conftest/policy/llm_safety.rego`
- Controls: LLM01 (prompt injection), LLM02 (insecure output), LLM06 (excessive agency)
- Evidence: Policy test suite showing all controls enforced

**NIST AI RMF Mapping:**
- File: `docs/governance/nist_ai_rmf_controls.md`
- Mapping: Each NIST control to HFO implementation
- Evidence: Completed mapping document with evidence_refs

## Compliance and Links

### Provenance (External Evidence)

All patterns are sourced from authoritative references:

- **OPA/Conftest:** https://www.openpolicyagent.org/docs/latest/ (CNCF graduated project)
- **CodeQL:** https://codeql.github.com/ (GitHub native)
- **Semgrep:** https://semgrep.dev/ (Used by GitLab, Snowflake, others)
- **OpenFeature:** https://openfeature.dev/ (CNCF incubating project)
- **Argo Rollouts:** https://argoproj.github.io/rollouts/ (CNCF graduated Argo project)
- **SLSA:** https://slsa.dev/ (Google, Linux Foundation)
- **Sigstore Cosign:** https://www.sigstore.dev/ (Linux Foundation)
- **OpenTelemetry:** https://opentelemetry.io/ (CNCF incubating, wide adoption)
- **DORA Metrics:** https://dora.dev/ (Google Cloud, DevOps Research and Assessment)
- **TechDocs:** https://backstage.io/docs/features/techdocs/ (Spotify Backstage, CNCF incubating)
- **Diátaxis:** https://diataxis.fr/ (Documentation framework)
- **OWASP LLM Top-10:** https://owasp.org/www-project-top-10-for-large-language-model-applications/
- **NIST AI RMF:** https://www.nist.gov/itl/ai-risk-management-framework

### HFO Gen21 Alignment

This decision aligns with Gen21 GEM principles:

- **Zero Invention:** All patterns are proven (see provenance links above)
- **PREY Workflow:** Patterns integrate at specific PREY phases (React=gates, Engage=flags, Yield=observability)
- **Swarmlord Facade:** No changes to human interface; safety is transparent
- **Safety Envelope:** Extends existing canary/tripwires/revert with automation
- **Independent Verify:** Policy gates strengthen the Verify PASS requirement
- **Blackboard Receipts:** All safety events logged to JSONL with evidence_refs
- **Stigmergy Protocol:** Observability data becomes part of shared context

## Alternatives Not Chosen (With Rationale)

### Build Custom Policy Engine
**Why Not:** Violates Zero Invention; OPA is proven and CNCF standard

### Use Vendor-Specific Feature Flags (LaunchDarkly Only)
**Why Not:** Lock-in risk; OpenFeature provides vendor-neutral API

### Skip Progressive Delivery (Deploy Everything at Once)
**Why Not:** Violates safety envelope principle; blast radius too large

### Manual Artifact Signing
**Why Not:** Does not scale; Cosign provides automation with keyless option

### Build Custom Observability
**Why Not:** Violates Zero Invention; OpenTelemetry is industry standard

## Notes

* **Cost Consideration:** Most tools have free/open-source tiers sufficient for HFO development
* **Fallback Plan:** If Kubernetes unavailable, can use feature flags + manual canary with metrics
* **Migration Path:** Existing HFO Gen21 systems can adopt phases incrementally without breaking changes
* **Team Skill Requirements:** Assumes familiarity with CI/CD, basic K8s concepts; provides learning resources

## Related Documents

- **Primary Research:** `hfo_research_doc/hfo-safety-integration-policy-as-code.md`
- **Executive Summary:** `hfo_research_doc/hfo-safety-integration-executive-summary.md`
- **Gen21 GEM SSOT:** `hfo_gem/gen_21/gpt5-attempt-3-gem.md`
- **AGENTS.md:** Root-level agent operating guide

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-10-30 | 1.0 | HFO Research | Initial ADR based on safety integration research |

---

**Blackboard Receipt:**
```json
{
  "mission_id": "hfo_safety_adr_2025-10-30",
  "phase": "engage",
  "summary": "Created ADR-001 for policy-as-code and progressive delivery integration",
  "evidence_refs": [
    "hfo_research_doc/ADR-001-safety-integration-policy-as-code.md:1-300"
  ],
  "safety_envelope": {
    "chunk_size_max": 200,
    "tripwires": ["provenance_verified", "no_invention_violations"]
  },
  "timestamp": "2025-10-30T17:20:00Z"
}
```
