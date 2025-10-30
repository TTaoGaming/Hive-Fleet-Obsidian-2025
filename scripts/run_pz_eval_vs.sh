#!/usr/bin/env bash
# Lightweight wrapper for scripts/pz_eval_simple_tag_v3.py
# Usage:
#   bash scripts/run_pz_eval_vs.sh <pred> <prey> [episodes] [seed] [outdir] [baseline]
# Examples:
#   bash scripts/run_pz_eval_vs.sh random heuristic 100 42
#   bash scripts/run_pz_eval_vs.sh heuristic custom:scripts.agents.sample_custom_agent:FleeCentroid 50 7
set -euo pipefail

PRED=${1:-heuristic}
PREY=${2:-random}
EPISODES=${3:-100}
SEED=${4:-42}
OUTDIR=${5:-hfo_petting_zoo_results}
BASELINE=${6:-research}

python3 "$(dirname "$0")/pz_eval_simple_tag_v3.py" \
  --pred "$PRED" \
  --prey "$PREY" \
  --episodes "$EPISODES" \
  --seed "$SEED" \
  --outdir "$OUTDIR" \
  --baseline "$BASELINE"
