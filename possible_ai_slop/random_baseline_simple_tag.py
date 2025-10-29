import json
import numpy as np
from pettingzoo.mpe import simple_tag_v3

env = simple_tag_v3.parallel_env(
    num_good=1,
    num_adversaries=3,
    num_obstacles=2,
    max_cycles=25,
    continuous_actions=True
)

num_episodes = 100
capture_episodes = 0

for episode in range(num_episodes):
    observations = env.reset()
    episode_capture = False
    terminated = {agent: False for agent in env.agents}
    truncated = {agent: False for agent in env.agents}
    
    while not all(terminated.values()) and not all(truncated.values()):
        actions = {agent: env.action_space(agent).sample() for agent in env.agents}
        observations, rewards, terminations, truncations, infos = env.step(actions)
        terminated.update(terminations)
        truncated.update(truncations)
        
        # Check for capture: if any good agent received -10 reward (collision)
        for agent in env.agents:
            if 'agent' in agent and rewards[agent] <= -10:
                episode_capture = True
                break
    
    if episode_capture:
        capture_episodes += 1

capture_rate = (capture_episodes / num_episodes) * 100

print(f"Capture rate for random policies (3 predators vs 1 prey): {capture_rate:.2f}%")

data = {
    "paper": "Multi-Agent Actor-Critic for Mixed Cooperative-Competitive Environments (Lowe et al., 2017)",
    "settings": {
        "num_adversaries": 3,  # predators
        "num_good": 1,  # prey
        "continuous_actions": True,
        "max_cycles": 25,
        "local_ratio": 1.0  # full observations, no partial masking in base simple_tag
    },
    "random_capture_rate_percent": round(capture_rate, 2),
    "num_episodes": num_episodes,
    "env_config": {
        "num_obstacles": 2
    }
}

with open("simple_tag_lowe_settings.json", "w") as f:
    json.dump(data, f, indent=4)

print("Data saved to simple_tag_lowe_settings.json")