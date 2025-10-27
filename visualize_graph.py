"""
Visualize the LangGraph multi-agent orchestrator graph structure
"""

from langgraph_multi_agent_orchestrator import build_multi_agent_graph

def visualize_graph():
    """Generate and display the graph visualization"""
    graph = build_multi_agent_graph()
    
    try:
        # Try to generate PNG visualization
        png_data = graph.get_graph().draw_mermaid_png()
        
        with open("orchestrator_graph.png", "wb") as f:
            f.write(png_data)
        
        print("✅ Graph visualization saved to: orchestrator_graph.png")
        
    except Exception as e:
        print(f"Note: Could not generate PNG (this is OK): {e}")
        print("\nGenerating Mermaid diagram instead...")
        
        # Generate Mermaid diagram
        mermaid = graph.get_graph().draw_mermaid()
        
        with open("orchestrator_graph.mmd", "w") as f:
            f.write(mermaid)
        
        print("✅ Mermaid diagram saved to: orchestrator_graph.mmd")
        print("\nMermaid Diagram:")
        print("=" * 80)
        print(mermaid)
        print("=" * 80)

if __name__ == "__main__":
    visualize_graph()
