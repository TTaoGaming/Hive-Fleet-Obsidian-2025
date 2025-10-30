# HFO Crew Parallel - Quick Start Guide

## Prerequisites

- Python 3.12+
- OpenAI API key

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Note: If you encounter dependency conflicts with CrewAI, you can install it separately:

```bash
pip install crewai
```

### 2. Configure API Key

Create a `.env` file in the repository root:

```bash
cp hfo_crew_parallel/.env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-api-key-here
CREW_MODEL_NAME=gpt-4o-mini
EXPLORE_RATIO=0.6
EXPLOIT_RATIO=0.4
```

### 3. Validate Setup

Run the validation script to verify all infrastructure components:

```bash
python hfo_crew_parallel/demo_validate.py
```

Expected output:
```
================================================================================
HFO Crew Parallel - Infrastructure Validation
================================================================================

[1/4] Testing Blackboard...
  ✓ Blackboard operational: X receipt(s) logged

[2/4] Testing Safety Envelope...
  ✓ Line count check: 50 lines (passed=True)
  ✓ Placeholder scan: passed=True
  ✓ Chunking: 3 chunk(s) created

[3/4] Testing Configuration...
  ✓ Model: gpt-4o-mini
  ✓ Temperature: 0.1
  ✓ Explore/Exploit: 0.6/0.4
  ✓ API Key: set

[4/4] Testing Mission Intent...
  ✓ Mission ID: mi_daily_2025-10-30
  ✓ Lanes: 2 (lane_a, lane_b)
  ✓ Quorum: 2/3 validators
  ✓ Chunk size max: 200
  ✓ Placeholder ban: True
```

## Usage

### Basic Command

Run with default settings (uses today's mission intent):

```bash
python -m hfo_crew_parallel.cli "Implement feature X with parallel agents"
```

### Advanced Command

Specify custom mission intent and parameters:

```bash
python -m hfo_crew_parallel.cli \
  "Complete task Y safely and efficiently" \
  --mission-path hfo_mission_intent/2025-10-30/mission_intent_daily_2025-10-30.v5.yml \
  --max-retries 3 \
  --model gpt-4o
```

### Python API

Use programmatically in your scripts:

```python
from hfo_crew_parallel.config import CrewConfig, MissionIntent
from hfo_crew_parallel.swarmlord import SwarmlordOrchestrator

# Initialize
config = CrewConfig()
mission = MissionIntent()
orchestrator = SwarmlordOrchestrator(config=config, mission_intent=mission)

# Execute mission with parallel lanes
result = orchestrator.execute_mission(
    mission_context="Your specific objectives here",
    max_retries=3
)

# Check results
if result['status'] == 'success':
    print(f"Mission completed in {result['attempt']} attempts")
    for lane_result in result['lane_results']:
        print(f"Lane {lane_result['lane']}: {lane_result['status']}")
else:
    print(f"Mission failed after {result['attempts']} attempts")
```

## How It Works

### PREY Workflow

Each lane follows the PREY loop:

1. **Perceive**: Sense repository context and mission intent
2. **React**: Plan execution strategy with safety constraints
3. **Engage**: Execute work in chunks (≤200 lines each)
4. **Yield**: Assemble outputs into review bundle

### Parallel Lanes

- **Lane Count**: Configured in mission intent (default: 2)
- **Explore vs Exploit**: 60% lanes explore (novel approaches), 40% exploit (refine known solutions)
- **Execution**: Lanes run in parallel using ThreadPoolExecutor

### Verification Quorum

Results verified by 3 validators (need 2/3 to pass):

1. **Immunizer**: Checks quality and safety compliance
2. **Disruptor**: Adversarial testing for edge cases
3. **Verifier Aux**: Independent verification perspective

### Blackboard Coordination

All agents log receipts to `hfo_blackboard/obsidian_synapse_blackboard.jsonl`:

```json
{
  "mission_id": "mi_daily_2025-10-30",
  "phase": "engage",
  "summary": "Lane A completed work",
  "evidence_refs": ["file.py:1-50"],
  "safety_envelope": {"chunk_size_max": 200},
  "timestamp": "2025-10-30T16:00:00Z"
}
```

### Safety Constraints

- ✅ Max 200 lines per chunk
- ✅ No placeholders (TODO, FIXME, etc.)
- ✅ Evidence refs required for all actions
- ✅ Independent verification before finalization

## Troubleshooting

### "OPENAI_API_KEY not set"

**Solution**: Create `.env` file with your API key:

```bash
echo "OPENAI_API_KEY=sk-your-key" > .env
```

### "ModuleNotFoundError: No module named 'crewai'"

**Solution**: Install CrewAI:

```bash
pip install crewai
```

### Verification Failing

**Diagnosis**: Check blackboard for detailed receipts:

```bash
tail -50 hfo_blackboard/obsidian_synapse_blackboard.jsonl | python -m json.tool
```

Look for receipts with `phase: "verify"` to see what failed.

### Network Timeouts During pip install

**Solution**: Install CrewAI separately with increased timeout:

```bash
pip install --timeout=300 crewai
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | None | OpenAI API key (required) |
| `CREW_MODEL_NAME` | `gpt-4o-mini` | LLM model to use |
| `CREW_TEMPERATURE` | `0.1` | Temperature for LLM |
| `CREW_MAX_ITER` | `5` | Max iterations per agent |
| `EXPLORE_RATIO` | `0.6` | Ratio of exploration lanes |
| `EXPLOIT_RATIO` | `0.4` | Ratio of exploitation lanes |
| `BLACKBOARD_PATH` | `hfo_blackboard/obsidian_synapse_blackboard.jsonl` | Blackboard file path |

### Mission Intent Parameters

Edit `hfo_mission_intent/YYYY-MM-DD/mission_intent_daily_YYYY-MM-DD.v5.yml`:

```yaml
lanes:
  count: 2  # Number of parallel lanes
  names: [lane_a, lane_b]  # Lane identifiers

quorum:
  threshold: 2  # Validators needed to pass (2 of 3)
  validators: [immunizer, disruptor, verifier_aux]

safety:
  chunk_size_max: 200  # Max lines per chunk
  placeholder_ban: true  # Ban TODO/FIXME/etc
```

## Next Steps

1. ✅ Validate infrastructure works
2. ✅ Set up API key
3. Run a simple mission to test:
   ```bash
   python -m hfo_crew_parallel.cli "Test parallel agent system with minimal task"
   ```
4. Check blackboard for receipts
5. Review verification results
6. Scale up to more complex missions

## Getting Help

- Check README: `hfo_crew_parallel/README.md`
- Review AGENTS.md: Operating guide for all agents
- Inspect blackboard: `hfo_blackboard/obsidian_synapse_blackboard.jsonl`
- Run validation: `python hfo_crew_parallel/demo_validate.py`
