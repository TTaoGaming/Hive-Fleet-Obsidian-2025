from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Any, List


def unit(v: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n < eps:
        return np.zeros_like(v)
    return v / n


def dir_to_continuous_action(d: np.ndarray) -> np.ndarray:
    ax = float(d[0]); ay = float(d[1])
    out = np.zeros(5, dtype=np.float32)
    if abs(ax) < 1e-6 and abs(ay) < 1e-6:
        out[0] = 1.0
        return out
    out[1] = max(0.0, -ax)
    out[2] = max(0.0, ax)
    out[3] = max(0.0, -ay)
    out[4] = max(0.0, ay)
    mx = out[1:5].max() or 1.0
    out[1:5] = out[1:5] / mx
    return out


@dataclass
class Params:
    tangent_gain: float = 0.6  # how much to slide along wall when near boundary
    near_thr: float = 0.97     # abs(pos) >= near_thr considered near wall
    bound: float = 1.0         # world boundary
    k_lead: float = 0.15       # small lead on prey velocity


class WallTangentPursuit:
    """
    Predator policy: pursuit blended with wall-tangent sliding near boundaries.
    Intuition: when pushing straight into a wall/corner creates jams, add a tangential
    component along the boundary to flow around and close.
    """

    def __init__(self, role: str = "pred", baseline: str = "research", **kwargs: Any) -> None:  # noqa: ARG002
        self.role = role
        self.baseline = baseline
        p = Params(**{k: v for k, v in kwargs.items() if k in Params.__annotations__}) if kwargs else Params()
        self.params = p

    def _get_world(self, penv):
        raw = penv.unwrapped
        w = raw.world
        prey = [a for a in w.agents if not getattr(a, 'adversary', False)][0]
        preds: List[Any] = [a for a in w.agents if getattr(a, 'adversary', False)]
        return w, prey, preds

    def _wall_tangent(self, pos: np.ndarray) -> np.ndarray:
        # Compute outward normal for the dominant axis touching the boundary, then its tangent
        i = 0 if abs(pos[0]) >= abs(pos[1]) else 1
        normal = np.zeros(2, dtype=np.float32)
        normal[i] = np.sign(pos[i]) if abs(pos[i]) >= self.params.near_thr else 0.0
        # Tangent is perpendicular: rotate 90 degrees
        tangent = np.array([-normal[1], normal[0]], dtype=np.float32)
        if np.linalg.norm(tangent) < 1e-6:
            # If not clearly near one axis wall, choose tangent relative to radial direction
            radial = unit(pos)
            tangent = np.array([-radial[1], radial[0]], dtype=np.float32)
        return unit(tangent)

    def select_action(self, penv, agent_name: str):  # noqa: ANN001
        w, prey, preds = self._get_world(penv)
        aobj = next(a for a in preds + [prey] if getattr(a, 'name', None) == agent_name)
        assert getattr(aobj, 'adversary', False), "WallTangentPursuit is a predator policy"
        my_pos = aobj.state.p_pos.copy()
        my_vel = aobj.state.p_vel.copy()
        prey_pos = prey.state.p_pos.copy()
        prey_vel = prey.state.p_vel.copy()

        # Base pursuit with small lead
        desired = (prey_pos + self.params.k_lead * prey_vel) - my_pos
        d = unit(desired)

        # If near boundary (self or prey), blend with wall tangent
        near_self = (abs(my_pos[0]) >= self.params.near_thr) or (abs(my_pos[1]) >= self.params.near_thr)
        near_prey = (abs(prey_pos[0]) >= self.params.near_thr) or (abs(prey_pos[1]) >= self.params.near_thr)
        if near_self or near_prey:
            t = self._wall_tangent(my_pos if near_self else prey_pos)
            # choose tangent direction that reduces angle to prey vector
            if np.dot(t, (prey_pos - my_pos)) < 0:
                t = -t
            mix = np.clip(self.params.tangent_gain, 0.0, 1.0)
            d = unit((1.0 - mix) * d + mix * t)

        return dir_to_continuous_action(d)
