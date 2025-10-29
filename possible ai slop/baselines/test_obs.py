import numpy as np
from pettingzoo.mpe import simple_tag_v3

env = simple_tag_v3.parallel_env(
    continuous_actions=True,
    max_cycles=25,
    num_adversaries=3,
    num_good=1
)

obs, _ = env.reset()

print("Agents:", env.agents)
for agent in env.agents:
    print(f"\n{agent} obs shape: {obs[agent].shape}, obs: {obs[agent]}")

# Take one step with random actions
actions = {agent: env.action_space(agent).sample() for agent in env.agents}
obs, rewards, term, trunc, info = env.step(actions)

print("\nAfter one step:")
for agent in env.agents:
    print(f"\n{agent} obs shape: {obs[agent].shape}, obs: {obs[agent]}")