# Multi-Crew Orchestration Quick Start

This guide helps you get started with the HFO Multi-Crew Parallel Orchestration system.

## What is Multi-Crew Orchestration?

A system that:
- Runs **multiple AI agents in parallel** using CrewAI
- Implements **disperse-converge pattern** for parallel problem solving
- Uses **quorum-based verification** (2 of 3 validators must approve)
- Maintains **stigmergy** (indirect coordination) via blackboard JSONL
- Enforces **safety envelope** (chunk limits, tripwires, auto-retry)
- Supports **8/2 explore/exploit ratio** for quality diversity

## Prerequisites

- Python 3.12+
- OpenAI API key (or Anthropic for Claude)
- Git repository cloned

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `crewai` - Multi-agent orchestration framework
- `crewai-tools` - Pre-built tools for agents
- All existing HFO dependencies

### 2. Configure API Keys

Copy the environment template:

```bash
cp .env.example .env
```

Edit `.env` and add your API key:

```bash
OPENAI_API_KEY=sk-your-key-here
```

**Important**: Don't commit `.env` to git (already in `.gitignore`)

### 3. Verify Setup

Run the setup test:

```bash
python scripts/test_multi_crew_setup.py
```

Expected output:
```
✓ Imports: PASS
✓ Configuration: PASS
✓ Blackboard Logger: PASS
✓ Orchestrator Init: PASS
```

## Usage

### Demo Mission (No API Key Required)

Run a demonstration without making API calls:

```bash
python scripts/demo_multi_crew_mission.py
```

This simulates:
- 2 parallel lanes (1 explore, 1 exploit)
- PREY workflow (Perceive → React → Engage → Yield)
- Quorum verification (Immunizer, Disruptor, Verifier)
- Blackboard logging

### Production Mission (Requires API Key)

Run the full orchestration with real LLM agents:

```bash
python scripts/hfo_multi_crew_orchestrator.py
```

This will:
1. Load configuration from `.env`
2. Create parallel PREY lanes
3. Execute mission with CrewAI agents
4. Run quorum verification
5. Auto-retry up to 3 times if needed
6. Log all evidence to blackboard

## Configuration

Edit `.env` to customize:

```bash
# Number of parallel lanes (default: 2)
HFO_PARALLEL_LANES=2

# Explore/exploit ratio (default: 8:2)
HFO_EXPLORE_EXPLOIT_RATIO=8:2

# Quorum threshold (default: 2 of 3)
HFO_QUORUM_THRESHOLD=2

# Safety limits
HFO_CHUNK_SIZE_MAX=200
HFO_AUTO_RETRY_MAX=3
```

## Understanding the Output

### Console Output

```
Mission ID: mission_2025-10-30
Parallel lanes: 2
Explore/Exploit: 8/2
Quorum threshold: 2/3

[DISPERSE] Running parallel lanes...
  ▸ Lane explore_0 starting...
  ▸ Lane exploit_0 starting...

[CONVERGE] Aggregating results...
  ▸ Verification quorum starting...

[DIGEST] Mission Result: PASS
```

### Blackboard Receipts

All operations log to `hfo_blackboard/obsidian_synapse_blackboard.jsonl`:

```bash
# View recent receipts
tail -20 hfo_blackboard/obsidian_synapse_blackboard.jsonl

# Filter by mission
grep "mission_2025-10-30" hfo_blackboard/obsidian_synapse_blackboard.jsonl
```

Each receipt contains:
- `mission_id` - Unique identifier
- `phase` - PREY phase (perceive, react, engage, yield, verify, digest)
- `summary` - What happened
- `evidence_refs` - Files/metrics/artifacts
- `safety_envelope` - Limits and constraints
- `timestamp` - When it happened

## Workflows

### PREY Loop (Per Lane)

```
Perceive → React → Engage → Yield
    ↓        ↓        ↓        ↓
 Context   Plan   Execute  Bundle
```

### Disperse-Converge (Overall)

```
Mission Goal
     ↓
  Disperse (parallel lanes)
     ├─ Lane 1 (explore)
     ├─ Lane 2 (explore)
     └─ Lane 3 (exploit)
     ↓
  Converge (aggregate)
     ↓
  Verify Quorum (2/3)
     ↓
  Digest or Retry
```

### Verification Quorum

```
Results → Immunizer   → PASS/FAIL
       → Disruptor    → PASS/FAIL
       → Verifier_Aux → PASS/FAIL
              ↓
       Aggregate (2/3 threshold)
              ↓
       PASS → Digest
       FAIL → Retry (narrower scope)
```

## Troubleshooting

### "CrewAI not installed"

```bash
pip install crewai crewai-tools
```

### "OPENAI_API_KEY not set"

1. Copy `.env.example` to `.env`
2. Add your API key: `OPENAI_API_KEY=sk-...`
3. Ensure `.env` is in the same directory as the script

### "Quorum verification failed"

The system auto-retries up to 3 times with:
- Reduced chunk size
- Narrower scope
- Stricter safety checks

Check the blackboard for details:
```bash
grep "verify.*FAIL" hfo_blackboard/obsidian_synapse_blackboard.jsonl
```

### "Rate limit exceeded"

If using OpenAI API:
- Reduce `HFO_PARALLEL_LANES` in `.env`
- Add delays between operations
- Consider using a different model tier

## Next Steps

1. **Run Demo** - Verify everything works without API calls
2. **Add API Key** - Configure `.env` with your credentials
3. **Test Basic Mission** - Run `hfo_multi_crew_orchestrator.py`
4. **Custom Missions** - Modify mission goal for your needs
5. **Scale Up** - Increase parallel lanes for more throughput

## Advanced Usage

See the full documentation:
- [Multi-Crew Orchestration Guide](../docs/MULTI_CREW_ORCHESTRATION.md)
- [Mission Intent](../hfo_mission_intent/2025-10-30/mission_intent_daily_2025-10-30.v5.yml)
- [AGENTS.md](../AGENTS.md) - Operating guide

## Integration

This system integrates with existing HFO components:
- **AGENTS.md** - Follows operating guide principles
- **Mission Intent** - Loads configuration from YAML
- **Blackboard JSONL** - Logs evidence and receipts
- **PettingZoo** - Can verify using game environments
- **Existing Scripts** - Compatible with current workflow

## Support

For issues or questions:
1. Check blackboard receipts for error details
2. Run setup test: `python scripts/test_multi_crew_setup.py`
3. Review the troubleshooting section above
4. Consult documentation in `docs/` directory
