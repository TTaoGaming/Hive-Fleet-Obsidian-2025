import json
import numpy as np
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mpe2 import simple_tag_v3
from baselines.heuristic_predator import heuristic_predator_policy

# Set seed for reproducibility
np.random.seed(42)

env = simple_tag_v3.parallel_env(
    continuous_actions=True,
    max_cycles=100,
    num_adversaries=3,
    num_good=1
)

parser = argparse.ArgumentParser()
parser.add_argument('--episodes', type=int, default=100)
args = parser.parse_args()

episodes = []

for episode in range(args.episodes):
    obs, infos = env.reset()
    
    episode_rewards = {agent: 0 for agent in env.agents}
    captures = 0
    done = False
    
    while not done:
        actions = {}
        for agent in env.agents:
            if 'adversary' in agent:
                obs_agent = obs[agent]
                actions[agent] = heuristic_predator_policy(obs_agent)
            else:
                # Random for good agents
                actions[agent] = env.action_space(agent).sample()
        
        obs, rewards, terminations, truncations, infos = env.step(actions)
        
        # Accumulate rewards
        for agent in env.agents:
            episode_rewards[agent] += rewards.get(agent, 0)
        
        # Check for captures based on predator rewards (>=10 per step)
        capture_this_step = any(rewards.get(agent, 0) >= 10 for agent in env.agents if 'adversary' in agent)
        if capture_this_step:
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
filename = f"heuristic_pred_vs_random_prey_3pred1prey_local0.5_canary_{args.episodes}.json"
with open(filename, "w") as f:
    json.dump(episodes, f, indent=2)

print(f"Completed {len(episodes)} episodes. Average captures: {np.mean([e['captures'] for e in episodes]):.2f}")