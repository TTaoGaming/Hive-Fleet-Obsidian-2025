# ADR-001: Multi-Lane CrewAI Orchestrator Architecture

## Status
Accepted (with production hardening applied)

## Context
We need a multi-agent system for parallel execution of tasks using CrewAI, following the PREY protocol (Perceive → React → Engage → Yield) with quorum-based verification and blackboard stigmergy.

### Requirements (from mission intent mi_daily_2025-10-30)
- Parallel execution of 2+ lanes
- Explore/exploit ratio of 40/60
- Quorum verification with 2/3 threshold
- Stigmergy via blackboard JSONL
- Autonomous operation (zero mid-loop prompts)
- Safety envelope (chunk limits, placeholder bans)

## Decision
We will implement a multi-lane orchestrator using CrewAI with the following architecture:

### Core Components

1. **Parallel Lane Execution**
   - Use Python's `ThreadPoolExecutor` for true parallelism
   - Each lane runs independently with its own CrewAI crew
   - Timeout protection (default: 300 seconds)
   - Retry logic with exponential backoff (max 3 retries)

2. **PREY Protocol Per Lane**
   - **Perceiver Agent**: Scans context (repo, mission intent, blackboard)
   - **Reactor Agent**: Creates action plans with safety tripwires
   - **Implementer Agent**: Executes with explore/exploit modes
   - **Assimilator Agent**: Packages outputs into review bundles

3. **Quorum Verification**
   - **Immunizer**: Safety and consistency checks
   - **Disruptor**: Adversarial probes to prevent persistent green
   - **Verifier Aux**: Auxiliary validation
   - Threshold: 2 out of 3 validators must pass

4. **Blackboard Stigmergy**
   - Append-only JSONL receipts for all PREY phases
   - Evidence refs for all actions
   - Safety envelope metadata

### Technology Choices

**CrewAI (v0.86.0)**
- Mature framework for multi-agent orchestration
- Built-in support for agent roles, tasks, and crews
- Sequential and hierarchical processes
- Integrates with LangChain ecosystem

**Alternatives Considered:**
- LangGraph: More flexible but requires more boilerplate
- AutoGen: Less mature, different paradigm
- Custom implementation: Too much reinvention

**Why CrewAI:**
✅ Proven in production
✅ Simple mental model (agents → tasks → crews)
✅ Good defaults
✅ Active community

### Process Type: Sequential
Using `Process.sequential` for all lanes because:
- Tasks have clear dependencies (Perceive → React → Engage → Yield)
- Simpler to reason about and debug
- Avoids delegation complexity
- Future: can upgrade to `Process.hierarchical` if needed

### Parallel Execution: ThreadPoolExecutor
Using ThreadPoolExecutor instead of:
- `multiprocessing`: Heavier, serialization overhead
- `asyncio`: CrewAI's sync API not async-native
- Sequential: Would negate parallelism benefits

### Error Handling Strategy

**Retry Logic:**
```python
# Exponential backoff: 1s, 2s, 4s
for attempt in range(max_retries):
    try:
        return execute()
    except Exception:
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)
```

**Timeout Protection:**
```python
future.result(timeout=LANE_TIMEOUT_SECONDS)
```

**Graceful Degradation:**
- Failed lanes don't crash entire system
- Quorum can pass with partial failures
- Detailed error logging with stack traces

## Consequences

### Positive
✅ **Scalability**: Can run 2-10+ lanes in parallel
✅ **Resilience**: Retries and timeouts prevent hangs
✅ **Observability**: Logging and blackboard receipts
✅ **Safety**: Quorum prevents bad outputs from shipping
✅ **Flexibility**: Configurable via environment variables
✅ **Testability**: Unit tests for each component

### Negative
⚠️ **API Costs**: Parallel lanes = parallel API calls
⚠️ **Rate Limits**: Could hit OpenAI rate limits
⚠️ **Complexity**: More moving parts than single-agent
⚠️ **Debugging**: Parallel execution harder to trace

### Risks Mitigated
✅ **Timeout Risk**: Explicit timeouts on all operations
✅ **Error Masking**: Detailed error logging with traces
✅ **API Key Issues**: Validation before execution
✅ **Retry Storms**: Exponential backoff prevents hammering
✅ **Resource Leaks**: Proper cleanup in exception handlers

### Risks Remaining
⚠️ **Rate Limiting**: No built-in rate limiter (manual monitoring needed)
⚠️ **Cost Control**: No automatic cost limits (set in OpenAI dashboard)
⚠️ **Memory Leaks**: No explicit memory cleanup (relying on Python GC)

