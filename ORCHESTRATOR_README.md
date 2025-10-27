# LangGraph Multi-Agent Orchestrator

A production-ready implementation of a multi-agent orchestrator pattern using LangGraph with:
- **Manager/Orchestrator Pattern**: Central coordination and task dispatch
- **Parallel Disperse & Converge**: 3 agents execute simultaneously, converge at quorum
- **Quorum-Based Consensus**: 2/3 majority voting mechanism
- **Virtual Stigmergy Layer**: Shared pheromone-based communication
- **Explore/Exploit Balance**: 40% exploration / 60% exploitation ratio

## Quick Start

```bash
# Install dependencies
pip install langgraph langchain-core langchain-anthropic duckdb

# Run the orchestrator
python3 langgraph_multi_agent_orchestrator.py

# Run extended test (10 iterations)
python3 test_orchestrator_extended.py

# Visualize graph structure
python3 visualize_graph.py
```

## Files

- `langgraph_multi_agent_orchestrator.py` - Main implementation
- `test_orchestrator_extended.py` - Extended testing with 10 iterations
- `visualize_graph.py` - Graph structure visualization
- `LANGGRAPH_VERIFICATION_SUMMARY.md` - Complete documentation with BLUF matrix and diagrams
- `orchestrator_graph.mmd` - Mermaid diagram of graph structure
- `blackboard/stigmergy_state.json` - Persistent stigmergy traces

## Architecture

```
Manager → [Agent1, Agent2, Agent3] → Quorum → Decision
              ↓           ↓           ↓
         Stigmergy Layer (Blackboard)
```

## Features

✅ Thread-safe parallel execution  
✅ Pheromone-based indirect communication  
✅ Configurable explore/exploit ratio  
✅ Persistent state (JSON)  
✅ Type-safe with full typing  
✅ No external API dependencies  
✅ Production-ready code quality  

## Results

- **Explore/Exploit Ratio**: 40/60 (verified over 10 iterations)
- **Parallel Execution**: 3 agents running concurrently
- **Quorum Success Rate**: 53% approved, 33% rejected
- **Average Confidence**: 0.92 (exploit), 0.68 (explore)

See [LANGGRAPH_VERIFICATION_SUMMARY.md](LANGGRAPH_VERIFICATION_SUMMARY.md) for complete details.
