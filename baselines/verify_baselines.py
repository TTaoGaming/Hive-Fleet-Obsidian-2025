import json
import numpy as np

def load_json(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def calculate_metrics(data):
    captures_per_episode = [ep['captures'] / 1.0 for ep in data]  # normalize by num_good
    avg_capture_rate = np.mean(captures_per_episode)
    return avg_capture_rate

# Load data for 2x2 matrix
rvr_data = load_json('baselines/random_vs_random_3pred1prey_local0.5.json')
hvr_data = load_json('baselines/heuristic_pred_vs_random_prey_3pred1prey_local0.5.json')
rvh_data = load_json('baselines/random_pred_vs_heuristic_prey_3pred1prey_local0.5.json')
hvh_data = load_json('baselines/heuristic_vs_heuristic_3pred1prey_local0.5.json')

rvr_rate = calculate_metrics(rvr_data)
hvr_rate = calculate_metrics(hvr_data)
rvh_rate = calculate_metrics(rvh_data)
hvh_rate = calculate_metrics(hvh_data)

print(f"Random vs Random: Average capture rate = {rvr_rate:.4f}")
print(f"Heuristic Pred vs Random Prey: Average capture rate = {hvr_rate:.4f}")
print(f"Random Pred vs Heuristic Prey: Average capture rate = {rvh_rate:.4f}")
print(f"Heuristic vs Heuristic: Average capture rate = {hvh_rate:.4f}")

verification = {
    "rvr_rate": float(rvr_rate),
    "hvr_rate": float(hvr_rate),
    "rvh_rate": float(rvh_rate),
    "hvh_rate": float(hvh_rate),
    "params": {
        "num_adversaries": 3,
        "num_good": 1,
        "max_cycles": 25,
        "continuous_actions": True,
        "local_ratio": 0.5
    },
    "passes": int(
        rvr_rate < 0.2 and hvr_rate < 0.2 and rvh_rate < 0.2 and hvh_rate < 0.2 and
        hvr_rate > rvr_rate and rvh_rate > rvr_rate and hvh_rate > rvr_rate
    )
}

print(f"Verification passes: {verification['passes']}")

# Save verification
with open('baselines/verification_results_3pred1prey_local0.5.json', 'w') as f:
    json.dump(verification, f, indent=2)