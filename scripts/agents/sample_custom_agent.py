"""
Sample custom agent policies for simple_tag_v3 to use with pz_eval_simple_tag_v3.py

Usage example (prey uses FleeCentroid):
  python scripts/pz_eval_simple_tag_v3.py --pred heuristic --prey custom:scripts.agents.sample_custom_agent:FleeCentroid

Contract: classes must accept (role: str, baseline: str) in __init__ and implement
  select_action(self, penv, agent_name: str) -> np.ndarray | int
"""
from __future__ import annotations

import numpy as np

# Reuse mapping from a local copy if needed; otherwise inline minimal version

def _unit(v: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    n = np.linalg.norm(v)
    if n < eps:
        return np.zeros_like(v)
    return v / n


def _dir_to_continuous_action(d: np.ndarray) -> np.ndarray:
    ax = float(d[0]); ay = float(d[1])
    out = np.zeros(5, dtype=np.float32)
    if abs(ax) < 1e-6 and abs(ay) < 1e-6:
        out[0] = 1.0; return out
    if ax < 0: out[1] = -ax
    else: out[2] = ax
    if ay < 0: out[3] = -ay
    else: out[4] = ay
    mx = out[1:5].max() if out[1:5].size else 1.0
    if mx > 1e-6:
        out[1:5] = out[1:5] / mx
    return out


class FleeCentroid:
    """Prey policy: flee from the centroid of all predators.

    Works best when instantiated with role='prey'. If used for predators, it will
    fall back to random actions (from the env action_space).
    """
    def __init__(self, role: str = "prey", baseline: str = "research") -> None:  # noqa: D401
        self.role = role
        self.baseline = baseline

    def select_action(self, penv, agent_name: str):  # noqa: ANN001
        raw = penv.unwrapped
        w = raw.world
        aobj = next(a for a in w.agents if getattr(a, 'name', None) == agent_name)
        is_pred = getattr(aobj, 'adversary', False)
        if is_pred:
            # Not designed for predators; fall back to random
            return penv.action_space(agent_name).sample()
        my_pos = aobj.state.p_pos.copy()

        preds = [a for a in w.agents if getattr(a, 'adversary', False)]
        if not preds:
            return penv.action_space(agent_name).sample()
        centroid = sum((p.state.p_pos for p in preds), start=np.zeros(2)) / float(len(preds))
        desired = my_pos - centroid
        d = _unit(desired)
        return _dir_to_continuous_action(d)
