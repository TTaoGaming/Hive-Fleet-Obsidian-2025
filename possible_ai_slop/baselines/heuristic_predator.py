import numpy as np

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

def heuristic_predator_policy(obs):
    obs = mask_obs(obs, is_adversary=True)
    # Obs for adversary: vel(2):0-2, pos(2):2-4, landmarks(4):4-8, other_pos(6):8-14 (2 adv + 1 good), other_vel(2):14-16 (good vel)
    # Prey (good) rel pos is always the last 2 of other_pos: indices 12:14
    # Prey vel: 14:16
    prey_rel = obs[12:14]
    prey_vel = obs[14:16]
    
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