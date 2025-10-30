# ADR-0001: Adopt Layered Defense Architecture for AI Safety and Hallucination Mitigation

## Status

**Proposed** - 2025-10-30

## Context

Hive Fleet Obsidian (HFO) operates as an autonomous AI agent system with significant code generation and modification capabilities. Without proper safeguards, compounding hallucinations pose serious risks:

1. **Unverified code changes** can introduce subtle bugs or security vulnerabilities
2. **Agent-generated documentation** may contain fabricated claims or broken references
3. **Autonomous decision-making** without validation can lead to cascading failures
4. **Knowledge drift** occurs when agents reference their own unverified outputs

Current HFO architecture includes safety mechanisms (PREY loop, blackboard receipts, verify gates) but lacks industry-standard tooling for policy enforcement, static analysis, progressive delivery, and supply chain integrity.

### Problem Statement

How can HFO achieve defense-in-depth against AI hallucinations while maintaining development velocity and aligning with existing PREY/HIVE/GROWTH/SWARM workflows?

### Key Requirements

1. **Pre-merge validation**: Block low-quality changes before human review
2. **Runtime safety**: Limit blast radius of risky changes in production
3. **Supply chain integrity**: Verify provenance of all deployed artifacts
4. **Knowledge stabilization**: Create verifiable documentation substrate for agents
5. **LLM-specific controls**: Prevent prompt injection, excessive agency, and output leakage
6. **HFO workflow alignment**: Integrate with existing PREY/HIVE/GROWTH/SWARM patterns
7. **Minimal complexity**: Prefer open standards and CNCF projects over custom solutions

## Decision

We will adopt a **layered defense architecture** combining industry-proven patterns from Google, Netflix, Spotify, and CNCF projects:

### Layer 1: Pre-Merge Gates (Policy-as-Code)

- **Tool**: Open Policy Agent (OPA) with Conftest
- **Purpose**: Enforce HFO requirements (tests passing, chunk size ≤200 lines, blackboard receipts, no placeholders)
- **Justification**: Used by Netflix for unified policy enforcement; simple Rego language; integrates with GitHub Actions

### Layer 2: Static Analysis

- **Tools**: CodeQL for security, Semgrep for custom patterns
- **Purpose**: Detect vulnerabilities and anti-patterns before merge
- **Justification**: GitHub native (CodeQL); fast and customizable (Semgrep); used across industry

### Layer 3: Supply Chain Integrity

- **Tools**: SLSA provenance attestations, Sigstore Cosign
- **Purpose**: Cryptographic proof of artifact origin and build process
- **Justification**: Google standard (SLSA); Linux Foundation project (Sigstore); prevents artifact tampering

### Layer 4: Progressive Delivery

- **Tools**: OpenFeature for flags, Argo Rollouts for canaries
- **Purpose**: Runtime control with auto-rollback on metric violations
- **Justification**: CNCF standards; used by enterprise (Intuit, Tesla); limits blast radius

### Layer 5: Observability

- **Tool**: OpenTelemetry
- **Purpose**: Metric-driven canary analysis and DORA tracking
- **Justification**: CNCF standard; vendor-neutral; enables data-driven rollback decisions

### Layer 6: Knowledge Management

- **Tool**: Backstage TechDocs with Diátaxis structure
- **Purpose**: Stable, versioned documentation substrate for agent consumption
- **Justification**: Spotify open source; separates docs by type (tutorial/how-to/reference/explanation)

### Layer 7: LLM Security

- **Framework**: OWASP LLM Top-10 controls, NIST AI RMF alignment
- **Purpose**: Runtime guards against prompt injection, excessive agency, sensitive data leaks
- **Justification**: Emerging industry standard; addresses AI-specific attack vectors

## Consequences

### Positive

1. **Defense in Depth**: Independent layers multiply protective effects (illustrative estimate: >99% reduction in hallucinations reaching production)
2. **Open Standards**: All tools are CNCF projects or industry standards, reducing vendor lock-in
3. **Battle-Tested**: Patterns used at scale by Google, Netflix, Spotify reduce implementation risk
4. **HFO Alignment**: Maps cleanly to existing workflows:
   - Pre-merge gates → HIVE Verify
   - Progressive delivery → SWARM Assess
   - Observability → PREY Perceive
   - Knowledge management → GROWTH Disseminate
5. **Measurable**: DORA metrics and custom telemetry provide feedback for continuous improvement

### Negative

