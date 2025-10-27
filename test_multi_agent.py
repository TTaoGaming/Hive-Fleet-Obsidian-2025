"""
Additional test cases for the LangGraph Multi-Agent System
"""

from langgraph_multi_agent_system import run_multi_agent_system

def test_multiple_tasks():
    """Test the system with various task types"""
    
    tasks = [
        "Design a scalable database architecture for real-time analytics",
        "Optimize machine learning model deployment pipeline",
        "Create a security audit framework for cloud infrastructure"
    ]
    
    print("="*80)
    print("LANGGRAPH MULTI-AGENT SYSTEM - MULTIPLE TASK TESTS")
    print("="*80 + "\n")
    
    results = []
    
    for i, task in enumerate(tasks, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}/{len(tasks)}")
        print(f"{'='*80}\n")
        
        final_state = run_multi_agent_system(task)
        
        results.append({
            "task": task,
            "decision": final_state.get("quorum_decision"),
            "agents": len(final_state.get("agent_votes", {})),
            "blackboard_entries": len(final_state.get("blackboard").entries)
        })
        
        print("\n" + "-"*80 + "\n")
    
    # Summary of all tests
    print("\n" + "="*80)
    print("OVERALL TEST SUMMARY")
    print("="*80 + "\n")
    
    for i, result in enumerate(results, 1):
        print(f"Test {i}:")
        print(f"  Task: {result['task']}")
        print(f"  Decision: {result['decision']}")
        print(f"  Agents: {result['agents']}")
        print(f"  Blackboard Entries: {result['blackboard_entries']}")
        print()
    
    print("="*80)
    print(f"✅ All {len(tasks)} tests completed successfully")
    print("="*80 + "\n")


if __name__ == "__main__":
    test_multiple_tasks()
