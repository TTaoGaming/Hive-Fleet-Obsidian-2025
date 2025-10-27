"""
LangGraph Multi-Agent System with Stigmergy Layer
==================================================

Implements:
- Manager/Orchestrator pattern
- Parallel agent dispatch and converge
- Quorum decision making
- Virtual stigmergy layer (shared blackboard)
- Explore/Exploit 8/2 ratio
"""

from typing import Annotated, TypedDict, Literal, List, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import json
from datetime import datetime, timezone
import random


# ============================================================================
# STIGMERGY LAYER - Shared Blackboard for Agent Coordination
# ============================================================================

class StigmergyBlackboard:
    """
    Append-only blackboard for agent coordination via stigmergy.
    Agents leave traces/signals that other agents can read and respond to.
    """
    def __init__(self):
        self.entries: List[Dict[str, Any]] = []
        
    def append(self, agent_id: str, event_type: str, data: Dict[str, Any]):
        """Append an entry to the blackboard (append-only, no edits)"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "event_type": event_type,
            "data": data
        }
        self.entries.append(entry)
        return entry
    
    def query(self, event_type: str = None, agent_id: str = None) -> List[Dict[str, Any]]:
        """Query entries from the blackboard"""
        results = self.entries
        if event_type:
            results = [e for e in results if e["event_type"] == event_type]
        if agent_id:
            results = [e for e in results if e["agent_id"] == agent_id]
        return results
    
    def get_latest(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get the latest n entries"""
        return self.entries[-n:] if self.entries else []
    
    def to_json(self) -> str:
        """Export blackboard as JSON"""
        return json.dumps(self.entries, indent=2)


# ============================================================================
# STATE DEFINITION
# ============================================================================

class AgentState(TypedDict):
    """State shared across all agents in the graph"""
    messages: Annotated[list[BaseMessage], add_messages]
    blackboard: StigmergyBlackboard
    task_description: str
    exploration_results: List[Dict[str, Any]]
    exploitation_results: List[Dict[str, Any]]
    quorum_decision: str
    step_count: int
    agent_votes: Dict[str, str]


# ============================================================================
# AGENT NODES
# ============================================================================

def manager_node(state: AgentState) -> AgentState:
    """
    Manager/Orchestrator Node
    - Receives task
    - Breaks it down
    - Dispatches to parallel agents
    """
    blackboard = state.get("blackboard") or StigmergyBlackboard()
    task = state.get("task_description", "No task specified")
    
    # Log manager activity to blackboard
    blackboard.append(
        agent_id="manager",
        event_type="task_received",
        data={"task": task, "action": "analyzing and dispatching"}
    )
    
    # Manager analyzes and creates dispatch plan
    dispatch_plan = {
        "explore_agents": 8,  # 80% explore
        "exploit_agents": 2,  # 20% exploit
        "strategy": "parallel_dispatch_converge"
    }
    
    blackboard.append(
        agent_id="manager",
        event_type="dispatch_plan",
        data=dispatch_plan
    )
    
    manager_msg = AIMessage(
        content=f"[MANAGER] Analyzed task: '{task}'. Dispatching {dispatch_plan['explore_agents']} explorer agents and {dispatch_plan['exploit_agents']} exploiter agents."
    )
    
    return {
        **state,
        "messages": state.get("messages", []) + [manager_msg],
        "blackboard": blackboard,
        "step_count": state.get("step_count", 0) + 1
    }


def explorer_agents_node(state: AgentState) -> AgentState:
    """
    Explorer Agents Node (Parallel Execution Simulated)
    - Multiple agents explore different solutions
    - Each leaves traces on blackboard
    - 80% of total agent capacity
    """
    blackboard = state.get("blackboard") or StigmergyBlackboard()
    task = state.get("task_description", "")
    
    # Simulate 8 explorer agents working in parallel
    exploration_results = []
    
    for i in range(8):
        agent_id = f"explorer_{i+1}"
        
        # Each explorer investigates a different approach
        exploration = {
            "agent_id": agent_id,
            "approach": f"approach_{i+1}",
            "findings": f"Explored solution path {i+1} for: {task}",
            "confidence": random.uniform(0.5, 0.95),
            "novelty_score": random.uniform(0.6, 1.0)
        }
        
        exploration_results.append(exploration)
        
        # Leave trace on stigmergy blackboard
        blackboard.append(
            agent_id=agent_id,
            event_type="exploration_complete",
            data=exploration
        )
    
    explorer_msg = AIMessage(
        content=f"[EXPLORERS] 8 explorer agents completed parallel search. Found {len(exploration_results)} potential solution paths."
    )
    
    return {
        **state,
        "messages": state.get("messages", []) + [explorer_msg],
        "blackboard": blackboard,
        "exploration_results": exploration_results,
        "step_count": state.get("step_count", 0) + 1
    }


