#!/usr/bin/env python3
"""
Multi-Lane CrewAI Orchestrator with Parallel Execution.

Implements:
- Parallel PREY lanes (Perceive -> React -> Engage -> Yield)
- Disperse-converge pattern with quorum verification
- Stigmergy via blackboard JSONL
- Explore/exploit ratio (4/6)
- Autonomous operation with minimal manual touch

Aligned with:
- AGENTS.md PREY protocol
- Mission intent mi_daily_2025-10-30 v5
- Clarification passes 4 & 5
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from blackboard_logger import append_receipt, ChunkId

try:
    from crewai import Agent, Task, Crew, Process
    from dotenv import load_dotenv
except ImportError as e:
    raise SystemExit(
        f"Missing dependencies. Install with: pip install -r requirements.txt\n"
        f"Error: {e}"
    )

# Load environment variables
load_dotenv()

# Mission configuration
MISSION_ID = os.getenv("HFO_MISSION_ID", "mi_daily_2025-10-30")
PARALLEL_LANES = int(os.getenv("HFO_PARALLEL_LANES", "2"))
CHUNK_SIZE_MAX = int(os.getenv("HFO_CHUNK_SIZE_MAX", "200"))
EXPLORE_RATIO = 0.4  # 40% exploration, 60% exploitation


@dataclass
class LaneConfig:
    """Configuration for a single PREY lane."""
    lane_id: str
    lane_name: str
    mode: str  # "explore" or "exploit"
    time_budget_minutes: int = 5


@dataclass
class LaneResult:
    """Result from a lane execution."""
    lane_id: str
    lane_name: str
    success: bool
    output: str
    evidence_refs: List[str]
    metrics: Dict[str, Any]


def log_receipt(phase: str, summary: str, evidence: List[str], 
                chunk_id: Optional[ChunkId] = None) -> None:
    """Log a receipt to the blackboard JSONL."""
    append_receipt(
        mission_id=MISSION_ID,
        phase=phase,
        summary=summary,
        evidence_refs=evidence,
        safety_envelope={"chunk_size_max": CHUNK_SIZE_MAX, "line_target_min": 0},
        blocked_capabilities=[],
        chunk_id=chunk_id,
    )


def create_perceiver_agent() -> Agent:
    """Create the Perceiver agent for sensing context."""
    return Agent(
        role="Perceiver",
        goal="Scan repository, mission intent, and blackboard to understand current state",
        backstory=(
            "Strategic sensor gathering evidence from files, mission intent YAML, "
            "and blackboard JSONL for informed decision-making"
        ),
        allow_delegation=False,
        verbose=False,
    )


def create_reactor_agent() -> Agent:
    """Create the Reactor agent for planning."""
    return Agent(
        role="Reactor",
        goal="Analyze context and create concrete action plans with safety tripwires",
        backstory=(
            "Tactical planner breaking down goals into small, safe, "
            "parallelizable chunks with measurable success criteria"
        ),
        allow_delegation=False,
        verbose=False,
    )


def create_implementer_agent(mode: str) -> Agent:
    """Create the Implementer agent for execution."""
    goal_suffix = (
        "with creative exploration and variance"
        if mode == "explore"
        else "with proven patterns and stability"
    )
    return Agent(
        role="Implementer",
        goal=f"Execute planned actions safely {goal_suffix}",
        backstory=(
            f"Executor applying {'diverse strategies' if mode == 'explore' else 'reliable methods'} "
            "with strict chunk limits and placeholder bans"
        ),
        allow_delegation=False,
        verbose=False,
    )


def create_assimilator_agent() -> Agent:
    """Create the Assimilator agent for yielding results."""
    return Agent(
        role="Assimilator",
        goal="Package outputs into review bundles with evidence refs",
        backstory=(
            "Synthesizer creating coherent bundles with clear evidence trails "
            "for independent verification"
        ),
        allow_delegation=False,
        verbose=False,
    )


def create_lane_crew(config: LaneConfig) -> Crew:
    """Create a Crew for a single PREY lane."""
    perceiver = create_perceiver_agent()
    reactor = create_reactor_agent()
    implementer = create_implementer_agent(config.mode)
    assimilator = create_assimilator_agent()
    
    # Define tasks for PREY cycle
    perceive_task = Task(
        description=(
            f"For lane {config.lane_name}: Scan mission intent, "
            "current repo state, and recent blackboard entries. "
            "Summarize key context in 3-5 bullets."
        ),
        agent=perceiver,
        expected_output="Context summary with 3-5 key points",
    )
    
    react_task = Task(
        description=(
            f"For lane {config.lane_name} ({config.mode} mode): "
            "Create an action plan with 2-3 concrete steps. "
            "Include safety checks and success criteria."
        ),
        agent=reactor,
        expected_output="Action plan with steps and safety criteria",
    )
    
    engage_task = Task(
        description=(
            f"For lane {config.lane_name}: Execute the planned actions. "
            "Produce concrete outputs (code, docs, or analysis). "
            "Respect chunk limits and avoid placeholders."
        ),
        agent=implementer,
        expected_output="Execution summary with concrete outputs",
    )
    
    yield_task = Task(
        description=(
            f"For lane {config.lane_name}: Package all outputs into a review bundle. "
            "Include evidence refs and metrics. Prepare for verification."
        ),
        agent=assimilator,
        expected_output="Review bundle with evidence and metrics",
    )
    
    crew = Crew(
        agents=[perceiver, reactor, implementer, assimilator],
        tasks=[perceive_task, react_task, engage_task, yield_task],
        process=Process.sequential,
        verbose=bool(os.getenv("HFO_CREW_VERBOSE", "false").lower() == "true"),
    )
    
    return crew


def execute_lane(config: LaneConfig) -> LaneResult:
    """Execute a single PREY lane and return results."""
    log_receipt(
        "engage",
        f"Starting lane {config.lane_name} in {config.mode} mode",
        [f"lane:{config.lane_id}"],
    )
    
    try:
        crew = create_lane_crew(config)
        result = crew.kickoff()
        
        output_str = str(result)
        evidence = [
            f"lane:{config.lane_id}",
            f"mode:{config.mode}",
            f"output_len:{len(output_str)}",
        ]
        
        log_receipt(
            "yield",
            f"Lane {config.lane_name} completed successfully",
            evidence,
        )
        
        return LaneResult(
            lane_id=config.lane_id,
            lane_name=config.lane_name,
            success=True,
            output=output_str,
            evidence_refs=evidence,
            metrics={"output_length": len(output_str), "mode": config.mode},
        )
    
    except Exception as e:
        error_msg = f"Lane {config.lane_name} failed: {str(e)}"
        log_receipt(
            "yield",
            error_msg,
            [f"lane:{config.lane_id}", f"error:{type(e).__name__}"],
        )
        
        return LaneResult(
            lane_id=config.lane_id,
            lane_name=config.lane_name,
            success=False,
            output=error_msg,
            evidence_refs=[f"lane:{config.lane_id}", "status:failed"],
            metrics={"error": str(e), "mode": config.mode},
        )


def run_parallel_lanes(lane_configs: List[LaneConfig]) -> List[LaneResult]:
    """Execute multiple lanes in parallel using ThreadPoolExecutor."""
    log_receipt(
        "engage",
        f"Starting {len(lane_configs)} parallel lanes",
        [f"lane_count:{len(lane_configs)}"],
    )
    
    results = []
    with ThreadPoolExecutor(max_workers=len(lane_configs)) as executor:
        future_to_lane = {
            executor.submit(execute_lane, config): config
            for config in lane_configs
        }
        
        for future in as_completed(future_to_lane):
            config = future_to_lane[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                # Fallback if future itself fails
                results.append(
                    LaneResult(
                        lane_id=config.lane_id,
                        lane_name=config.lane_name,
                        success=False,
                        output=f"Lane execution failed: {str(e)}",
                        evidence_refs=[f"lane:{config.lane_id}", "status:failed"],
                        metrics={"error": str(e)},
                    )
                )
    
    return results


def create_lane_configs(num_lanes: int, explore_ratio: float) -> List[LaneConfig]:
    """Create lane configurations with explore/exploit distribution."""
    configs = []
    num_explore = max(1, int(num_lanes * explore_ratio))
    
    for i in range(num_lanes):
        mode = "explore" if i < num_explore else "exploit"
        configs.append(
            LaneConfig(
                lane_id=f"lane_{i}",
                lane_name=f"lane_{chr(97 + i)}",  # lane_a, lane_b, etc.
                mode=mode,
                time_budget_minutes=5,
            )
        )
    
    # Shuffle to mix explore/exploit
    random.shuffle(configs)
    return configs


def main() -> int:
    """Main orchestration function implementing Swarmlord facade."""
    from hfo_quorum_verifier import run_quorum_verification
    
    print("=" * 70)
    print("Hive Fleet Obsidian - Multi-Lane Orchestrator")
    print("=" * 70)
    print(f"Mission ID: {MISSION_ID}")
    print(f"Parallel Lanes: {PARALLEL_LANES}")
    print(f"Explore/Exploit Ratio: {EXPLORE_RATIO}/{1-EXPLORE_RATIO}")
    print("=" * 70)
    
    # Phase 1: Perceive
    log_receipt(
        "perceive",
        f"Multi-lane orchestrator starting with {PARALLEL_LANES} parallel lanes",
        [
            __file__,
            f"mission_id:{MISSION_ID}",
            f"lanes:{PARALLEL_LANES}",
            f"explore_ratio:{EXPLORE_RATIO}",
        ],
    )
    
    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  WARNING: OPENAI_API_KEY not found in environment")
        print("Please set it in .env file (copy from .env.example)")
        print("Get your API key from: https://platform.openai.com/api-keys")
        return 1
    
    # Phase 2: React - Create lane configurations
    lane_configs = create_lane_configs(PARALLEL_LANES, EXPLORE_RATIO)
    
    config_summary = [f"{c.lane_name}:{c.mode}" for c in lane_configs]
    log_receipt(
        "react",
        f"Created {len(lane_configs)} lane configurations",
        [f"configs:{','.join(config_summary)}"],
    )
    
    print(f"\nLane Configuration:")
    for config in lane_configs:
        print(f"  - {config.lane_name}: {config.mode} mode (budget: {config.time_budget_minutes}m)")
    
    # Phase 3: Engage - Execute parallel lanes (DISPERSE)
    print(f"\n{'='*70}")
    print("DISPERSE: Executing parallel lanes...")
    print(f"{'='*70}")
    
    lane_results = run_parallel_lanes(lane_configs)
    
    success_count = sum(1 for r in lane_results if r.success)
    print(f"\nLane execution complete: {success_count}/{len(lane_results)} succeeded")
    
    for result in lane_results:
        status = "✓" if result.success else "✗"
        print(f"  {status} {result.lane_name} ({result.metrics.get('mode', 'unknown')})")
    
    # Phase 4: Verify - Quorum verification (CONVERGE)
    print(f"\n{'='*70}")
    print("CONVERGE: Running quorum verification...")
    print(f"{'='*70}")
    
    quorum_result = run_quorum_verification(lane_results, MISSION_ID, threshold=2)
    
    print(f"\n{quorum_result.summary}")
    
    if quorum_result.passed:
        print(f"\n✅ QUORUM VERIFICATION PASSED")
        print(f"   {quorum_result.validators_passed}/{quorum_result.validators_total} validators approved")
    else:
        print(f"\n❌ QUORUM VERIFICATION FAILED")
        print(f"   Only {quorum_result.validators_passed}/{quorum_result.validators_total} validators passed")
        print(f"   (threshold: {quorum_result.threshold})")
    
    # Show detailed findings
    print(f"\nDetailed Findings:")
    for val_result in quorum_result.individual_results:
        print(f"\n  {val_result.validator_name}:")
        for finding in val_result.findings[:3]:  # Show first 3 findings
            print(f"    - {finding}")
    
    # Phase 5: Digest
    digest_summary = (
        f"Multi-lane execution complete. "
        f"Quorum: {'PASS' if quorum_result.passed else 'FAIL'}"
    )
    
    log_receipt(
        "digest",
        digest_summary,
        [
            f"lanes_executed:{len(lane_results)}",
            f"lanes_successful:{success_count}",
            f"quorum_passed:{quorum_result.passed}",
            f"validators_passed:{quorum_result.validators_passed}",
        ],
    )
    
    print(f"\n{'='*70}")
    print("Digest logged to blackboard. See hfo_blackboard/obsidian_synapse_blackboard.jsonl")
    print(f"{'='*70}\n")
    
    return 0 if quorum_result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

