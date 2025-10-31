# Clarification Pass 1 — 2025-10-31

orchestrator: Swarmlord of Webs (sole human interface)

## BLUF
- Today’s focus: unify all evals under a single PREY workflow (Option A) with LLM at every stage and a deterministic Verify gate.
- User interaction model: you clarify with Swarmlord to set the mission intent, then receive only a verified Swarmlord digest.
- Safety and audit unchanged: chunk ≤ 200 lines, placeholder ban, receipts to blackboard, OTEL spans, quorum Verify before any digest.

## Objectives (Pass 1)
- Lock the E2E flow: USR → Swarmlord → Mission intent → Parallel lanes → Yields → Verify quorum → Pass/Fail → Digest back to user.
- Confirm LLM-per-stage orchestration: Orchestrate, Perceive, React, Engage, Yield, and Digest are LLM calls; Verify stays independent and deterministic (LLM may annotate, not decide).
- Confirm single-runner posture: ARC, simple math, and PettingZoo operate as provider adapters behind the same PREY workflow and artifacts.

## Flow diagram (parser-safe)
```mermaid
graph LR
  USR[User] --> SW[Swarmlord]
  SW --> MI[Mission intent]
  SW --> LANES[Parallel lanes]
  LANES --> YB[Yields]
  YB --> VQ[Verify quorum]
  VQ --> PASS[Pass]
  VQ --> FAIL[Fail]
  PASS --> DIG[Digest]
  FAIL --> RETRY[Targeted re run]
  RETRY --> LANES
  DIG --> USR
```

## Lane internals (LLM per PREY stage)
```mermaid
graph TB
  O[Swarmlord plan LLM] --> P[Perceive LLM]
  P --> R[React plan LLM]
  R --> E[Engage execute LLM]
  E --> Y[Yield bundle LLM]
  Y --> V[Verify deterministic]
  V --> VPASS[Pass]
  V --> VFAIL[Fail]
  VFAIL --> R
  VPASS --> DONE[Lane done]
```

## Multi view diagrams (parser safe)

### UML sequence — user to digest
```mermaid
sequenceDiagram
  participant USR as User
  participant SW as Swarmlord
  participant LN as Lanes
  participant VQ as Verify
  participant DG as Digest
  USR->>SW: clarify mission
  SW->>LN: run lanes P R E Y
  LN-->>VQ: yields with evidence
  VQ-->>SW: pass or fail
  alt pass
    SW-->>DG: build digest
    DG-->>USR: deliver digest
  else fail
    SW-->>LN: targeted re run
  end
```

### UML statechart — lane lifecycle
```mermaid
stateDiagram-v2
  [*] --> Perceive
  Perceive --> React
  React --> Engage
  Engage --> Yield
  Yield --> Verify
  Verify --> Pass
  Verify --> Fail
  Fail --> React
  Pass --> [*]
```

### BPMN like flow — end to end
```mermaid
graph LR
  START[Start] --> SW[Swarmlord]
  SW --> MI[Mission intent]
  MI --> GW[Gateway lanes]
  GW --> L1[Lane one PREY]
  GW --> L2[Lane two PREY]
  L1 --> Y1[Yield one]
  L2 --> Y2[Yield two]
  Y1 --> COL[Collect yields]
  Y2 --> COL
  COL --> VQ[Verify quorum]
  VQ --> PASS[Pass]
  VQ --> FAIL[Fail]
  FAIL --> RETRY[Targeted re run]
  RETRY --> GW
  PASS --> DIG[Digest]
  DIG --> END[End]
```

### DAG — run level dependencies
```mermaid
graph LR
  ORCH[Orchestrate] --> P1[Perceive lane a]
  ORCH --> P2[Perceive lane b]
  P1 --> R1[React lane a]
  P2 --> R2[React lane b]
  R1 --> E1[Engage lane a]
  R2 --> E2[Engage lane b]
  E1 --> Y1[Yield lane a]
  E2 --> Y2[Yield lane b]
  Y1 --> VQ[Verify quorum]
  Y2 --> VQ
  VQ --> DIG[Digest]
```

### C4 style context — simple
```mermaid
graph LR
  subgraph UserSpace
    USR[User]
  end
  subgraph ObsidianSystem
    SW[Swarmlord facade]
    BB[Blackboard jsonl]
    OT[OTEL traces]
    VQ[Verify gate]
  end
  subgraph Providers
    ARC[ARC provider]
    MATH[Math provider]
    PZ[PZ provider]
  end
  USR --> SW
  SW --> BB
  SW --> ARC
  SW --> MATH
  SW --> PZ
  ARC --> VQ
  MATH --> VQ
  PZ --> VQ
  VQ --> SW
  SW --> OT
  SW --> USR
```

## Initial decisions (locked for this day)
- Single eval workflow, one entry point; providers: ARC | math | pz_simple_tag.
- LLM tiering: fast reasoning models for Orchestrate/Perceive/React/Yield/Digest; task-appropriate model for Engage.
- Default output tokens (max_tokens): 4000 per stage to avoid truncation; models may produce less.
- Budgets and backpressure: mission/lane/stage token caps; retry-on-empty once; remove response_format on retry if needed.
- Verify gate: independent, deterministic quorum; PASS required before digest.

## Inputs you may provide here
- Eval type and dataset parameters (e.g., ARC split/limit/seed; math prompts; PZ episodes/seed).
- llm_per_stage preferences (model hints, max_tokens, reasoning effort, timeouts).
- Lanes/concurrency and budget priorities (accuracy vs. cost vs. latency).
- Any compliance or safety constraints to enforce during Engage.

## Next step
- Proceed to Clarification Pass 2 and 3 (minimum) to refine eval/provider params and stage defaults.
- Mission intent will be created only after ≥ Pass 3 (target 5) to reduce churn and align with the SSOT policy.

## Evolution (provenance note)
- Seeded the unified PREY workflow with LLM per stage and deterministic Verify.
- Established user touchpoints (clarification, digest) and safety envelope.
- Sets the baseline for later passes to tune tokens, models, and orchestration; no breaking changes introduced here.
