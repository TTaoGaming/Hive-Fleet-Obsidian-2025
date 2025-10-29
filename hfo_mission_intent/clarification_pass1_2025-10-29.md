# Mission Intent — Clarification Pass 1 (TEMP)

created_at: 2025-10-29T13:52:00Z
mission_id: gem21_gpt5_attempt3_2025-10-29
status: pass1-draft
owner: TTao
orchestrator: Swarmlord of Webs (C2 facade)
timebox: 30m (minimal babysitting/manual interventions)

---

## BLUF
- Goal: Draft a Gen21 SSOT markdown (GPT5 attempt 3) that cold-starts Swarmlord and regenerates the full HFO system with minimal babysitting.
- Process: Clarify intent (≥3 passes if new), then PREY mapped to JADC2 (Sense → Make Sense → Act → Feedback), then independent Verify, then final digest (BLUF/matrix/diagram/notes).
- Scope today: Lock mission intent via Clarification Passes; do NOT write code or SSOT yet.
- Target: Reuse ≥95% of Gen19, remove hallucinations/truncation, prepare for Swarmlord Kilo mode v20 regeneration.
 - Tools stance: Actively use real tools/services (internet, MCP servers, VS Code extensions) as needed; avoid simulated or hallucinated tools.

---

## Artifacts (proposed)
- SSOT (today: not created): `hfo_gem/gen_21/gpt5-attempt-3-gem.md`
- Mission intent YAML (later): `hfo_mission_intent/mission_intent_2025-10-29.yml`
- Blackboard (append-only JSONL): `hfo_blackboard/obsidian_synapse_blackboard.jsonl`

Confirm/adjust paths during Pass 1.

---

## Swim lanes overview (Pass 1)
```mermaid
flowchart LR
  %% Lanes as subgraphs for clarity
  subgraph U["User"]
    U1[Give Intent]
    U2[Confirm Intent or New?]
  end

  subgraph L["Loader"]
    L1[Env Snapshot Hooks]
    L2[Persist Files I/O]
  end

  subgraph W["Swarmlord of Webs (C2)"]
    W1[Clarify x3 if New]
    W2[Draft mission_intent.yml]
    W3[Plan PREY Batch]
    W4[Assemble Review Bundle]
    W5[Final Facade Digest]
  end

  subgraph P["Workers (PREY)"]
    P1[gather_snapshot]
    P2[classify_and_plan]
    P3[execute_subtask_batch]
    P4[assemble_review_bundle]
  end

  subgraph V["Independent Verifier"]
    V1[Lint/Tests/Policy]
    V2[Risk/Blockers Audit]
    V3[Approve / Request Fixes]
  end

  subgraph B["Blackboard (JSONL)"]
    B1[(Append-only Events)]
  end

  %% Flow
  U1 --> W1
  W1 -->|Existing intent?| U2
  U2 -->|Yes| W3
  U2 -->|No| W2
  W2 --> L2 --> B1

  W3 --> P1 --> P2 --> P3 --> P4
  P4 --> W4 --> V1 --> V2 --> V3
  V3 -->|Fail| W3
  V3 -->|Pass| L2 --> B1 --> W5
  W5 --> U1
  %% Loader supports I/O and env sensing
  L1 -. snapshot assists .-> P1
```

---

## PREY ↔ JADC2 mapping
```mermaid
flowchart TB
  A[gather_snapshot]:::sense --> B[classify_and_plan]:::makesense
  B --> C[execute_subtask_batch]:::act
  C --> D[assemble_review_bundle]:::feedback
  classDef sense fill:#1f77b4,color:#fff
  classDef makesense fill:#9467bd,color:#fff
  classDef act fill:#2ca02c,color:#fff
  classDef feedback fill:#ff7f0e,color:#fff
  %% JADC2 overlay
  E[Sense]:::sense --> F[Make Sense]:::makesense --> G[Act]:::act --> H[Feedback]:::feedback
```

---

## Safety envelope and verify gate
```mermaid
flowchart LR
  S1[Plan Safety Envelope] --> S2[Canary: limited scope]
  S2 --> S3[Tripwires: lines/tests/policy]
  S3 -->|Hit| S4[Revert: restore prior]
  S3 -->|Clear| S5[Verifier Pass]
  S5 --> D1[Digest: BLUF + matrix + diagram + notes]
```

---

## Acceptance criteria (SSOT, for later)
- Cold-start compatible: Drop-in enables Swarmlord online + system regen with ≤3 manual steps.
- Output discipline: Every mission produces BLUF, operating_mode, tradeoff_matrix, diagram_stub, safety summary, blockers.
- Anti-truncation: Full content, no placeholders; chunked drafting with line targets and verification.
- Lineage: ≥95% reuse of Gen19 where applicable, with hallucinations removed.

---

## Decisions to confirm (Pass 1)
- [x] Confirm mission goal framing above.
- [x] Confirm artifact names/paths.
- [ ] Confirm sequencing: Today only mission_intent; later SSOT Gen21, then Swarmlord v20.
- [ ] Confirm minimum line target for SSOT (proposed: 280–400 lines).
- [ ] Confirm swim lanes order: User → Loader → Webs → PREY → Verifier → Blackboard → Webs → User.
- [ ] Confirm Verify gate is mandatory before human-facing digest (no bypass).
- [ ] Confirm ≥95% lineage from Gen19 with de-hallucination edits.
- [ ] Confirm timezone for timestamps (proposed: UTC / Z-suffix).

---

## Open questions (fast answers ok)
1) Preferred mission_id format? (resolved: `gem21_gpt5_attempt3_2025-10-29`)
2) SSOT path/name okay? (resolved: `hfo_gem/gen_21/gpt5-attempt-3-gem.md`)
3) Timebox for today’s intent phase? (resolved: 30 minutes, minimal babysitting)
4) Any hard constraints we must respect? (resolved: actively use real tools/services; download/install as needed; avoid simulated tools)
5) Must include additional digest elements? (resolved: BLUF + matrix + diagram + short notes only)
6) Timezone for timestamps? (proposed: UTC / Z-suffix)
7) Minimum line target for SSOT? (proposed: 280–400 lines)

---

## Next
- Await your checkboxes/edits; then proceed to Clarification Pass 2 (constraints & safety envelope) and Pass 3 (workflow mapping & verification), then draft `mission_intent_2025-10-29.yml` for approval.
