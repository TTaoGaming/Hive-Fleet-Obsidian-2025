# Getting Started with Multi-Crew Orchestrator

This guide will help you set up and run the Multi-Crew Parallel Orchestration System.

## Prerequisites

- Python 3.10 or higher (required for modern type hints and dataclass features)
- pip (Python package installer)

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/TTaoGaming/Hive-Fleet-Obsidian-2025.git
cd Hive-Fleet-Obsidian-2025
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `crewai` - Multi-agent orchestration framework
- `crewai-tools` - Tools for CrewAI agents
- `python-dotenv` - Environment variable management
- Plus dependencies for PettingZoo, LangChain, LangGraph, etc.

## Quick Demo (No API Key Required)

Try the demo first to see the system in action without needing an API key:

```bash
python3 scripts/demo_multi_crew.py
```

This demonstrates:
- Mission configuration
- Lane results structure
- Quorum verification (immunizer, disruptor, verifier_aux)
- Explore/exploit distribution
- Adversarial detection
- Blackboard receipts

Expected output:
```
🐝 Hive Fleet Obsidian - Multi-Crew Orchestrator Demo
...
✅ Demo Complete!
```

## Verify Tests

Run the test suite to ensure everything is working:

```bash
python3 tests/test_multi_crew_orchestrator.py
```

Expected output:
```
🧪 Running multi-crew orchestrator tests...
✓ MissionConfig test passed
✓ LaneResult test passed
...
Results: 7 passed, 0 failed
```

## Configure for Real Agents

### Step 1: Get an OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Create a new API key
4. Copy the key (starts with `sk-...`)

### Step 2: Configure Environment

```bash
# Copy the template
cp .env.template .env

# Edit .env and add your API key
# OPENAI_API_KEY=sk-your-actual-key-here
```

Alternatively, edit `.env` manually:

```bash
nano .env  # or vim, code, etc.
```

Required configuration:
```bash
OPENAI_API_KEY=sk-your-actual-key-here
```

Optional configurations (already have sensible defaults):
```bash
HFO_MISSION_ID=multi_crew_parallel_2025-10-30
HFO_LANE_COUNT=2
HFO_EXPLORE_EXPLOIT_RATIO=0.2  # 20% explore, 80% exploit
HFO_QUORUM_THRESHOLD=2  # out of 3 validators
```

## Run the Orchestrator

### Basic Usage

```bash
bash scripts/run_multi_crew.sh
```

This runs with default settings:
- 2 parallel lanes
- 0.2 explore/exploit ratio (20% explore, 80% exploit)

### Custom Configuration

```bash
# Run with 4 lanes
bash scripts/run_multi_crew.sh 4

# Run with 4 lanes and 25% explore ratio
bash scripts/run_multi_crew.sh 4 0.25

# Run with 10 lanes and 30% explore ratio
bash scripts/run_multi_crew.sh 10 0.3
```

### Direct Python Invocation

```bash
# With environment variables
export HFO_LANE_COUNT=4
export HFO_EXPLORE_EXPLOIT_RATIO=0.25
python3 scripts/hfo_multi_crew_orchestrator.py
```

## Understanding the Output

When you run the orchestrator, you'll see:

```
🐝 Hive Fleet Obsidian - Multi-Crew Parallel Orchestrator
Mission ID: multi_crew_parallel_2025-10-30
Lanes: 2 (explore/exploit: 0.2)
Quorum: 2/3 validators

📊 Mission Digest:
{
  "mission_id": "multi_crew_parallel_2025-10-30",
  "lane_count": 2,
  "verification_passed": true,
  ...
}

✅ Verification: PASS
📝 Blackboard: hfo_blackboard/obsidian_synapse_blackboard.jsonl
```

Key indicators:
- **Verification: PASS** - All validators approved the results
- **Verification: FAIL** - Some issues detected, check blackboard for details

## Inspecting the Blackboard

The blackboard contains all receipts from the mission:

