import gymnasium as gym
from gymnasium import spaces
import numpy as np
from agents.bacolod_model import BacolodModel

class BacolodGymEnv(gym.Env):
    """
    Custom Environment that follows gymnasium interface.
    This connects the BacolodModel (ABM) to the RL Agent.
    
    Thesis Alignment:
    - Action Space: Continuous (Box), size 21 (3 levers * 7 barangays) [Thesis Section 3.4.3]
    - Observation Space: Continuous (Box), size 10 (Compliance + Budget + Time + PolCap) [Thesis Section 3.4.2]
    - Reward Function: Multi-Objective (Compliance + Sustainability - Backlash) [Thesis Section 3.4.4]
    """
    metadata = {'render.modes': ['human']}

    def __init__(self):
        super(BacolodGymEnv, self).__init__()

        # --- 1. DEFINE ACTION SPACE (Thesis Eq 3.8) ---
        # 21 Continuous values representing the fraction of the Quarterly Budget.
        # Range: [0.0, 1.0]
        # Order: [Bgy0_IEC, Bgy0_Enf, Bgy0_Inc, Bgy1_IEC, ..., Bgy6_Inc]
        self.action_space = spaces.Box(low=0.0, high=1.0, shape=(21,), dtype=np.float32)

        # --- 2. DEFINE OBSERVATION SPACE (Thesis Eq 3.6) ---
        # 10 Continuous values: 
        # [CB_1, CB_2, ..., CB_7, B_Rem, M_Index, P_Cap]
        # Range: [0.0, 1.0] (Everything is normalized)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(10,), dtype=np.float32)

        # Initialize the ABM container
        self.model = None

    def reset(self, seed=None, options=None):
        """
        Resets the simulation for a new training episode (Start of a new 3-year term).
        """
        super().reset(seed=seed)
        
        # Create a fresh instance of the ABM
        # We use a fixed seed for reproducibility during debugging, but random for training
        self.model = BacolodModel(seed=seed if seed else 42)
        
        # Get the initial state (S_0)
        observation = self.model.get_state()
        
        return observation, {}

    def step(self, action):
        """
        The AI takes ONE action (Budget Allocation), and the environment advances by ONE QUARTER.
        Thesis Section 3.2.3: "The DRL agent will make policy adjustments every quarter."
        """
        # 1. Apply the AI's action to the model (The "Hands")
        self.model.apply_action(action)
        
        # 2. Run the simulation for ONE QUARTER (90 days/ticks)
        # The AI operates on a quarterly clock, while the ABM operates on a daily clock.
        for _ in range(90):
            self.model.step()
            
            # Stop early if the simulation ends (e.g., 3 years passed)
            if not self.model.running:
                break
        
        # 3. Get the new State (S_t+1) (The "Eyes")
        observation = self.model.get_state()
        
        # 4. Calculate Reward (R_t) (The "Scoreboard")
        reward = self.model.calculate_reward()
        
        # 5. Check Termination
        # The episode ends if the ABM stops running (e.g., 3 years/1080 ticks reached)
        terminated = not self.model.running
        truncated = False 
        
        # Debug Info (Optional)
        info = {
            "step": self.model.schedule.steps,
            "budget": self.model.current_budget,
            "compliance": observation[0:7].mean() # Avg compliance
        }
        
        return observation, reward, terminated, truncated, info

    def render(self, mode='human'):
        """
        Optional: Print stats to console for debugging.
        """
        if self.model:
            obs = self.model.get_state()
            print(f"--- Quarter {(self.model.schedule.steps // 90)} Report ---")
            print(f"Avg Compliance: {obs[0:7].mean():.2f}")
            print(f"Budget Left: {obs[7]*100:.1f}%")
            print(f"Political Cap: {obs[9]:.2f}")