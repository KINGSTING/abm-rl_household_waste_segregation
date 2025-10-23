"""
src/phase3/scenario_runner.py

This script runs comparative simulations for different policy scenarios.
It compares:
1.  'baseline': No policy intervention.
2.  'uniform_static': A fixed, manually-defined policy (e.g., 0.5 info, 0.2
    enforcement) applied uniformly to all barangays.
3.  'rl_differentiated': The trained RL agent making dynamic, differentiated
    decisions.
"""
import os
import argparse
import pandas as pd
import numpy as np

# Import the ABM (from Phase 1) and Env (from Phase 2)
# TODO: Replace with actual imports
from src.phase2.rl_environment import BacolodWasteModel, WastePolicyEnv

# Import the RL model loader (from Phase 2)
# We assume stable-baselines3
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


def run_abm_simulation(abm: BacolodWasteModel, n_steps: int, policies: np.ndarray) -> pd.DataFrame:
    """
    Helper function to run the core ABM with a fixed policy.

    Args:
        abm (BacolodWasteModel): An initialized ABM instance.
        n_steps (int): Total number of ABM steps (days) to run.
        policies (np.ndarray): The policy (shape [n_barangays, 2]) to apply.

    Returns:
        pd.DataFrame: A log of compliance over time.
    """
    abm.reset()
    abm.update_policies(policies)  # Set the policy once

    results = []
    for step in range(n_steps):
        abm.step()  # ABM runs with the fixed policy
        compliance_rates = abm.get_compliance_rates_per_barangay()

        step_data = {
            'step': step,
            'mean_compliance': np.mean(compliance_rates)
        }
        for i, rate in enumerate(compliance_rates):
            step_data[f'compliance_b{i}'] = rate
        results.append(step_data)

    return pd.DataFrame(results)


def run_rl_simulation(rl_env: WastePolicyEnv, model: BaseAlgorithm, n_rl_steps: int) -> pd.DataFrame:
    """
    Helper function to run the simulation using a trained RL policy.

    Args:
        rl_env (WastePolicyEnv): An initialized environment.
        model (BaseAlgorithm): The loaded, trained RL model.
        n_rl_steps (int): Total number of RL steps (quarters) to run.

    Returns:
        pd.DataFrame: A log of compliance and actions over time.
    """
    obs, info = rl_env.reset()
    results = []

    for rl_step in range(n_rl_steps):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = rl_env.step(action)

        step_data = {
            'rl_step': rl_step,
            'mean_compliance': info['mean_compliance'],
            'total_cost': info['total_cost'],
            'reward': reward
        }

        # Log compliance and actions for each barangay
        num_barangays = rl_env.num_barangays
        for b in range(num_barangays):
            step_data[f'compliance_b{b}'] = obs['compliance_rates'][b]
            step_data[f'action_info_b{b}'] = action[b, 0]
            step_data[f'action_enforce_b{b}'] = action[b, 1]

        results.append(step_data)

        if terminated or truncated:
            break

    return pd.DataFrame(results)


def main(args):
    """
    Main function to orchestrate the scenario runs.
    """
    print("--- [Scenario Runner] Starting ---")

    # --- Common Config ---
    # TODO: Load from a YAML config file
    n_barangays = 5
    n_households = 100
    abm_steps_per_rl_step = 90
    rl_steps = 20  # 5 years
    total_abm_steps = abm_steps_per_rl_step * rl_steps

    abm_config = {
        'num_barangays': n_barangays,
        'num_households_per_barangay': n_households
    }

    # Base environment config
    rl_env_config = {
        'num_barangays': n_barangays,
        'abm_steps_per_rl_step': abm_steps_per_rl_step,
        'max_rl_steps': rl_steps,
        'abm_config': abm_config,
        'verbose': False
    }

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # --- 1. Baseline Scenario (No Policy) ---
    print("Running Scenario 1: 'Baseline' (No Policy)")
    baseline_abm = BacolodWasteModel(abm_config)
    baseline_policies = np.zeros((n_barangays, 2))  # [0 info, 0 enforce]
    df_baseline = run_abm_simulation(baseline_abm, total_abm_steps, baseline_policies)
    df_baseline['scenario'] = 'baseline'

    output_path = os.path.join(args.output_dir, "scenario_baseline.csv")
    df_baseline.to_csv(output_path, index=False)
    print(f"Saved 'baseline' results to {output_path}")

    # --- 2. Uniform Static Policy Scenario ---
    print("Running Scenario 2: 'Uniform Static' (Fixed Policy)")
    uniform_abm = BacolodWasteModel(abm_config)
    # Define a "reasonable" fixed policy (e.g., 0.3 info, 0.1 enforcement)
    uniform_policy_level = [0.3, 0.1]
    uniform_policies = np.tile(uniform_policy_level, (n_barangays, 1))

    df_uniform = run_abm_simulation(uniform_abm, total_abm_steps, uniform_policies)
    df_uniform['scenario'] = 'uniform_static'

    output_path = os.path.join(args.output_dir, "scenario_uniform_static.csv")
    df_uniform.to_csv(output_path, index=False)
    print(f"Saved 'uniform_static' results to {output_path}")

    # --- 3. Differentiated RL Policy Scenario ---
    if not args.rl_model_path:
        print("Skipping Scenario 3: 'RL Differentiated' (No model path provided)")
    elif not os.path.exists(args.rl_model_path):
        print(f"Skipping Scenario 3: Model file not found at {args.rl_model_path}")
    else:
        print("Running Scenario 3: 'RL Differentiated' (Trained Policy)")
        # We need the RL Env for this, as it handles the stepping
        rl_env = WastePolicyEnv(rl_env_config)

        # Load the trained model
        try:
            model = BaseAlgorithm.load(args.rl_model_path)
        except Exception as e:
            print(f"Error loading RL model: {e}. Skipping scenario.")
            return

        df_rl = run_rl_simulation(rl_env, model, rl_steps)
        df_rl['scenario'] = 'rl_differentiated'

        output_path = os.path.join(args.output_dir, "scenario_rl_differentiated.csv")
        df_rl.to_csv(output_path, index=False)
        print(f"Saved 'rl_differentiated' results to {output_path}")

    print("--- [Scenario Runner] Complete ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run comparative policy scenarios.")
    parser.add_argument(
        "--rl_model_path",
        type=str,
        help="Path to the trained RL model .zip file (optional).",
        default="outputs/models/rl_policies/ppo_5barangay_initial_run_best/best_model.zip"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        help="Directory to save scenario CSV results.",
        default="data/simulation_outputs/phase3_scenarios"
    )

    args = parser.parse_args()
    main(args)