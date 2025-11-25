from stable_baselines3 import PPO
from rl_environment import BarangayEnv
import os

# 1. Create the Environment
env = BarangayEnv()

# 2. Define the RL Model (PPO is a standard, robust algorithm)
model = PPO("MlpPolicy", env, verbose=1)

# 3. Train the Agent
print("Starting Training...")
# 12 quarters * 1000 episodes = 12,000 timesteps
model.learn(total_timesteps=12000) 
print("Training Complete!")

# 4. Save the Model
models_dir = "models/PPO"
if not os.path.exists(models_dir):
    os.makedirs(models_dir)
model.save(f"{models_dir}/waste_policy_agent")

# --- 5. Test the Trained Agent ---
print("\nTesting Trained Policy...")
obs, _ = env.reset()
for i in range(12): # Run for 12 quarters (3 years)
    action, _states = model.predict(obs)
    obs, rewards, terminated, truncated, info = env.step(action)
    
    print(f"Quarter {i+1}:")
    print(f"  Policy Selected: Fine={action[0]:.2f}, Inc={action[1]:.2f}, IEC={action[2]:.2f}")
    print(f"  Result: Compliance={obs[0]:.2f}, Improper={obs[1]:.0f}, Reward={rewards:.2f}")