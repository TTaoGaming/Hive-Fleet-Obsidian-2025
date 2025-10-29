from __future__ import annotations

from typing import Any, Dict, Iterable, Optional
import numpy as np

from .policy_base import BasePolicy, StepContext


class Coordinator:
    """Optional team-level coordinator for hierarchical/homogeneous control.

    Override any hook(s) you need. By default they are no-ops.
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    # Episode lifecycle
    def before_episode(self, episode: int, shared: Dict[str, Any]) -> None:
        pass

    def after_episode(self, episode: int, shared: Dict[str, Any]) -> None:
        pass

    # Step lifecycle
    def before_step(self, t: int, shared: Dict[str, Any]) -> None:
        pass

    def after_step(self, t: int, shared: Dict[str, Any]) -> None:
        pass


class MultiAgentController:
    """Maps each PettingZoo agent to a policy instance, with optional Coordinator.

    Supports heterogeneous predators and prey policies. Provide a dict mapping
    agent_name -> policy, or provide two dicts (predators and prey) and the
    controller will assign by name.
    """

    def __init__(
        self,
        policy_by_agent: Dict[str, BasePolicy],
        coordinator: Optional[Coordinator] = None,
        seed: Optional[int] = None,
    ):
        self.policy_by_agent = policy_by_agent
        self.coordinator = coordinator or Coordinator(seed=seed)
        self.rng = np.random.default_rng(seed)

    @staticmethod
    def split_roles(agent_names: Iterable[str]) -> Dict[str, str]:
        """Infer roles by name: 'adversary_*' -> predator, others -> prey."""
        roles = {}
        for name in agent_names:
            if "adversary" in name:
                roles[name] = "predator"
            else:
                roles[name] = "prey"
        return roles

    def act_for(self, agent: str, obs, action_space, observation_space, t: int, episode: int, shared: Dict[str, Any]):
        policy = self.policy_by_agent[agent]
        ctx = StepContext(
            agent=agent,
            t=t,
            episode=episode,
            shared=shared,
            action_space=action_space,
            observation_space=observation_space,
            rng=self.rng,
        )
        return policy.act(obs, ctx)
