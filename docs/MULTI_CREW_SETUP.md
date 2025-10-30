# Multi-Crew Availability System

Multi-lane orchestrator with parallel execution, quorum verification, and stigmergy via blackboard JSONL.

## Features

- **Parallel PREY Lanes**: Multiple lanes execute simultaneously (Perceive → React → Engage → Yield)
- **Disperse-Converge Pattern**: Lanes disperse for parallel execution, then converge for quorum verification
- **Explore/Exploit Ratio**: Configurable 40/60 split between exploration and exploitation
- **Quorum Verification**: 3 validators (immunizer, disruptor, verifier_aux) with 2/3 threshold
- **Stigmergy via Blackboard**: All actions logged to JSONL for coordination
- **Autonomous Operation**: Minimal manual touch, no mid-loop prompts

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

Get your OpenAI API key from: https://platform.openai.com/api-keys

### 3. Run Multi-Lane Orchestrator

```bash
python scripts/hfo_multi_lane_orchestrator.py
```

## Configuration

Configure via environment variables in `.env`:

```bash
# Required
OPENAI_API_KEY=your_key_here

# Optional
HFO_MISSION_ID=mi_daily_2025-10-30
HFO_PARALLEL_LANES=2
HFO_CHUNK_SIZE_MAX=200
HFO_CREW_VERBOSE=false
```

## Architecture

### PREY Loop (per lane)

```
Perceive → React → Engage → Yield
```

1. **Perceive**: Scan mission intent, repo state, blackboard
2. **React**: Create action plan with safety tripwires
3. **Engage**: Execute actions with chunk limits
4. **Yield**: Package outputs with evidence refs

### Disperse-Converge Pattern

```
        ┌─ Lane A (explore) ─┐
Disperse┼─ Lane B (exploit) ─┼─ Converge → Quorum Verify → Digest
        └─ Lane C (explore) ─┘
```

### Quorum Verification

Three independent validators:

1. **Immunizer**: Safety and consistency checks
   - No placeholders (TODO, ..., omitted)
   - Evidence refs present
   - Chunk size limits respected

2. **Disruptor**: Adversarial probes
   - Output diversity checks
   - Anti-noop detection
   - Prevent persistent green

3. **Verifier Aux**: Auxiliary validation
   - Metrics presence
   - Evidence format validation
   - Success/failure distribution

**Threshold**: 2 out of 3 validators must pass

## Explore/Exploit Ratio

- **Explore (40%)**: Creative exploration, diverse strategies, variance
- **Exploit (60%)**: Proven patterns, stability, reliability

Configured via `EXPLORE_RATIO = 0.4` (40% exploration)

## Blackboard Protocol

All actions logged to `hfo_blackboard/obsidian_synapse_blackboard.jsonl`:

```json
{
  "mission_id": "mi_daily_2025-10-30",
  "phase": "engage",
  "summary": "Starting lane lane_a in explore mode",
  "evidence_refs": ["lane:lane_0"],
  "safety_envelope": {"chunk_size_max": 200, "line_target_min": 0},
  "blocked_capabilities": [],
  "timestamp": "2025-10-30T16:30:00Z"
}
```

## Files

- `scripts/hfo_multi_lane_orchestrator.py` - Main orchestrator
- `scripts/hfo_quorum_verifier.py` - Quorum verification module
- `scripts/blackboard_logger.py` - Blackboard JSONL logger
- `scripts/hfo_swarmlord_crewai_run.py` - Original CrewAI canary
- `.env.example` - Environment configuration template

## Alignment

Aligned with:
- `AGENTS.md` - PREY protocol and safety envelope
- `hfo_mission_intent/2025-10-30/mission_intent_daily_2025-10-30.v5.yml`
- Clarification passes 4 & 5

## Next Steps

1. Test with real mission intent tasks
2. Add OpenTelemetry telemetry spans
3. Port to LangGraph for advanced orchestration
4. Expand to 3-4 lanes with dynamic scaling
5. Add crew manifest with specialized roles
