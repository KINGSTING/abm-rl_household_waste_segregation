"""
src/phase2/rl_trainer.py

This script trains a Reinforcement Learning agent (e.g., PPO)
on the WastePolicyEnv.

It uses stable-baselines3 for the RL algorithm and sets up
parallel environments for faster training.
"""
import os
import argparse
import time

# --- RL Library Imports (stable-baselines3) ---
try:
    from stable_baselines3 import PPO, SAC
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.vec_env import SubprocVecEnv
    from stable_baselines3.common.callbacks import CallbackList, CheckpointCallback, EvalCallback
except ImportError:
    print("Error: stable-baselines3 not found. This script requires it.")
    print("Please install: pip install stable-baselines3[extra]")
    exit(1)

# --- Custom Environment Imports ---
from src.phase2.rl_environment import WastePolicyEnv
# TODO: This mock is for standalone testing.
# Remove it when src.phase1.model.BacolodWasteModel is available.
from src.phase2.rl_environment import BacolodWasteModel


def train_rl_model(
        total_timesteps: int,
        n_cpu: int,
        output_dir: str,
        log_dir: str,
        model_name: str,
        algo: str = "PPO"
):
    """
    Sets up and runs the RL training process.

    Args:
        total_timesteps (int): Total number of samples to train on.
        n_cpu (int): Number of parallel environments (processes) to use.
        output_dir (str): Base directory to save models.
        log_dir (str): Base directory to save TensorBoard logs.
        model_name (str): A unique name for this training run.
        algo (str): The RL algorithm to use ('PPO' or 'SAC').
    """
    print(f"--- [RL Trainer] Starting New Run ---")
    print(f"  - Algorithm: {algo}")
    print(f"  - Total Timesteps: {total_timesteps:,}")
    print(f"  - Parallel Envs (CPUs): {n_cpu}")
    print(f"  - Run Name: {model_name}")

    # 1. --- Define Paths ---
    model_save_dir = os.path.join(output_dir, "models", "rl_policies")
    final_model_path = os.path.join(model_save_dir, f"{model_name}_final.zip")
    best_model_save_path = os.path.join(model_save_dir, f"{model_name}_best")
    checkpoint_save_path = os.path.join(model_save_dir, f"{model_name}_checkpoints")
    tensorboard_log_path = os.path.join(log_dir, model_name)
    eval_log_path = os.path.join(tensorboard_log_path, "eval_logs")

    # Create directories if they don't exist
    os.makedirs(model_save_dir, exist_ok=True)
    os.makedirs(tensorboard_log_path, exist_ok=True)
    os.makedirs(eval_log_path, exist_ok=True)

    # 2. --- Environment Configuration ---
    # This config will be passed to each parallel environment
    # TODO: This should be loaded from your config/rl_training_config.yaml
    env_config = {
        'num_barangays': 5,  # A key parameter to match your data
        'abm_steps_per_rl_step': 90,  # 90 days (1 quarter)
        'max_rl_steps': 5,  # 20 quarters (5 years)
        'compliance_weight': 1000.0,
        'cost_weight': 1.0,
        'info_cost_factor': 100.0,
        'enforcement_cost_factor': 200.0,
        'verbose': False,  # Must be False for parallel training
        'abm_config': {
            'num_barangays': 5,
            'num_households_per_barangay': 100
        }
    }

    # 3. --- Create Vectorized Training Environment ---
    # We use make_vec_env to create `n_cpu` copies of the environment
    # running in parallel Subprocesses.
    print(f"[RL Trainer] Creating {n_cpu} parallel environments...")
    train_env = make_vec_env(
        env_id=WastePolicyEnv,  # Our custom env class
        n_envs=n_cpu,
        seed=int(time.time()),  # Use current time as a random seed
        vec_env_cls=SubprocVecEnv,  # Use Subprocesses for true parallelism
        env_kwargs={'config': env_config}  # Pass our config to the env
    )

    # 4. --- Create a Separate Evaluation Environment ---
    # This env is not vectorized and is used by the EvalCallback
    # to test the model's performance periodically.
    print("[RL Trainer] Creating evaluation environment...")
    eval_env = WastePolicyEnv(env_config)

    # 5. --- Set up Callbacks ---
    # Save a checkpoint every 50,000 steps
    # Note: save_freq is per-environment, so we divide by n_cpu
    checkpoint_callback = CheckpointCallback(
        save_freq=max(50_000 // n_cpu, 1),
        save_path=checkpoint_save_path,
        name_prefix=f"{model_name}_ckpt"
    )

    # Evaluate the model every 20,000 steps on the eval_env
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=best_model_save_path,
        log_path=eval_log_path,
        eval_freq=max(20_000 // n_cpu, 1),
        n_eval_episodes=5,  # Run 5 episodes for a stable score
        deterministic=True,
        render=False
    )

    # Combine callbacks
    callback_list = CallbackList([checkpoint_callback, eval_callback])

    # 6. --- Initialize the RL Model ---
    model_params = {
        "policy": "MultiInputPolicy",  # CRITICAL: Use MultiInputPolicy for Dict spaces
        "env": train_env,
        "verbose": 1,
        "tensorboard_log": tensorboard_log_path
    }

    if algo.upper() == "PPO":
        model = PPO(
            **model_params,
            n_steps=2048,  # Steps to collect per env before update
            batch_size=64,
            n_epochs=10,
            gamma=0.99,  # Discount factor
            ent_coef=0.01  # Entropy coefficient (exploration)
        )
    elif algo.upper() == "SAC":
        model = SAC(
            **model_params,
            buffer_size=1_000_000,  # SAC is off-policy
            batch_size=256,
            learning_starts=10_000,
            gamma=0.99,
        )
    else:
        raise ValueError(f"Algorithm '{algo}' not supported. Use 'PPO' or 'SAC'.")

    print(f"[RL Trainer] Model initialized: {algo.upper()}")
    print(f"  - Policy: {model_params['policy']}")

    # 7. --- Train the Model ---
    print("--- [RL Trainer] Starting training... ---")
    print(f"Logs available in TensorBoard: tensorboard --logdir {log_dir}")
    print("This will take a while. Press Ctrl+C to interrupt.")

    try:
        model.learn(
            total_timesteps=total_timesteps,
            callback=callback_list,
            progress_bar=True
        )
    except KeyboardInterrupt:
        print("\n[RL Trainer] Training interrupted by user.")

    # 8. --- Save the Final Model ---
    print(f"[RL Trainer] Saving final model to {final_model_path}...")
    model.save(final_model_path)

    print("--- [RL Trainer] Training Complete ---")
    print(f"  - Final model saved to: {final_model_path}")
    print(f"  - Best model (from eval) saved to: {best_model_save_path}")

    # Clean up environments
    train_env.close()
    eval_env.close()


# --- Main block to run the script from the command line ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train an RL model for Waste Segregation Policy.")

    parser.add_argument(
        "--timesteps",
        type=int,
        default=1_000_000,
        help="Total training timesteps (e.g., 1000000)."
    )
    parser.add_argument(
        "--algo",
        type=str,
        default="PPO",
        help="RL Algorithm to use (e.g., PPO, SAC)."
    )
    parser.add_argument(
        "--n-cpu",
        type=int,
        default=4,
        help="Number of parallel environments to use."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Base directory to save models (e.g., 'outputs')."
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="outputs/reports/rl_logs",
        help="Directory to save TensorBoard logs."
    )
    parser.add_argument(
        "--name",
        type=str,
        default=f"run_{int(time.time())}",
        help="Unique name for this training run (e.g., 'ppo_5barangay_run1')."
    )

    args = parser.parse_args()

    # Start the training
    train_rl_model(
        total_timesteps=args.timesteps,
        n_cpu=args.n_cpu,
        output_dir=args.output_dir,
        log_dir=args.log_dir,
        model_name=args.name,
        algo=args.algo
    )