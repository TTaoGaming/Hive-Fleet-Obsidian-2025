#!/usr/bin/env bash
# Multi-Crew Parallel Orchestrator Runner
# Usage: bash scripts/run_multi_crew.sh [lanes] [explore_ratio]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Defaults
LANES="${1:-2}"
EXPLORE_RATIO="${2:-0.2}"

echo "🐝 Hive Fleet Obsidian - Multi-Crew Orchestrator"
echo "Lanes: $LANES (explore ratio: $EXPLORE_RATIO)"
echo ""

# Check for .env file
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "⚠️  .env file not found!"
    echo "   Copying .env.template to .env..."
    cp "$PROJECT_ROOT/.env.template" "$PROJECT_ROOT/.env"
    echo "   Please edit .env and add your OPENAI_API_KEY"
    echo "   Get one at: https://platform.openai.com/api-keys"
    exit 1
fi

# Set environment
export HFO_LANE_COUNT="$LANES"
export HFO_EXPLORE_EXPLOIT_RATIO="$EXPLORE_RATIO"
export HFO_MISSION_ID="multi_crew_parallel_$(date -u +%Y-%m-%d)"

# Run orchestrator
cd "$PROJECT_ROOT"
python3 scripts/hfo_multi_crew_orchestrator.py
