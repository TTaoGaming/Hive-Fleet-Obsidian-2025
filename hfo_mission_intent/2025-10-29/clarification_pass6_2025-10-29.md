# Mission Intent — Clarification Pass 6 (FINAL ALIGNMENT - TEMP)

created_at: 2025-10-29T14:33:00Z
mission_id: gem21_gpt5_attempt3_2025-10-29
status: pass6-draft
owner: TTao
orchestrator: Swarmlord of Webs (sole interface)
linked_docs:
  - ./clarification_pass1_2025-10-29.md
  - ./clarification_pass2_2025-10-29.md
  - ./clarification_pass3_2025-10-29.md
  - ./clarification_pass4_2025-10-29.md
  - ./clarification_pass5_2025-10-29.md
references:
  - hfo_gem/gen_19/original_gem.md
  - hfo_swarmlord_of_webs_kilo_code_mode/swarmlord-of-webs-export-v15.yaml
  - hfo_swarmlord_of_webs_kilo_code_mode/hallucination-swarmlord-of-webs-mode-v19-2025-10-29.yaml (reference only, do not use)

---

## BLUF
- End state: A single Gen21 SSOT markdown (≥1000 lines) you can drop into any clean repo to bootstrap and bring Swarmlord of Webs online as your only interface; Swarmlord clarifies mission intent, orchestrates PREY, runs independent Verify, and returns a digest (BLUF/matrix/diagram/notes) only after PASS.
- Policy: PREY terminology canonical (Perceive, React, Engage, Yield), mapping to Sense/Make Sense/Act/Feedback and grounded in JADC2, OODA, MAPE-K literature.
- Guardrails: Real tools only with receipts; canary/tripwire/revert safety; Zulu timestamps; remove babysitting and ban simulated tools.

---

## Matrix — Final gates and success criteria
| Gate | Criteria | Evidence |
|---|---|---|
| G1: SSOT completeness | ≥1000 lines, no placeholders, includes "Swarmlord Operations" | line_count; section headers present |
| G2: Interface contract | Human speaks only to Swarmlord after online | SSOT states facade contract; no worker prompts to human |
| G3: PREY mapping | PREY↔Sense/Make Sense/Act/Feedback; provenance to JADC2/OODA/MAPE-K | SSOT section with mapping diagram |
| G4: Safety | Canary, tripwires (line_count<0.9×target, placeholders, test/policy fails), revert plan | Safety section + blackboard entries with chunk_id/regen_flag |
| G5: Tooling | Real tools; installs/downloads allowed; evidence_refs | Blackboard evidence refs; dependency locks |
| G6: Verify | Independent, non-editing; PASS required before digest | verify_report; PASS → digest emitted |
| G7: Cold-start | ≤3 manual steps to get Swarmlord online | SSOT "Bootstrap" section lists ≤3 steps |
| G8: Lineage | Gen19 base; Gen1 intent honored; v15 referenced, v19 excluded | references and rationale notes in SSOT |
| G9: Timestamps | UTC (Z) | created_at and blackboard timestamps |

---

## Diagram — Drop-in to Digest (minimal babysitting)
```mermaid
%%{init: {'theme':'dark', 'themeVariables': { 'fontSize': '20px' }}}%%
flowchart LR
  D[Drop-in SSOT.md (Gen21 ≥1000)] --> BOOT[Bootstrap Loader (≤3 steps)]
  BOOT --> SW["Swarmlord Online (sole interface)"]
  SW --> CL[Clarify Mission Intent]
  CL --> PR[P.R.E.Y Orchestration]
  PR --> VF[Independent Verify]
  VF -->|FAIL| PR
  VF -->|PASS| DG[Digest → BLUF / Matrix / Diagram / Notes]
```

---

## Notes
- No tactical prompts to the human: no copy/paste requests, no manual confirmations—Swarmlord handles execution routing; you remain strategic.
- Evidence discipline: every material action logged with evidence_refs; blackboard is append-only.
- Pain point added to SSOT: "Too many manual touches + simulated fake tools that gaslight" → explicitly forbidden.

---

## Decisions to authorize mission_intent.yml
- [ ] Approve PREY as canonical with mappings (JADC2/OODA/MAPE-K provenance)
- [ ] Approve single-interface contract (Swarmlord only)
- [ ] Approve SSOT Gen21 ≥1000 lines with dedicated "Swarmlord Operations"
- [ ] Approve safety envelope (canary/tripwire/revert) and Z timestamps
- [ ] Approve real-tooling posture with evidence_refs; ban simulated tools
- [ ] Approve legacy stance: Gen19 base, Gen1 honored; v15 ref OK; v19 excluded
- [ ] Authorize drafting of `mission_intent_2025-10-29.yml` reflecting Pass 1–6
