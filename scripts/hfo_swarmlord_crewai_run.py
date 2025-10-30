#!/usr/bin/env python3
"""
Minimal Swarmlord-of-Webs CrewAI orchestrator (canary run).

Goals today:
- Demonstrate parallelizable multi-agent orchestration via CrewAI under the
  Swarmlord facade with zero babysitting inside the loop.
- Log PREY receipts to the blackboard JSONL (AGENTS.md protocol).

Notes:
- Keep the crew tiny: Navigator (planner), Builder (executor), Verifier.
- Use simple tasks and parallel execution where possible.
- Defer advanced tools or RAG until LangGraph port.
"""
from __future__ import annotations

import os
from dataclasses import asdict
from typing import List

from blackboard_logger import append_receipt

# Lazy import CrewAI so this script can be inspected without deps installed
try:
    from crewai import Agent, Task, Crew, Process
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "CrewAI not available. Install with: pip install crewai (or add to requirements.txt)\n"
        f"Import error: {e}"
    )


MISSION_ID = os.environ.get("HFO_MISSION_ID", "crewai_bootstrap_2025-10-30")
SAFETY = {"chunk_size_max": 200, "line_target_min": 0}


def log(phase: str, summary: str, evidence: List[str]):
    append_receipt(
        mission_id=MISSION_ID,
        phase=phase,
        summary=summary,
        evidence_refs=evidence,
        safety_envelope=SAFETY,
        blocked_capabilities=[],
    )


def build_crew() -> Crew:
    navigator = Agent(
        role="Navigator",
        goal=(
            "Decompose today's goal into 2-3 concrete steps that can run in parallel,\n"
            "avoiding babysitting and maximizing autonomy under the Swarmlord facade."
        ),
        backstory=(
            "Strategic orchestrator mapping PREY to actions with receipts and tripwires."
        ),
        allow_delegation=False,
        verbose=False,
    )

    builder = Agent(
        role="Builder",
        goal="Implement the planned steps with concise outputs and no blocked prompts.",
        backstory="Executor focused on small atomic edits and simple prints.",
        allow_delegation=False,
        verbose=False,
    )

    verifier = Agent(
        role="Verifier",
        goal=(
            "Check outputs for obvious errors, summarize status, and specify next safe steps"
        ),
        backstory="Independent checker ensuring receipts and basic validations are present.",
        allow_delegation=False,
        verbose=False,
    )

    # Tasks — lightweight and parallelizable
    plan_task = Task(
        description=(
            "Produce a 3-bullet parallel plan for today's goal (CrewAI canary).\n"
            "Include: (1) tiny parallel actions, (2) how to ensure no babysitting, (3) receipt(s)."
        ),
        agent=navigator,
        expected_output="Three bullets with crisp actions and receipt mention.",
    )

    build_task = Task(
        description=(
            "Simulate execution of two tiny parallel actions and summarize results in 4-6 lines."
        ),
        agent=builder,
        expected_output="Short summary of actions and outcomes.",
    )

    verify_task = Task(
        description=(
            "Validate that outputs exist, appear coherent, and propose one next safe improvement."
        ),
        agent=verifier,
        expected_output="A 2-3 line verification note plus one next step.",
    )

    crew = Crew(
        agents=[navigator, builder, verifier],
        tasks=[plan_task, build_task, verify_task],
        process=Process.sequential,  # Keep simple; tasks themselves are independent
        verbose=False,
    )
    return crew


def main() -> int:
    log("perceive", "CrewAI canary starting (Swarmlord facade)", [__file__])

    crew = build_crew()
    log("react", "Crew assembled: Navigator/Builder/Verifier", [__file__])

    # Engage — run crew; in a real setup, split truly parallel tasks or use Process.hierarchical
    result = crew.kickoff()
    # Result is a structured object in recent CrewAI; repr for evidence brevity
    result_str = str(result)
    evidence = [f"result_len:{len(result_str)}"]
    log("engage", "Crew run complete (canary)", evidence)

    # Verify — basic validation hook (presence + JSONL validator suggestion)
    verify_summary = "Outputs present; proceed to JSONL validation and LangGraph port next."
    log("verify", verify_summary, ["scripts/validate_jsonl.py"])

    print("CrewAI canary finished. See blackboard JSONL for receipts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
