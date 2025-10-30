# HiveFleetObsidian Project

## Purpose
HiveFleetObsidian is a research and development project focused on evolutionary AI systems, gem generation, audits, and baseline testing for MOLT shell simulations. It explores concepts like gene seeds, strategic synthesis, and swarm strategies in a structured, timestamped workflow.

## Structure
- **HFO_molt_shell_2025-10-25T16:24:00Z/**: Contains earlier pass data including audits_reports, baselines_results, core_scripts, gems (with duplicates and generations), summaries_docs, and todo/notes.
- **HFO_molt_shell_2025-10-25T17:00:00Z/**: Contains later pass data including audits_reports, baselines_results, core_scripts, summaries_docs, and handoff documents.

This setup enables tracking of project evolution across timestamps.

## Multi-Crew Parallel Orchestration System 🐝

**NEW**: Parallel multi-agent orchestration with disperse-converge pattern, quorum verification, and stigmergy.

### Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run demo (no API key needed)
python3 scripts/demo_multi_crew.py

# 3. Configure for real agents
cp .env.template .env
# Edit .env and add your OPENAI_API_KEY

# 4. Run orchestrator
bash scripts/run_multi_crew.sh

# Or with custom parameters (lanes, explore_ratio)
bash scripts/run_multi_crew.sh 4 0.25
```

### Features

- **Parallel PREY Lanes**: Perceive → React → Engage → Yield
- **Quorum Verification**: 3 validators (immunizer, disruptor, verifier_aux)
- **Blackboard Stigmergy**: JSONL-based coordination
- **Explore/Exploit**: 2/8 ratio seeding (configurable)
- **Safety Envelope**: Chunk limits, tripwires, canary-first
- **Zero Babysitting**: No mid-loop human prompts

See [docs/MULTI_CREW_ORCHESTRATOR.md](docs/MULTI_CREW_ORCHESTRATOR.md) for full documentation.

## PettingZoo MPE simple_tag_v3 evaluation

Quick tools to test predator/prey policies against random or heuristic fleeing prey are under `scripts/`:

- `scripts/pz_eval_simple_tag_v3.py`: Flexible evaluator. Choose predator and prey policies via flags:
	- `--pred random|heuristic|custom:module:Class`
	- `--prey random|heuristic|custom:module:Class`
	- `--baseline research|enhanced` selects the heuristic variant.
	- Outputs JSON results in `hfo_petting_zoo_results/` by default.

- `scripts/run_pz_eval_vs.sh`: Bash wrapper for convenience.

Examples:

```bash
# Random predators vs heuristic (fleeing) prey
bash scripts/run_pz_eval_vs.sh random heuristic 100 42

# Heuristic predators vs a custom prey policy class
bash scripts/run_pz_eval_vs.sh heuristic custom:scripts.agents.sample_custom_agent:FleeCentroid 50 7
```

See `scripts/agents/sample_custom_agent.py` for a minimal custom prey policy example.