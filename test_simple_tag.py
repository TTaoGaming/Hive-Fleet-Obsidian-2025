from mpe2 import simple_tag_v3

env = simple_tag_v3.parallel_env(
    num_good=1,
    num_adversaries=3,
    num_obstacles=2,
    max_cycles=25,
    continuous_actions=False
)

env.reset()

terminated = {agent: False for agent in env.agents}
truncated = {agent: False for agent in env.agents}
episode_steps = 0

while not all(terminated.values()) and not all(truncated.values()) and episode_steps < 25:
    actions = {agent: env.action_space(agent).sample() for agent in env.agents}
    observations, rewards, terminated, truncated, infos = env.step(actions)
    episode_steps += 1

print(f"Simulation completed successfully after {episode_steps} steps.")