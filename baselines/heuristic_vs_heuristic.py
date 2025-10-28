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

def mask_obs(obs, local_ratio=0.5, is_adversary=True):
    masked = obs.copy()
    # Landmarks rel pos: indices 4:8 (2 landmarks * 2)
    for i in range(2):
        pos_start = 4 + i * 2
        rel_pos = masked[pos_start:pos_start + 2]
        dist = np.linalg.norm(rel_pos)
        if dist > local_ratio:
            masked[pos_start:pos_start + 2] = 0.0

    if is_adversary:
        # other agents rel pos: 8:14 (3 others * 2), other_vel:14:16
        for i in range(3):
            pos_start = 8 + i * 2
            rel_pos = masked[pos_start:pos_start + 2]
            dist = np.linalg.norm(rel_pos)
            if dist > local_ratio:
                masked[pos_start:pos_start + 2] = 0.0
    else:
        # For good: other_pos 8:14 (3 preds * 2), no other_vel
        for i in range(3):
            pos_start = 8 + i * 2
            rel_pos = masked[pos_start:pos_start + 2]
            dist = np.linalg.norm(rel_pos)
            if dist > local_ratio:
                masked[pos_start:pos_start + 2] = 0.0

    return masked

def get_action_for_adversary(obs_adversary):
    obs_adversary = mask_obs(obs_adversary, is_adversary=True)
    # Obs for adversary: vel(2):0-2, pos(2):2-4, landmarks(4):4-8, other_pos(6):8-14 (2 adv + 1 good), other_vel(2):14-16 (good vel)
    # Prey (good) rel pos is always the last 2 of other_pos: indices 12:14
    # Prey vel: 14:16
    prey_rel = obs_adversary[12:14]
    prey_vel = obs_adversary[14:16]
    
    # Simple lead pursuit: predict prey position
    predicted_rel = prey_rel + prey_vel  # assume dt=1
    pred_dist = np.linalg.norm(predicted_rel)
    
    if pred_dist > 0:
        direction = predicted_rel / pred_dist
    else:
        # Fallback to current position
        dist = np.linalg.norm(prey_rel)
        if dist > 0:
            direction = prey_rel / dist
        else:
            direction = np.array([0.0, 0.0])
    
    # Action: 5D - map direction [-1,1] to [0,1] for movement + communication (3 zeros)
    action = np.zeros(5)
    action[0] = (direction[0] + 1) / 2
    action[1] = (direction[1] + 1) / 2
    return action

def get_action_for_prey(obs_prey):
    obs_prey = mask_obs(obs_prey, is_adversary=False)
    # Obs for prey: vel(2):0-2, pos(2):2-4, landmarks(4):4-8, other_pos(6):8-14 (3 preds)
    relative_pos = obs_prey[8:14].reshape(3, 2)
    
    distances = np.linalg.norm(relative_pos, axis=1)
    
    # Find closest non-zero distance
    valid_distances = distances[distances > 0]
    if len(valid_distances) == 0:
        # No visible preds, stay still or random
        direction = np.array([0.0, 0.0])
    else:
        closest_idx = np.argmin(valid_distances)
        nearest_rel = relative_pos[closest_idx]
        dist = distances[closest_idx]
        if dist > 0:
            direction = - nearest_rel / dist  # Flee opposite
        else:
            direction = np.array([0.0, 0.0])
    
    # Action: 5D - map direction [-1,1] to [0,1] for movement + communication (3 zeros)
    action = np.zeros(5)
    action[0] = (direction[0] + 1) / 2
    action[1] = (direction[1] + 1) / 2
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
                # Heuristic for adversaries (predators)
                obs_agent = obs[agent]
                actions[agent] = get_action_for_adversary(obs_agent)
            else:
                # Heuristic for good (prey)
                obs_agent = obs[agent]
                actions[agent] = get_action_for_prey(obs_agent)
        
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
with open("heuristic_vs_heuristic_3pred1prey_local0.5.json", "w") as f:
    json.dump(episodes, f, indent=2)

print(f"Completed {len(episodes)} episodes. Average captures: {np.mean([e['captures'] for e in episodes]):.2f}")