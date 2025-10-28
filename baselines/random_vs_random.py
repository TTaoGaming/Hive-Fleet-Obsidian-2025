import json
import numpy as np

from mpe2 import simple_tag_v3

# Set seed for reproducibility
np.random.seed(42)

env = simple_tag_v3.parallel_env(
    continuous_actions=True,
    max_cycles=25,
    num_adversaries=3,
    num_good=1
)

episodes = []

for episode in range(100):
    obs = env.reset()
    episode_rewards = {agent: 0 for agent in env.agents}
    captures = 0
    done = False
    
    while not done:
        actions = {}
        for agent in env.agents:
            # Random action
            actions[agent] = env.action_space(agent).sample()
        
        obs, rewards, terminations, truncations, infos = env.step(actions)
        
        # Accumulate rewards
        for agent in env.agents:
            episode_rewards[agent] += rewards[agent]
        
        # Check for captures (prey terminations)
        if any(terminations.values()):
            # Count terminated good agents (preys)
            for agent, terminated in terminations.items():
                if terminated and 'agent' in agent:  # agent names: 'adversary_*', 'agent_*'
                    captures += 1
        
        done = all(terminations.values()) or all(truncations.values())
    
    done_reason = "capture" if captures > 0 else "max_cycles"
    
    episode_data = {
        "episode": episode,
        "rewards": episode_rewards,
        "captures": captures,
        "done_reason": done_reason
    }
    episodes.append(episode_data)

# Save to JSON
with open("random_vs_random_3pred1prey_local0.5.json", "w") as f:
    json.dump(episodes, f, indent=2)

print(f"Completed {len(episodes)} episodes. Average captures: {np.mean([e['captures'] for e in episodes]):.2f}")