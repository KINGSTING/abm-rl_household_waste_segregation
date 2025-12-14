import os
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.callbacks import CheckpointCallback

# Import your custom environment
from bacolod_gym import BacolodGymEnv

def main():
    # 1. Create Directories for Logs and Models
    models_dir = "models/PPO"
    log_dir = "logs"
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    # 2. Instantiate the Environment
    env = BacolodGymEnv()
    
    # Sanity Check: Ensures your Gym environment adheres to standards
    # If this fails, there is a bug in bacolod_gym.py
    print("Checking environment...")
    check_env(env)
    print("Environment is valid!")

    # 3. Define the PPO Model (The "Brain")
    # Hyperparameters aligned with Thesis Section 3.4.1 [cite: 608]
    # - Policy: "MlpPolicy" (Multi-Layer Perceptron for continuous data)
    # - Gamma: 0.99 [cite: 599]
    # - Network Architecture: Actor-Critic with 2 hidden layers of 64 neurons [cite: 608]
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        tensorboard_log=log_dir,
        learning_rate=0.0003,
        gamma=0.99,  # Thesis Eq 3.5.3 (Discount Factor)
        policy_kwargs=dict(
            net_arch=dict(pi=[64, 64], vf=[64, 64]) # 64 neurons per layer
        )
    )

    # 4. Train the Agent
    # Thesis Section 3.5.1 suggests training over many "lifetimes".
    # 1 Episode = 3 Years (approx 12 steps). 
    # 10,000 steps = approx 833 full simulation runs.
    TIMESTEPS = 10000 
    
    print(f"Starting training for {TIMESTEPS} steps...")
    model.learn(total_timesteps=TIMESTEPS, progress_bar=True)
    
    # 5. Save the Final Model
    model_path = f"{models_dir}/bacolod_ppo_final"
    model.save(model_path)
    print(f"Training complete. Model saved to {model_path}.zip")

    # --- OPTIONAL: Test the Trained Model ---
    print("\nTesting the trained policy...")
    obs, _ = env.reset()
    done = False
    
    while not done:
        # Ask the AI for an action based on the current state
        action, _states = model.predict(obs)
        
        # Apply the action
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        
        # Print the result of this quarter
        print(f"Step: {info['step']} | Budget Left: {info['budget']:.0f} | Compliance: {info['compliance']:.2%}")

if __name__ == "__main__":
    main()