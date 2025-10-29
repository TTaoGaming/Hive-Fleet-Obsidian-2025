# Swarmlord-Swimlane-Vision

## BLUF
Swarmlord facade parses user intent, enforces C2 YAML (3x clarification if unclear), triggers internal PREY loop (Perceive-React-Engage-Yield) for tool-preferring adaptation, ensuring resilience via stigmergy blackboard, OBSID roles, triad reflexion, red/blue forks. Yield synthesizes BLUF-matrix-diagram for user if pass; internal retry on fail. Ongoing chat loop. Grounded in GEM 19 lvl1/v11: stigmergy blackboard state, OBSID/triad flows, red/blue forks, zero-invention biology/neuro (ant trails, Hebbian reflexion, wolf pack).

## Swimlane Sequence
```mermaid
sequenceDiagram
    participant U as User
    participant F as Swarmlord
    participant P as Perceive
    participant R as React
    participant E as Engage
    participant Y as Yield
    participant B as Blackboard
    U-->F: Input
    F-->P: Parse intent
    P-->B: Sense state (blackboard/tools)
    B-->R: State data
    alt [C2 ready (PREY trigger)]
        R-->E: Cynefin classify then Delegate + CoT Reflexion + red/blue forks
        E-->Y: Act/execute
        Y-.->Y: Verify (90% gates)/retry if fail
        Y-->B: blackboard append
        Y-->F: Synth BLUF-matrix-diagram (if pass)
    else [No C2 (further clarification)]
        R-->F: 3x clarify then C2 YAML enforced
    end
    F-->U: Response (facade/hidden PREY)
    U-->F: Ongoing loop
    Note over F,Y,B: Facade user-only; PREY internal hidden; tool-preferring; OBSID guards (8 roles); triad flows; biology: ant stigmergy, Hebbian reflexion, wolf coordination.
```

## Cynefin Table
| Domain    | Mnemonic          | Approach             | Precedents                  |
|-----------|-------------------|----------------------|-----------------------------|
| Clear     | Simple CBR/tools  | Sense-Categorize-Respond | Ant trails (stigmergy)     |
| Complicated | Searches/thinking | Sense-Analyze-Respond   | Neural searches (Hebbian)  |
| Complex   | Canary/probe      | Probe-Sense-Respond    | Wolf pack coordination     |
| Chaotic   | Act-now           | Act-Sense-Respond      | Emergency neural firing    |
| Disorder  | Confused (5+ clarifies) | Break into known domains | Reflexion scars (Hebbian) |

## Integration
v11 overmind facade: GEM19 stigmergy (blackboard JSONL append-only/TTL), OBSID roles (Observers perceive, Bridgers connect, Shapers form, Immunizers verify, Disruptors critique, Injectors project, Assimilators reflect, Navigators guide), triad reflexion (Past: assimilate yield; Present: immunize adapt; Future: inject mutate), red/blue forks (debug/architect) in Engage for zero-invention biology/neuro.

## Variants
- PREY focus: Internal OODA+feedback loops hidden; tool/execute_command/PettingZoo preference.
- Future meta: HIVE/SWARM for multi-mission (meta-loops oversight + overmind 12:1 sim).

## Principles Matrix
| Principle       | Description |
|-----------------|-------------|
| Upstream C2     | Intent parsing → 3x clarification → YAML enforcement before PREY |
| Verify Yield    | Zero-trust gates (read_file/write_to_file integrity, hallucination checks); retry + Hebbian scar if fail |
| Delegate Engage | new_task decomposition + red/blue forks + CoT reflexion; OBSID guards |
| Reflex React    | Cynefin classify + triad flows for adaptation |
| State blackboard| Stigmergy JSONL (plasticity scores, TTL); lvl1 pod emu |
| Shape response  | BLUF + matrix + 1-3 diagrams + PREY CoT + Adaptations; <300 tokens |
| Triad flows     | Past (Assimilator reflection), Present (Immunizers verify), Future (Injector projection) |