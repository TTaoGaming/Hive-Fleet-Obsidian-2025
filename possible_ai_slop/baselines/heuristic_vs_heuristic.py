import json
import numpy as np
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mpe2 import simple_tag_v3
from baselines.heuristic_predator import heuristic_predator_policy
from baselines.heuristic_prey import heuristic_prey_policy

# Set seed for reproducibility
np.random.seed(42)

env = simple_tag_v3.parallel_env(
    continuous_actions=True,
    max_cycles=25,
    num_adversaries=3,
    num_good=1
)

# Log environment parameters for debugging
print(f"Environment parameters:")
print(f"  local_ratio: {env.unwrapped.local_ratio}")
print(f"  max_cycles: {env.unwrapped.max_cycles}")
print(f"  continuous_actions: {env.unwrapped.continuous_actions}")
print(f"  num_adversaries: {env.unwrapped.num_adversaries}")
print(f"  num_good: {env.unwrapped.num_good}")
print(f"  map_size: {env.unwrapped.world_size}")

parser = argparse.ArgumentParser()
parser.add_argument('--episodes', type=int, default=100)
args = parser.parse_args()

episodes = []

for episode in range(args.episodes):
    obs, infos = env.reset()
    episode_rewards = {agent: 0 for agent in env.agents}
    captures = 0
    done = False
    
    step = 0
    while not done:
        actions = {}
        for agent in env.agents:
            if 'adversary' in agent:
                # Heuristic for adversaries (predators)
                obs_agent = obs[agent]
                actions[agent] = heuristic_predator_policy(obs_agent)
            else:
                # Heuristic for good (prey)
                obs_agent = obs[agent]
                actions[agent] = heuristic_prey_policy(obs_agent)
        
        obs, rewards, terminations, truncations, infos = env.step(actions)
        
        # Log first step observations for debugging (once per episode)
        if step == 0 and episode == 0:
            print(f"Sample observations (first step, first episode):")
            for agent in env.agents:
                print(f"  {agent}: shape={obs[agent].shape}, non-zero count={np.count_nonzero(obs[agent])}")
                # Print masked positions for one agent
                if 'adversary' in agent:
                    from baselines.heuristic_predator import mask_obs
                    masked = mask_obs(obs[agent], is_adversary=True)
                    print(f"    Masked non-zero positions: {np.where(masked != 0)}")
        
        # Accumulate rewards
        for agent in env.agents:
            episode_rewards[agent] += rewards.get(agent, 0)
        
        # Check for captures based on predator rewards (>=10 per step)
        capture_this_step = any(rewards.get(agent, 0) >= 10 for agent in env.agents if 'adversary' in agent)
        if capture_this_step:
            captures += 1
            print(f"Capture detected at step {step} in episode {episode}")
        
        done = all(terminations.values()) or all(truncations.values())
        step += 1
    
    done_reason = "capture" if captures > 0 else "max_cycles"
    
    episode_data = {
        "episode": episode,
        "rewards": episode_rewards,
        "captures": captures,
        "done_reason": done_reason
    }
    episodes.append(episode_data)

# Save to JSON
filename = f"heuristic_vs_heuristic_3pred1prey_local0.5_canary_{args.episodes}.json"
with open(filename, "w") as f:
    json.dump(episodes, f, indent=2)

print(f"Completed {len(episodes)} episodes. Average captures: {np.mean([e['captures'] for e in episodes]):.2f}")