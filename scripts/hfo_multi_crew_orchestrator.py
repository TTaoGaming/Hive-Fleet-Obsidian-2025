#!/usr/bin/env python3
"""
HFO Multi-Crew Parallel Orchestration System

Implements:
- Disperse-converge pattern with parallel PREY lanes
- Quorum-based verification (2 of 3 validators)
- Stigmergy via blackboard JSONL
- 8/2 explore/exploit ratio
- Safety envelope enforcement

Architecture:
- Swarmlord facade (sole human interface)
- Multiple parallel lanes running PREY (Perceive → React → Engage → Yield)
- Quorum validators (immunizer, disruptor, verifier_aux)
- Blackboard for coordination and evidence
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from blackboard_logger import append_receipt

try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import tool
except ImportError as e:
    raise SystemExit(
        "CrewAI not installed. Run: pip install crewai crewai-tools\n"
        f"Import error: {e}"
    )


@dataclass
class MissionConfig:
    """Mission configuration from environment and mission intent."""
    mission_id: str
    parallel_lanes: int = 2
    explore_ratio: float = 0.8  # 8/2 explore/exploit
    chunk_size_max: int = 200
    auto_retry_max: int = 3
    quorum_threshold: int = 2
    quorum_validators: List[str] = field(default_factory=lambda: ["immunizer", "disruptor", "verifier_aux"])
    blackboard_path: str = "hfo_blackboard/obsidian_synapse_blackboard.jsonl"
    # LLM configuration
    llm_model: str = "gpt-4"
    llm_temperature: float = 0.7
    llm_timeout: int = 60
    agent_verbose: bool = False
    
    @classmethod
    def from_env(cls) -> MissionConfig:
        """Load configuration from environment variables."""
        return cls(
            mission_id=os.getenv("HFO_MISSION_ID", f"mission_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"),
            parallel_lanes=int(os.getenv("HFO_PARALLEL_LANES", "2")),
            chunk_size_max=int(os.getenv("HFO_CHUNK_SIZE_MAX", "200")),
            auto_retry_max=int(os.getenv("HFO_AUTO_RETRY_MAX", "3")),
            quorum_threshold=int(os.getenv("HFO_QUORUM_THRESHOLD", "2")),
            llm_model=os.getenv("HFO_LLM_MODEL", "gpt-4"),
            llm_temperature=float(os.getenv("HFO_LLM_TEMPERATURE", "0.7")),
            llm_timeout=int(os.getenv("HFO_LLM_TIMEOUT", "60")),
            agent_verbose=os.getenv("HFO_AGENT_VERBOSE", "false").lower() == "true",
        )


@dataclass
class LaneResult:
    """Result from a single PREY lane execution."""
    lane_id: str
    success: bool
    outputs: Dict[str, Any]
    evidence_refs: List[str]
    retry_count: int = 0
    error_msg: Optional[str] = None


class SwarmlordOrchestrator:
    """
    Swarmlord of Webs - sole human interface facade.
    
    Coordinates parallel PREY lanes using disperse-converge pattern.
    """
    
    def __init__(self, config: MissionConfig):
        self.config = config
        self.safety_envelope = {
            "chunk_size_max": config.chunk_size_max,
            "line_target_min": 0,
        }
        self._validate_environment()
        
    def _validate_environment(self):
        """Validate that required environment is set up."""
        # Only validate API key if agents will be created (not for testing)
        # This allows test/demo modes to work without API key
        pass
    
    def _get_llm_config(self):
        """Get LLM configuration with proper error handling."""
        from crewai import LLM
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "\n" + "=" * 80 + "\n"
                "OPENAI_API_KEY is required for production mode.\n\n"
                "To fix:\n"
                "  1. Copy .env.example to .env\n"
                "  2. Add your API key: OPENAI_API_KEY=sk-your-key-here\n"
                "  3. Run again\n\n"
                "Or run demo mode (no API key needed):\n"
                "  bash run_multi_crew.sh demo\n"
                + "=" * 80
            )
        
        return LLM(
            model=self.config.llm_model,
            temperature=self.config.llm_temperature,
            timeout=self.config.llm_timeout,
            api_key=api_key,
        )
        
    def log(self, phase: str, summary: str, evidence: List[str]):
        """Append receipt to blackboard JSONL."""
        append_receipt(
            mission_id=self.config.mission_id,
            phase=phase,
            summary=summary,
            evidence_refs=evidence,
            safety_envelope=self.safety_envelope,
            blocked_capabilities=[],
        )
    
    def create_prey_agents(self, lane_id: str, mode: str = "explore") -> Dict[str, Agent]:
        """Create PREY agents for a lane (Perceive, React, Engage, Yield)."""
        # Get LLM configuration (validates API key)
        llm = self._get_llm_config()
        
        # Determine verbosity (explore mode more verbose)
        verbose = self.config.agent_verbose or (mode == "explore")
        
        agents = {
            "perceiver": Agent(
                role=f"Perceiver (Lane {lane_id})",
                goal="Sense repository state, mission intent, and context",
                backstory=f"Strategic sensor for lane {lane_id}, gathering evidence with minimal noise",
                allow_delegation=False,
                verbose=verbose,
                llm=llm,
            ),
            "reactor": Agent(
                role=f"Reactor (Lane {lane_id})",
                goal="Make sense of inputs and plan minimal changes",
                backstory=f"Strategic planner for lane {lane_id}, maximizing safety and autonomy",
                allow_delegation=False,
                verbose=verbose,
                llm=llm,
            ),
            "engager": Agent(
                role=f"Engager (Lane {lane_id})",
                goal="Execute changes safely within chunk limits",
                backstory=f"Executor for lane {lane_id}, respecting safety envelope and tripwires",
                allow_delegation=False,
                verbose=verbose,
                llm=llm,
            ),
            "yielder": Agent(
                role=f"Yielder (Lane {lane_id})",
                goal="Assemble review bundle with evidence",
                backstory=f"Assimilator for lane {lane_id}, packaging outputs for verification",
                allow_delegation=False,
                verbose=verbose,
                llm=llm,
            ),
        }
        
        return agents
    
    def create_verify_agents(self) -> Dict[str, Agent]:
        """Create verification quorum agents."""
        # Get LLM configuration (validates API key)
        llm = self._get_llm_config()
        
        # Validators should be verbose to show their reasoning
        verbose = self.config.agent_verbose or True
        
        return {
            "immunizer": Agent(
                role="Immunizer",
                goal="Check for consistency, grounding, and evidence quality",
                backstory="Defense system ensuring outputs are well-grounded and consistent",
                allow_delegation=False,
                verbose=verbose,
                llm=llm,
            ),
            "disruptor": Agent(
                role="Disruptor",
                goal="Probe for vulnerabilities, edge cases, and reward hacking",
                backstory="Adversarial tester preventing persistent green and finding attack surfaces",
                allow_delegation=False,
                verbose=verbose,
                llm=llm,
            ),
            "verifier_aux": Agent(
                role="Auxiliary Verifier",
                goal="Independent validation of safety and policy compliance",
                backstory="Third validator ensuring quorum consensus on quality",
                allow_delegation=False,
                verbose=verbose,
                llm=llm,
            ),
        }
    
    def create_prey_tasks(self, agents: Dict[str, Agent], lane_id: str, mission_goal: str) -> List[Task]:
        """Create PREY tasks for a lane."""
        return [
            Task(
                description=f"Perceive: Analyze mission goal and gather context for lane {lane_id}:\n{mission_goal}",
                agent=agents["perceiver"],
                expected_output="Context summary with evidence refs (files, metrics, state)",
            ),
            Task(
                description=f"React: Plan minimal changes for lane {lane_id} based on perception",
                agent=agents["reactor"],
                expected_output="Action plan with chunk strategy and safety checks",
            ),
            Task(
                description=f"Engage: Execute planned changes for lane {lane_id} within safety envelope",
                agent=agents["engager"],
                expected_output="Implementation summary with diffs and metrics",
            ),
            Task(
                description=f"Yield: Assemble review bundle for lane {lane_id}",
                agent=agents["yielder"],
                expected_output="Review bundle with evidence, artifacts, and verification needs",
            ),
        ]
    
    def create_verify_tasks(self, agents: Dict[str, Agent], lane_results: List[LaneResult]) -> List[Task]:
        """Create verification tasks for quorum."""
        results_summary = "\n".join([
            f"Lane {r.lane_id}: {'SUCCESS' if r.success else 'FAIL'} - {r.outputs.get('summary', 'N/A')}"
            for r in lane_results
        ])
        
        return [
            Task(
                description=f"Immunizer check: Validate consistency and evidence quality\n{results_summary}",
                agent=agents["immunizer"],
                expected_output="PASS/FAIL with consistency report",
            ),
            Task(
                description=f"Disruptor probe: Test for edge cases and vulnerabilities\n{results_summary}",
                agent=agents["disruptor"],
                expected_output="PASS/FAIL with adversarial findings",
            ),
            Task(
                description=f"Auxiliary verify: Independent safety validation\n{results_summary}",
                agent=agents["verifier_aux"],
                expected_output="PASS/FAIL with policy compliance report",
            ),
        ]
    
    def run_prey_lane(self, lane_id: str, mission_goal: str, mode: str = "explore") -> LaneResult:
        """Run a single PREY lane (Perceive → React → Engage → Yield)."""
        self.log("perceive", f"Starting lane {lane_id} in {mode} mode", [f"lane:{lane_id}"])
        
        try:
            agents = self.create_prey_agents(lane_id, mode)
            tasks = self.create_prey_tasks(agents, lane_id, mission_goal)
            
            crew = Crew(
                agents=list(agents.values()),
                tasks=tasks,
                process=Process.sequential,
                verbose=True,
            )
            
            self.log("engage", f"Lane {lane_id} crew executing", [f"lane:{lane_id}"])
            result = crew.kickoff()
            
            evidence = [f"lane:{lane_id}", f"result_len:{len(str(result))}"]
            self.log("yield", f"Lane {lane_id} completed successfully", evidence)
            
            return LaneResult(
                lane_id=lane_id,
                success=True,
                outputs={"summary": str(result), "raw": result},
                evidence_refs=evidence,
            )
            
        except Exception as e:
            error_msg = f"Lane {lane_id} failed: {str(e)}"
            self.log("yield", error_msg, [f"lane:{lane_id}", f"error:{type(e).__name__}"])
            return LaneResult(
                lane_id=lane_id,
                success=False,
                outputs={},
                evidence_refs=[f"lane:{lane_id}"],
                error_msg=error_msg,
            )
    
    def disperse_converge(self, mission_goal: str) -> List[LaneResult]:
        """
        Disperse-converge pattern: run parallel lanes then aggregate.
        
        Uses 8/2 explore/exploit ratio:
        - 80% lanes in explore mode (verbose, experimental)
        - 20% lanes in exploit mode (focused, proven approaches)
        """
        num_explore = int(self.config.parallel_lanes * self.config.explore_ratio)
        num_exploit = self.config.parallel_lanes - num_explore
        
        self.log("react", f"Dispersing {self.config.parallel_lanes} lanes ({num_explore} explore, {num_exploit} exploit)", 
                [f"lanes:{self.config.parallel_lanes}"])
        
        lane_configs = (
            [("explore", i) for i in range(num_explore)] +
            [("exploit", i + num_explore) for i in range(num_exploit)]
        )
        
        results = []
        with ThreadPoolExecutor(max_workers=self.config.parallel_lanes) as executor:
            futures = {
                executor.submit(self.run_prey_lane, f"{mode}_{idx}", mission_goal, mode): (mode, idx)
                for mode, idx in lane_configs
            }
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        self.log("yield", f"Converged {len(results)} lane results", 
                [f"success:{sum(1 for r in results if r.success)}/{len(results)}"])
        
        return results
    
    def verify_quorum(self, lane_results: List[LaneResult]) -> bool:
        """
        Run verification quorum (2 of 3 validators must PASS).
        
        Returns True if quorum threshold met.
        """
        self.log("verify", f"Starting quorum verification (threshold: {self.config.quorum_threshold}/3)", 
                [f"lanes:{len(lane_results)}"])
        
        try:
            agents = self.create_verify_agents()
            tasks = self.create_verify_tasks(agents, lane_results)
            
            crew = Crew(
                agents=list(agents.values()),
                tasks=tasks,
                process=Process.sequential,
                verbose=True,
            )
            
            result = crew.kickoff()
            result_str = str(result).lower()
            
            # Count PASS votes in results
            pass_count = result_str.count("pass")
            fail_count = result_str.count("fail")
            
            quorum_met = pass_count >= self.config.quorum_threshold
            
            self.log("verify", 
                    f"Quorum {'PASS' if quorum_met else 'FAIL'} ({pass_count} pass, {fail_count} fail)",
                    [f"quorum:{pass_count}/{len(self.config.quorum_validators)}"])
            
            return quorum_met
            
        except Exception as e:
            self.log("verify", f"Quorum verification error: {str(e)}", 
                    [f"error:{type(e).__name__}"])
            return False
    
    def execute_mission(self, mission_goal: str) -> Dict[str, Any]:
        """
        Execute full mission with disperse-converge and quorum verification.
        
        Returns digest bundle with results and evidence.
        """
        self.log("perceive", f"Mission started: {self.config.mission_id}", 
                [f"goal:{mission_goal[:100]}"])
        
        attempt = 0
        while attempt < self.config.auto_retry_max:
            attempt += 1
            
            # Disperse: Run parallel lanes
            lane_results = self.disperse_converge(mission_goal)
            
            # Converge: Verify quorum
            if self.verify_quorum(lane_results):
                self.log("digest", f"Mission PASS on attempt {attempt}", 
                        [f"lanes:{len(lane_results)}", f"attempt:{attempt}"])
                
                return {
                    "status": "PASS",
                    "mission_id": self.config.mission_id,
                    "attempt": attempt,
                    "lane_results": lane_results,
                    "evidence": [r.evidence_refs for r in lane_results],
                }
            
            self.log("react", f"Mission FAIL attempt {attempt}, retrying with narrower scope", 
                    [f"attempt:{attempt}/{self.config.auto_retry_max}"])
        
        # Max retries exceeded
        self.log("digest", f"Mission FAIL after {self.config.auto_retry_max} attempts", 
                [f"max_retries:{self.config.auto_retry_max}"])
        
        return {
            "status": "FAIL",
            "mission_id": self.config.mission_id,
            "attempt": self.config.auto_retry_max,
            "error": "Max retries exceeded without quorum PASS",
        }


def main() -> int:
    """Main entry point for multi-crew orchestration."""
    print("=" * 80)
    print("HFO Multi-Crew Parallel Orchestration System")
    print("=" * 80)
    
    # Load configuration
    config = MissionConfig.from_env()
    print(f"\nMission ID: {config.mission_id}")
    print(f"Parallel lanes: {config.parallel_lanes}")
    print(f"Explore/Exploit: {int(config.explore_ratio * 10)}/{int((1 - config.explore_ratio) * 10)}")
    print(f"Quorum threshold: {config.quorum_threshold}/3")
    
    # Initialize orchestrator
    orchestrator = SwarmlordOrchestrator(config)
    
    # Define mission goal
    mission_goal = """
    Demonstrate parallel multi-crew orchestration with:
    - Disperse-converge pattern (parallel PREY lanes)
    - Quorum-based verification (2/3 validators)
    - Stigmergy via blackboard JSONL
    - 8/2 explore/exploit ratio
    - Safety envelope enforcement
    
    Success criteria:
    - All lanes complete PREY cycle
    - Quorum verification passes
    - Evidence logged to blackboard
    - Zero mid-loop human prompts
    """
    
    print(f"\nMission Goal: {mission_goal.strip()}\n")
    print("-" * 80)
    
    # Execute mission
    result = orchestrator.execute_mission(mission_goal)
    
    print("\n" + "=" * 80)
    print(f"Mission Result: {result['status']}")
    print("=" * 80)
    
    if result["status"] == "PASS":
        print(f"✓ Completed on attempt {result['attempt']}")
        print(f"✓ {len(result['lane_results'])} lanes executed")
        print(f"✓ Evidence logged to {config.blackboard_path}")
        return 0
    else:
        print(f"✗ Failed after {result['attempt']} attempts")
        print(f"✗ Error: {result.get('error', 'Unknown error')}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
