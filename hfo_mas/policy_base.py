from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
import numpy as np


@dataclass
class StepContext:
    """Context passed to policies at each act call.

    Attributes:
        agent: The agent name (e.g., "adversary_0" or "agent_0").
        t: The current step index within the episode.
        episode: The episode index (0-based).
        shared: A mutable dict shared across agents for coordination.
        action_space: The Gym-like action space for this agent.
        observation_space: The Gym-like observation space for this agent.
        rng: A NumPy Generator for reproducible randomness.
    """

    agent: str
    t: int
    episode: int
    shared: dict
    action_space: Any
    observation_space: Any
    rng: np.random.Generator


class BasePolicy:
    """Base per-agent policy contract."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    def act(self, obs: np.ndarray, ctx: StepContext) -> Any:
        """Return an action for the given observation and context.

        Must return a value compatible with ctx.action_space.
        """
        raise NotImplementedError


class RandomPolicy(BasePolicy):
    """Samples uniformly from the action space."""

    def act(self, obs: np.ndarray, ctx: StepContext) -> Any:
        return ctx.action_space.sample()


class FnPolicy(BasePolicy):
    """Wrap a plain function into a policy: fn(obs, ctx) -> action."""

    def __init__(self, fn: Callable[[np.ndarray, StepContext], Any], seed: Optional[int] = None):
        super().__init__(seed=seed)
        self._fn = fn

    def act(self, obs: np.ndarray, ctx: StepContext) -> Any:
        return self._fn(obs, ctx)
