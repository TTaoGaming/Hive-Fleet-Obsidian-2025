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
    k_lead: float = 0.35      # stronger lead on prey velocity than baseline
    inward_gain: float = 0.15 # small push inward when agent is near wall but prey is not
    near_thr: float = 0.97


class LeadTTIPursuit:
    """
    Predator policy: short-horizon lead/TTI-inspired pursuit with mild inward correction.
    Aims ahead of prey based on its velocity; adds inward push near boundaries to avoid
    pushing along the outward normal indefinitely.
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
        assert getattr(aobj, 'adversary', False), "LeadTTIPursuit is a predator policy"
        my_pos = aobj.state.p_pos.copy()
        prey_pos = prey.state.p_pos.copy()
        prey_vel = prey.state.p_vel.copy()

        # Lead pursuit
        prey_future = prey_pos + self.params.k_lead * prey_vel
        d = unit(prey_future - my_pos)

        # Mild inward correction if agent near wall and prey not
        near_agent = (abs(my_pos[0]) >= self.params.near_thr) or (abs(my_pos[1]) >= self.params.near_thr)
        near_prey = (abs(prey_pos[0]) >= self.params.near_thr) or (abs(prey_pos[1]) >= self.params.near_thr)
        if near_agent and not near_prey:
            inward = np.zeros(2, dtype=np.float32)
            for i in range(2):
                if abs(my_pos[i]) >= self.params.near_thr:
                    inward[i] = -self.params.inward_gain * np.sign(my_pos[i])
            d = unit(d + inward)

        return dir_to_continuous_action(d)
