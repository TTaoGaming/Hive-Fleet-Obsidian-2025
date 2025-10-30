# Clarification Pass 1 — 2025-10-30

orchestrator: Swarmlord of Webs (sole human interface)

mission_context:
- You, the human, speak only to the Swarmlord of Webs. Workers/agents never address you directly.
- We begin with iterative clarification passes on your intent. Minimum required passes: 3 (never fewer).
- After agreement on clarification, the Swarmlord creates (or assigns creation of) a timestamped mission intent YAML that becomes the single source of truth for execution.

clarification_cadence:
- Pass 1 (this file): Capture objectives, constraints, interface contract, safety, PREY definition, verify/digest expectations.
- Pass 2+: Resolve ambiguities, enumerate deliverables, edge cases, and concrete success criteria.
- Pass ≥3 (agreement gate): Confirm scope/constraints; authorize generation of mission intent YAML.

ssot_after_agreement:
- Artifact: hfo_mission_intent/YYYY-MM-DD/mission_intent_YYYY-MM-DD.yml (timestamped; immutable once locked; new versions append by date).
- Role: Becomes the binding SSOT for the run. Execution adheres to the SSOT until superseded by a new dated file.

execution_model:
- Manager-only facade: Swarmlord delegates to workers; workers never speak to human.
- PREY loop per GEM Gen21 (execution layer):
  - Perceive: Build perception snapshots (repo + context), capture ground signals, and record sources.
  - React: Choose posture and approach (e.g., Cynefin domain classification) and select tools/agents.
  - Engage: Execute safely with explicit safety criteria and tripwires; no babysitting or manual approvals mid-loop.
  - Yield: Produce a concrete, verifiable payload (artifact, diff, metrics, or structured summary).
- Verify gate:
  - Check for hallucination/drift; ensure Perceive/React/Engage/Yield are consistent and evidence-backed.
  - If FAIL: Rerun PREY (bounded retries/timeouts). If PASS: Return to Swarmlord.
- Digest to human:
  - Swarmlord packages a digest: BLUF, what’s good/not, retries taken/remaining, evidence references, and next steps.

safety_envelope:
- No mid-loop prompts to the human; only the Swarmlord delivers digests at checkpoints.
- Guardrails: Tripwires/canaries; bounded write sizes; explicit verification before “done.”
- Evidence discipline: Record material actions/snapshots so Verify can reason over them.

handoff_protocol:
- After agreement (≥3 passes), Swarmlord will produce/assign the mission intent YAML for the day and then dispatch worker agents with PREY tasks.
- Workers operate until a verified PASS or until timeout backoff triggers a report with partials and remediation options.

acceptance_for_pass1:
- Confirm the interface contract (Swarmlord-only; workers silent to human).
- Confirm minimum of 3 clarification passes before SSOT creation.
- Confirm that the timestamped mission intent YAML becomes SSOT upon agreement.
- Confirm PREY definition, Verify gate behavior, and digest expectations.

open_questions (to address in Pass 2):
- Any specific tools or environments that must be used/avoided for this run?
- Timeouts/retry budgets you prefer (e.g., max PREY loops before report)?
- Preferred digest shape (BLUF length, matrices, Mermaid diagrams, etc.)?

next_step:
- If you approve Pass 1, we proceed to Clarification Pass 2 to lock scope, deliverables, and concrete success criteria.# Clarification Pass 1 — 2025-10-30

orchestrator: Swarmlord of Webs (C2 facade)

mission_id: crewai_bootstrap_2025-10-30

scope_today:
- Bring up minimal parallel agent orchestration under Swarmlord using CrewAI first, with blackboard receipts and tripwires.
- Produce a runnable script (no babysitting), a logger utility for receipts, and a concise HFO playbook mapping PREY and safety.
- Keep LangGraph as the next step; today’s focus is CrewAI wiring under the Swarmlord facade.

constraints:
- Sole interface: Human speaks only to Swarmlord once online (workers do not prompt the human mid-loop).
- Evidence discipline: Append JSONL receipts to `hfo_blackboard/obsidian_synapse_blackboard.jsonl` for material actions.
- Safety envelope: Canary first; ≤200 lines per write; tripwires (placeholders banned; VERIFY gate before “done”).
- No manual approvals inside the loop; Verify must pass independently before delivery.

assumptions:
- Python environment active for this workspace; package installs allowed.
- CrewAI acceptable for initial orchestration; LangGraph already available (requirements include langgraph).
- PettingZoo not required for today’s verify; we’ll verify via JSONL validation and dry-run outputs.

## PREY — Pass 1

### Perceive
- Repo assets: `AGENTS.md` defines PREY, receipts, and safety envelope; `hfo_blackboard/…` exists; `hfo_swarmlord_of_webs_kilo_code_mode/` includes v15 YAML exports; requirements include LangGraph but no CrewAI yet.
- Gap: Missing coded receipt helper aligned with AGENTS.md; missing runnable CrewAI entrypoint; missing HFO playbook for CrewAI under Swarmlord.
- Today’s targets: add a blackboard logger, a minimal parallel CrewAI orchestrator, and a CrewAI playbook.

### React
- Approach: Keep changes small and composable.
  - Add `scripts/blackboard_logger.py` with `append_receipt()` matching AGENTS.md JSONL schema.
  - Add `scripts/hfo_swarmlord_crewai_run.py` defining 3 agents (Navigator/Planner, Builder/Executor, Verifier) and parallelizable tasks; log receipts at each PREY phase.
  - Add `hfo_swarmlord_of_webs_kilo_code_mode/crew_ai_playbook.md` with setup, PREY mapping, and run steps.
  - Install `crewai` in the active environment and optionally pin later.
- Safety: Start with a canary dry run, check `scripts/validate_jsonl.py` passes, and record Verify receipt.

### Engage
- Implement the three artifacts above in ≤200-line chunks per file.
- Wire minimal parallel behavior (independent tasks executed concurrently where possible) while keeping output simple and receiptful.
- Do not change existing mission history; append-only receipts.

### Yield
- On dry run, expect:
  - Console summary from the orchestrator.
  - New JSONL receipts written with phases `perceive|react|engage|yield|verify` for `mission_id: crewai_bootstrap_2025-10-30`.
  - Validation PASS via `scripts/validate_jsonl.py`.
- Deliverables today: the 3 artifacts + optional requirements update.

## Success criteria
- No placeholders in committed artifacts; line-count per file ≤200 lines.
- JSONL receipts valid and append-only; include `evidence_refs` and `safety_envelope`.
- Orchestrator runs without waiting for manual approvals; Verify step performed and logged.

## Next steps (not today)
- Transition orchestration to LangGraph (reuse the logger; swap Crew for Graph). Add inbox/interrupt mapping for human-in-the-loop when desired—but default to zero babysitting.
- Expand agents set to align with OBSIDIAN roles and Kilo Code workflows.
