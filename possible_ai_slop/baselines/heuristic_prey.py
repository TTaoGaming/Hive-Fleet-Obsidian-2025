import numpy as np

def mask_obs(obs, local_ratio=0.5, is_adversary=False):
    masked = obs.copy()
    # Landmarks rel pos: indices 4:8 (2 landmarks * 2)
    for i in range(2):
        pos_start = 4 + i * 2
        rel_pos = masked[pos_start:pos_start + 2]
        dist = np.linalg.norm(rel_pos)
        if dist > local_ratio:
            masked[pos_start:pos_start + 2] = 0.0

    # For good: other_pos 8:14 (3 preds * 2), no other_vel
    for i in range(3):
        pos_start = 8 + i * 2
        rel_pos = masked[pos_start:pos_start + 2]
        dist = np.linalg.norm(rel_pos)
        if dist > local_ratio:
            masked[pos_start:pos_start + 2] = 0.0

    return masked

def heuristic_prey_policy(obs):
    obs = mask_obs(obs, is_adversary=False)
    # Obs for prey: vel(2):0-2, pos(2):2-4, landmarks(4):4-8, other_pos(6):8-14 (3 preds)
    relative_pos = obs[8:14].reshape(3, 2)
    
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