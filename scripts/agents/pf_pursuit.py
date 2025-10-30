"""
Potential-Field Pursuit policy for simple_tag_v3 (predators).
Attracts to prey, repels walls and obstacles. Single-agent friendly.

Usage with evaluator:
  python scripts/pz_eval_simple_tag_v3.py \
    --pred custom:scripts.agents.pf_pursuit:PFPursuit \
    --prey heuristic --episodes 20 --seed 42
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


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


@dataclass
class Params:
    k_attr: float = 1.0
    k_rep_obs: float = 0.8
    k_rep_wall: float = 0.0  # scale wall repulsion (0 disables)
    r_inf: float = 0.25  # influence radius for obstacles/walls
    heading_ema: float = 0.0  # 0 = off
    max_speed: float = 1.0
    wall_margin: float = 0.02  # treat wall as at |pos|>=1.0; start repelling when within (1 - wall_margin)


class PFPursuit:
    def __init__(self, role: str = "pred", baseline: str = "research", **kwargs) -> None:  # noqa: D401
        self.role = role
        self.baseline = baseline
        self.p = Params(**kwargs)
        self._ema_dir = np.zeros(2, dtype=np.float32)

    def select_action(self, penv, agent_name: str):  # noqa: ANN001
        # Only meaningful for predators; prey falls back to random
        raw = penv.unwrapped
        w = raw.world
        aobj = next(a for a in w.agents if getattr(a, 'name', None) == agent_name)
        is_pred = getattr(aobj, 'adversary', False)
        if not is_pred:
            return penv.action_space(agent_name).sample()

        # State
        my_pos = aobj.state.p_pos.copy()
        prey = [a for a in w.agents if not getattr(a, 'adversary', False)][0]
        prey_pos = prey.state.p_pos.copy()
        landmarks = [l for l in w.landmarks]

        # Attractive component
        v_attr = self.p.k_attr * _unit(prey_pos - my_pos)

        # Obstacle repulsion (landmarks as obstacles)
        v_rep_obs = np.zeros(2, dtype=np.float32)
        for l in landmarks:
            o = l.state.p_pos.copy()
            d = my_pos - o
            dist = np.linalg.norm(d) + 1e-6
            if dist < self.p.r_inf:
                v_rep_obs += (1.0 / dist - 1.0 / self.p.r_inf) * _unit(d)
        v_rep_obs *= self.p.k_rep_obs

        # Wall repulsion (box [-1,1]^2)
        v_rep_wall = np.zeros(2, dtype=np.float32)
        bound = 1.0
        margin = self.p.r_inf
        for i in range(2):
            # distance to +wall and -wall
            dist_pos = (bound - my_pos[i])
            dist_neg = (bound + my_pos[i])
            if dist_pos < margin:
                v_rep_wall[i] -= (1.0 / max(dist_pos, 1e-6) - 1.0 / margin)
            if dist_neg < margin:
                v_rep_wall[i] += (1.0 / max(dist_neg, 1e-6) - 1.0 / margin)

        # Scale wall repulsion and combine
        v = v_attr + v_rep_obs + (self.p.k_rep_wall * v_rep_wall)
        d = _unit(v)

        # EMA heading smoothing
        if self.p.heading_ema > 0.0:
            self._ema_dir = (
                self.p.heading_ema * d + (1.0 - self.p.heading_ema) * self._ema_dir
            )
            d = _unit(self._ema_dir)

        return _dir_to_continuous_action(d)
