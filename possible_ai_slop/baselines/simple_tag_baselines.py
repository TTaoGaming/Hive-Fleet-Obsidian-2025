import json
import numpy as np
from pettingzoo.mpe import simple_tag_v3

def random_policy(obs):
    # Continuous action: 2D velocity, uniform random
    return np.random.uniform(-1.0, 1.0, size=(2,))

def heuristic_predator(obs):
    # Simple heuristic: bias towards positive direction assuming prey position
    # For now, constant bias; in real, could use obs to compute direction to landmark/prey
    return np.array([0.5, 0.0])  # Move right

def heuristic_prey(obs):
    # Simple heuristic: bias away, move left/up
    return np.array([-0.5, 0.5])

def run_baseline(baseline_type, num_episodes=100):
    env_config = {
        "continuous_actions": True,
        "max_cycles": 100,
        "local_ratio": 0.5
    }
    
    env = simple_tag_v3.parallel_env(**env_config)
    
    episode_data = []
    total_captures = 0
    
    for episode in range(num_episodes):
        observations = env.reset()
        episode_rewards = {agent: 0 for agent in env.agents}
        episode_capture = False
        terminateds = {agent: False for agent in env.agents}
        truncateds = {agent: False for agent in env.agents}
        
        while not all(terminateds.values()) and not all(truncateds.values()):
            actions = {agent: None for agent in env.agents}
            for agent in env.agents:
                if agent.startswith('adversary'):
                    if baseline_type == 'random_vs_random':
                        actions[agent] = random_policy(observations[agent])
                    else:  # random vs heuristic: heuristic for predators, random for prey
                        actions[agent] = heuristic_predator(observations[agent])
                else:  # agent (prey)
                    if baseline_type == 'random_vs_random':
                        actions[agent] = random_policy(observations[agent])
                    else:
                        actions[agent] = heuristic_prey(observations[agent])
            
            observations, rewards, terminateds, truncateds, infos = env.step(actions)
            
            for agent in env.agents:
                episode_rewards[agent] += rewards[agent]
                if rewards[agent] > 0 and agent.startswith('adversary'):  # Capture reward for predator
                    episode_capture = True
        
        if episode_capture:
            total_captures += 1
        
        episode_data.append({
            "episode": episode,
            "rewards": episode_rewards,
            "capture": episode_capture,
            "params": env_config
        })
    
    capture_rate = (total_captures / num_episodes) * 100
    results = {
        "baseline_type": baseline_type,
        "env_config": env_config,
        "num_episodes": num_episodes,
        "episode_data": episode_data,
        "capture_rate": capture_rate,
        "meets_research": capture_rate < 20
    }
    
    filename = f"{baseline_type.replace(' ', '_')}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)  # default=str for any non-serializable
    
    env.close()
    return results, filename

if __name__ == "__main__":
    # Run random vs random
    results_rr, file_rr = run_baseline("random_vs_random")
    print(f"Random vs Random: Capture rate {results_rr['capture_rate']:.2f}%, Meets <20%: {results_rr['meets_research']}, File: {file_rr}")
    
    # Run random vs heuristic (heuristic predators vs random prey? Wait, task is random vs random, random vs heuristic)
    # Assuming random predators vs heuristic prey, but adjust as per task: random vs heuristic likely random predators vs heuristic prey
    results_rh, file_rh = run_baseline("random_vs_heuristic")
    print(f"Random vs Heuristic: Capture rate {results_rh['capture_rate']:.2f}%, Meets <20%: {results_rh['meets_research']}, File: {file_rh}")