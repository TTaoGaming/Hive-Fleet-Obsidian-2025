#!/usr/bin/env bash
set -euo pipefail

# Generate a 2x2 simple_tag_v3 GIF with 3 episodes per cell into a dated folder.
# Usage: bash scripts/run_pz_make_matrix_gif.sh [SEED] [MAX_CYCLES] [DURATION_MS]
# Defaults: SEED=42, MAX_CYCLES=25, DURATION_MS=120

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "${PY}" ]]; then
  PY="python3"
fi

SEED="${1:-42}"
MAX_CYCLES="${2:-25}"
DURATION_MS="${3:-120}"

DATE_DIR="$(date +%Y-%m-%d)"
OUTDIR="${ROOT_DIR}/hfo_petting_zoo_results/${DATE_DIR}"
mkdir -p "${OUTDIR}"

exec "${PY}" "${ROOT_DIR}/scripts/pz_make_matrix_gif.py" \
  --episodes 3 \
  --seed "${SEED}" \
  --max-cycles "${MAX_CYCLES}" \
  --duration-ms "${DURATION_MS}" \
  --outdir "${OUTDIR}"
#!/usr/bin/env bash
set -euo pipefail

# Wrapper to generate a 2x2 animated GIF for PettingZoo simple_tag_v3
# Usage:
#   bash scripts/run_pz_make_matrix_gif.sh [EPISODES] [SEED] [MAX_CYCLES] [DURATION_MS]
# Defaults:
#   EPISODES=3  SEED=42  MAX_CYCLES=25  DURATION_MS=120
# Output directory:
#   hfo_petting_zoo_results/YYYY-MM-DD/

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "${PY}" ]]; then
  PY="python3"
fi

EPISODES="${1:-3}"
SEED="${2:-42}"
MAX_CYCLES="${3:-25}"
DURATION_MS="${4:-120}"

DATE_DIR="${ROOT_DIR}/hfo_petting_zoo_results/$(date +%F)"
mkdir -p "${DATE_DIR}"

exec "${PY}" "${ROOT_DIR}/scripts/pz_make_matrix_gif.py" \
  --episodes "${EPISODES}" \
  --seed "${SEED}" \
  --max-cycles "${MAX_CYCLES}" \
  --duration-ms "${DURATION_MS}" \
  --outdir "${DATE_DIR}"
