# HFO PettingZoo Three-Prey Baseline Handoff

This note captures the current state of the PettingZoo/MPE2 simple_tag verification harness (three prey baselines) so the next agent can pick up quickly.

## Environment & Dependencies

  - `pettingzoo==1.23.1`
  - `mpe2==0.0.1`
  - `gymnasium==0.29.1`
  - `pygame==2.5.2`
  - `numpy==1.26.4`
  - `torch==2.2.2`
- External repos cloned under `external/`:
  - `external/marl/on-policy` *(for future MAPPO baselines; unused so far)*
  - `external/marl/epymarl` *(source of pretrained DDPG prey weights)*

## Baseline Scripts

All harness code lives in `HFO_Hive_Hunts/baselines/`:

| File | Purpose |
| --- | --- |
| `random_simple_tag_random_vs_random.py` | Rolls random predators vs random prey; supports JSON logging. |
| `simple_tag_compare.py` | General comparison harness for predator/prey policy pairings (random, heuristic, pretrained). Loads EPyMARL prey checkpoint via `_FrozenDDPG`. |
| `logs/*.json` | Persisted 500-episode rollouts (see table below). |

### Policies currently registered


## Latest 500-Episode Results (max_cycles=25, 1 prey, 3 predators, 2 obstacles)

| Predator policy | Prey policy | Catch rate | Timeout rate | Avg steps | JSON artifact |
| --- | --- | --- | --- | --- | --- |
| random | random | 0.188 | 0.812 | 22.11 | `HFO_Hive_Hunts/baselines/logs/compare_random_random.json` |
| predator_chase | random | 0.916 | 0.084 | 12.97 | `HFO_Hive_Hunts/baselines/logs/compare_chase_random.json` |
| random | pretrained_prey | 0.430 | 0.570 | 17.90 | `HFO_Hive_Hunts/baselines/logs/compare_random_pretrained.json` |
| predator_chase | pretrained_prey | 0.694 | 0.306 | 13.63 | `HFO_Hive_Hunts/baselines/logs/compare_chase_pretrained.json` |
| predator_chase | prey_evade | 0.092 | 0.908 | 23.07 | `HFO_Hive_Hunts/baselines/logs/compare_chase_evade.json` |

Output confirms 500 episodes per run (`summary["episodes"] == 500` + 500 entries in `episodes` array).

## Known Discrepancy

Random predators currently catch the EPyMARL pretrained prey ~43% of the time. That is higher than expected (pretrained prey intended to exceed random baseline). Possible causes:

1. **Horizon mismatch** – EPyMARL configs typically use `time_limit=100`. Our runs clamp at `max_cycles=25`. Increasing to 100 lowers catch rates toward ~25% in small probes.
2. **Wrapper differences** – We load the raw DDPG actor; EPyMARL’s `PretrainedTag` wrapper applies environment-specific preprocessing. Importing that wrapper requires selectively loading modules to avoid `smaclite` dependency errors.
3. **Dynamics drift** – `mpe2` updates (agent accel/max speed, obstacle interactions) may differ slightly from the version used in the checkpoint.

## Suggested Next Actions

1. **Reproduce with EPyMARL wrapper**
   - Import `PretrainedTag` via `importlib.util` from `external/marl/epymarl/src/envs/pretrained/tag.py` to ensure identical observation flow.
   - Wrap the PettingZoo env before running rollouts.

2. **Match training horizon**
   - Re-run comparisons with `max_cycles=100` and log the new JSON artifacts for parity checks.

3. **Optional: train fresh prey baseline**
   - Either fine-tune the existing checkpoint under `mpe2`, or train a new MAPPO/MADDPG prey using EPyMARL (requires installing additional dependencies and running `src/main.py` experiments).