def exploiter_agents_node(state: AgentState) -> AgentState:
    """
    Exploiter Agents Node (Parallel Execution Simulated)
    - Refine best known solutions
    - Focus on optimization
    - 20% of total agent capacity
    """
    blackboard = state.get("blackboard") or StigmergyBlackboard()
    exploration_results = state.get("exploration_results", [])
    
    # Exploiters read from blackboard to see what explorers found
    blackboard_traces = blackboard.query(event_type="exploration_complete")
    
    # Simulate 2 exploiter agents refining top solutions
    exploitation_results = []
    
    # Select top exploration results to refine
    sorted_explorations = sorted(
        exploration_results, 
        key=lambda x: x.get("confidence", 0), 
        reverse=True
    )[:2]
    
    for i, top_solution in enumerate(sorted_explorations):
        agent_id = f"exploiter_{i+1}"
        
        exploitation = {
            "agent_id": agent_id,
            "refined_approach": top_solution["approach"],
            "optimization": f"Refined {top_solution['approach']} with optimization",
            "confidence": min(top_solution["confidence"] * 1.15, 0.99),
            "based_on": top_solution["agent_id"]
        }
        
        exploitation_results.append(exploitation)
        
        # Leave trace on stigmergy blackboard
        blackboard.append(
            agent_id=agent_id,
            event_type="exploitation_complete",
            data=exploitation
        )
    
    exploiter_msg = AIMessage(
        content=f"[EXPLOITERS] 2 exploiter agents refined top solutions. Optimization complete."
    )
    
    return {
        **state,
        "messages": state.get("messages", []) + [exploiter_msg],
        "blackboard": blackboard,
        "exploitation_results": exploitation_results,
        "step_count": state.get("step_count", 0) + 1
    }


def quorum_convergence_node(state: AgentState) -> AgentState:
    """
    Quorum Convergence Node
    - Collects results from all agents
    - Agents "vote" via blackboard signals
    - Determines consensus decision
    """
    blackboard = state.get("blackboard") or StigmergyBlackboard()
    exploration_results = state.get("exploration_results", [])
    exploitation_results = state.get("exploitation_results", [])
    
    # Read all agent traces from blackboard
    all_explorations = blackboard.query(event_type="exploration_complete")
    all_exploitations = blackboard.query(event_type="exploitation_complete")
    
    # Voting mechanism: each agent votes for best solution
    agent_votes = {}
    
    # Explorers vote
    for result in exploration_results:
        agent_votes[result["agent_id"]] = result["approach"]
    
    # Exploiters vote (with higher weight)
    for result in exploitation_results:
        agent_votes[result["agent_id"]] = result["refined_approach"]
        # Exploiter votes count double (simulated by adding duplicate)
        agent_votes[result["agent_id"] + "_weighted"] = result["refined_approach"]
    
    # Tally votes
    vote_counts = {}
    for vote in agent_votes.values():
        vote_counts[vote] = vote_counts.get(vote, 0) + 1
    
    # Determine quorum decision (majority vote)
    if vote_counts:
        quorum_decision = max(vote_counts.items(), key=lambda x: x[1])[0]
    else:
        quorum_decision = "No consensus reached"
    
    # Log quorum decision to blackboard
    blackboard.append(
        agent_id="quorum",
        event_type="decision_made",
        data={
            "decision": quorum_decision,
            "vote_counts": vote_counts,
            "total_agents": len(agent_votes),
            "consensus_strength": max(vote_counts.values()) / len(agent_votes) if agent_votes else 0
        }
    )
    
    quorum_msg = AIMessage(
        content=f"[QUORUM] Convergence complete. Decision: {quorum_decision}. Vote distribution: {vote_counts}"
    )
    
    return {
        **state,
        "messages": state.get("messages", []) + [quorum_msg],
        "blackboard": blackboard,
        "quorum_decision": quorum_decision,
        "agent_votes": agent_votes,
        "step_count": state.get("step_count", 0) + 1
    }


