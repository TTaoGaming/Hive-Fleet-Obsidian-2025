# Gen21 MAS: PettingZoo simple_tag_v3 — Stabilized Baseline (Oct 29, 2025)

This document captures the known-good baseline, run instructions, and expected 2×2 results for the PettingZoo MPE `simple_tag_v3` setup, so we can quickly detect and recover from regressions.

## Snapshot

- Baseline tag (known-good): `pz-matrix-verified-20251029-100eps` → commit `8a9e1c6`
- Stabilization merge into main: commit `a64658e` (Merge: revert to matrix-verified baseline + add MAS canary CI + pre-commit)
- Date: 2025-10-29

## Components and paths

- 2×2 matrix runner: `scripts/pz_matrix_simple_tag_v3.py`
  - Continuous actions, simple pursuit predator, flee prey
  - Emits JSON results to `hfo_petting_zoo_results/`
  - Verification checks included in JSON and enforceable via flags
- Quick runner wrapper: `scripts/run_pz_simple_tag_matrix.sh`
- Random-vs-Random verifier: `scripts/pz_verify_simple_tag_v3.py`
- CI Canary: `.github/workflows/mas-canary.yml`
  - Runs on PRs/pushes touching MAS/scripts
  - Fails if ordering violated or HvsR below threshold
- Pre-commit: `.pre-commit-config.yaml`
  - Lightweight 10-episode canary (HvsR min 0.60) + hygiene hooks

## How to run (local quick checks)

- 2×2 quick matrix (fast canary):

```bash
bash scripts/run_pz_simple_tag_matrix.sh 20 42
```

- Direct Python invocation with hard gates:

```bash
python3 scripts/pz_matrix_simple_tag_v3.py \
  --episodes 20 \
  --seed 42 \
  --outdir hfo_petting_zoo_results \
  --min-hvsr 0.70
```

- Generate a 2×2 animated GIF (3 episodes/cell by default):

```bash
# Simple wrapper (uses .venv if present) and writes to dated folder
bash scripts/run_pz_make_matrix_gif.sh

# Or call the Python script directly and choose an output folder
python3 scripts/pz_make_matrix_gif.py --episodes 3 --seed 42 --max-cycles 25 --duration-ms 120 --outdir hfo_petting_zoo_results/$(date +%Y-%m-%d)
```
Output file example: `hfo_petting_zoo_results/YYYY-MM-DD/simple_tag_v3_matrix_<TS>_seed<seed>_eps<episodes>.gif`

Flags in `pz_matrix_simple_tag_v3.py`:
- `--min-hvsr <float>`: fail if HvsR catch_rate falls below this threshold
- `--no-fail-on-bad-ordering`: disable failure on ordering violations (default is to fail)

## Expected ordering and typical results

Ordering that should hold:
- HvsR ≥ RvsR
- RvsH ≤ RvsR
- HvsH ≤ HvsR

Typical catch rates observed on the stabilized baseline:
- Episodes per cell = 20, seed = 42 (quick canary)
  - RvsR ≈ 0.05–0.20
  - HvsR ≈ 1.00
  - RvsH ≈ 0.00
  - HvsH ≈ 0.00–0.10
- Episodes per cell = 100, seeds = {42, 5} (matrix verification runs)
  - HvsR commonly ≥ 0.85–0.95
  - Ordering constraints above should pass

Note: Use the JSON outputs in `hfo_petting_zoo_results/` as ground truth for specific runs.

## CI and pre-commit gates

- CI (GitHub Actions): runs 20 eps/cell, seed 42; fails build if:
  - HvsR < 0.70, or
  - Any ordering rule is violated
- Pre-commit (local): runs 10 eps/cell, seed 42; fails commit if:
  - HvsR < 0.60, or
  - Any ordering rule is violated

These guardrails keep `main` stable and catch regressions early on branches.

## Recovery/rollback guide

- Quick reset to known-good code for triage:

```bash
git checkout pz-matrix-verified-20251029-100eps  # commit 8a9e1c6
```

- Dedicated rollback branch (frozen at known-good): `rollback/pz-matrix-verified-20251029`
- Stabilization branch used for revert PR: `stabilize/pz-matrix-verified-20251029`

If `main` regresses, prefer a revert PR to return to `8a9e1c6` (history-preserving), or cherry-pick only MAS files from that tag.

## Notes

- Requirements pinned in `requirements.txt` (includes `pettingzoo`, `gymnasium`, `mpe2`, `numpy`, `pygame`, `Pillow`).
- Environment differences (library versions/OS/Python) can slightly shift catch rates; rely on ordering and thresholds to judge pass/fail.
- JSON result filenames encode parameters: `hfo_petting_zoo_results/simple_tag_v3_matrix_<TIMESTAMP>_seed<seed>_eps<episodes>.json`.
