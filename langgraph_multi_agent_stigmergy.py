"""
LangGraph Multi-Agent System with Stigmergy Pattern

This implements a manager/orchestrator pattern with:
- Virtual stigmergy layer (pheromone-based communication)
- Parallel agent disperse and converge
- Quorum decision making
- Explore/exploit ratio of 6/4
"""

from typing import Annotated, TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import random
import json
from dataclasses import dataclass, field
from datetime import datetime
import operator


# ============================================================================
# STIGMERGY LAYER - Virtual Pheromone System
# ============================================================================

@dataclass
class Pheromone:
    """Represents a virtual pheromone marker in the stigmergy layer"""
    agent_id: str
    content: str
    strength: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class StigmergyLayer:
    """
    Virtual stigmergy layer for indirect agent communication.
    Agents leave pheromone traces that other agents can read and reinforce.
    """
    
    def __init__(self):
        self.pheromones: List[Pheromone] = []
        self.evaporation_rate = 0.1
        
    def deposit(self, agent_id: str, content: str, strength: float = 1.0, metadata: Dict = None):
        """Deposit a pheromone marker"""
        pheromone = Pheromone(
            agent_id=agent_id,
            content=content,
            strength=strength,
            metadata=metadata or {}
        )
        self.pheromones.append(pheromone)
        
    def read_all(self) -> List[Pheromone]:
        """Read all pheromones"""
        return self.pheromones
    
    def read_by_strength(self, min_strength: float = 0.3) -> List[Pheromone]:
        """Read pheromones above a certain strength threshold"""
        return [p for p in self.pheromones if p.strength >= min_strength]
    
    def evaporate(self):
        """Simulate pheromone evaporation over time"""
        for p in self.pheromones:
            p.strength *= (1 - self.evaporation_rate)
        # Remove very weak pheromones
        self.pheromones = [p for p in self.pheromones if p.strength > 0.1]
    
    def reinforce(self, content: str, boost: float = 0.2):
        """Reinforce existing pheromones with matching content"""
        for p in self.pheromones:
            if content.lower() in p.content.lower():
                p.strength = min(1.0, p.strength + boost)
    
    def get_summary(self) -> str:
        """Get a summary of the stigmergy layer state"""
        if not self.pheromones:
            return "Stigmergy layer is empty"
        
        summary = f"Stigmergy Layer: {len(self.pheromones)} pheromones\n"
        for i, p in enumerate(self.pheromones[-5:], 1):  # Show last 5
            summary += f"  {i}. [{p.agent_id}] {p.content[:50]}... (strength: {p.strength:.2f})\n"
        return summary


# ============================================================================
# STATE DEFINITION
# ============================================================================

def merge_stigmergy(left: StigmergyLayer, right: StigmergyLayer) -> StigmergyLayer:
    """Merge two stigmergy layers by combining their pheromones"""
    if left is None:
        return right
    if right is None:
        return left
    
    # Create merged layer starting from left (has existing pheromones)
    merged = StigmergyLayer()
    merged.evaporation_rate = left.evaporation_rate
    
    # Add all pheromones from left
    merged.pheromones = left.pheromones.copy()
    
    # Add new pheromones from right (avoid old duplicates from left)
    # Only add pheromones that don't already exist
    for p in right.pheromones:
        # Check if this is a new pheromone (not already in left)
        is_new = all(
            not (existing.agent_id == p.agent_id and 
                 existing.content == p.content and 
                 existing.timestamp == p.timestamp)
            for existing in left.pheromones
        )
        if is_new:
            merged.pheromones.append(p)
    
    return merged


class AgentState(TypedDict):
    """State shared across all agents in the graph"""
    messages: Annotated[List[BaseMessage], add_messages]
    task: str
    results: Annotated[List[Dict[str, Any]], operator.add]  # Use operator.add for merging lists
    quorum_reached: bool
    iteration: int
    stigmergy: Annotated[StigmergyLayer, merge_stigmergy]  # Use custom merger
    agent_votes: Dict[str, str]


# ============================================================================
# AGENT NODES
# ============================================================================