1. **Implementation Effort**: 10-phase rollout over ~3 months for full deployment
2. **Tooling Complexity**: 7 new tools to learn, configure, and maintain
3. **Performance Overhead**: Static analysis and policy checks add CI time (estimated +2-5 minutes)
4. **False Positives**: Policy and static analysis rules require tuning to reduce noise
5. **Learning Curve**: Team must learn Rego (OPA), AnalysisTemplates (Argo), OTEL instrumentation

### Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tool fatigue from too many new systems | High | Medium | Phased rollout (2-3 tools per month); extensive runbooks |
| Policy rules too strict, blocking valid work | Medium | High | Start with warnings only; tune based on violations; override mechanism |
| False security confidence from tooling | Medium | High | Regular red team exercises; track metrics on violations found/missed |
| Vendor/project abandonment | Low | Medium | All choices are CNCF projects or backed by major vendors |
| Performance degradation in CI/CD | Medium | Medium | Optimize rules; parallelize checks; cache analysis results |

## Alternatives Considered

### Alternative 1: Custom Verification System

**Description**: Build HFO-specific verification tools from scratch

**Rejected Because**:
- High development cost (months of engineering)
- No community support or battle-testing
- Likely to miss edge cases that industry tools already handle
- Maintenance burden entirely on HFO team

### Alternative 2: Minimal Approach (OPA + CodeQL only)

**Description**: Use only policy gates and security scanning

**Rejected Because**:
- No runtime blast radius control (missing canaries/flags)
- No supply chain integrity (missing SLSA/Cosign)
- No observability feedback loop (missing OTEL)
- Doesn't address knowledge stabilization for agent learning

### Alternative 3: Commercial Platforms (LaunchDarkly, Harness, etc.)

**Description**: Use proprietary platforms instead of open standards

**Rejected Because**:
- Vendor lock-in risk
- Higher cost at scale
- Less flexibility for HFO-specific integrations
- Community around CNCF projects larger and more active

## Implementation Plan

### Phase 1: Foundation (Weeks 1-2)

1. Add OPA/Conftest policies for chunk size, placeholders, test coverage
2. Enable CodeQL security scanning on all PRs
3. Document ADR (this document)
4. Update AGENTS.md with policy requirements

**Success Criteria**: At least one policy violation caught and prevented

### Phase 2: Static Analysis (Weeks 3-4)

1. Deploy Semgrep with HFO-specific rules (blackboard receipt validation, evidence_refs)
2. Create custom rules for PREY loop patterns
3. Add pre-commit hooks for local validation

**Success Criteria**: 90% reduction in missing evidence_refs violations

### Phase 3: Flags and Observability (Month 2)

1. Implement OpenFeature wrapper for blocked_capabilities
2. Add OTEL instrumentation to PREY loop (Perceive/React/Engage/Yield)
3. Create custom metrics for chunk_size, hallucination_rate, verify_pass_rate

**Success Criteria**: All agent actions behind feature flags; telemetry visible in dashboard

### Phase 4: Progressive Delivery (Month 2-3)

1. Deploy Argo Rollouts for HFO services
2. Create AnalysisTemplates for error rate, latency, custom metrics
3. Define canary rollout strategy (10% → 50% → 100%)

**Success Criteria**: First successful canary deployment with auto-rollback on failure

### Phase 5: Supply Chain (Month 3)

1. Generate SLSA provenance in CI
2. Sign artifacts with Cosign
3. Add signature verification to deploy pipeline

**Success Criteria**: All deployed artifacts have valid signatures and provenance

### Phase 6: Knowledge Management (Month 3+)

1. Set up Backstage with TechDocs plugin
2. Structure docs with Diátaxis framework
3. Require ADR link for merges

**Success Criteria**: All HFO docs searchable in dev portal; ADRs for major decisions

### Phase 7: LLM Security (Ongoing)

1. Implement LLM security guards (prompt injection, sensitive data detection)
2. Add OWASP LLM checks to OPA policies
3. Run quarterly red team exercises

**Success Criteria**: Zero prompt injection incidents; red team finds vulnerabilities that are fixed

## Roadmap: Cold Start to SOTA

### Capability Maturity Model