## Implementation Notes

### Production Hardening Applied (2025-10-30)

Based on audit findings, the following improvements were made:

1. **Logging**: Replaced `print()` with Python `logging` module
2. **Retries**: Added exponential backoff (3 retries, 1s/2s/4s delays)
3. **Timeouts**: Added timeout protection to ThreadPoolExecutor
4. **API Validation**: Validate API key format before execution
5. **Error Traces**: Full stack traces logged for all exceptions

### Configuration

Environment variables (see `.env.example`):
```bash
# Core
OPENAI_API_KEY=sk-...           # Required
HFO_PARALLEL_LANES=2            # Number of lanes
HFO_MISSION_ID=mi_daily_...     # Mission identifier

# Production
HFO_LANE_TIMEOUT_SECONDS=300    # 5 minute timeout
HFO_MAX_RETRIES=3               # Retry attempts

# Safety
HFO_CHUNK_SIZE_MAX=200          # Max lines per write
```

### Best Practices Followed

✅ Agent roles clearly defined
✅ Tasks have explicit expected outputs
✅ Delegation disabled (prevents loops)
✅ Verbose mode configurable
✅ Process type explicitly set
✅ Error handling comprehensive

### Best Practices Not Yet Implemented

Future enhancements:
- Tools integration (file system, search)
- Crew memory configuration
- Callbacks for progress tracking
- LLM configuration/fallbacks
- Cache management
- Performance metrics

## Alternatives Considered

### Alternative 1: LangGraph
**Pros:**
- More flexible control flow
- Better for complex DAGs
- First-class state management

**Cons:**
- More boilerplate
- Steeper learning curve
- Overkill for sequential PREY

**Why not chosen:** CrewAI's simplicity better matches our use case

### Alternative 2: Sequential (No Parallelism)
**Pros:**
- Simpler implementation
- Easier debugging
- Lower API costs

**Cons:**
- Slower throughput
- Doesn't meet mission requirement for parallel execution

**Why not chosen:** Mission intent explicitly requires parallelism

### Alternative 3: Process.hierarchical
**Pros:**
- Better for complex delegation
- Manager/worker pattern

**Cons:**
- Added complexity
- Not needed for current PREY flow

**Why not chosen:** Can upgrade later if needed

## Testing Strategy

### Unit Tests (✅ Implemented)
- Lane configuration (explore/exploit ratio)
- Quorum verification (pass/fail scenarios)
- Blackboard logging
- Module imports

### Integration Tests (⚠️ Planned)
- End-to-end with mock API
- Timeout scenarios
- Retry scenarios
- Error recovery

### Performance Tests (⚠️ Planned)
- Concurrent lane execution
- Rate limit handling
- Memory usage over time

## Monitoring & Observability

### Current
✅ Python logging (INFO/WARNING/ERROR levels)
✅ Blackboard JSONL receipts (all PREY phases)
✅ Evidence refs for traceability

### Future
- OpenTelemetry traces
- Metrics (latency, success rate, costs)
- Alerts (failures, timeouts, rate limits)

## Migration Path

This implementation is designed for extensibility:

1. **Phase 1** (Current): 2 lanes, basic orchestration
2. **Phase 2**: Add tools to agents (file system, search)
3. **Phase 3**: Crew memory and caching
4. **Phase 4**: Scale to 5-10 lanes
5. **Phase 5**: Port to LangGraph if needed for complex flows

## References

- [CrewAI Documentation](https://docs.crewai.com/)
- [AGENTS.md](../AGENTS.md) - PREY protocol
- [Mission Intent v5](../hfo_mission_intent/2025-10-30/mission_intent_daily_2025-10-30.v5.yml)
- [Clarification Pass 5](../hfo_mission_intent/2025-10-30/clarification_pass5_2025-10-30.md)
- [Audit Report](CREWAI_AUDIT_REPORT.md)

## Appendix: Audit Results

**Overall Assessment**: Functionally correct, production-hardened

**Confidence Level**: 95% (was 85% before hardening)

**Production Readiness**: ✅ Ready with hardening applied

See [CREWAI_AUDIT_REPORT.md](CREWAI_AUDIT_REPORT.md) for full audit details.

## Decision Makers
- Implementation: GitHub Copilot
- Review: TTaoGaming
- Date: 2025-10-30

## Changelog
- 2025-10-30: Initial implementation
- 2025-10-30: Production hardening (logging, retries, timeouts, validation)
