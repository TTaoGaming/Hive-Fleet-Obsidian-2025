"""
Swarmlord orchestrator for parallel crew coordination.

Implements disperse-converge pattern with stigmergy via blackboard.
"""

import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from crewai import Crew, Process
from langchain_openai import ChatOpenAI

from .agents import (
    create_perceiver_agent,
    create_reactor_agent,
    create_engager_agent,
    create_yielder_agent,
    create_immunizer_agent,
    create_disruptor_agent,
    create_verifier_aux_agent,
)
from .tasks import (
    create_perceive_task,
    create_react_task,
    create_engage_task,
    create_yield_task,
    create_verify_task,
)
from .blackboard import BlackboardManager
from .config import CrewConfig, MissionIntent
from .safety import SafetyEnvelope


class SwarmlordOrchestrator:
    """Orchestrates parallel crew lanes with disperse-converge pattern."""
    
    def __init__(
        self,
        config: Optional[CrewConfig] = None,
        mission_intent: Optional[MissionIntent] = None
    ):
        """Initialize Swarmlord orchestrator.
        
        Args:
            config: Crew configuration
            mission_intent: Mission intent specification
        """
        self.config = config or CrewConfig()
        self.mission = mission_intent or MissionIntent()
        self.blackboard = BlackboardManager(self.config.blackboard_path)
        self.safety = SafetyEnvelope(self.mission.chunk_size_max)
        
        self.llm = ChatOpenAI(
            model=self.config.model_name,
            temperature=self.config.temperature,
            openai_api_key=self.config.openai_api_key
        )
        
        self.mission_id = self.mission.mission_id
        self._log_initialization()
    
    def _log_initialization(self) -> None:
        """Log orchestrator initialization to blackboard."""
        self.blackboard.append_receipt(
            mission_id=self.mission_id,
            phase="init",
            summary=f"Swarmlord initialized: {self.mission.lanes_count} lanes, quorum {self.mission.quorum_threshold}",
            evidence_refs=[f"config:lanes={self.mission.lanes_count}"],
            safety_envelope=self.safety.get_status()
        )
    
    def _create_lane_crew(self, lane_name: str, mission_context: str) -> Crew:
        """Create a crew for a single PREY lane.
        
        Args:
            lane_name: Name of the lane
            mission_context: Mission context and objectives
            
        Returns:
            Configured crew for the lane
        """
        perceiver = create_perceiver_agent(self.llm)
        reactor = create_reactor_agent(self.llm)
        engager = create_engager_agent(self.llm)
        yielder = create_yielder_agent(self.llm)
        
        perceive_task = create_perceive_task(perceiver, mission_context)
        react_task = create_react_task(reactor)
        engage_task = create_engage_task(engager)
        yield_task = create_yield_task(yielder)
        
        return Crew(
            agents=[perceiver, reactor, engager, yielder],
            tasks=[perceive_task, react_task, engage_task, yield_task],
            process=Process.sequential,
            verbose=True,
        )
    
    def _execute_lane(
        self,
        lane_name: str,
        mission_context: str,
        explore: bool
    ) -> Dict[str, Any]:
        """Execute a single lane.
        
        Args:
            lane_name: Name of the lane
            mission_context: Mission context
            explore: True for exploration, False for exploitation
            
        Returns:
            Lane execution result
        """
        mode = "explore" if explore else "exploit"
        
        self.blackboard.append_receipt(
            mission_id=self.mission_id,
            phase="perceive",
            summary=f"Lane {lane_name} starting ({mode} mode)",
            evidence_refs=[f"lane:{lane_name}"],
            safety_envelope=self.safety.get_status(),
            lane=lane_name,
            mode=mode
        )
        
        try:
            crew = self._create_lane_crew(lane_name, mission_context)
            result = crew.kickoff()
            
            self.blackboard.append_receipt(
                mission_id=self.mission_id,
                phase="yield",
                summary=f"Lane {lane_name} completed ({mode} mode)",
                evidence_refs=[f"lane:{lane_name}:result"],
                safety_envelope=self.safety.get_status(),
                lane=lane_name,
                mode=mode
            )
            
            return {
                'lane': lane_name,
                'mode': mode,
                'status': 'success',
                'result': str(result),
            }
            
        except Exception as e:
            self.blackboard.append_receipt(
                mission_id=self.mission_id,
                phase="yield",
                summary=f"Lane {lane_name} failed: {str(e)}",
                evidence_refs=[f"lane:{lane_name}:error"],
                safety_envelope=self.safety.get_status(),
                lane=lane_name,
                mode=mode,
                error=str(e)
            )
            
            return {
                'lane': lane_name,
                'mode': mode,
                'status': 'failed',
                'error': str(e),
            }
    
    def _verify_quorum(self, lane_results: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
        """Run verification quorum on lane results.
        
        Args:
            lane_results: Results from all lanes
            
        Returns:
            (passed, verification_report)
        """
        immunizer = create_immunizer_agent(self.llm)
        disruptor = create_disruptor_agent(self.llm)
        verifier_aux = create_verifier_aux_agent(self.llm)
        
        bundle_summary = "\n".join([
            f"Lane {r['lane']} ({r['mode']}): {r['status']}"
            for r in lane_results
        ])
        
        verify_tasks = [
            create_verify_task(immunizer, bundle_summary, "immunizer"),
            create_verify_task(disruptor, bundle_summary, "disruptor"),
            create_verify_task(verifier_aux, bundle_summary, "verifier_aux"),
        ]
        
        verify_crew = Crew(
            agents=[immunizer, disruptor, verifier_aux],
            tasks=verify_tasks,
            process=Process.sequential,
            verbose=True,
        )
        
        try:
            verify_result = verify_crew.kickoff()
            
            pass_count = str(verify_result).lower().count('pass')
            fail_count = str(verify_result).lower().count('fail')
            
            quorum_passed = pass_count >= self.mission.quorum_threshold
            
            self.blackboard.append_receipt(
                mission_id=self.mission_id,
                phase="verify",
                summary=f"Quorum verification: {'PASS' if quorum_passed else 'FAIL'} ({pass_count}/{len(verify_tasks)} passed)",
                evidence_refs=["verify:quorum"],
                safety_envelope=self.safety.get_status(),
                quorum_passed=quorum_passed,
                pass_count=pass_count,
                fail_count=fail_count
            )
            
            return quorum_passed, {
                'passed': quorum_passed,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'result': str(verify_result),
            }
            
        except Exception as e:
            self.blackboard.append_receipt(
                mission_id=self.mission_id,
                phase="verify",
                summary=f"Verification failed: {str(e)}",
                evidence_refs=["verify:error"],
                safety_envelope=self.safety.get_status(),
                error=str(e)
            )
            
            return False, {'passed': False, 'error': str(e)}
    
    def execute_mission(
        self,
        mission_context: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Execute full mission with parallel lanes and verification.
        
        Args:
            mission_context: Mission objectives and context
            max_retries: Maximum retry attempts on failure
            
        Returns:
            Mission execution report
        """
        for attempt in range(max_retries):
            self.blackboard.append_receipt(
                mission_id=self.mission_id,
                phase="perceive",
                summary=f"Mission attempt {attempt + 1}/{max_retries}",
                evidence_refs=[f"attempt:{attempt + 1}"],
                safety_envelope=self.safety.get_status()
            )
            
            lane_results = []
            lanes = self.mission.lane_names[:self.mission.lanes_count]
            
            explore_count = int(len(lanes) * self.config.explore_ratio)
            explore_lanes = random.sample(lanes, min(explore_count, len(lanes)))
            
            with ThreadPoolExecutor(max_workers=len(lanes)) as executor:
                futures = {
                    executor.submit(
                        self._execute_lane,
                        lane,
                        mission_context,
                        lane in explore_lanes
                    ): lane
                    for lane in lanes
                }
                
                for future in as_completed(futures):
                    result = future.result()
                    lane_results.append(result)
            
            quorum_passed, verify_report = self._verify_quorum(lane_results)
            
            if quorum_passed:
                self.blackboard.append_receipt(
                    mission_id=self.mission_id,
                    phase="digest",
                    summary=f"Mission succeeded on attempt {attempt + 1}",
                    evidence_refs=["mission:success"],
                    safety_envelope=self.safety.get_status(),
                    attempt=attempt + 1
                )
                
                return {
                    'status': 'success',
                    'attempt': attempt + 1,
                    'lane_results': lane_results,
                    'verification': verify_report,
                }
            
            self.blackboard.append_receipt(
                mission_id=self.mission_id,
                phase="react",
                summary=f"Attempt {attempt + 1} failed verification, retrying with smaller scope",
                evidence_refs=[f"attempt:{attempt + 1}:retry"],
                safety_envelope=self.safety.get_status(),
                regen_flag=True
            )
        
        self.blackboard.append_receipt(
            mission_id=self.mission_id,
            phase="digest",
            summary=f"Mission failed after {max_retries} attempts",
            evidence_refs=["mission:failed"],
            safety_envelope=self.safety.get_status()
        )
        
        return {
            'status': 'failed',
            'attempts': max_retries,
            'lane_results': lane_results,
            'verification': verify_report,
        }
