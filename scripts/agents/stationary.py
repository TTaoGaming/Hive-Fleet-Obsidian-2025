from __future__ import annotations

import numpy as np

from typing import Any

# Reuse dir_to_continuous_action by duplicating minimal logic to avoid circular import

def _dir_to_continuous_action(d: np.ndarray) -> np.ndarray:
    ax = float(d[0])
    ay = float(d[1])
    out = np.zeros(5, dtype=np.float32)
    if abs(ax) < 1e-6 and abs(ay) < 1e-6:
        out[0] = 1.0
        return out
    if ax < 0:
        out[1] = -ax
    else:
        out[2] = ax
    if ay < 0:
        out[3] = -ay
    else:
        out[4] = ay
    mx = out[1:5].max() if out[1:5].size else 1.0
    if mx > 1e-6:
        out[1:5] = out[1:5] / mx
    return out


class Stationary:
    """
    Stationary policy: outputs a no-op/zero-direction action to keep the agent still.
    Intended for prey in simple_tag_v3 continuous action space.
    """

    def __init__(self, role: str = "prey", baseline: str = "research", **kwargs: Any) -> None:  # noqa: ARG002
        self.role = role
        self.baseline = baseline

    def select_action(self, penv, agent_name: str):  # noqa: ANN001
        # Prefer explicit no-op encoding to be robust across wrappers
        return _dir_to_continuous_action(np.array([0.0, 0.0], dtype=np.float32))
