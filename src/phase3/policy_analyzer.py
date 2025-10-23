"""
src/phase3/policy_analyzer.py

Analyzes a trained RL policy by "interrogating" it.
We feed it a set of hypothetical observations (states) and
record the policy's chosen actions.

This helps to understand the "mind" of the agent, e.g.:
- How does it react to low compliance?
- How does it react to high compliance?
- Does it apply different policies to different barangays?
"""
import os
import argparse
import numpy as np
import pandas as pd

# Import the RL model loader
try:
    from stable_baselines3.common.base_class import BaseAlgorithm
except ImportError:
    print("Warning: stable-baselines3 not found. This script requires it.")


    class BaseAlgorithm:  # Placeholder
        def load(self, *args, **kwargs):
            raise ImportError("stable-baselines3 is not installed.")

        @staticmethod
        def predict(*args, **kwargs):
            raise ImportError("stable-baselines3 is not installed.")


def create_test_observations(n_barangays: int) -> dict:
    """
    Creates a dictionary of named, hypothetical observations.

    Each observation must match the structure of the WastePolicyEnv's
    observation_space (a Dict with 'compliance_rates' and 'current_policies').
    """
    # Define a default "current_policies" state (e.g., medium-low)
    default_policies = np.tile([0.2, 0.1], (n_barangays, 1)).astype(np.float32)

    test_states = {
        "baseline_all_zero": {
            "compliance_rates": np.zeros(n_barangays, dtype=np.float32),
            "current_policies": np.zeros((n_barangays, 2), dtype=np.float32)
        },
        "baseline_all_low": {
            "compliance_rates": np.full(n_barangays, 0.1, dtype=np.float32),
            "current_policies": default_policies
        },
        "baseline_all_medium": {
            "compliance_rates": np.full(n_barangays, 0.5, dtype=np.float32),
            "current_policies": default_policies
        },
        "baseline_all_high": {
            "compliance_rates": np.full(n_barangays, 0.9, dtype=np.float32),
            "current_policies": np.tile([0.8, 0.8], (n_barangays, 1)).astype(np.float32)
        },
        "differentiated_one_low": {
            "compliance_rates": np.array([0.1] + [0.7] * (n_barangays - 1), dtype=np.float32),
            "current_policies": default_policies
        },
        "differentiated_one_high": {
            "compliance_rates": np.array([0.9] + [0.3] * (n_barangays - 1), dtype=np.float32),
            "current_policies": default_policies
        }
    }

    return test_states


def analyze_policy(model_path: str, n_barangays: int, output_path: str):
    """
    Loads the model, generates test states, and gets policy actions.
    """
    print(f"--- [Policy Analyzer] ---")
    print(f"Loading model: {model_path}")

    # 1. Load the trained model
    if not os.path.exists(model_path):
        print(f"Error: Model file not found at {model_path}")
        return
    try:
        model = BaseAlgorithm.load(model_path)
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    # 2. Create test observations
    test_observations = create_test_observations(n_barangays)
    print(f"Created {len(test_observations)} test observations.")

    # 3. "Interrogate" the policy
    results = []
    for state_name, obs in test_observations.items():
        # Get the policy's action for this observation
        # We must batch the observation (add a leading dimension)
        # obs_batch = {key: np.expand_dims(val, axis=0) for key, val in obs.items()}
        # Note: For SB3, predict() handles the batching automatically.

        action, _ = model.predict(obs, deterministic=True)

        print(f"\nAnalyzing state: '{state_name}'")
        print(f"  -> Obs (Compliance): {[round(c, 2) for c in obs['compliance_rates']]}")
        print(f"  => Action (Info):     {[round(a, 2) for a in action[:, 0]]}")
        print(f"  => Action (Enforce):  {[round(a, 2) for a in action[:, 1]]}")

        # Store results
        for b in range(n_barangays):
            results.append({
                'state_name': state_name,
                'barangay': b,
                'obs_compliance': obs['compliance_rates'][b],
                'action_info': action[b, 0],
                'action_enforce': action[b, 1]
            })

    # 4. Save results to CSV
    df_results = pd.DataFrame(results)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_results.to_csv(output_path, index=False)
    print(f"\n--- [Policy Analyzer] Complete ---")
    print(f"Analysis saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze a trained RL policy's behavior.")
    parser.add_argument(
        "--model_path",
        type=str,
        required=True,
        help="Path to the trained RL model .zip file (e.g., outputs/models/rl_policies/best_model.zip)"
    )
    parser.add_argument(
        "--n_barangays",
        type=int,
        required=True,
        help="Number of barangays (must match the trained model)."
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default="outputs/reports/policy_analysis.csv",
        help="Path to save the analysis CSV file."
    )

    args = parser.parse_args()

    analyze_policy(
        model_path=args.model_path,
        n_barangays=args.n_barangays,
        output_path=args.output_path
    )