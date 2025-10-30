# ADR-001: Multi-Crew Parallel Agent System Architecture

**Status**: DRAFT - Under Review  
**Date**: 2025-10-30  
**Author**: GitHub Copilot  
**Reviewers**: TTaoGaming

## Context

Mission intent v5 (2025-10-30) requires a multi-crew parallel agent system implementing:
- PREY workflow (Perceive → React → Engage → Yield)
- Parallel lane execution with explore/exploit strategy (60/40 split)
- Quorum-based verification (2 of 3 validators)
- Stigmergy coordination via blackboard (append-only JSONL)
- Safety envelope enforcement (chunk limits, placeholder bans)

## Decision

Implement a CrewAI-based orchestration system with the following architecture:

### Components

1. **Swarmlord Orchestrator** (`swarmlord.py`)
   - Coordinates N parallel lanes using ThreadPoolExecutor
   - Implements explore/exploit portfolio diversity
   - Aggregates results and runs verification quorum

2. **PREY Agents** (`agents.py`)
   - Perceiver: Scans context and environment
   - Reactor: Plans execution strategy
   - Engager: Executes work within constraints
   - Yielder: Packages outputs for review

3. **Verification Agents** (`agents.py`)
   - Immunizer: Validates quality and safety
   - Disruptor: Adversarial testing
   - Verifier Aux: Independent verification

4. **Supporting Infrastructure**
   - `blackboard.py`: Stigmergy coordination
   - `safety.py`: Safety constraint enforcement
   - `config.py`: Configuration management
   - `tasks.py`: Task definitions for PREY phases

## Consequences

### Positive

✅ **Modularity**: Clear separation of concerns between agents, tasks, orchestration  
✅ **Safety**: Explicit safety constraints (chunk limits, placeholder bans)  
✅ **Traceability**: Blackboard provides audit trail of all operations  
✅ **Scalability**: Can increase lane count via configuration  
✅ **AGENTS.md Compliance**: Follows repository protocol requirements  

### Negative

⚠️ **Tool Dependencies**: Requires CrewAI, which has complex dependencies  
⚠️ **API Costs**: Multiple LLM calls per mission (7 agents × N lanes)  
⚠️ **Complexity**: Multi-layer abstraction may be hard to debug  

## Audit Findings (2025-10-30)

### Critical Issues Identified

#### 1. Missing Agent Tools ❌
**Problem**: Agents lack tools to interact with environment  
**Impact**: Cannot read files, execute commands, or perform actual work  
**Status**: NOT IMPLEMENTED  

```python
# Current (incomplete):
Agent(role='Perceiver', goal='...', backstory='...', llm=llm)

# Should be:
Agent(
    role='Perceiver',
    goal='...',
    backstory='...',
    tools=[FileReadTool(), DirectorySearchTool(), ...],
    llm=llm
)
```

**Recommendation**: Add CrewAI tools or custom tools for:
- File system operations (read, write, search)
- Git operations (status, diff, log)
- Command execution (bash, linters, tests)

#### 2. Missing Task Context Propagation ❌
**Problem**: Tasks don't receive outputs from previous tasks  
**Impact**: PREY workflow broken - agents work in isolation  
**Status**: NOT IMPLEMENTED  

```python
# Current (incomplete):
perceive_task = Task(description='...', agent=perceiver)
react_task = Task(description='...', agent=reactor)

# Should be:
perceive_task = Task(
    description='...',
    agent=perceiver,
    expected_output='Perception report'
)
react_task = Task(
    description='...',
    agent=reactor,
    context=[perceive_task],  # Receives perceive output
    expected_output='Execution plan'
)
```

**Recommendation**: Use `context` parameter to chain tasks properly.

#### 3. Flawed Verification Quorum ❌
**Problem**: Counts "pass"/"fail" strings instead of structured votes  
**Impact**: Unreliable verification, easily fooled by agent reasoning text  
**Status**: PARTIALLY IMPLEMENTED (naive)  

```python
# Current (unreliable):
pass_count = str(verify_result).lower().count('pass')
fail_count = str(verify_result).lower().count('fail')

# Should be:
class VerificationVote(BaseModel):
    validator: str
    verdict: Literal['PASS', 'FAIL']
    reasoning: str
    
# Use output_pydantic with VerificationVote model
```

**Recommendation**: Use Pydantic models for structured task outputs.

### High-Priority Issues

#### 4. No API Key Validation ⚠️
**Problem**: Instantiates ChatOpenAI without checking API key validity  
**Impact**: Fails at runtime with cryptic errors  
**Status**: NOT IMPLEMENTED  

**Recommendation**: Add validation in `__init__`:
```python
if not self.config.openai_api_key:
    raise ValueError("OPENAI_API_KEY not set in environment")
```

#### 5. Inadequate Error Handling ⚠️
**Problem**: ThreadPoolExecutor and crew execution lack proper error boundaries  
**Impact**: One failing lane could crash entire mission  
**Status**: MINIMAL (try/except exists but incomplete)  

**Recommendation**: Add:
- Timeout per lane execution
- Graceful degradation if < quorum lanes succeed
- Detailed error logging to blackboard

### Medium-Priority Issues

#### 6. No Scope Narrowing on Retry ⚠️
**Problem**: Documentation claims "scope narrowing" but code doesn't implement it  
**Impact**: False documentation, retries don't improve  
**Status**: HALLUCINATED  

**Recommendation**: Either implement scope narrowing or remove from docs.

#### 7. Evidence Refs Not Generated by Agents ⚠️
**Problem**: Blackboard logs evidence_refs, but agents don't generate them  
**Impact**: Manual evidence refs only, no automated tracking  
**Status**: PARTIALLY IMPLEMENTED  

