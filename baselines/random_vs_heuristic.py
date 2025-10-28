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

def mask_obs(obs, local_ratio=0.5):
    masked = obs.copy()
    # For adversary: obs shape 16
    # landmarks rel pos: indices 4:8 (2 landmarks * 2)
    for i in range(2):
        pos_start = 4 + i * 2
        rel_pos = masked[pos_start:pos_start + 2]
        dist = np.linalg.norm(rel_pos)
        if dist > local_ratio:
            masked[pos_start:pos_start + 2] = 0.0

    # other agents rel pos: 8:14 (3 * 2)
    for i in range(3):
        pos_start = 8 + i * 2
        rel_pos = masked[pos_start:pos_start + 2]
        dist = np.linalg.norm(rel_pos)
        if dist > local_ratio:
            masked[pos_start:pos_start + 2] = 0.0
            # Mask corresponding vel if good agent, but since vel is only for good, and heuristic doesn't use vel, skip detailed

    # For good agent obs 14, similar but no other_vel
    return masked


def get_action_for_adversary(obs_adversary):
    obs_adversary = mask_obs(obs_adversary)
    # Obs structure for adversary: vel(2) + own_pos(2) + landmarks(4) + other agents relative(6 for 3 others) + other_vel(2) = 16
    # Other agents relative positions: indices 8:14, reshape to 3x2
    relative_pos = obs_adversary[8:14].reshape(3, 2)
    
    # Own position not needed for relative direction, since relative_pos are already relative to own
    distances = np.linalg.norm(relative_pos, axis=1)
    
    # Find closest non-zero distance
    valid_distances = distances[distances > 0]
    if len(valid_distances) == 0:
        # No visible agents, stay still
        direction = np.array([0.0, 0.0])
    else:
        closest_idx = np.argmin(valid_distances)
        direction = relative_pos[closest_idx]
        dist = distances[closest_idx]
        if dist > 0:
            direction = direction / dist
        else:
            direction = np.array([0.0, 0.0])
    
    # Action: 5D - movement (2) + communication (3 zeros)
    action = np.array([direction[0], direction[1], 0.0, 0.0, 0.0])
    return action

episodes = []

for episode in range(100):
    obs, infos = env.reset()
    
    episode_rewards = {agent: 0 for agent in env.agents}
    captures = 0
    done = False
    
    while not done:
        actions = {}
        for agent in env.agents:
            if 'adversary' in agent:
                obs_agent = obs[agent]
                actions[agent] = get_action_for_adversary(obs_agent)
            else:
                # Random for good agents
                actions[agent] = env.action_space(agent).sample()
        
        obs, rewards, terminations, truncations, infos = env.step(actions)
        
        # Accumulate rewards
        for agent in env.agents:
            episode_rewards[agent] += rewards.get(agent, 0)
        
        # Count captures (terminated good agents)
        for agent, terminated in terminations.items():
            if terminated and 'good' in agent:
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
with open("baselines/random_vs_heuristic_3pred1prey_local0.5.json", "w") as f:
    json.dump(episodes, f, indent=2)

print(f"Completed {len(episodes)} episodes. Average captures: {np.mean([e['captures'] for e in episodes]):.2f}")