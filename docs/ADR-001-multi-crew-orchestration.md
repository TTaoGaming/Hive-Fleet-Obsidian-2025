# ADR-001: Multi-Crew Parallel Orchestration with CrewAI

**Status**: Accepted with revisions needed  
**Date**: 2025-10-30  
**Deciders**: System Architect, Implementation Team  
**Audited By**: Code Review

## Context

We need a parallel multi-agent orchestration system for Hive Fleet Obsidian that implements:
- Disperse-converge pattern for distributed problem solving
- Quorum-based verification (2 of 3 validators)
- Stigmergy via blackboard JSONL
- 8/2 explore/exploit ratio for quality diversity
- Safety envelope with auto-retry

## Decision

We will use **CrewAI** (v1.2.1) as the multi-agent orchestration framework with custom parallel execution via ThreadPoolExecutor.

## Rationale

### Why CrewAI?

**Advantages:**
1. ✅ **Agent Framework**: Built-in Agent, Task, and Crew abstractions
2. ✅ **LLM Integration**: Native support for OpenAI, Anthropic, and others
3. ✅ **Process Types**: Sequential, Hierarchical, and Consensus modes
4. ✅ **Active Development**: Regular updates and community support
5. ✅ **Pythonic API**: Clean, dataclass-based configuration

**Alternatives Considered:**
- **LangGraph**: More complex, overkill for current needs, migration path available
- **AutoGen**: Less mature, different paradigm (conversational)
- **Custom Framework**: Too much overhead, reinventing wheel

### Architecture Decisions

#### 1. Parallel Execution Strategy

**Decision**: Use ThreadPoolExecutor for parallel crew execution  
**Rationale**: 
- CrewAI doesn't natively support parallel crews
- ThreadPoolExecutor provides clean, Python-native parallelism
- Each crew instance is independent (no shared state issues)
- Allows configurable concurrency limits

**Code Pattern**:
```python
with ThreadPoolExecutor(max_workers=parallel_lanes) as executor:
    futures = {executor.submit(run_prey_lane, lane_id): lane_id}
    for future in as_completed(futures):
        results.append(future.result())
```

#### 2. Agent Configuration

**Decision**: Use Sequential process with non-delegating agents  
**Rationale**:
- PREY workflow (Perceive → React → Engage → Yield) is inherently sequential
- Delegation adds complexity without benefit in sequential mode
- Each phase has specific responsibilities

**Agent Pattern**:
```python
Agent(
    role="Perceiver",
    goal="Sense context",
    backstory="Strategic sensor",
    allow_delegation=False,  # Critical for sequential
    verbose=configurable      # Should be environment-driven
)
```

#### 3. Memory and State Management

**Decision**: External stigmergy via blackboard JSONL  
**Rationale**:
- CrewAI's built-in memory is per-crew, not persistent
- Blackboard provides audit trail and cross-lane coordination
- JSONL format is append-only, conflict-free
- Aligns with existing HFO infrastructure

**Pattern**:
```python
append_receipt(
    mission_id=mission_id,
    phase="engage",
    evidence_refs=["file:line", "metric:value"],
    safety_envelope={"chunk_size_max": 200}
)
```

#### 4. Verification Quorum

**Decision**: Independent validator agents with 2/3 threshold  
**Rationale**:
- Prevents single point of failure
- Adversarial (Disruptor) prevents persistent green
- Immunizer checks consistency and grounding
- Verifier_Aux provides safety net

## Audit Findings

### ✅ Strengths

1. **Correct Parallel Pattern**: ThreadPoolExecutor is industry best practice
2. **Sequential Process**: Appropriate for PREY workflow
3. **External Memory**: Blackboard JSONL avoids CrewAI memory pitfalls
4. **Error Handling**: Try-except with structured LaneResult
5. **Task Design**: Clear descriptions and expected outputs
6. **No Delegation**: Correctly disabled for sequential process

### ❌ Critical Issues Found

1. **Agent Initialization Requires API Key**
   - **Issue**: Agents instantiate LLM immediately, even for testing
   - **Impact**: Cannot run tests or demos without API key
   - **Fix**: Add LLM parameter with optional mock/fallback
   
2. **No LLM Configuration**
   - **Issue**: No explicit LLM settings (model, temperature, timeout)
   - **Impact**: Using defaults, no control over behavior
   - **Fix**: Add LLM configuration to MissionConfig

3. **No API Key Validation**
   - **Issue**: Fails late with cryptic error
   - **Impact**: Poor user experience
   - **Fix**: Validate API key early with clear message

### ⚠️ Warnings

1. **Verbose Hardcoded**: Should be environment-configurable
2. **No Timeout Config**: LLM calls could hang indefinitely
3. **No Rate Limiting**: Could hit API limits in parallel execution

### 📋 Recommendations

#### Immediate Fixes (Critical)

1. **Add LLM Parameter to Agents**
   ```python
   from crewai import LLM
   
   # In create_prey_agents:
   llm = LLM(
       model=os.getenv("HFO_LLM_MODEL", "gpt-4"),
       temperature=float(os.getenv("HFO_LLM_TEMPERATURE", "0.7")),
       timeout=int(os.getenv("HFO_LLM_TIMEOUT", "60"))
   ) if os.getenv("OPENAI_API_KEY") else None
   
   Agent(..., llm=llm)
   ```

