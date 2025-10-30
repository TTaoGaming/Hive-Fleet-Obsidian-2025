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
    inward_margin: float = 0.03  # target a point slightly inside the boundary relative to prey
    k_lead: float = 0.10         # small lead on prey velocity
    near_thr: float = 0.97
    bound: float = 1.0


class CornerClampPursuit:
    """
    Predator policy: aim for a point clamped just inside the boundary near the prey
    to avoid pushing exactly on the outward normal at walls/corners.
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

    def select_action(self, penv, agent_name: str):  # noqa: ANN001
        w, prey, preds = self._get_world(penv)
        aobj = next(a for a in preds + [prey] if getattr(a, 'name', None) == agent_name)
        assert getattr(aobj, 'adversary', False), "CornerClampPursuit is a predator policy"
        my_pos = aobj.state.p_pos.copy()
        prey_pos = prey.state.p_pos.copy()
        prey_vel = prey.state.p_vel.copy()

        # Predict prey slightly and then clamp target inside the boundary by inward_margin
        prey_future = prey_pos + self.params.k_lead * prey_vel
        margin = self.params.inward_margin
        bound = self.params.bound
        clamped = np.clip(prey_future, -bound + margin, bound - margin)
        d = unit(clamped - my_pos)
        return dir_to_continuous_action(d)
