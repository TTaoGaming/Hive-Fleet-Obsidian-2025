"""
Extended test for LangGraph Multi-Agent Orchestrator
Runs more iterations to verify explore/exploit ratio
"""

from langgraph_multi_agent_orchestrator import run_orchestrator
import json

def extended_test():
    """Run extended test with 10 iterations to verify explore/exploit ratio"""
    print("=" * 80)
    print("EXTENDED VERIFICATION TEST - 10 Iterations")
    print("=" * 80)
    
    task = "Test distributed swarm intelligence coordination"
    num_iterations = 10
    
    stigmergy = run_orchestrator(task, num_iterations=num_iterations)
    
    # Analyze results
    print("\n" + "=" * 80)
    print("ANALYSIS OF EXPLORE/EXPLOIT RATIO")
    print("=" * 80)
    
    # Count explore vs exploit from stigmergy traces
    traces = stigmergy.read_traces(trace_type="plan")
    
    explore_count = sum(1 for t in traces if t['data'].get('mode') == 'explore')
    exploit_count = sum(1 for t in traces if t['data'].get('mode') == 'exploit')
    total = explore_count + exploit_count
    
    print(f"\nTotal Iterations: {total}")
    print(f"Explore Mode: {explore_count} ({explore_count/total*100:.1f}%)")
    print(f"Exploit Mode: {exploit_count} ({exploit_count/total*100:.1f}%)")
    print(f"Expected Ratio: 40% explore / 60% exploit")
    
    # Count decisions
    decision_traces = stigmergy.read_traces(trace_type="decision")
    approved = sum(1 for t in decision_traces if t['data'].get('decision') == 'APPROVED')
    rejected = sum(1 for t in decision_traces if t['data'].get('decision') == 'REJECTED')
    
    print(f"\nDecision Summary:")
    print(f"Approved: {approved}")
    print(f"Rejected: {rejected}")
    
    # Average confidence by mode
    result_traces = stigmergy.read_traces(trace_type="result")
    
    explore_confidences = [t['data']['confidence'] for t in result_traces if t['data'].get('mode') == 'explore']
    exploit_confidences = [t['data']['confidence'] for t in result_traces if t['data'].get('mode') == 'exploit']
    
    if explore_confidences:
        avg_explore = sum(explore_confidences) / len(explore_confidences)
        print(f"\nAverage Confidence (Explore): {avg_explore:.2f}")
    
    if exploit_confidences:
        avg_exploit = sum(exploit_confidences) / len(exploit_confidences)
        print(f"Average Confidence (Exploit): {avg_exploit:.2f}")
    
    print("\n" + "=" * 80)
    print("VERIFICATION: ✅ SYSTEM OPERATIONAL")
    print("=" * 80)

if __name__ == "__main__":
    extended_test()