2. **API Key Validation**
   ```python
   def validate_api_key(self) -> bool:
       if not os.getenv("OPENAI_API_KEY"):
           raise ValueError(
               "OPENAI_API_KEY required. Set in .env or environment."
           )
       return True
   ```

3. **Make Verbose Configurable**
   ```python
   verbose = os.getenv("HFO_AGENT_VERBOSE", "false").lower() == "true"
   ```

#### Short-term Improvements

1. Add retry logic for LLM calls
2. Add rate limiting between parallel lanes
3. Add memory size limits for long-running crews
4. Add telemetry for LLM token usage

#### Long-term Considerations

1. **Migration to LangGraph**: For more complex workflows
2. **Custom Tools**: Add domain-specific tools to agents
3. **Feedback Loops**: Use verification results to improve plans
4. **Adaptive Concurrency**: Adjust lanes based on performance

## Testing Strategy

### Unit Tests
- ✅ Demo mode works (no API calls)
- ✅ Configuration loads correctly
- ✅ Blackboard logging functional
- ❌ Agent creation fails without API key (needs fix)

### Integration Tests
- ⏳ End-to-end with mock LLM (after fixes)
- ⏳ Parallel lane execution
- ⏳ Quorum verification logic

### Production Validation
- ⏳ Real LLM calls with API key
- ⏳ Error recovery and retry
- ⏳ Blackboard audit trail

## Compliance Check

### CrewAI Best Practices

| Practice | Status | Notes |
|----------|--------|-------|
| Explicit LLM config | ❌ | Needs addition |
| Task expected_output | ✅ | All tasks have it |
| No delegation in sequential | ✅ | Correctly set to False |
| Environment-based config | ✅ | Using .env |
| Error handling | ✅ | Try-except blocks |
| Parallel execution | ✅ | ThreadPoolExecutor |
| Memory management | ✅ | External blackboard |

### HFO Mission Intent v5 Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Sole human interface (Swarmlord) | ✅ | SwarmlordOrchestrator facade |
| Zero mid-loop prompts | ✅ | Fully autonomous |
| PREY workflow | ✅ | Perceive→React→Engage→Yield |
| Quorum verification (2/3) | ✅ | 3 validators, threshold=2 |
| Stigmergy via blackboard | ✅ | JSONL receipts |
| 8/2 explore/exploit | ✅ | Configurable ratio |
| Safety envelope | ✅ | Chunk limits, tripwires |
| Auto-retry (max 3) | ✅ | Retry loop implemented |
| Evidence-based receipts | ✅ | All operations logged |

### AGENTS.md Protocol Compliance

| Rule | Status | Notes |
|------|--------|-------|
| PREY canonical loop | ✅ | Exact terminology used |
| Blackboard append-only | ✅ | Using append_receipt |
| Evidence refs required | ✅ | All receipts include refs |
| Safety envelope enforced | ✅ | Chunk limits checked |
| No placeholders | ✅ | Real implementations |
| Canary-first | ⚠️ | Could be more explicit |

## Consequences

### Positive

1. ✅ **Industry-standard framework**: Using CrewAI aligns with community practices
2. ✅ **Maintainable**: Clear separation of concerns, well-documented
3. ✅ **Extensible**: Easy to add new agents, validators, or lanes
4. ✅ **Testable**: Demo mode allows testing without API costs
5. ✅ **Compliant**: Meets mission intent and operating guide requirements

### Negative

1. ❌ **API Key Dependency**: Cannot initialize agents without key (fixable)
2. ⚠️ **No Native Parallelism**: Need external orchestration
3. ⚠️ **Memory Limitations**: No built-in long-term memory
4. ⚠️ **Rate Limits**: Parallel execution can hit API limits

### Neutral

1. 📋 **Migration Path**: Can move to LangGraph later if needed
2. 📋 **Tool Integration**: Can add custom tools incrementally
3. 📋 **Model Flexibility**: Can swap LLMs via environment config

## Action Items

### Priority 1 (Critical - Before Production)
- [ ] Fix: Add LLM parameter to Agent creation
- [ ] Fix: Add API key validation with clear error message
- [ ] Fix: Make verbose configurable via environment
- [ ] Test: Verify agent creation with and without API key

### Priority 2 (Important - Before Scale)
- [ ] Add: LLM timeout configuration
- [ ] Add: Rate limiting for parallel lanes
- [ ] Test: End-to-end with real API calls
- [ ] Document: API usage and cost estimates

### Priority 3 (Enhancement)
- [ ] Add: Token usage tracking
- [ ] Add: Adaptive concurrency
- [ ] Explore: Custom tools for agents
- [ ] Explore: Memory persistence options

## Verification

This ADR will be considered complete when:

1. ✅ All Priority 1 fixes implemented and tested
2. ✅ Updated code passes all tests (demo + setup + integration)
3. ✅ Documentation updated with findings
4. ✅ User can run system with and without API key
5. ✅ Audit findings addressed in follow-up commits

## References

- CrewAI Documentation: https://docs.crewai.com/
- CrewAI GitHub: https://github.com/joaomdmoura/crewAI
- Mission Intent v5: `hfo_mission_intent/2025-10-30/mission_intent_daily_2025-10-30.v5.yml`
- AGENTS.md: Operating guide for HFO agents
- ThreadPoolExecutor: Python standard library for parallel execution

## Revision History

- 2025-10-30: Initial ADR created from audit
- 2025-10-30: Critical issues identified, fixes planned
