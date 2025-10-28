import json
import numpy as np

def load_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def calculate_metrics(data):
    captures_per_episode = [ep['captures'] / 1.0 for ep in data]  # normalize by num_good
    avg_capture_rate = np.mean(captures_per_episode)
    return avg_capture_rate

# Load data
random_data = load_json('baselines/random_vs_random_3pred1prey_local0.5.json')
heuristic_data = load_json('baselines/random_vs_heuristic_3pred1prey_local0.5.json')

random_rate = calculate_metrics(random_data)
heuristic_rate = calculate_metrics(heuristic_data)

print(f"Random vs Random: Average capture rate = {random_rate:.4f}")
print(f"Random vs Heuristic: Average capture rate = {heuristic_rate:.4f}")

verification = {
    "random_rate": float(random_rate),
    "heuristic_rate": float(heuristic_rate),
    "params": {
        "num_adversaries": 3,
        "num_good": 1,
        "max_cycles": 25,
        "continuous_actions": True,
        "local_ratio": 0.5
    },
    "passes": int(random_rate < 0.2 and heuristic_rate < 0.2)
}

print(f"Verification passes: {verification['passes']}")

# Save verification
with open('baselines/verification_results_3pred1prey_local0.5.json', 'w') as f:
    json.dump(verification, f, indent=2)