# HiveFleetObsidian Project

## Purpose
HiveFleetObsidian is a research and development project focused on evolutionary AI systems, gem generation, audits, and baseline testing for MOLT shell simulations. It explores concepts like gene seeds, strategic synthesis, and swarm strategies in a structured, timestamped workflow.

## New: Multi-Crew Parallel Orchestration 🚀

A parallel multi-agent system using CrewAI with:
- **Disperse-Converge Pattern** - Parallel PREY lanes for distributed problem solving
- **Quorum Verification** - 2 of 3 validators (Immunizer, Disruptor, Verifier) must approve
- **Stigmergy** - Indirect coordination via blackboard JSONL
- **8/2 Explore/Exploit** - Quality diversity with 80% exploration, 20% exploitation
- **Safety Envelope** - Chunk limits, tripwires, auto-retry with scope reduction

**Quick Start:**
```bash
# Run demo (no API key needed)
bash run_multi_crew.sh demo

# Setup for production use
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run with real LLM agents
bash run_multi_crew.sh production
```

See [QUICKSTART_MULTI_CREW.md](QUICKSTART_MULTI_CREW.md) for full details.

## Structure
- **HFO_molt_shell_2025-10-25T16:24:00Z/**: Contains earlier pass data including audits_reports, baselines_results, core_scripts, gems (with duplicates and generations), summaries_docs, and todo/notes.
- **HFO_molt_shell_2025-10-25T17:00:00Z/**: Contains later pass data including audits_reports, baselines_results, core_scripts, summaries_docs, and handoff documents.

This setup enables tracking of project evolution across timestamps.

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