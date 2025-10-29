import json
import numpy as np
from mpe2 import simple_tag_v3
from datetime import datetime

settings = {
    "env": "simple_tag_v3",
    "params": {"num_good": 1, "num_adversaries": 3, "num_obstacles": 2, "continuous_actions": False, "max_cycles": 25},
    "agents": "random vs random",
    "seeds": list(range(5)),
    "mode": "discrete",
    "steps_per_episode": 25,
    "timestamp": datetime.utcnow().isoformat() + "Z"
}

episodes = []
aggregates = {"catch_events": 0, "total_steps": 0, "total_rewards": [], "avg_reward": 0, "catch_rate": 0, "avg_steps_to_catch": 0}

for seed in settings["seeds"]:
    env = simple_tag_v3.parallel_env(**settings["params"])
    obs = env.reset(seed=seed)
    good_rewards = []
    catch_events = 0
    steps = 0
    for step in range(settings["steps_per_episode"]):
        actions = {agent: env.action_space(agent).sample() for agent in env.agents}
        obs, reward, termination, truncation, info = env.step(actions)
        good_reward = reward.get('good_0', 0)
        good_rewards.append(good_reward)
        if good_reward > 0:
            catch_events += 1
        steps += 1
        if all(termination.values()) or all(truncation.values()):
            break
    env.close()

    episode = {
        "seed": seed,
        "steps": steps,
        "catch_events": catch_events,
        "rewards": good_rewards,
        "total_reward": sum(good_rewards),
        "avg_reward": np.mean(good_rewards) if good_rewards else 0
    }
    episodes.append(episode)

    aggregates["catch_events"] += catch_events
    aggregates["total_steps"] += steps
    aggregates["total_rewards"].extend(good_rewards)

aggregates["avg_reward"] = np.mean(aggregates["total_rewards"]) if aggregates["total_rewards"] else 0
aggregates["catch_rate"] = aggregates["catch_events"] / len(episodes)
aggregates["avg_steps_to_catch"] = aggregates["total_steps"] / aggregates["catch_events"] if aggregates["catch_events"] > 0 else 0

results = {"settings": settings, "episodes": episodes, "aggregates": aggregates}

timestamp = settings["timestamp"][:19].replace(":", "-")
filename = f"results/baseline_results_{timestamp}.json"
with open(filename, "w") as f:
    json.dump(results, f, indent=2)

print(f"Baseline complete: JSON saved to {filename}")
avg_steps_str = f"{aggregates['avg_steps_to_catch']:.2f}" if aggregates['catch_events'] > 0 else 'N/A'
print(f"Aggregates: catch_rate={aggregates['catch_rate']:.2f}, avg_steps_to_catch={avg_steps_str}, avg_reward={aggregates['avg_reward']:.2f}")