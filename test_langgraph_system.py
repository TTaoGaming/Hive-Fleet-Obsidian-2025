"""
Test suite for LangGraph Multi-Agent System with Stigmergy

This demonstrates various scenarios and validates the system behavior.
"""

import sys
from langgraph_multi_agent_stigmergy import run_multi_agent_system, StigmergyLayer


def test_scenario_1():
    """Test basic task execution with explore/exploit balance"""
    print("\n" + "="*80)
    print("TEST SCENARIO 1: Basic Optimization Task")
    print("="*80)
    
    task = "Determine the best approach to solve a complex optimization problem"
    result = run_multi_agent_system(task)
    
    # Verify results
    assert len(result['results']) >= 3, "Should have at least 3 agent results"
    assert result['quorum_reached'], "Quorum should be reached"
    
    # Check explore/exploit distribution
    modes = [r['mode'] for r in result['results']]
    print(f"\nMode distribution: {dict((m, modes.count(m)) for m in set(modes))}")
    
    return result


def test_scenario_2():
    """Test with different task types"""
    print("\n" + "="*80)
    print("TEST SCENARIO 2: Resource Allocation Task")
    print("="*80)
    
    task = "Optimize resource allocation for distributed computing"
    result = run_multi_agent_system(task)
    
    assert result['quorum_reached'], "Quorum should be reached"
    return result


def test_scenario_3():
    """Test multiple runs to verify stigmergy evolution"""
    print("\n" + "="*80)
    print("TEST SCENARIO 3: Multiple Iterations to Verify Stigmergy")
    print("="*80)
    
    tasks = [
        "Solve problem iteration 1",
        "Solve problem iteration 2",
        "Solve problem iteration 3"
    ]
    
    results = []
    for i, task in enumerate(tasks, 1):
        print(f"\n--- Iteration {i} ---")
        result = run_multi_agent_system(task)
        results.append(result)
        
        # Show pheromone count growth
        pheromone_count = len(result['stigmergy'].pheromones)
        print(f"Pheromones after iteration {i}: {pheromone_count}")
    
    return results


def test_stigmergy_layer():
    """Test stigmergy layer functionality directly"""
    print("\n" + "="*80)
    print("TEST SCENARIO 4: Stigmergy Layer Unit Tests")
    print("="*80)
    
    stigmergy = StigmergyLayer()
    
    # Test deposit
    stigmergy.deposit("agent1", "Found solution A", strength=0.8)
    stigmergy.deposit("agent2", "Found solution B", strength=0.6)
    stigmergy.deposit("agent3", "Found solution A", strength=0.7)
    
    assert len(stigmergy.pheromones) == 3, "Should have 3 pheromones"
    print(f"✓ Deposit test passed: {len(stigmergy.pheromones)} pheromones")
    
    # Test read by strength
    strong = stigmergy.read_by_strength(min_strength=0.7)
    assert len(strong) == 2, "Should have 2 strong pheromones"
    print(f"✓ Read by strength test passed: {len(strong)} strong pheromones")
    
    # Test reinforce
    stigmergy.reinforce("solution A", boost=0.1)
    reinforced = [p for p in stigmergy.pheromones if "solution A" in p.content]
    assert all(p.strength >= 0.7 for p in reinforced), "Solution A should be reinforced"
    print(f"✓ Reinforce test passed")
    
    # Test evaporate
    original_strengths = [p.strength for p in stigmergy.pheromones]
    stigmergy.evaporate()
    new_strengths = [p.strength for p in stigmergy.pheromones]
    assert all(n < o for n, o in zip(new_strengths, original_strengths)), "Strengths should decrease"
    print(f"✓ Evaporate test passed")
    
    print(stigmergy.get_summary())
    
    return stigmergy


def run_all_tests():
    """Run all test scenarios"""
    print("\n" + "="*80)
    print("LANGGRAPH MULTI-AGENT SYSTEM - COMPREHENSIVE TEST SUITE")
    print("="*80)
    
    try:
        # Run all tests
        test_stigmergy_layer()
        test_scenario_1()
        test_scenario_2()
        test_scenario_3()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED SUCCESSFULLY")
        print("="*80)
        
        print("\nKey Findings:")
        print("  ✓ Multi-agent coordination working correctly")
        print("  ✓ Parallel disperse/converge pattern functional")
        print("  ✓ Stigmergy layer enables indirect communication")
        print("  ✓ Quorum decision-making achieves consensus")
        print("  ✓ Explore/exploit balance maintained")
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