| Level | Name | Description | Tools | Outcome |
|-------|------|-------------|-------|---------|
| 0 | **Baseline** | Manual review, no automation | GitHub PRs only | High hallucination risk |
| 1 | **Reactive** | Post-merge detection | CodeQL warnings | Bugs found after merge |
| 2 | **Preventive** | Pre-merge gates | OPA + CodeQL required | Bugs blocked pre-merge |
| 3 | **Controlled** | Runtime blast radius | Flags + Canaries | Safe rollout, fast rollback |
| 4 | **Validated** | Supply chain integrity | SLSA + Cosign | Provenance verified |
| 5 | **Optimized** | Continuous improvement | OTEL + DORA | Data-driven evolution |
| 6 | **SOTA** | Full defense-in-depth | All layers active | <1% hallucinations reach production |

### Current State: Level 1 (Reactive)

HFO has PREY loop and verify gates but lacks automated enforcement.

### Target State: Level 6 (SOTA) in 6 months

All seven defense layers active with measurable outcomes.

### Progression Path

```
Month 0-1: Level 1 → Level 2 (Add OPA + CodeQL required checks)
Month 1-2: Level 2 → Level 3 (Add feature flags + observability)
Month 2-3: Level 3 → Level 4 (Add canaries + auto-rollback)
Month 3-4: Level 4 → Level 5 (Add SLSA provenance + signatures)
Month 4-5: Level 5 → Level 6 (Add TechDocs + LLM guards)
Month 5-6: Level 6 optimization and red team validation
```

### Dependencies

- **Level 2 requires**: GitHub Actions access, OPA/CodeQL runners
- **Level 3 requires**: Feature flag backend (can start with in-memory)
- **Level 4 requires**: Kubernetes cluster for Argo Rollouts
- **Level 5 requires**: Artifact registry with attestation support
- **Level 6 requires**: Backstage instance, OTEL backend (Jaeger/Prometheus)

### Risk Checkpoints

At each level transition, validate:
1. **No regression**: Existing capabilities still work
2. **Measurable improvement**: Metric shows progress (e.g., violations caught)
3. **Team confidence**: Engineers understand and trust new tools
4. **Performance acceptable**: CI/CD times within budget (< 10 min total)

If checkpoint fails, pause rollout and address before continuing.

## References

1. **Google Engineering Practices**: https://google.github.io/eng-practices/
2. **Google SRE Book**: https://sre.google/books/
3. **CNCF Project Maturity Levels**: https://www.cncf.io/projects/
4. **OWASP LLM Top 10**: https://owasp.org/www-project-top-10-for-large-language-model-applications/
5. **NIST AI RMF**: https://www.nist.gov/itl/ai-risk-management-framework
6. **HFO AGENTS.md**: Safety envelope, verify gate, blackboard protocol
7. **HFO Gen21 SSOT**: PREY/HIVE/GROWTH/SWARM workflow definitions

## Decision Record

- **Proposed by**: HFO Development Team / Copilot Agent
- **Date**: 2025-10-30
- **Review Status**: Pending team review and approval
- **Approval Required**: Repository owner sign-off
- **Implementation Timeline**: 6 months to full SOTA capability
- **Success Metrics**: 
  - Pre-merge violation detection rate > 80%
  - Canary auto-rollback within 5 minutes of SLO breach
  - Zero unverified artifacts deployed
  - DORA metrics improve over baseline (deploy frequency, lead time, MTTR)

## Appendix: HFO Workflow Mapping

### HIVE (Double Diamond + Meta-Evolution)

- **Discover**: Static analysis finds patterns across codebase
- **Define**: OPA policies codify requirements
- **Develop**: Feature flags enable safe experimentation
- **Deliver**: Progressive rollout validates in production
- **Evolve**: DORA metrics drive continuous improvement

### GROWTH (F3EAD)

- **Find**: Observability detects anomalies
- **Fix**: Policy gates enforce corrections
- **Finish**: Canary validates effectiveness
- **Exploit**: Success patterns become standard
- **Analyze**: Metrics quantify impact
- **Disseminate**: TechDocs capture knowledge

### SWARM (D3A + Mutate)

- **Decide**: Feature flags control experiment activation
- **Detect**: OpenTelemetry identifies issues
- **Deliver**: Argo Rollouts ships safely
- **Assess**: Analysis templates evaluate outcomes
- **Mutate**: Successful variants promoted

### PREY (Perceive → React → Engage → Yield)

- **Perceive**: Ingest telemetry and policy violations
- **React**: Classify risk level, select deployment strategy
- **Engage**: Execute with feature flags and canary
- **Yield**: Generate blackboard receipt with evidence
