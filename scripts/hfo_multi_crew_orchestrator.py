#!/usr/bin/env python3
"""
Multi-Crew Parallel Orchestrator - Hive Fleet Obsidian
Implements disperse-converge pattern with quorum verification and stigmergy.

Architecture:
- Swarmlord facade: sole human interface
- Parallel PREY lanes (Perceive → React → Engage → Yield)
- Quorum verification (immunizer, disruptor, verifier_aux)
- Blackboard stigmergy for coordination
- Explore/exploit ratio seeding (2/8 default)

Aligned with mission intent v5 (2025-10-30) and AGENTS.md protocol.
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

# Import blackboard logger
sys.path.insert(0, str(Path(__file__).parent))
from blackboard_logger import append_receipt, ChunkId
from hfo_multi_crew_core import MissionConfig, LaneResult, VerificationQuorum

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Lazy import CrewAI
try:
    from crewai import Agent, Task, Crew, Process
except ImportError as e:
    raise SystemExit(
        "CrewAI not installed. Run: pip install -r requirements.txt\n"
        f"Import error: {e}"
    )


# Extend MissionConfig with from_env class method
def _mission_config_from_env() -> MissionConfig:
    return MissionConfig(
        mission_id=os.getenv("HFO_MISSION_ID", "multi_crew_parallel_2025-10-30"),
        lane_count=int(os.getenv("HFO_LANE_COUNT", "2")),
        explore_exploit_ratio=float(os.getenv("HFO_EXPLORE_EXPLOIT_RATIO", "0.2")),
        quorum_threshold=int(os.getenv("HFO_QUORUM_THRESHOLD", "2")),
        chunk_size_max=int(os.getenv("HFO_CHUNK_SIZE_MAX", "200")),
        placeholder_ban=os.getenv("HFO_PLACEHOLDER_BAN", "true").lower() == "true",
        blackboard_path=os.getenv("HFO_BLACKBOARD_PATH", 
                                 "hfo_blackboard/obsidian_synapse_blackboard.jsonl"),
        lane_cycle_soft_minutes=int(os.getenv("HFO_LANE_CYCLE_SOFT_MINUTES", "5")),
        mission_soft_minutes=int(os.getenv("HFO_MISSION_SOFT_MINUTES", "30")),
    )

MissionConfig.from_env = staticmethod(_mission_config_from_env)


class PreyLane:
    """Single PREY lane: Perceive → React → Engage → Yield."""
    
    def __init__(self, lane_id: str, lane_index: int, config: MissionConfig, 
                 is_explore: bool):
        self.lane_id = lane_id
        self.lane_index = lane_index
        self.config = config
        self.is_explore = is_explore
        self.safety_envelope = {
            "chunk_size_max": config.chunk_size_max,
            "line_target_min": 0,
            "tripwire_status": "green"
        }
    
    def _log(self, phase: str, summary: str, evidence: List[str]):
        """Log receipt to blackboard."""
        append_receipt(
            mission_id=self.config.mission_id,
            phase=phase,
            summary=f"[{self.lane_id}] {summary}",
            evidence_refs=evidence,
            safety_envelope=self.safety_envelope,
            blocked_capabilities=[],
            chunk_id=ChunkId(index=self.lane_index, total=self.config.lane_count)
        )
    
    def _create_agents(self) -> tuple[Agent, Agent, Agent]:
        """Create PREY agents for this lane."""
        mode = "explore" if self.is_explore else "exploit"
        
        perceiver = Agent(
            role="Perceiver",
            goal=f"Sense environment and gather context for {mode} mode",
            backstory=(
                f"Specialized sensor agent in {mode} mode. "
                "Perceive phase: scan repo, read mission intent, capture constraints."
            ),
            allow_delegation=False,
            verbose=False,
        )
        
        reactor = Agent(
            role="Reactor",
            goal=f"Make sense and plan actions in {mode} mode",
            backstory=(
                f"Strategic planner in {mode} mode. "
                "React phase: classify domain, plan chunks, define tripwires."
            ),
            allow_delegation=False,
            verbose=False,
        )
        
        engager = Agent(
            role="Engager",
            goal=f"Execute safely with minimal changes in {mode} mode",
            backstory=(
                f"Surgical implementer in {mode} mode. "
                "Engage phase: atomic edits, check limits, append receipts."
            ),
            allow_delegation=False,
            verbose=False,
        )
        
        return perceiver, reactor, engager
    
    def run(self, mission_context: str) -> LaneResult:
        """Execute PREY loop for this lane."""
        start_time = datetime.now(timezone.utc)
        errors = []
        
        try:
            self._log("perceive", "Starting PREY lane", [__file__])
            
            perceiver, reactor, engager = self._create_agents()
            
            # Perceive task
            perceive_task = Task(
                description=(
                    f"Scan mission context and gather relevant information:\n{mission_context}\n"
                    f"Mode: {'explore (20% - try novel approaches)' if self.is_explore else 'exploit (80% - use proven patterns)'}\n"
                    "Output: 3-5 bullet points of key findings."
                ),
                agent=perceiver,
                expected_output="Brief bullet list of context and constraints.",
            )
            
            # React task
            react_task = Task(
                description=(
                    "Based on perception, create a focused action plan:\n"
                    "- Identify 1-2 high-leverage actions\n"
                    "- Define success criteria\n"
                    "- Specify safety checks\n"
                    "Output: Concise action plan (3-5 bullets)."
                ),
                agent=reactor,
                expected_output="Action plan with success criteria.",
            )
            
            # Engage task
            engage_task = Task(
                description=(
                    "Execute the planned actions safely:\n"
                    "- Make minimal, surgical changes\n"
                    "- Stay within chunk size limits\n"
                    "- Log evidence references\n"
                    "Output: Summary of actions taken and outcomes."
                ),
                agent=engager,
                expected_output="Execution summary with outcomes.",
            )
            
            crew = Crew(
                agents=[perceiver, reactor, engager],
                tasks=[perceive_task, react_task, engage_task],
                process=Process.sequential,
                verbose=False,
            )
            
            self._log("react", "Crew assembled, starting execution", [self.lane_id])
            
            result = crew.kickoff()
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            output = str(result)
            evidence = [f"{self.lane_id}:result_len={len(output)}"]
            
            self._log("engage", "PREY execution complete", evidence)
            
            return LaneResult(
                lane_id=self.lane_id,
                lane_index=self.lane_index,
                success=True,
                output=output,
                evidence_refs=evidence,
                duration_seconds=duration,
                errors=errors if errors else None
            )
            
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            error_msg = f"Lane execution failed: {e}"
            errors.append(error_msg)
            self._log("engage", f"FAIL: {error_msg}", [self.lane_id])
            
            return LaneResult(
                lane_id=self.lane_id,
                lane_index=self.lane_index,
                success=False,
                output="",
                evidence_refs=[self.lane_id],
                duration_seconds=duration,
                errors=errors
            )


class VerificationQuorumWithLogging(VerificationQuorum):
    """Extends VerificationQuorum with blackboard logging."""
    
    def _log(self, phase: str, summary: str, evidence: List[str]):
        """Log verification receipt."""
        append_receipt(
            mission_id=self.config.mission_id,
            phase=phase,
            summary=summary,
            evidence_refs=evidence,
            safety_envelope={"chunk_size_max": self.config.chunk_size_max},
            blocked_capabilities=[]
        )
    
    def verify(self, lane_results: List[LaneResult]) -> tuple[bool, str, List[str]]:
        """Run quorum verification on lane results with logging."""
        self._log("verify", "Starting quorum verification", 
                 [f"lane_count={len(lane_results)}"])
        
        quorum_pass, summary, evidence = super().verify(lane_results)
        
        self._log("verify", summary, evidence)
        
        return quorum_pass, summary, evidence


class SwarmlordOrchestrator:
    """Swarmlord facade - sole human interface for parallel multi-crew orchestration."""
    
    def __init__(self, config: MissionConfig):
        self.config = config
    
    def _log(self, phase: str, summary: str, evidence: List[str]):
        """Log orchestrator receipt."""
        append_receipt(
            mission_id=self.config.mission_id,
            phase=phase,
            summary=summary,
            evidence_refs=evidence,
            safety_envelope={"chunk_size_max": self.config.chunk_size_max},
            blocked_capabilities=[]
        )
    
    def _create_lanes(self) -> List[PreyLane]:
        """Create parallel PREY lanes with explore/exploit ratio."""
        lanes = []
        explore_count = max(1, int(self.config.lane_count * self.config.explore_exploit_ratio))
        
        for i in range(self.config.lane_count):
            lane_id = f"lane_{chr(97 + i)}"  # lane_a, lane_b, etc.
            is_explore = i < explore_count
            lane = PreyLane(lane_id, i, self.config, is_explore)
            lanes.append(lane)
        
        self._log("react", 
                 f"Created {self.config.lane_count} lanes ({explore_count} explore, "
                 f"{self.config.lane_count - explore_count} exploit)",
                 [f"lane_{chr(97 + i)}" for i in range(self.config.lane_count)])
        
        return lanes
    
    def run_mission(self, mission_context: str) -> Dict[str, Any]:
        """Execute parallel multi-crew mission with quorum verification."""
        self._log("perceive", "Mission starting - Swarmlord orchestrator active", 
                 [__file__, self.config.mission_id])
        
        lanes = self._create_lanes()
        
        # Disperse: Execute lanes in parallel
        self._log("engage", f"Dispersing {len(lanes)} parallel lanes", 
                 [lane.lane_id for lane in lanes])
        
        lane_results = []
        with ThreadPoolExecutor(max_workers=self.config.lane_count) as executor:
            futures = {
                executor.submit(lane.run, mission_context): lane 
                for lane in lanes
            }
            
            for future in as_completed(futures):
                lane = futures[future]
                try:
                    result = future.result()
                    lane_results.append(result)
                    self._log("yield", 
                             f"Lane {lane.lane_id} yielded: "
                             f"{'SUCCESS' if result.success else 'FAIL'}", 
                             result.evidence_refs)
                except Exception as e:
                    self._log("yield", f"Lane {lane.lane_id} exception: {e}", 
                             [lane.lane_id])
        
        # Converge: Aggregate and verify
        self._log("yield", f"Converging {len(lane_results)} lane results", 
                 [r.lane_id for r in lane_results])
        
        verifier = VerificationQuorumWithLogging(self.config)
        quorum_pass, verify_summary, verify_evidence = verifier.verify(lane_results)
        
        # Digest
        digest = {
            "mission_id": self.config.mission_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lane_count": self.config.lane_count,
            "explore_exploit_ratio": self.config.explore_exploit_ratio,
            "quorum_threshold": self.config.quorum_threshold,
            "verification_passed": quorum_pass,
            "verification_summary": verify_summary,
            "verification_evidence": verify_evidence,
            "lane_results": [r.to_dict() for r in lane_results],
        }
        
        self._log("digest", 
                 f"Mission complete: {'PASS' if quorum_pass else 'FAIL'} - {verify_summary}",
                 [self.config.blackboard_path])
        
        return digest


def main() -> int:
    """Main entry point."""
    config = MissionConfig.from_env()
    
    print(f"🐝 Hive Fleet Obsidian - Multi-Crew Parallel Orchestrator")
    print(f"Mission ID: {config.mission_id}")
    print(f"Lanes: {config.lane_count} (explore/exploit: {config.explore_exploit_ratio})")
    print(f"Quorum: {config.quorum_threshold}/3 validators")
    print()
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not found in environment!")
        print("   Copy .env.template to .env and add your API key.")
        print("   Get one at: https://platform.openai.com/api-keys")
        return 1
    
    mission_context = """
    Mission: Demonstrate parallel multi-crew orchestration with stigmergy.
    
    Goals:
    1. Validate disperse-converge pattern with PREY lanes
    2. Demonstrate quorum verification (immunizer, disruptor, verifier_aux)
    3. Log blackboard receipts for stigmergy coordination
    4. Verify explore/exploit ratio seeding (2/8)
    
    Success criteria:
    - All lanes execute in parallel
    - Quorum verification passes (2/3 validators)
    - Blackboard receipts logged
    - Zero mid-loop human prompts
    """
    
    orchestrator = SwarmlordOrchestrator(config)
    digest = orchestrator.run_mission(mission_context)
    
    # Output digest
    print("\n📊 Mission Digest:")
    print(json.dumps(digest, indent=2))
    print()
    print(f"✅ Verification: {'PASS' if digest['verification_passed'] else 'FAIL'}")
    print(f"📝 Blackboard: {config.blackboard_path}")
    
    return 0 if digest['verification_passed'] else 1


if __name__ == "__main__":
    raise SystemExit(main())
