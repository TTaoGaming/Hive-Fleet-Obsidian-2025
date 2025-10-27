#!/usr/bin/env python3
"""
Simple test runner for the LangGraph multi-agent system.
This demonstrates the system with different tasks.
"""

from langgraph_multiagent_system import run_multiagent_system, stigmergy

def test_scenario(task_description: str, scenario_name: str):
    """Run a test scenario"""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'='*80}\n")
    
    run_multiagent_system(task_description)
    
    print(f"\n{'='*80}")
    print(f"SCENARIO COMPLETE: {scenario_name}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║         LangGraph Multi-Agent System Test Suite                         ║
    ║                                                                          ║
    ║  Pattern: Manager-Orchestrator + Parallel Disperse-Converge             ║
    ║  Fleet: 2 Explorers (20%) + 8 Exploiters (80%)                          ║
    ║  Coordination: Virtual Stigmergy (Blackboard)                            ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Test Scenario 1: Caching Strategy
    test_scenario(
        "Develop a distributed caching strategy for high-performance web application",
        "Distributed Caching"
    )
    
    # Test Scenario 2: API Design
    test_scenario(
        "Design a RESTful API architecture for a microservices platform",
        "API Architecture"
    )
    
    # Final stigmergy analysis
    print("\n" + "="*80)
    print("STIGMERGY LAYER ANALYSIS")
    print("="*80)
    
    all_events = stigmergy.sense_pheromones(limit=100)
    
    print(f"\nTotal Events Logged: {len(all_events)}")
    
    # Count by event type
    event_counts = {}
    for event in all_events:
        event_type = event['event']
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
    
    print("\nEvent Distribution:")
    for event_type, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {event_type:20s}: {count:3d}")
    
    # Count by role
    role_counts = {}
    for event in all_events:
        role = event['role'].split(':')[0]
        role_counts[role] = role_counts.get(role, 0) + 1
    
    print("\nAgent Activity:")
    for role, count in sorted(role_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {role:20s}: {count:3d}")
    
    print("\n" + "="*80)
    print("✅ All tests completed successfully!")
    print("="*80)