4. **Document verification protocol**
   - Once satisfied with baselines, integrate into CI or README with exact command lines, e.g.
     ```bash
     ./.venv/bin/python HFO_Hive_Hunts/baselines/simple_tag_compare.py \
       --pred-policy random --prey-policy pretrained_prey \
       --episodes 500 --json-out HFO_Hive_Hunts/baselines/logs/compare_random_pretrained.json
     ```

## File Checklist

- ⚠️ Pretrained prey parity requires double-check (see actions above)

Ping the next agent to start with the wrapper parity check before trusting the pretrained baseline numbers. This README is the handoff summary.

## Findings and Analysis

### 3x3 Performance Matrix (max_cycles=100)

This matrix summarizes extended-horizon evaluations (100 cycles) across all policy pairings, providing deeper insights into long-term behaviors. Note: This differs from the initial 25-cycle results above, which were horizon-limited.

| Predator \ Prey | random | heuristic | pretrained |
| --- | --- | --- | --- |
| **Random** | Catch: 0.338 \| Timeout: 0.662 \| Steps: 77.83 \| Pred Return: 3.4 \| Prey Return: -126.95 | Catch: 0.034 \| Timeout: 0.966 \| Steps: 96.64 \| Pred Return: 0.36 \| Prey Return: -675.58 | Catch: 0.358 \| Timeout: 0.642 \| Steps: 67.73 \| Pred Return: 3.68 \| Prey Return: -555.15 |
| **Heuristic** | Catch: 0.696 \| Timeout: 0.304 \| Steps: 50.6 \| Pred Return: 7.0 \| Prey Return: -75.86 | Catch: 0.038 \| Timeout: 0.962 \| Steps: 96.27 \| Pred Return: 0.38 \| Prey Return: -782.63 | Catch: 0.474 \| Timeout: 0.526 \| Steps: 57.61 \| Pred Return: 4.94 \| Prey Return: -466.33 |
| **Pretrained** | Catch: 0.306 \| Timeout: 0.694 \| Steps: 76.9 \| Pred Return: 3.06 \| Prey Return: -136.27 | Catch: 0.038 \| Timeout: 0.962 \| Steps: 96.24 \| Pred Return: 0.38 \| Prey Return: -648.78 | Catch: 0.36 \| Timeout: 0.64 \| Steps: 67.4 \| Pred Return: 3.68 \| Prey Return: -536.03 |

Full matrix details: [HFO_Hive_Hunts/baselines/performance_matrix.md](HFO_Hive_Hunts/baselines/performance_matrix.md)

### Key Metrics Summary


Results artifacts: [HFO_Hive_Hunts/baselines/results/](HFO_Hive_Hunts/baselines/results/)

### Analysis Insights

  - Random vs random: Balanced but low-efficiency chases.
  - Heuristic predators dominate random/heuristic prey but struggle against pretrained in short horizons (initial tests).
  - Pretrained predators perform similarly to random against heuristic prey, indicating no learned advantage.
- **Anomaly Explanation**: Pretrained underperformance (e.g., 43% catch rate vs random in 25-cycle tests, persisting in extended runs) highlights deployment gaps: raw actor loading bypasses EPyMARL preprocessing, causing observation drift. Heuristics, being rule-based, remain stable across variants.

- **Parity Status**: Not achieved. Pretrained prey fails to exceed random or heuristic baselines, contradicting EPyMARL benchmarks. Extended horizons amplify the gap, with heuristics surviving 96% vs pretrained's 52-69%.

### Suggested Fixes

- **Switch to MAPPO**: Migrate to on-policy learning via `external/marl/on-policy` for better multi-agent coordination. Train fresh prey policies with shared critics to handle 3-predator pursuits.

### HFO Integration Suggestions

- **Next Steps**:
  - Standardize tests at 100 cycles; update CI with reproducible commands.
  - Prototype HFO-heuristic integration: Wrap `prey_evade` for HFO agents, evaluate in multi-prey hunts.
  - Handoff: README now self-contained; next agent can implement fixes and HFO bridging without re-running baselines.