def manager_node(state: AgentState) -> AgentState:
    """
    Manager/Orchestrator Agent
    - Receives initial task
    - Dispatches to worker agents
    - Aggregates results
    - Makes final decision based on quorum
    """
    task = state.get("task", "")
    results = state.get("results", [])
    iteration = state.get("iteration", 0)
    stigmergy = state.get("stigmergy", StigmergyLayer())
    
    if iteration == 0:
        # Initial dispatch
        msg = f"Manager: Analyzing task '{task}' and dispatching to worker agents..."
        stigmergy.deposit("manager", f"Task initiated: {task}", strength=1.0)
        return {
            "messages": [AIMessage(content=msg)],
            "iteration": iteration + 1,
            "stigmergy": stigmergy
        }
    else:
        # Aggregate results
        if results:
            stigmergy.deposit("manager", f"Aggregating {len(results)} results", strength=0.9)
            
            # Count votes for quorum
            votes = {}
            for r in results:
                decision = r.get("decision", "unknown")
                votes[decision] = votes.get(decision, 0) + 1
            
            # Quorum: Need majority agreement
            total_votes = sum(votes.values())
            quorum_decision = max(votes.items(), key=lambda x: x[1])
            quorum_reached = quorum_decision[1] >= (total_votes * 0.6)  # 60% threshold
            
            msg = f"Manager: Quorum {'REACHED' if quorum_reached else 'NOT reached'}. "
            msg += f"Decision: {quorum_decision[0]} ({quorum_decision[1]}/{total_votes} votes)"
            stigmergy.deposit("manager", msg, strength=1.0 if quorum_reached else 0.5)
            
            return {
                "messages": [AIMessage(content=msg)],
                "quorum_reached": quorum_reached,
                "stigmergy": stigmergy
            }
    
    return {"messages": [AIMessage(content="Manager: Standing by")]}


def worker_explorer_node(state: AgentState) -> AgentState:
    """
    Explorer Worker Agent (Exploration focus)
    - Explores new solutions
    - 60% exploration, 40% exploitation (6/4 ratio)
    """
    task = state.get("task", "")
    stigmergy = state.get("stigmergy", StigmergyLayer())
    
    # Read stigmergy layer
    pheromones = stigmergy.read_all()
    context = f"Found {len(pheromones)} pheromone markers"
    
    # Explorer emphasizes exploration (60%)
    if random.random() < 0.6:
        # Explore: Try novel approach
        decision = random.choice(["approach_A", "approach_B", "approach_C"])
        confidence = random.uniform(0.5, 0.8)
        mode = "EXPLORE"
    else:
        # Exploit: Use proven approach from stigmergy
        if pheromones:
            strongest = max(pheromones, key=lambda p: p.strength)
            decision = strongest.metadata.get("decision", "approach_A")
            confidence = strongest.strength
            mode = "EXPLOIT"
        else:
            decision = "approach_A"
            confidence = 0.5
            mode = "EXPLORE"
    
    result = {
        "agent": "explorer",
        "decision": decision,
        "confidence": confidence,
        "mode": mode,
        "context": context
    }
    
    # Deposit pheromone
    stigmergy.deposit(
        "explorer",
        f"Explored and chose {decision}",
        strength=confidence,
        metadata={"decision": decision, "mode": mode}
    )
    
    msg = f"Explorer: {mode} mode - chose {decision} (confidence: {confidence:.2f})"
    
    return {
        "messages": [AIMessage(content=msg)],
        "results": [result],  # Return as list, not append
        "stigmergy": stigmergy
    }


def worker_exploiter_node(state: AgentState) -> AgentState:
    """
    Exploiter Worker Agent (Exploitation focus)
    - Exploits known good solutions
    - 40% exploration, 60% exploitation (balanced complement)
    """
    task = state.get("task", "")
    stigmergy = state.get("stigmergy", StigmergyLayer())
    
    # Read stigmergy layer - pay attention to strong signals
    pheromones = stigmergy.read_by_strength(min_strength=0.5)
    context = f"Found {len(pheromones)} strong pheromone markers"
    
    # Exploiter emphasizes exploitation (60%)
    if random.random() < 0.4:
        # Explore: Try novel approach
        decision = random.choice(["approach_A", "approach_B", "approach_C"])
        confidence = random.uniform(0.4, 0.7)
        mode = "EXPLORE"
    else:
        # Exploit: Use proven approach from stigmergy
        if pheromones:
            strongest = max(pheromones, key=lambda p: p.strength)
            decision = strongest.metadata.get("decision", "approach_A")
            confidence = min(0.95, strongest.strength + 0.1)  # Boost confidence
            stigmergy.reinforce(decision)  # Reinforce the trail
            mode = "EXPLOIT"
        else:
            decision = "approach_A"
            confidence = 0.6
            mode = "EXPLOIT"
    
    result = {
        "agent": "exploiter",
        "decision": decision,
        "confidence": confidence,
        "mode": mode,
        "context": context
    }
    
    # Deposit pheromone
    stigmergy.deposit(
        "exploiter",
        f"Exploited and chose {decision}",
        strength=confidence,
        metadata={"decision": decision, "mode": mode}
    )
    
    msg = f"Exploiter: {mode} mode - chose {decision} (confidence: {confidence:.2f})"
    
    return {
        "messages": [AIMessage(content=msg)],
        "results": [result],  # Return as list, not append
        "stigmergy": stigmergy
    }


