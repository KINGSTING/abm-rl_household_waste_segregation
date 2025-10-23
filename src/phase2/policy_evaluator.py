"""
src/phase2/policy_evaluator.py

This script loads a pre-trained RL policy and runs it in the
WastePolicyEnv environment to evaluate its performance.

It collects detailed metrics from the simulation (compliance, cost,
actions taken) and saves them to a CSV file for analysis in
Jupyter notebooks or other tools.
"""

import os
import argparse
import pandas as pd
import numpy as np
import gymnasium as gym

# --- Assumed RL Library ---
# We assume stable-baselines3 (SB3) is used for training.
# If you use a different library (e.g., RLlib, CleanRL), you'll
# need to adjust the model loading and prediction parts.
try:
    from stable_baselines3.common.base_class import BaseAlgorithm
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3 import PPO, SAC, DDPG, TD3
except ImportError:
    print("Warning: stable-baselines3 not found. This script requires it.")
    print("Please install: pip install stable-baselines3[extra]")


    # Define a placeholder for the script to be syntactically correct
    class BaseAlgorithm:
        def load(self, *args, **kwargs):
            raise ImportError("stable-baselines3 is not installed.")

        @staticmethod
        def predict(*args, **kwargs):
            raise ImportError("stable-baselines3 is not installed.")

# Import our custom environment
from src.phase2.rl_environment import WastePolicyEnv

# Import (mock) ABM for type hinting and config
# TODO: Replace with actual import
from src.phase2.rl_environment import BacolodWasteModel


def evaluate_policy(
        model_path: str,
        env_config: dict,
        n_episodes: int = 1,
        deterministic: bool = True
) -> pd.DataFrame:
    """
    Loads a trained policy and runs it for a specified number of episodes.

    Args:
        model_path (str): Path to the saved .zip file of the SB3 model.
        env_config (dict): Configuration dictionary for WastePolicyEnv.
        n_episodes (int): Number of full episodes to run.
        deterministic (bool): Whether to use deterministic (True) or
                              stochastic (False) actions from the policy.
                              True is standard for evaluation.

    Returns:
        pd.DataFrame: A DataFrame containing detailed step-by-step results.
    """
    print(f"--- Starting Evaluation ---")
    print(f"  Model: {model_path}")
    print(f"  Episodes: {n_episodes}")
    print(f"  Deterministic: {deterministic}")

    # 1. Initialize the environment
    # Note: We don't wrap it in make_vec_env here, as we want
    # to run episodes sequentially and log complex info.
    eval_env = WastePolicyEnv(env_config)
    num_barangays = eval_env.num_barangays

    # 2. Load the trained model
    # The 'env' parameter is not strictly needed for .load() if the
    # environment is simple, but it's good practice.
    try:
        model = BaseAlgorithm.load(model_path, env=eval_env)
        print(f"Successfully loaded model from {model_path}")
    except Exception as e:
        print(f"Error loading model: {e}")
        print("This often happens if the environment definition changed.")
        print("Attempting to load without setting env...")
        try:
            # This can work if the spaces were saved with the model
            model = BaseAlgorithm.load(model_path)
            model.set_env(eval_env)
            print("Successfully loaded model and set env.")
        except Exception as e2:
            print(f"Fatal error loading model: {e2}")
            print("Please ensure stable-baselines3 is installed and the model path is correct.")
            return pd.DataFrame()  # Return empty dataframe

    # 3. Prepare data collection lists
    all_episode_data = []

    for ep in range(n_episodes):
        print(f"\nRunning Episode {ep + 1}/{n_episodes}...")

        obs, info = eval_env.reset()
        terminated, truncated = False, False

        ep_total_reward = 0
        ep_step = 0

        while not (terminated or truncated):
            # 4. Get action from the policy
            action, _states = model.predict(obs, deterministic=deterministic)

            # 5. Take step in the environment
            obs, reward, terminated, truncated, info = eval_env.step(action)

            # 6. Log data for this step
            step_data = {
                'episode': ep + 1,
                'rl_step': info.get('rl_step', ep_step),
                'reward': reward,
                'total_reward_so_far': ep_total_reward + reward,
                'mean_compliance': info.get('mean_compliance', 0),
                'total_cost': info.get('total_cost', 0),
                'reward_compliance': info.get('reward_compliance', 0),
                'penalty_cost': info.get('penalty_cost', 0),
            }

            # Log action and observation details
            for b in range(num_barangays):
                step_data[f'action_info_b{b}'] = action[b, 0]
                step_data[f'action_enforce_b{b}'] = action[b, 1]
                step_data[f'obs_compliance_b{b}'] = obs['compliance_rates'][b]

            all_episode_data.append(step_data)

            ep_total_reward += reward
            ep_step += 1

        print(f"Episode {ep + 1} finished.")
        print(f"  Total Steps: {ep_step}")
        print(f"  Total Reward: {ep_total_reward:.2f}")
        print(f"  Final Compliance: {info.get('mean_compliance', 0):.3f}")

    eval_env.close()

    # 7. Convert results to DataFrame
    results_df = pd.DataFrame(all_episode_data)

    # Re-order columns for clarity
    core_cols = ['episode', 'rl_step', 'reward', 'total_reward_so_far',
                 'mean_compliance', 'total_cost', 'reward_compliance', 'penalty_cost']
    # Find all other columns (actions, obs)
    other_cols = sorted([c for c in results_df.columns if c not in core_cols])
    results_df = results_df[core_cols + other_cols]

    print("\n--- Evaluation Complete ---")
    print(f"Mean Reward: {results_df.groupby('episode')['reward'].sum().mean():.2f}")
    print(f"Mean Final Compliance: {results_df.groupby('episode')['mean_compliance'].last().mean():.3f}")

    return results_df


# --- Main block for running the evaluator from the command line ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a trained RL policy.")

    # --- Arguments ---
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Path to the saved SB3 model .zip file (e.g., outputs/models/rl_policies/ppo_waste_model.zip)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evaluation_results.csv",
        help="Path to save the resulting CSV file (e.g., outputs/reports/ppo_evaluation.csv)"
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=5,
        help="Number of episodes to run for evaluation."
    )
    parser.add_argument(
        "--barangays",
        type=int,
        default=3,
        help="Number of barangays (must match the trained model)."
    )

    args = parser.parse_args()

    # --- Check if model file exists ---
    if not os.path.exists(args.model):
        print(f"Error: Model file not found at {args.model}")
        print("This script is for *evaluating* a *pre-trained* model.")
        print("You must run rl_trainer.py first to generate a model file.")
        print("Exiting.")
    else:
        # --- Environment Configuration ---
        # This config MUST match the config used for training the model.
        env_config = {
            'num_barangays': args.barangays,
            'abm_steps_per_rl_step': 90,  # 90 days
            'max_rl_steps': 20,  # 20 quarters = 5 years
            'compliance_weight': 1000.0,
            'cost_weight': 1.0,
            'info_cost_factor': 100.0,
            'enforcement_cost_factor': 200.0,
            'verbose': False,  # Don't want verbose output during evaluation
            'abm_config': {
                'num_barangays': args.barangays,
                'num_households_per_barangay': 100
            }
        }

        # --- Run Evaluation ---
        results_df = evaluate_policy(
            model_path=args.model,
            env_config=env_config,
            n_episodes=args.episodes,
            deterministic=True
        )

        # --- Save Results ---
        if not results_df.empty:
            # Ensure output directory exists
            output_dir = os.path.dirname(args.output)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            results_df.to_csv(args.output, index=False)
            print(f"\n✅ Evaluation results saved to {args.output}")