def orchestrator_final_node(state: AgentState) -> AgentState:
    """
    Final Orchestrator Node
    - Reviews quorum decision
    - Synthesizes final output
    - Logs to blackboard
    """
    blackboard = state.get("blackboard") or StigmergyBlackboard()
    quorum_decision = state.get("quorum_decision", "No decision")
    task = state.get("task_description", "")
    
    # Log final decision
    blackboard.append(
        agent_id="orchestrator",
        event_type="task_complete",
        data={
            "task": task,
            "final_decision": quorum_decision,
            "total_steps": state.get("step_count", 0) + 1
        }
    )
    
    final_msg = AIMessage(
        content=f"[ORCHESTRATOR] Task complete. Final decision: {quorum_decision}"
    )
    
    return {
        **state,
        "messages": state.get("messages", []) + [final_msg],
        "blackboard": blackboard,
        "step_count": state.get("step_count", 0) + 1
    }


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_multi_agent_graph():
    """
    Create the LangGraph multi-agent workflow with:
    - Manager/Orchestrator pattern
    - Parallel agent dispatch (explore/exploit 8/2)
    - Quorum convergence
    - Stigmergy layer
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("manager", manager_node)
    workflow.add_node("explorers", explorer_agents_node)
    workflow.add_node("exploiters", exploiter_agents_node)
    workflow.add_node("quorum", quorum_convergence_node)
    workflow.add_node("orchestrator", orchestrator_final_node)
    
    # Define edges (workflow flow)
    workflow.set_entry_point("manager")
    workflow.add_edge("manager", "explorers")
    workflow.add_edge("explorers", "exploiters")
    workflow.add_edge("exploiters", "quorum")
    workflow.add_edge("quorum", "orchestrator")
    workflow.add_edge("orchestrator", END)
    
    return workflow.compile()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_multi_agent_system(task_description: str):
    """
    Execute the multi-agent system with a given task
    """
    print("\n" + "="*80)
    print("LANGGRAPH MULTI-AGENT SYSTEM")
    print("Manager/Orchestrator + Parallel Dispatch + Quorum + Stigmergy")
    print("="*80 + "\n")
    
    # Initialize state
    initial_state = {
        "messages": [HumanMessage(content=task_description)],
        "blackboard": StigmergyBlackboard(),
        "task_description": task_description,
        "exploration_results": [],
        "exploitation_results": [],
        "quorum_decision": "",
        "step_count": 0,
        "agent_votes": {}
    }
    
    # Create and run graph
    graph = create_multi_agent_graph()
    
    print(f"📋 Task: {task_description}\n")
    print("🚀 Starting multi-agent workflow...\n")
    
    # Execute graph
    final_state = None
    for step_output in graph.stream(initial_state):
        for node_name, node_state in step_output.items():
            print(f"🔹 Node: {node_name}")
            if "messages" in node_state and node_state["messages"]:
                latest_msg = node_state["messages"][-1]
                print(f"   {latest_msg.content}")
            print()
            final_state = node_state
    
    # Display blackboard
    print("\n" + "="*80)
    print("STIGMERGY BLACKBOARD (Append-Only Agent Coordination Layer)")
    print("="*80 + "\n")
    
    if final_state and "blackboard" in final_state:
        blackboard = final_state["blackboard"]
        for entry in blackboard.entries:
            print(f"[{entry['timestamp']}] {entry['agent_id']} → {entry['event_type']}")
            print(f"  Data: {json.dumps(entry['data'], indent=4)}")
            print()
    
    # Summary
    print("\n" + "="*80)
    print("EXECUTION SUMMARY")
    print("="*80)
    print(f"✅ Task: {task_description}")
    if final_state:
        blackboard = final_state.get('blackboard', StigmergyBlackboard())
        print(f"✅ Final Decision: {final_state.get('quorum_decision', 'N/A')}")
        print(f"✅ Total Steps: {final_state.get('step_count', 0)}")
        print(f"✅ Agents Participated: {len(final_state.get('agent_votes', {}))}")
        print(f"✅ Blackboard Entries: {len(blackboard.entries)}")
    print("="*80 + "\n")
    
    return final_state


if __name__ == "__main__":
    # Test the multi-agent system
    task = "Optimize the deployment pipeline for microservices architecture"
    final_state = run_multi_agent_system(task)
    
    # Export blackboard to file
    if final_state and "blackboard" in final_state:
        blackboard_json = final_state["blackboard"].to_json()
        with open("blackboard/langgraph_test_blackboard.jsonl", "w") as f:
            f.write(blackboard_json)
        print("📝 Blackboard exported to: blackboard/langgraph_test_blackboard.jsonl\n")
