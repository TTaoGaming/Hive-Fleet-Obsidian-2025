from __future__ import annotations

from typing import Any, Optional
import numpy as np

from .policy_base import BasePolicy, StepContext


class HeuristicChasePolicy(BasePolicy):
    """Very simple predator heuristic for simple_tag_v3.

    Assumptions:
    - Observation vector for predators ends with the relative position to the prey (dx, dy).
    - Works for both continuous and discrete action spaces.

    If the assumption is off, it still moves toward the last two features, which
    often correlates with the main target in MPE layouts; this tends to produce
    some catches over multiple episodes.
    """

    def __init__(self, speed: float = 1.0, seed: Optional[int] = None):
        super().__init__(seed=seed)
        self.speed = float(speed)

    def _to_discrete(self, vec: np.ndarray, ctx: StepContext) -> int:
        # Map a 2D vector to one of 5 actions: 0=up,1=down,2=right,3=left,4=stay (typical MPE mapping)
        x, y = float(vec[0]), float(vec[1])
        if abs(x) < 1e-6 and abs(y) < 1e-6:
            return 4
        if abs(x) > abs(y):
            return 2 if x > 0 else 3
        else:
            return 0 if y > 0 else 1

    def _to_continuous(self, vec: np.ndarray, ctx: StepContext):
        # Map to action space shape. Some MPE envs expose continuous 2D accel; others 5D thrust-like.
        shape = getattr(ctx.action_space, 'shape', None)
        if shape is not None and len(shape) > 0:
            n = int(shape[0])
        else:
            n = 2
        if n == 2:
            a = vec.astype(np.float32)
            norm = np.linalg.norm(a) + 1e-8
            a = (a / norm) * self.speed
        elif n == 5:
            # One-hot like control for [up, down, right, left, stay]
            idx = self._to_discrete(vec, ctx)
            a = np.zeros(5, dtype=np.float32)
            a[idx] = 1.0
        else:
            # Fallback: pad/truncate 2D to n dims
            base = vec.astype(np.float32)
            norm = np.linalg.norm(base) + 1e-8
            base = (base / norm) * self.speed
            a = np.zeros(n, dtype=np.float32)
            a[: min(n, 2)] = base[: min(n, 2)]
        if hasattr(ctx.action_space, 'low') and hasattr(ctx.action_space, 'high'):
            low = np.array(ctx.action_space.low, dtype=np.float32)
            high = np.array(ctx.action_space.high, dtype=np.float32)
            a = np.clip(a, low, high)
        return a

    def act(self, obs: np.ndarray, ctx: StepContext) -> Any:
        # Heuristic: chase vector from last 2 dims of obs
        if not isinstance(obs, np.ndarray):
            obs = np.asarray(obs, dtype=np.float32)
        if obs.size >= 2:
            target_vec = obs[-2:]
        else:
            target_vec = np.zeros(2, dtype=np.float32)

        # If we're a prey (agent not adversary), just random-walk
        if 'adversary' not in ctx.agent:
            return ctx.action_space.sample()

        # Choose action kind by action space type
        if hasattr(ctx.action_space, 'n'):
            return self._to_discrete(target_vec, ctx)
        else:
            return self._to_continuous(target_vec, ctx)


class PreyFleePolicy(BasePolicy):
    """Simple prey evasion heuristic: move opposite the last-2-dim vector.

    Same observation assumption as HeuristicChasePolicy but inverted. For
    predators (if mis-assigned), defaults to random.
    """

    def __init__(self, speed: float = 1.0, seed: Optional[int] = None):
        super().__init__(seed=seed)
        self.speed = float(speed)

    def _to_discrete(self, vec: np.ndarray, ctx: StepContext) -> int:
        x, y = float(vec[0]), float(vec[1])
        if abs(x) < 1e-6 and abs(y) < 1e-6:
            return 4
        if abs(x) > abs(y):
            return 3 if x > 0 else 2  # invert left/right
        else:
            return 1 if y > 0 else 0  # invert up/down

    def _to_continuous(self, vec: np.ndarray, ctx: StepContext):
        shape = getattr(ctx.action_space, 'shape', None)
        n = int(shape[0]) if shape is not None and len(shape) > 0 else 2
        v = -vec  # flee = opposite direction
        if n == 2:
            a = v.astype(np.float32)
            norm = np.linalg.norm(a) + 1e-8
            a = (a / norm) * self.speed
        elif n == 5:
            idx = HeuristicChasePolicy()._to_discrete(v, ctx)  # reuse mapping
            a = np.zeros(5, dtype=np.float32)
            a[idx] = 1.0
        else:
            base = v.astype(np.float32)
            norm = np.linalg.norm(base) + 1e-8
            base = (base / norm) * self.speed
            a = np.zeros(n, dtype=np.float32)
            a[: min(n, 2)] = base[: min(n, 2)]
        if hasattr(ctx.action_space, 'low') and hasattr(ctx.action_space, 'high'):
            low = np.array(ctx.action_space.low, dtype=np.float32)
            high = np.array(ctx.action_space.high, dtype=np.float32)
            a = np.clip(a, low, high)
        return a

    def act(self, obs: np.ndarray, ctx: StepContext) -> Any:
        if 'adversary' in ctx.agent:
            return ctx.action_space.sample()  # if assigned to predator, do random
        if not isinstance(obs, np.ndarray):
            obs = np.asarray(obs, dtype=np.float32)
        target_vec = obs[-2:] if obs.size >= 2 else np.zeros(2, dtype=np.float32)
        if hasattr(ctx.action_space, 'n'):
            return self._to_discrete(target_vec, ctx)
        else:
            return self._to_continuous(target_vec, ctx)