**Recommendation**: Configure task outputs to include evidence refs.

## Industry Best Practices Comparison

### CrewAI Best Practices

| Best Practice | Status | Implementation |
|---------------|--------|----------------|
| **Tools per Agent** | ❌ Missing | No tools assigned to any agent |
| **Task Context Chaining** | ❌ Missing | Tasks don't use `context` parameter |
| **Structured Outputs** | ❌ Missing | No Pydantic models for outputs |
| **Memory/Context** | ❌ Missing | No crew memory configured |
| **Error Handling** | ⚠️ Partial | Basic try/except, no retries per task |
| **Process Definition** | ✅ Good | Sequential process correct for PREY |
| **Agent Roles** | ✅ Good | Well-defined roles and backstories |
| **Separation of Concerns** | ✅ Good | Clear agent/task/orchestrator split |

### Multi-Agent System Best Practices

| Best Practice | Status | Implementation |
|---------------|--------|----------------|
| **Coordination Mechanism** | ✅ Good | Blackboard stigmergy pattern |
| **Fault Tolerance** | ⚠️ Partial | Retries exist, no graceful degradation |
| **Scalability** | ✅ Good | ThreadPoolExecutor for parallel lanes |
| **Observability** | ✅ Good | Blackboard JSONL audit trail |
| **Safety Constraints** | ✅ Good | Explicit safety envelope |
| **Quorum Consensus** | ⚠️ Partial | Naive string matching |
| **Portfolio Diversity** | ✅ Good | Explore/exploit split implemented |

## Verification Status

### What Actually Works ✅

1. **Infrastructure Layer**: Blackboard, Safety, Config modules all work independently
2. **Validation Script**: `demo_validate.py` passes all checks
3. **Import Structure**: Modules properly separated, CrewAI optional for core
4. **Configuration**: Env-based config with mission YAML loading works
5. **Safety Enforcement**: Chunk limits, placeholder detection functional

### What Doesn't Work ❌

1. **Full Crew Execution**: Agents cannot perform work without tools
2. **PREY Workflow**: Tasks don't communicate between phases
3. **Verification Quorum**: Unreliable vote counting
4. **Scope Narrowing**: Not implemented despite documentation
5. **Evidence Generation**: Not automated by agents

### What's Untested ⚠️

1. **Parallel Execution**: ThreadPoolExecutor with actual CrewAI crews
2. **API Integration**: Real OpenAI API calls (no API key in environment)
3. **Error Recovery**: Retry mechanism with actual failures
4. **Memory Usage**: Long-running missions with large blackboards

## Recommendations

### Immediate (Before Production)

1. **Add Tools to Agents** (CRITICAL)
   - Implement or import file system tools
   - Add git operation tools
   - Configure bash execution tool

2. **Fix Task Context** (CRITICAL)
   - Add `context` parameter to chain tasks
   - Use Pydantic models for outputs
   - Test PREY workflow end-to-end

3. **Improve Verification** (HIGH)
   - Use structured output models
   - Implement proper voting mechanism
   - Add verification result validation

4. **Add API Key Validation** (HIGH)
   - Check at initialization
   - Provide clear error messages
   - Document API key requirements

### Short-Term (Next Iteration)

5. **Implement Scope Narrowing** (MEDIUM)
   - Actually reduce scope on retry
   - Or remove from documentation

6. **Add Error Boundaries** (MEDIUM)
   - Timeout per lane
   - Graceful degradation
   - Better error logging

7. **Evidence Automation** (MEDIUM)
   - Configure agents to generate evidence
   - Validate evidence refs format

### Long-Term (Future Enhancements)

8. **Add Memory/Context** (LOW)
   - Use CrewAI memory features
   - Persist context between missions

9. **Performance Optimization** (LOW)
   - Reduce LLM calls where possible
   - Cache common operations

10. **Integration Tests** (LOW)
    - End-to-end tests with real API
    - Load testing with multiple lanes

## References

### CrewAI Documentation
- [CrewAI Agents](https://docs.crewai.com/core-concepts/Agents/)
- [CrewAI Tasks](https://docs.crewai.com/core-concepts/Tasks/)
- [CrewAI Tools](https://docs.crewai.com/core-concepts/Tools/)
- [CrewAI Crews](https://docs.crewai.com/core-concepts/Crews/)

### Related Patterns
- Blackboard Architecture Pattern (stigmergy)
- PREY Loop (Sense → Make Sense → Act → Yield)
- Quorum Consensus Algorithms
- Portfolio Diversity (Explore/Exploit)

## Decision Review

**Should this implementation be used in production?**

**NO** - Not without addressing critical issues:

1. ❌ Agents cannot perform work (no tools)
2. ❌ PREY workflow is broken (no task context)
3. ❌ Verification is unreliable (string matching)

**What needs to happen:**

1. Fix critical issues #1-3 above
2. Add integration tests with real API
3. Validate end-to-end workflow execution
4. Document actual capabilities vs. claimed

**Timeline Estimate:**
- Fix critical issues: 2-4 hours
- Integration testing: 2-3 hours
- Documentation updates: 1 hour
- **Total**: ~1 day of focused work

## Conclusion

The implementation provides a **solid architectural foundation** with good separation of concerns, safety constraints, and observability. However, it is **not production-ready** due to missing core functionality (agent tools, task context) and unreliable verification logic.

The infrastructure layer (blackboard, safety, config) is well-implemented and functional. The orchestration layer (swarmlord, agents, tasks) requires significant work to match the documented capabilities.

**Recommendation**: Address critical issues before deploying, or clearly document current limitations.

---

**Signatures**

Author: GitHub Copilot  
Date: 2025-10-30  
Status: Awaiting Review by @TTaoGaming
