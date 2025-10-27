"""
Visualization generator for LangGraph Multi-Agent System
"""

def generate_mermaid_diagram():
    """Generate Mermaid diagram for the multi-agent workflow"""
    diagram = """
```mermaid
graph TD
    Start([User Task]) --> Manager[Manager/Orchestrator Node]
    
    Manager -->|Dispatch 8 Agents<br/>80% Explore| Explorers[Explorer Agents<br/>Parallel Execution]
    
    Explorers -->|Results to<br/>Exploiters| Exploiters[Exploiter Agents<br/>2 Agents - 20%]
    
    Explorers -.->|Write Traces| Blackboard[(Stigmergy Blackboard<br/>Append-Only)]
    Exploiters -.->|Write Traces| Blackboard
    
    Blackboard -.->|Read Traces| Exploiters
    Blackboard -.->|Read Traces| Quorum
    
    Exploiters --> Quorum[Quorum Convergence<br/>Vote & Decide]
    
    Quorum -->|Final Decision| Orchestrator[Orchestrator Final<br/>Synthesize Results]
    
    Orchestrator --> End([Task Complete])
    
    style Manager fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style Explorers fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    style Exploiters fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style Quorum fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    style Orchestrator fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    style Blackboard fill:#fff9c4,stroke:#f57f17,stroke-width:3px
```
"""
    return diagram


def generate_architecture_diagram():
    """Generate architecture overview diagram"""
    diagram = """
```mermaid
flowchart TB
    subgraph UserLayer[User Interface Layer]
        Task[Task Input]
    end
    
    subgraph OrchestrationLayer[Orchestration Layer]
        Manager[Manager Node]
        Orchestrator[Orchestrator Node]
    end
    
    subgraph AgentLayer[Agent Execution Layer]
        subgraph ExploreGroup[Explore 80%]
            E1[Explorer 1]
            E2[Explorer 2]
            E3[Explorer 3]
            E4[Explorer 4]
            E5[Explorer 5]
            E6[Explorer 6]
            E7[Explorer 7]
            E8[Explorer 8]
        end
        
        subgraph ExploitGroup[Exploit 20%]
            X1[Exploiter 1]
            X2[Exploiter 2]
        end
    end
    
    subgraph DecisionLayer[Decision Layer]
        Quorum[Quorum/Convergence]
    end
    
    subgraph CoordinationLayer[Coordination Layer - Stigmergy]
        Blackboard[(Append-Only<br/>Blackboard)]
    end
    
    Task --> Manager
    Manager --> ExploreGroup
    ExploreGroup --> ExploitGroup
    
    E1 & E2 & E3 & E4 & E5 & E6 & E7 & E8 -.->|Write Traces| Blackboard
    X1 & X2 -.->|Write Traces| Blackboard
    
    Blackboard -.->|Read Traces| X1
    Blackboard -.->|Read Traces| X2
    Blackboard -.->|Read Traces| Quorum
    
    ExploitGroup --> Quorum
    Quorum --> Orchestrator
    Orchestrator --> Output[Final Decision]
    
    style Manager fill:#e1f5ff
    style Orchestrator fill:#fce4ec
    style ExploreGroup fill:#f3e5f5
    style ExploitGroup fill:#fff3e0
    style Quorum fill:#e8f5e9
    style Blackboard fill:#fff9c4,stroke:#f57f17,stroke-width:3px
```
"""
    return diagram


def generate_stigmergy_pattern():
    """Generate stigmergy pattern diagram"""
    diagram = """
```mermaid
sequenceDiagram
    participant Manager
    participant Explorer1
    participant Explorer2
    participant Blackboard
    participant Exploiter1
    participant Quorum
    
    Manager->>Blackboard: Write: task_received
    Manager->>Blackboard: Write: dispatch_plan
    
    par Parallel Exploration
        Explorer1->>Blackboard: Write: exploration_complete (approach_1)
        Explorer2->>Blackboard: Write: exploration_complete (approach_2)
    end
    
    Blackboard->>Exploiter1: Read: exploration results
    Exploiter1->>Blackboard: Write: exploitation_complete (refined_approach_1)
    
    Blackboard->>Quorum: Read: all agent traces
    Quorum->>Quorum: Tally votes from traces
    Quorum->>Blackboard: Write: decision_made
    
    Note over Blackboard: All entries are append-only<br/>No edits or deletions
```
"""
    return diagram


if __name__ == "__main__":
    print("Workflow Diagram:")
    print(generate_mermaid_diagram())
    print("\n\nArchitecture Diagram:")
    print(generate_architecture_diagram())
    print("\n\nStigmergy Pattern:")
    print(generate_stigmergy_pattern())