```bash
# View recent receipts
tail -20 hfo_blackboard/obsidian_synapse_blackboard.jsonl

# Count receipts
wc -l hfo_blackboard/obsidian_synapse_blackboard.jsonl

# View receipts for a specific mission
grep "multi_crew_parallel" hfo_blackboard/obsidian_synapse_blackboard.jsonl

# Pretty print a receipt
tail -1 hfo_blackboard/obsidian_synapse_blackboard.jsonl | python3 -m json.tool
```

## Verify Blackboard Logging

Run the blackboard verification script:

```bash
python3 scripts/verify_blackboard.py
```

This:
1. Writes test receipts (perceive, react, engage)
2. Verifies JSONL structure
3. Demonstrates stigmergy pattern

## Troubleshooting

### "CrewAI not installed"

```bash
pip install -r requirements.txt
```

### "OPENAI_API_KEY not found"

Make sure you:
1. Created `.env` from `.env.template`
2. Added your API key to `.env`
3. Used the correct format: `OPENAI_API_KEY=sk-...`

Verify:
```bash
cat .env | grep OPENAI_API_KEY
```

### "No module named 'dotenv'"

```bash
pip install python-dotenv
```

### Verification fails

Check the blackboard for validator evidence:

```bash
grep "verify" hfo_blackboard/obsidian_synapse_blackboard.jsonl | tail -5
```

Common issues:
- **Immunizer FAIL**: Lane execution errors
- **Disruptor FAIL**: Placeholders (TODO) or identical outputs
- **Verifier Aux FAIL**: Timeout or errors present

### Lane timeouts

Increase soft limits in `.env`:

```bash
HFO_LANE_CYCLE_SOFT_MINUTES=10
HFO_MISSION_SOFT_MINUTES=60
```

## Advanced Usage

### Custom Mission Context

Edit `scripts/hfo_multi_crew_orchestrator.py` and modify the `mission_context` in `main()`:

```python
mission_context = """
Your custom mission description here.

Goals:
1. Specific goal 1
2. Specific goal 2

Success criteria:
- Criterion 1
- Criterion 2
"""
```

### Programmatic Usage

```python
from scripts.hfo_multi_crew_orchestrator import (
    SwarmlordOrchestrator,
    MissionConfig,
)

config = MissionConfig.from_env()
orchestrator = SwarmlordOrchestrator(config)

digest = orchestrator.run_mission("""
    Your mission context here...
""")

print(f"Verification: {'PASS' if digest['verification_passed'] else 'FAIL'}")
```

### Integration with Existing Code

The orchestrator can be imported and used in your scripts:

```python
import os
os.environ["HFO_LANE_COUNT"] = "4"
os.environ["HFO_EXPLORE_EXPLOIT_RATIO"] = "0.3"

from scripts.hfo_multi_crew_orchestrator import SwarmlordOrchestrator, MissionConfig

config = MissionConfig.from_env()
orchestrator = SwarmlordOrchestrator(config)
result = orchestrator.run_mission("Analyze repository structure")
```

## Next Steps

1. **Scale up**: Try with 4, 8, or 10+ lanes
2. **Custom missions**: Modify mission context for your tasks
3. **Add tools**: Integrate with file ops, git, tests
4. **LangGraph port**: Migrate to graph-based orchestration
5. **Advanced verification**: Add domain-specific validators

## Resources

- [Multi-Crew Documentation](../docs/MULTI_CREW_ORCHESTRATOR.md)
- [Mission Intent v5](../hfo_mission_intent/2025-10-30/mission_intent_daily_2025-10-30.v5.yml)
- [AGENTS.md Protocol](../AGENTS.md)
- [CrewAI Documentation](https://docs.crewai.com/)

## Support

For issues or questions:
1. Check existing blackboard receipts
2. Run demo and tests to verify setup
3. Review verification evidence
4. Check mission intent and AGENTS.md protocol
