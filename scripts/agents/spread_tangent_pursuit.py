from __future__ import annotations

import re
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


def _agent_index(name: str) -> int:
    m = re.search(r"(\d+)$", name)
    return int(m.group(1)) if m else 0


@dataclass
class Params:
    tangent_gain: float = 0.8   # stronger slide along wall
    offset_mag: float = 0.08    # lateral offset target along tangent to reduce crowding
    near_thr: float = 0.97
    k_lead: float = 0.20


class SpreadTangentPursuit:
    """
    Predator policy: wall-tangent sliding plus per-agent lateral offset to avoid crowding.
    Each predator targets a slightly different point along the tangent near walls, improving closure.
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
        i = 0 if abs(pos[0]) >= abs(pos[1]) else 1
        normal = np.zeros(2, dtype=np.float32)
        # If clearly at/near wall, set normal axis
        if abs(pos[i]) >= self.params.near_thr:
            normal[i] = np.sign(pos[i])
        else:
            radial = unit(pos)
            normal = radial
        tangent = np.array([-normal[1], normal[0]], dtype=np.float32)
        return unit(tangent)

    def select_action(self, penv, agent_name: str):  # noqa: ANN001
        w, prey, preds = self._get_world(penv)
        aobj = next(a for a in preds + [prey] if getattr(a, 'name', None) == agent_name)
        assert getattr(aobj, 'adversary', False), "SpreadTangentPursuit is a predator policy"
        idx = _agent_index(agent_name)

        my_pos = aobj.state.p_pos.copy()
        prey_pos = prey.state.p_pos.copy()
        prey_vel = prey.state.p_vel.copy()

        # Base: lead pursuit
        prey_future = prey_pos + self.params.k_lead * prey_vel
        d = unit(prey_future - my_pos)

        # If near boundary (self or prey), slide along tangent and offset aimpoint
        near_self = (abs(my_pos[0]) >= self.params.near_thr) or (abs(my_pos[1]) >= self.params.near_thr)
        near_prey = (abs(prey_pos[0]) >= self.params.near_thr) or (abs(prey_pos[1]) >= self.params.near_thr)
        if near_self or near_prey:
            base = my_pos if near_self else prey_pos
            t = self._wall_tangent(base)
            # Alternate sign by index to spread to both sides of corner/edge
            if (idx % 2) == 1:
                t = -t
            # set target slightly along tangent from prey, then aim there
            aim = prey_pos + self.params.offset_mag * t
            desired = aim - my_pos
            # blend with pursuit
            mix = np.clip(self.params.tangent_gain, 0.0, 1.0)
            d = unit((1.0 - mix) * d + mix * unit(desired))

        return dir_to_continuous_action(d)
