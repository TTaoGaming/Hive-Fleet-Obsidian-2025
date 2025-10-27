"""
LangGraph Multi-Agent Manager and Orchestrator Pattern
with Parallel Disperse/Converge Quorum and Virtual Stigmergy Layer

This implementation demonstrates:
1. Manager/Orchestrator Pattern - Central coordination
2. Parallel Agent Disperse & Converge - Multiple agents work simultaneously
3. Quorum-based Decision Making - Consensus among agents
4. Virtual Stigmergy Layer - Shared state for indirect communication
5. Explore/Exploit Ratio (40/60) - Balance between exploration and exploitation
"""

from typing import Annotated, TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import random
from operator import add
import threading
import copy


# ===== STIGMERGY LAYER (Virtual Blackboard) =====
class StigmergyLayer:
    """
    Virtual stigmergy layer for indirect agent communication.
    Agents leave traces/pheromones that influence other agents' behavior.
    Thread-safe for parallel agent execution.
    """
    
    def __init__(self, persist_path: str = "blackboard/stigmergy_state.json"):
        self.persist_path = Path(persist_path)
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self.traces: Dict[str, Any] = {}
        self.lock = threading.RLock()  # Reentrant lock for thread safety
        self.load()
    
    def deposit_trace(self, agent_id: str, trace_type: str, data: Any):
        """Agent deposits a trace (pheromone) in the environment"""
        timestamp = datetime.now(timezone.utc).isoformat()
        trace_key = f"{agent_id}_{trace_type}_{timestamp}"
        
        with self.lock:
            self.traces[trace_key] = {
                "agent_id": agent_id,
                "type": trace_type,
                "data": data,
                "timestamp": timestamp,
                "strength": 1.0  # Pheromone strength
            }
            self._save()
    
    def read_traces(self, trace_type: str = None, min_strength: float = 0.1) -> List[Dict]:
        """Read traces from environment, optionally filtered by type"""
        with self.lock:
            traces = []
            for key, trace in self.traces.items():
                if trace["strength"] < min_strength:
                    continue
                if trace_type is None or trace["type"] == trace_type:
                    # Use deepcopy for complete isolation in concurrent environment
                    traces.append(copy.deepcopy(trace))
            return sorted(traces, key=lambda x: x["timestamp"], reverse=True)
    
    def evaporate(self, decay_rate: float = 0.1):
        """Pheromone evaporation - traces decay over time"""
        with self.lock:
            for key in list(self.traces.keys()):
                self.traces[key]["strength"] *= (1 - decay_rate)
                if self.traces[key]["strength"] < 0.01:
                    del self.traces[key]
            self._save()
    
    def _save(self):
        """
        Persist stigmergy state to disk.
        PRIVATE: Must be called with self.lock held.
        
        Note: Lock verification removed as threading.Lock.locked() doesn't reliably
        check current thread ownership. Instead, rely on proper usage via with-lock blocks.
        """
        with open(self.persist_path, 'w') as f:
            json.dump(self.traces, f, indent=2)
    
    def load(self):
        """Load stigmergy state from disk"""
        with self.lock:
            if self.persist_path.exists():
                with open(self.persist_path, 'r') as f:
                    self.traces = json.load(f)


