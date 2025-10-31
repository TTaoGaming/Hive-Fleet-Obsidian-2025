# Mission Intent — Policy and Workflow

This folder holds daily mission intents and their supporting clarification passes.

## Precondition (required)
- Do not create a mission intent for a date until there are at least three Clarification Pass documents for that same date.
- Expected names:
  - `clarification_pass1_YYYY-MM-DD.md`
  - `clarification_pass2_YYYY-MM-DD.md`
  - `clarification_pass3_YYYY-MM-DD.md`
  - Pass 4–5 are optional but recommended.

## Enforcement
- Local pre-commit: blocks committing mission intents without ≥3 same-date `clarification_pass_refs` that exist.
- CI workflow: fails push/PR if a mission intent lacks ≥3 same-date clarification pass refs.
- Non-compliant intents must be marked `hallucination_flag: true` and moved to `archive/`.

## Required fields in mission intent
- `clarification_pass_refs`: ≥3 entries; paths must exist and match the same date.
- `goal`, `constraints`, `success_criteria`, `safety` (tripwires, canary_plan, revert_plan), `created_at`, `version`.

## LLM defaults (current)
- Default output token limit: `max_tokens = 4000` per stage to reduce truncation; models may use fewer tokens as appropriate.

## Helpful files
- Template: `hfo_mission_intent/mission_intent_template.yml`
- Validator: `scripts/validators/validate_mission_intents.py`
- Pre-commit hook: `.pre-commit-config.yaml`
- CI workflow: `.github/workflows/mission-intent-guard.yml`

## Example day flow
1) Write Clarification Pass 1–3 for the date under `hfo_mission_intent/YYYY-MM-DD/`.
2) Create the mission intent using the template and include `clarification_pass_refs` to those three files.
3) Commit: pre-commit runs the validator; fix any errors.
4) Push/PR: CI enforces the same guard.
5) Proceed to run lanes only after the mission intent clears the guard.
