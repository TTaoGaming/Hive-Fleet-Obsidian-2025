from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from pettingzoo.mpe import simple_tag_v3

from .policy_base import BasePolicy, RandomPolicy
from .controllers import MultiAgentController, Coordinator


@dataclass
class EpisodeResult:
    caught: bool
    steps: int


def make_env(episodes: int, seed: int, continuous_actions: bool = True):
    env = simple_tag_v3.parallel_env(continuous_actions=continuous_actions)
    env.reset(seed=seed)
    return env


def build_controller(
    env,
    predator_policies: Sequence[BasePolicy] | Dict[str, BasePolicy] | BasePolicy,
    prey_policies: Sequence[BasePolicy] | Dict[str, BasePolicy] | BasePolicy,
    seed: Optional[int] = None,
    coordinator: Optional[Coordinator] = None,
) -> Tuple[MultiAgentController, Dict[str, str]]:
    agents = list(env.agents)
    roles = MultiAgentController.split_roles(agents)

    def expand(policies: Sequence[BasePolicy] | Dict[str, BasePolicy] | BasePolicy, want: List[str]) -> Dict[str, BasePolicy]:
        if isinstance(policies, BasePolicy):
            return {name: policies for name in want}
        if isinstance(policies, dict):
            return {name: policies[name] for name in want}
        # sequence: cycle or truncate
        out: Dict[str, BasePolicy] = {}
        for i, name in enumerate(want):
            out[name] = policies[i % len(policies)]
        return out

    predator_names = [a for a in agents if roles[a] == "predator"]
    prey_names = [a for a in agents if roles[a] == "prey"]

    p_map = expand(predator_policies, predator_names)
    q_map = expand(prey_policies, prey_names)

    policy_by_agent = {**p_map, **q_map}
    mac = MultiAgentController(policy_by_agent=policy_by_agent, coordinator=coordinator, seed=seed)
    return mac, roles


def run_episodes(
    episodes: int = 5,
    seed: int = 42,
    predator_policies: Sequence[BasePolicy] | Dict[str, BasePolicy] | BasePolicy = RandomPolicy(),
    prey_policies: Sequence[BasePolicy] | Dict[str, BasePolicy] | BasePolicy = RandomPolicy(),
    continuous_actions: bool = True,
    coordinator: Optional[Coordinator] = None,
) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)
    env = make_env(episodes=episodes, seed=seed, continuous_actions=continuous_actions)
    controller, roles = build_controller(env, predator_policies, prey_policies, seed=seed, coordinator=coordinator)

    caught_count = 0
    steps_to_first_catch: List[int] = []

    for ep in range(episodes):
        reset_ret = env.reset(seed=int(rng.integers(0, 2**31 - 1)))
        obs = reset_ret[0] if isinstance(reset_ret, tuple) else reset_ret
        shared: Dict[str, Any] = {"roles": roles}
        controller.coordinator.before_episode(ep, shared)

        t = 0
        first_catch_step: Optional[int] = None
        
        # Parallel API loop: act on current obs keys until env is done (env.agents becomes empty)
        while True:
            controller.coordinator.before_step(t, shared)

            if not obs:
                break
            actions = {}
            for agent in list(obs.keys()):
                a_space = env.action_space(agent)
                o_space = env.observation_space(agent)
                action = controller.act_for(agent, obs[agent], a_space, o_space, t=t, episode=ep, shared=shared)
                actions[agent] = action

            next_obs, rewards, terminated, truncated, info = env.step(actions)

            # Check catch event: in simple_tag, predators get positive reward on catch.
            # We'll consider any positive reward for any predator as a catch signal.
            if first_catch_step is None:
                for agent, r in rewards.items():
                    if roles.get(agent) == "predator" and r > 0:
                        first_catch_step = t + 1
                        break

            controller.coordinator.after_step(t, shared)
            obs = next_obs
            if not env.agents:
                break
            t += 1

        controller.coordinator.after_episode(ep, shared)

        if first_catch_step is not None:
            caught_count += 1
            steps_to_first_catch.append(first_catch_step)

    result = {
        "episodes": episodes,
        "seed": seed,
        "caught_episodes": caught_count,
        "catch_rate": caught_count / episodes if episodes > 0 else 0.0,
        "avg_steps_to_first_catch": float(np.mean(steps_to_first_catch)) if steps_to_first_catch else None,
        "steps_to_first_catch": steps_to_first_catch,
    }
    env.close()
    return result
