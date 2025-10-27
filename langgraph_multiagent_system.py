#!/usr/bin/env python3
"""
LangGraph Multi-Agent System with Manager-Orchestrator Pattern
Features:
- Parallel agent disperse and converge quorum pattern
- Virtual stigmergy layer (blackboard-based)
- Explore/exploit ratio: 2/8 (20% explore, 80% exploit)
"""

from typing import Annotated, TypedDict, List, Dict, Any, Literal
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import json
import time
import os
from datetime import datetime, timezone
import duckdb
import threading

# ============================================================================
# VIRTUAL STIGMERGY LAYER (Blackboard)
# ============================================================================

class VirtualStigmergy:
    """
    Virtual stigmergy layer for agent communication and coordination.
    Uses append-only blackboard pattern with DuckDB for persistence.
    """
    
    def __init__(self, blackboard_dir: str = "./blackboard"):
        self.blackboard_dir = blackboard_dir
        self.jsonl_path = os.path.join(blackboard_dir, "obsidian_synapse_blackboard.jsonl")
        self.db_path = os.path.join(blackboard_dir, "obsidian_synapse_blackboard.duckdb")
        self.lock = threading.Lock()  # Thread safety for concurrent access
        self.ensure_blackboard_exists()
    
    def ensure_blackboard_exists(self):
        """Ensure blackboard files exist"""
        if not os.path.exists(self.blackboard_dir):
            os.makedirs(self.blackboard_dir)
        
        # Ensure JSONL exists
        if not os.path.exists(self.jsonl_path):
            open(self.jsonl_path, 'a').close()
        
        # Ensure DuckDB exists with schema
        if not os.path.exists(self.db_path):
            conn = duckdb.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    timestamp TEXT,
                    event TEXT,
                    role TEXT,
                    summary TEXT,
                    artifacts TEXT
                )
            """)
            conn.close()
    
    def deposit_pheromone(self, role: str, event: str, summary: str, artifacts: Dict[str, Any] = None):
        """
        Deposit a pheromone (message) to the stigmergy layer.
        Append-only - never modifies existing data.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = {
            "timestamp": timestamp,
            "event": event,
            "role": role,
            "summary": summary,
            "artifacts": artifacts or {}
        }
        
        with self.lock:  # Thread-safe access
            # Write to JSONL (append-only)
            with open(self.jsonl_path, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            
            # Write to DuckDB (INSERT only) - use fresh connection each time
            conn = duckdb.connect(self.db_path)
            try:
                conn.execute("""
                    INSERT INTO events (timestamp, event, role, summary, artifacts)
                    VALUES (?, ?, ?, ?, ?)
                """, [timestamp, event, role, summary, json.dumps(artifacts or {})])
            finally:
                conn.close()
        
        return entry
    
    def sense_pheromones(self, event_type: str = None, limit: int = 10) -> List[Dict]:
        """
        Sense recent pheromones from the stigmergy layer.
        Used by agents to read shared state.
        """
        with self.lock:  # Thread-safe access
            conn = duckdb.connect(self.db_path)
            try:
                if event_type:
                    query = """
                        SELECT timestamp, event, role, summary, artifacts 
                        FROM events 
                        WHERE event = ?
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    """
                    results = conn.execute(query, [event_type, limit]).fetchall()
                else:
                    query = """
                        SELECT timestamp, event, role, summary, artifacts 
                        FROM events 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    """
                    results = conn.execute(query, [limit]).fetchall()
            finally:
                conn.close()
            
            pheromones = []
            for row in results:
                pheromones.append({
                    "timestamp": row[0],
                    "event": row[1],
                    "role": row[2],
                    "summary": row[3],
                    "artifacts": json.loads(row[4]) if row[4] else {}
                })
            
            return pheromones


# ============================================================================
# STATE DEFINITION
# ============================================================================

class AgentState(TypedDict):
    """Shared state for multi-agent coordination"""
    messages: Annotated[list[BaseMessage], add_messages]
    task: str
    agent_results: Dict[str, Any]
    quorum_votes: List[Dict[str, Any]]
    final_decision: str
    explore_results: List[str]
    exploit_results: List[str]
    iteration: int


# ============================================================================
# AGENT DEFINITIONS
# ============================================================================

class Agent:
    """Base agent with stigmergy integration"""
    
    def __init__(self, name: str, role: str, stigmergy: VirtualStigmergy):
        self.name = name
        self.role = role
        self.stigmergy = stigmergy
    
    def log_action(self, event: str, summary: str, artifacts: Dict = None):
        """Log action to stigmergy layer"""
        return self.stigmergy.deposit_pheromone(
            role=f"{self.role}:{self.name}",
            event=event,
            summary=summary,
            artifacts=artifacts
        )
    
    def sense_context(self, event_type: str = None) -> List[Dict]:
        """Sense recent context from stigmergy"""
        return self.stigmergy.sense_pheromones(event_type=event_type, limit=5)


class ExplorerAgent(Agent):
    """Explorer agent - discovers new approaches (20% of fleet)"""
    
    def explore(self, task: str) -> Dict[str, Any]:
        """Explore new solution approaches"""
        self.log_action("explore", f"Exploring novel approaches for: {task}")
        
        # Simulate exploration - in production, this would use LLM
        approaches = [
            f"Novel approach A for {task}",
            f"Experimental method B for {task}",
            f"Untested strategy C for {task}"
        ]
        
        result = {
            "agent": self.name,
            "type": "explore",
            "approaches": approaches,
            "confidence": 0.6,  # Explorers have lower initial confidence
            "innovation_score": 0.8
        }
        
        self.log_action(
            "explore_complete",
            f"Generated {len(approaches)} novel approaches",
            result
        )
        
        return result


class ExploiterAgent(Agent):
    """Exploiter agent - optimizes known solutions (80% of fleet)"""
    
    def exploit(self, task: str) -> Dict[str, Any]:
        """Exploit and optimize known approaches"""
        self.log_action("exploit", f"Optimizing proven approaches for: {task}")
        
        # Sense what explorers found
        context = self.sense_context("explore_complete")
        
        # Simulate exploitation - in production, this would use LLM
        optimizations = [
            f"Optimized solution 1 for {task}",
            f"Refined approach 2 for {task}",
            f"Battle-tested method 3 for {task}"
        ]
        
        result = {
            "agent": self.name,
            "type": "exploit",
            "solutions": optimizations,
            "confidence": 0.9,  # Exploiters have higher confidence
            "efficiency_score": 0.85,
            "context_used": len(context)
        }
        
        self.log_action(
            "exploit_complete",
            f"Generated {len(optimizations)} optimized solutions",
            result
        )
        
        return result


class ManagerAgent(Agent):
    """Manager agent - coordinates and orchestrates the fleet"""
    
    def decompose_task(self, task: str) -> Dict[str, Any]:
        """Decompose task and assign to agent fleet"""
        self.log_action("decompose", f"Decomposing task: {task}")
        
        decomposition = {
            "original_task": task,
            "subtasks": [
                "Explore novel approaches",
                "Optimize known patterns",
                "Validate solutions",
                "Converge to consensus"
            ],
            "agent_allocation": {
                "explorers": 2,  # 20% explore
                "exploiters": 8  # 80% exploit
            }
        }
        
        self.log_action(
            "decompose_complete",
            "Task decomposed and agents allocated",
            decomposition
        )
        
        return decomposition
    
    def orchestrate_quorum(self, results: List[Dict]) -> Dict[str, Any]:
        """Orchestrate quorum consensus from agent results"""
        self.log_action("quorum_start", f"Starting quorum with {len(results)} results")
        
        # Weight votes by confidence and type
        votes = []
        for result in results:
            weight = result.get("confidence", 0.5)
            if result.get("type") == "exploit":
                weight *= 1.2  # Favor exploitation (80/20 rule)
            
            votes.append({
                "agent": result.get("agent"),
                "type": result.get("type"),
                "weight": weight,
                "content": result
            })
        
        # Sort by weight and select top consensus
        votes.sort(key=lambda x: x["weight"], reverse=True)
        
        quorum_result = {
            "total_votes": len(votes),
            "top_choices": votes[:3],
            "consensus_weight": sum(v["weight"] for v in votes[:3]) / len(votes) if votes else 0,
            "explore_count": sum(1 for v in votes if v["type"] == "explore"),
            "exploit_count": sum(1 for v in votes if v["type"] == "exploit")
        }
        
        self.log_action(
            "quorum_complete",
            f"Quorum reached with {quorum_result['total_votes']} votes",
            quorum_result
        )
        
        return quorum_result


# ============================================================================
# GRAPH NODE FUNCTIONS
# ============================================================================

# Global stigmergy instance
stigmergy = VirtualStigmergy()

# Create manager
manager = ManagerAgent("ManagerAlpha", "manager", stigmergy)

# Create agent fleet: 2 explorers (20%), 8 exploiters (80%)
explorers = [
    ExplorerAgent(f"Explorer{i}", "explorer", stigmergy) 
    for i in range(1, 3)  # 2 explorers
]

exploiters = [
    ExploiterAgent(f"Exploiter{i}", "exploiter", stigmergy)
    for i in range(1, 9)  # 8 exploiters
]


def manager_decompose_node(state: AgentState) -> AgentState:
    """Manager decomposes the task"""
    task = state["task"]
    decomposition = manager.decompose_task(task)
    
    return {
        "messages": [AIMessage(content=f"Task decomposed: {decomposition['subtasks']}")],
        "agent_results": {"decomposition": decomposition},
        "iteration": state.get("iteration", 0)
    }


def parallel_explore_node(state: AgentState) -> AgentState:
    """Parallel exploration by explorer agents (20%)"""
    task = state["task"]
    results = []
    
    # All explorers work in parallel (simulated sequentially here)
    for explorer in explorers:
        result = explorer.explore(task)
        results.append(result)
    
    # Store in separate key to avoid concurrent write conflict
    return {
        "explore_results": [r["approaches"][0] for r in results],
        "messages": [AIMessage(content=f"Exploration complete: {len(results)} results")]
    }


def parallel_exploit_node(state: AgentState) -> AgentState:
    """Parallel exploitation by exploiter agents (80%)"""
    task = state["task"]
    results = []
    
    # All exploiters work in parallel (simulated sequentially here)
    for exploiter in exploiters:
        result = exploiter.exploit(task)
        results.append(result)
    
    # Store in separate key to avoid concurrent write conflict
    return {
        "exploit_results": [r["solutions"][0] for r in results],
        "messages": [AIMessage(content=f"Exploitation complete: {len(results)} results")]
    }


def converge_quorum_node(state: AgentState) -> AgentState:
    """Converge results via quorum consensus"""
    all_results = []
    
    # Gather results from stigmergy (indirect communication)
    # Explorers and exploiters have logged their results to the blackboard
    explore_events = stigmergy.sense_pheromones(event_type="explore_complete", limit=10)
    exploit_events = stigmergy.sense_pheromones(event_type="exploit_complete", limit=20)
    
    # Convert events to results format
    for event in explore_events:
        all_results.append(event.get("artifacts", {}))
    for event in exploit_events:
        all_results.append(event.get("artifacts", {}))
    
    # Manager orchestrates quorum
    quorum = manager.orchestrate_quorum(all_results)
    
    # Extract final decision
    top_choice = quorum["top_choices"][0] if quorum["top_choices"] else None
    decision = f"Consensus: {top_choice['type']} approach from {top_choice['agent']}" if top_choice else "No consensus"
    
    return {
        "quorum_votes": quorum["top_choices"],
        "final_decision": decision,
        "messages": [AIMessage(content=f"Quorum complete: {decision}")]
    }


def report_node(state: AgentState) -> AgentState:
    """Generate final report"""
    report = {
        "task": state["task"],
        "final_decision": state.get("final_decision", "No decision"),
        "explore_results_count": len(state.get("explore_results", [])),
        "exploit_results_count": len(state.get("exploit_results", [])),
        "quorum_votes": len(state.get("quorum_votes", [])),
        "stigmergy_events": len(stigmergy.sense_pheromones(limit=100))
    }
    
    manager.log_action("report", "Final report generated", report)
    
    return {
        "messages": [AIMessage(content=f"Report: {json.dumps(report, indent=2)}")]
    }


# ============================================================================
# BUILD GRAPH
# ============================================================================

def build_multiagent_graph() -> StateGraph:
    """Build the multi-agent coordination graph"""
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("manager_decompose", manager_decompose_node)
    workflow.add_node("parallel_explore", parallel_explore_node)
    workflow.add_node("parallel_exploit", parallel_exploit_node)
    workflow.add_node("converge_quorum", converge_quorum_node)
    workflow.add_node("report", report_node)
    
    # Define flow
    workflow.set_entry_point("manager_decompose")
    
    # Manager decomposes, then parallel disperse
    workflow.add_edge("manager_decompose", "parallel_explore")
    workflow.add_edge("manager_decompose", "parallel_exploit")
    
    # Both exploration and exploitation converge to quorum
    workflow.add_edge("parallel_explore", "converge_quorum")
    workflow.add_edge("parallel_exploit", "converge_quorum")
    
    # Quorum leads to report
    workflow.add_edge("converge_quorum", "report")
    
    # Report ends
    workflow.add_edge("report", END)
    
    return workflow.compile()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_multiagent_system(task: str):
    """Run the multi-agent system on a task"""
    
    print(f"\n{'='*80}")
    print(f"MULTI-AGENT SYSTEM EXECUTION")
    print(f"{'='*80}")
    print(f"Task: {task}")
    print(f"Fleet: 2 explorers (20%), 8 exploiters (80%)")
    print(f"Pattern: Disperse → Parallel Execute → Converge Quorum")
    print(f"{'='*80}\n")
    
    # Build graph
    graph = build_multiagent_graph()
    
    # Initial state
    initial_state = {
        "messages": [HumanMessage(content=task)],
        "task": task,
        "agent_results": {},
        "quorum_votes": [],
        "final_decision": "",
        "explore_results": [],
        "exploit_results": [],
        "iteration": 0
    }
    
    # Execute
    print("Executing multi-agent workflow...\n")
    
    for i, step in enumerate(graph.stream(initial_state), 1):
        node_name = list(step.keys())[0]
        print(f"Step {i}: {node_name}")
        
        # Print any messages
        if "messages" in step[node_name]:
            for msg in step[node_name]["messages"]:
                if hasattr(msg, 'content'):
                    print(f"  → {msg.content}")
        print()
    
    print(f"\n{'='*80}")
    print(f"EXECUTION COMPLETE")
    print(f"{'='*80}\n")
    
    # Show stigmergy layer state
    print("Stigmergy Layer Events (last 10):")
    events = stigmergy.sense_pheromones(limit=10)
    for event in reversed(events):
        print(f"  [{event['timestamp']}] {event['role']}: {event['summary']}")
    
    return graph


if __name__ == "__main__":
    # Run the multi-agent system
    task = "Develop a distributed caching strategy for high-performance web application"
    graph = run_multiagent_system(task)
    
    print("\n✓ Multi-agent system executed successfully!")
    print("✓ Virtual stigmergy layer active")
    print("✓ Explore/exploit ratio: 2/8 (20%/80%)")
    print("✓ Quorum consensus achieved")