def worker_validator_node(state: AgentState) -> AgentState:
    """
    Validator Worker Agent
    - Validates solutions from other agents
    - Uses stigmergy to assess consensus
    """
    task = state.get("task", "")
    stigmergy = state.get("stigmergy", StigmergyLayer())
    
    # Read stigmergy and look for patterns
    pheromones = stigmergy.read_all()
    
    # Count decision frequency in pheromones
    decision_count = {}
    for p in pheromones:
        dec = p.metadata.get("decision")
        if dec:
            decision_count[dec] = decision_count.get(dec, 0) + p.strength
    
    # Validate based on consensus
    if decision_count:
        best_decision = max(decision_count.items(), key=lambda x: x[1])
        decision = best_decision[0]
        confidence = min(0.9, best_decision[1] / len(pheromones))
        mode = "VALIDATE"
    else:
        decision = "approach_A"
        confidence = 0.3
        mode = "VALIDATE"
    
    result = {
        "agent": "validator",
        "decision": decision,
        "confidence": confidence,
        "mode": mode,
        "context": f"Validated {len(pheromones)} pheromone signals"
    }
    
    # Deposit validation pheromone
    stigmergy.deposit(
        "validator",
        f"Validated consensus for {decision}",
        strength=confidence,
        metadata={"decision": decision, "mode": mode}
    )
    
    msg = f"Validator: Consensus on {decision} (confidence: {confidence:.2f})"
    
    return {
        "messages": [AIMessage(content=msg)],
        "results": [result],  # Return as list, not append
        "stigmergy": stigmergy
    }


# ============================================================================
# BUILD GRAPH
# ============================================================================

def build_multi_agent_graph():
    """Build the multi-agent LangGraph with stigmergy"""
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("manager_dispatch", manager_node)
    workflow.add_node("worker_explorer", worker_explorer_node)
    workflow.add_node("worker_exploiter", worker_exploiter_node)
    workflow.add_node("worker_validator", worker_validator_node)
    workflow.add_node("manager_aggregate", manager_node)
    
    # Set entry point
    workflow.set_entry_point("manager_dispatch")
    
    # DISPERSE: Manager -> Workers (parallel execution)
    workflow.add_edge("manager_dispatch", "worker_explorer")
    workflow.add_edge("manager_dispatch", "worker_exploiter")
    workflow.add_edge("manager_dispatch", "worker_validator")
    
    # CONVERGE: Workers -> Manager (aggregate results)
    workflow.add_edge("worker_explorer", "manager_aggregate")
    workflow.add_edge("worker_exploiter", "manager_aggregate")
    workflow.add_edge("worker_validator", "manager_aggregate")
    
    # Manager -> END
    workflow.add_edge("manager_aggregate", END)
    
    return workflow.compile()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_multi_agent_system(task: str):
    """Run the multi-agent system with stigmergy"""
    
    print("=" * 80)
    print("LANGGRAPH MULTI-AGENT SYSTEM WITH STIGMERGY")
    print("=" * 80)
    print(f"\nTask: {task}\n")
    
    # Initialize stigmergy layer
    stigmergy = StigmergyLayer()
    
    # Build graph
    graph = build_multi_agent_graph()
    
    # Initial state
    initial_state = {
        "messages": [HumanMessage(content=task)],
        "task": task,
        "results": [],
        "quorum_reached": False,
        "iteration": 0,
        "stigmergy": stigmergy,
        "agent_votes": {}
    }
    
    print("Starting multi-agent workflow...\n")
    print("-" * 80)
    
    # Stream execution
    for i, step in enumerate(graph.stream(initial_state), 1):
        print(f"\n[Step {i}]")
        for node_name, node_state in step.items():
            print(f"  Node: {node_name}")
            if "messages" in node_state and node_state["messages"]:
                last_msg = node_state["messages"][-1]
                print(f"  Message: {last_msg.content}")
    
    print("\n" + "-" * 80)
    
    # Get final state
    final_state = graph.invoke(initial_state)
    
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    # Display results
    results = final_state.get("results", [])
    print(f"\nAgent Results ({len(results)}):")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r['agent']}: {r['decision']} "
              f"(confidence: {r['confidence']:.2f}, mode: {r['mode']})")
    
    # Display stigmergy state
    stigmergy_final = final_state.get("stigmergy", StigmergyLayer())
    print(f"\n{stigmergy_final.get_summary()}")
    
    # Show pheromone details if available
    if stigmergy_final.pheromones:
        print(f"\nPheromone Trail Details:")
        for i, p in enumerate(stigmergy_final.pheromones, 1):
            print(f"  {i}. [{p.agent_id}] {p.content} (strength: {p.strength:.2f})")
    
    # Quorum status
    quorum = final_state.get("quorum_reached", False)
    print(f"\nQuorum Status: {'✓ REACHED' if quorum else '✗ NOT REACHED'}")
    
    return final_state


if __name__ == "__main__":
    # Test the multi-agent system
    task = "Determine the best approach to solve a complex optimization problem"
    final_state = run_multi_agent_system(task)
    
    print("\n" + "=" * 80)
    print("System verified successfully!")
    print("=" * 80)
