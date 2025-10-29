#!/usr/bin/env bash
set -euo pipefail

# Wrapper to run 2x2 matrix for simple_tag_v3 with continuous_actions=True
# Usage:
#   bash scripts/run_pz_simple_tag_matrix.sh [EPISODES] [SEED] [OUTDIR]
# Defaults: EPISODES=100, SEED=42, OUTDIR=hfo_petting_zoo_results

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "${PY}" ]]; then
  PY="python3"
fi

EPISODES="${1:-100}"
SEED="${2:-42}"
OUTDIR="${3:-hfo_petting_zoo_results}"

exec "${PY}" "${ROOT_DIR}/scripts/pz_matrix_simple_tag_v3.py" \
  --episodes "${EPISODES}" \
  --seed "${SEED}" \
  --outdir "${OUTDIR}"