# Helper function to merge agent results
def merge_agent_results(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """Merge agent results from parallel execution"""
    merged = left.copy() if left else {}
    if right:
        merged.update(right)
    return merged


# Helper function to merge votes
def merge_votes(left: List[Dict], right: List[Dict]) -> List[Dict]:
    """Merge vote lists from parallel execution"""
    merged = left.copy() if left else []
    if right:
        merged.extend(right)
    return merged


# ===== STATE DEFINITION =====
class AgentState(TypedDict):
    """Shared state across all agents"""
    messages: Annotated[List[BaseMessage], add_messages]
    task: str
    manager_plan: Dict[str, Any]
    agent_results: Annotated[Dict[str, Any], merge_agent_results]
    quorum_votes: Annotated[List[Dict[str, Any]], merge_votes]
    quorum_reached: bool
    final_decision: str
    iteration: int
    explore_exploit_mode: str  # "explore" or "exploit"
    stigmergy: StigmergyLayer


# ===== AGENT NODES =====
def manager_node(state: AgentState) -> AgentState:
    """
    Manager/Orchestrator Agent
    - Analyzes task
    - Creates execution plan
    - Dispatches to worker agents
    - Decides explore vs exploit mode
    """
    task = state.get("task", "")
    iteration = state.get("iteration", 0)
    
    # Explore/Exploit decision (40% explore, 60% exploit)
    mode = "explore" if random.random() < 0.4 else "exploit"
    
    # Create plan
    plan = {
        "task_id": f"task_{iteration}",
        "mode": mode,
        "subtasks": [
            {"id": "subtask_1", "description": f"Analyze: {task}", "agent": "agent_1"},
            {"id": "subtask_2", "description": f"Process: {task}", "agent": "agent_2"},
            {"id": "subtask_3", "description": f"Validate: {task}", "agent": "agent_3"},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Deposit plan in stigmergy layer
    if state.get("stigmergy"):
        state["stigmergy"].deposit_trace("manager", "plan", plan)
    
    msg = AIMessage(content=f"Manager created plan in {mode} mode with {len(plan['subtasks'])} subtasks")
    
    return {
        "messages": [msg],
        "manager_plan": plan,
        "explore_exploit_mode": mode,
        "iteration": iteration + 1
    }


def agent_worker_1(state: AgentState) -> AgentState:
    """Worker Agent 1 - Analysis specialist"""
    plan = state.get("manager_plan", {})
    mode = state.get("explore_exploit_mode", "exploit")
    task = state.get("task", "")
    
    # Read stigmergy traces for context
    recent_traces = []
    if state.get("stigmergy"):
        recent_traces = state["stigmergy"].read_traces(trace_type="result")
    
    # Simulate work with explore/exploit behavior
    if mode == "explore":
        result = f"Agent 1: Explored new approach for '{task}' - found innovative pattern"
        confidence = 0.7
    else:
        result = f"Agent 1: Applied proven analysis method to '{task}' - high confidence result"
        confidence = 0.9
    
    result_data = {
        "agent": "agent_1",
        "result": result,
        "confidence": confidence,
        "mode": mode,
        "context_traces": len(recent_traces)
    }
    
    # Deposit result trace
    if state.get("stigmergy"):
        state["stigmergy"].deposit_trace("agent_1", "result", result_data)
    
    msg = AIMessage(content=f"Agent 1 completed analysis ({mode} mode, confidence: {confidence})")
    
    return {
        "messages": [msg],
        "agent_results": {"agent_1": result_data}
    }


def agent_worker_2(state: AgentState) -> AgentState:
    """Worker Agent 2 - Processing specialist"""
    plan = state.get("manager_plan", {})
    mode = state.get("explore_exploit_mode", "exploit")
    task = state.get("task", "")
    
    # Read stigmergy traces
    recent_traces = []
    if state.get("stigmergy"):
        recent_traces = state["stigmergy"].read_traces(trace_type="result")
    
    if mode == "explore":
        result = f"Agent 2: Tested experimental processing for '{task}' - discovered edge case"
        confidence = 0.6
    else:
        result = f"Agent 2: Used standard processing pipeline for '{task}' - reliable output"
        confidence = 0.95
    
    result_data = {
        "agent": "agent_2",
        "result": result,
        "confidence": confidence,
        "mode": mode,
        "context_traces": len(recent_traces)
    }
    
    if state.get("stigmergy"):
        state["stigmergy"].deposit_trace("agent_2", "result", result_data)
    
    msg = AIMessage(content=f"Agent 2 completed processing ({mode} mode, confidence: {confidence})")
    
    return {
        "messages": [msg],
        "agent_results": {"agent_2": result_data}
    }


def agent_worker_3(state: AgentState) -> AgentState:
    """Worker Agent 3 - Validation specialist"""
    plan = state.get("manager_plan", {})
    mode = state.get("explore_exploit_mode", "exploit")
    task = state.get("task", "")
    
    # Read stigmergy traces
    recent_traces = []
    if state.get("stigmergy"):
        recent_traces = state["stigmergy"].read_traces(trace_type="result")
    
    if mode == "explore":
        result = f"Agent 3: Validated '{task}' with novel criteria - found potential improvement"
        confidence = 0.75
    else:
        result = f"Agent 3: Validated '{task}' against standard criteria - passed all checks"
        confidence = 0.92
    
    result_data = {
        "agent": "agent_3",
        "result": result,
        "confidence": confidence,
        "mode": mode,
        "context_traces": len(recent_traces)
    }
    
    if state.get("stigmergy"):
        state["stigmergy"].deposit_trace("agent_3", "result", result_data)
    
    msg = AIMessage(content=f"Agent 3 completed validation ({mode} mode, confidence: {confidence})")
    
    return {
        "messages": [msg],
        "agent_results": {"agent_3": result_data}
    }


def quorum_node(state: AgentState) -> AgentState:
    """
    Quorum/Consensus Node
    - Collects results from all agents
    - Implements voting/consensus mechanism
    - Determines if quorum is reached (2/3 majority)
    """
    agent_results = state.get("agent_results", {})
    
    # Each agent votes based on confidence
    votes = []
    for agent_id, result_data in agent_results.items():
        vote = {
            "agent": agent_id,
            "vote": "approve" if result_data["confidence"] > 0.7 else "reject",
            "confidence": result_data["confidence"]
        }
        votes.append(vote)
    
    # Calculate quorum (need 2/3 approval)
    approvals = sum(1 for v in votes if v["vote"] == "approve")
    quorum_reached = approvals >= (len(votes) * 2 / 3)
    
    avg_confidence = sum(v["confidence"] for v in votes) / len(votes) if votes else 0
    
    decision = "APPROVED" if quorum_reached else "REJECTED"
    
    # Deposit quorum result in stigmergy
    if state.get("stigmergy"):
        state["stigmergy"].deposit_trace("quorum", "decision", {
            "decision": decision,
            "votes": votes,
            "avg_confidence": avg_confidence
        })
        # Evaporate old traces
        state["stigmergy"].evaporate(decay_rate=0.1)
    
    msg = AIMessage(
        content=f"Quorum reached: {quorum_reached} ({approvals}/{len(votes)} approved) - Decision: {decision}"
    )
    
    return {
        "messages": [msg],
        "quorum_votes": votes,
        "quorum_reached": quorum_reached,
        "final_decision": decision
    }


def should_continue(state: AgentState) -> str:
    """Routing function to determine next step"""
    # Simple routing: always go to END after quorum
    return END


# ===== BUILD GRAPH =====
def build_multi_agent_graph():
    """
    Build the multi-agent orchestrator graph with:
    - Manager (orchestrator)
    - 3 Worker agents (parallel execution)
    - Quorum/consensus node
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("manager", manager_node)
    workflow.add_node("agent_1", agent_worker_1)
    workflow.add_node("agent_2", agent_worker_2)
    workflow.add_node("agent_3", agent_worker_3)
    workflow.add_node("quorum", quorum_node)
    
    # Define flow
    workflow.set_entry_point("manager")
    
    # Manager dispatches to all agents in parallel
    workflow.add_edge("manager", "agent_1")
    workflow.add_edge("manager", "agent_2")
    workflow.add_edge("manager", "agent_3")
    
    # All agents converge to quorum
    workflow.add_edge("agent_1", "quorum")
    workflow.add_edge("agent_2", "quorum")
    workflow.add_edge("agent_3", "quorum")
    
    # Quorum to end
    workflow.add_conditional_edges(
        "quorum",
        should_continue,
        {END: END}
    )
    
    return workflow.compile()


# ===== MAIN EXECUTION =====
def run_orchestrator(task: str, num_iterations: int = 3):
    """
    Run the multi-agent orchestrator system
    
    Args:
        task: The task to process
        num_iterations: Number of times to run the workflow
    """
    print("=" * 80)
    print("LangGraph Multi-Agent Orchestrator with Stigmergy")
    print("=" * 80)
    print(f"Task: {task}")
    print(f"Iterations: {num_iterations}")
    print("=" * 80)
    
    # Initialize stigmergy layer
    stigmergy = StigmergyLayer()
    
    # Build graph
    graph = build_multi_agent_graph()
    
    # Run iterations
    for i in range(num_iterations):
        print(f"\n{'=' * 80}")
        print(f"ITERATION {i + 1}/{num_iterations}")
        print(f"{'=' * 80}\n")
        
        initial_state = {
            "messages": [HumanMessage(content=f"Iteration {i + 1}: {task}")],
            "task": task,
            "manager_plan": {},
            "agent_results": {},
            "quorum_votes": [],
            "quorum_reached": False,
            "final_decision": "",
            "iteration": i,
            "explore_exploit_mode": "",
            "stigmergy": stigmergy
        }
        
        # Execute graph
        result = None
        for step in graph.stream(initial_state):
            for node_name, node_output in step.items():
                print(f"\n[{node_name.upper()}]")
                if "messages" in node_output:
                    for msg in node_output["messages"]:
                        print(f"  {msg.content}")
                result = node_output
        
        # Print iteration summary
        if result:
            print(f"\n{'─' * 80}")
            print("ITERATION SUMMARY:")
            print(f"  Mode: {result.get('explore_exploit_mode', 'N/A')}")
            print(f"  Final Decision: {result.get('final_decision', 'N/A')}")
            print(f"  Quorum Reached: {result.get('quorum_reached', False)}")
            if result.get('quorum_votes'):
                print(f"  Votes: {len(result['quorum_votes'])} agents participated")
                for vote in result['quorum_votes']:
                    print(f"    - {vote['agent']}: {vote['vote']} (confidence: {vote['confidence']:.2f})")
            print(f"{'─' * 80}")
        
        # Small delay between iterations
        time.sleep(0.5)
    
    # Print final stigmergy state
    print(f"\n{'=' * 80}")
    print("FINAL STIGMERGY STATE")
    print(f"{'=' * 80}")
    traces = stigmergy.read_traces()
    print(f"Active traces: {len(traces)}")
    for trace in traces[:10]:  # Show last 10
        print(f"  - [{trace['type']}] {trace['agent_id']}: strength={trace['strength']:.2f}")
    
    print(f"\n{'=' * 80}")
    print("EXECUTION COMPLETE")
    print(f"{'=' * 80}\n")
    
    return stigmergy


if __name__ == "__main__":
    # Test the multi-agent orchestrator
    task = "Analyze and process distributed AI swarm intelligence patterns"
    
    print("\n🐝 Starting Multi-Agent Orchestrator Demo 🐝\n")
    
    stigmergy = run_orchestrator(task, num_iterations=3)
    
    print("\n✅ Demo completed successfully!")
    print(f"📊 Stigmergy state saved to: {stigmergy.persist_path}")
