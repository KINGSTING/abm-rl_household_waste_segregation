import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from model import WasteModel
from barangay_config import BARANGAY_CONFIGS # Import your 7 configs

class BarangayEnv(gym.Env):
    """
    Custom Environment that runs 7 Parallel ABM Simulations.
    """
    metadata = {"render_modes": ["console"]}

    def __init__(self):
        super(BarangayEnv, self).__init__()
        
        # --- 1. Define Action Space (The Policy Levers) ---
        # The Agent outputs 3 values between 0 and 1:
        # [Fine Efficacy, Incentive Efficacy, IEC Intensity]
        self.action_space = spaces.Box(
            low=0.0, high=1.0, shape=(3,), dtype=np.float32
        )

        # --- 2. Define Observation State (The Feedback) ---
        # What does the Agent see?
        # [Avg Compliance Rate, Avg Improper Disposal, Avg Collections]
        self.observation_space = spaces.Box(
            low=0.0, high=np.inf, shape=(3,), dtype=np.float32
        )
        
        # Simulation settings
        self.configs = BARANGAY_CONFIGS # Load the 7 configs
        self.timesteps_per_quarter = 90 # 90 Days per step
        self.current_quarter = 0
        self.max_quarters = 12 # 3 Years
        
        self.models = [] # This list will hold the 7 active simulations

    def reset(self, seed=None, options=None):
        """
        Resets the environment to the beginning (Year 1, Quarter 1).
        Re-initializes all 7 simulations with default policies.
        """
        super().reset(seed=seed)
        self.current_quarter = 0
        self.models = []
        
        # Initialize 7 separate models based on the configs
        for config in self.configs:
            model = WasteModel(
                N_HOUSEHOLDS=config['N_HOUSEHOLDS'],
                N_OFFICIALS=config['N_OFFICIALS'],
                N_VEHICLES=config['N_VEHICLES'],
                width=config['width'],
                height=config['height'],
                initial_compliance=config['initial_compliance'],
                # Default policy values (Agent will change these immediately in step 1)
                FINE_EFFICACY=0.1, 
                INCENTIVE_EFFICACY=0.1, 
                IEC_INTENSITY=0.1
            )
            self.models.append(model)
            
        # Get initial observation (State)
        return self._get_observation(), {}

    def step(self, action):
        """
        1. Apply ONE policy (Action) to ALL 7 models.
        2. Run all 7 models for 90 steps (1 quarter).
        3. Aggregate results to calculate Reward.
        """
        # Unpack the action (Policy Variables)
        fine_eff, incentive_eff, iec_intensity = action
        
        # --- A. RUN SIMULATIONS ---
        quarterly_data = []
        
        for model in self.models:
            # 1. Update Policy Variables for this model
            model.FINE_EFFICACY = fine_eff
            model.INCENTIVE_EFFICACY = incentive_eff
            model.IEC_INTENSITY = iec_intensity
            
            # 2. Run the ABM for 90 days (ticks)
            for _ in range(self.timesteps_per_quarter):
                model.step()
            
            # 3. Collect Data from this specific barangay
            # We grab the last row of data collected by Mesa
            df = model.datacollector.get_model_vars_dataframe()
            if not df.empty:
                last_state = df.iloc[-1]
                quarterly_data.append({
                    "compliance": last_state["ComplianceRate"],
                    "improper": last_state["ImproperDisposal"],
                    "collections": last_state["Collections"]
                })
            else:
                # Fallback if something fails
                quarterly_data.append({"compliance": 0, "improper": 0, "collections": 0})

        # --- B. AGGREGATE RESULTS (The "State") ---
        # Calculate the average performance across all 7 Barangays
        df_results = pd.DataFrame(quarterly_data)
        
        avg_compliance = df_results["compliance"].mean()
        total_improper = df_results["improper"].sum() # Total bad behavior
        total_collections = df_results["collections"].sum()
        
        observation = np.array([
            avg_compliance, 
            total_improper, 
            total_collections
        ], dtype=np.float32)

        # --- C. CALCULATE REWARD ---
        # Reward Function: Maximize Compliance, Minimize Improper Disposal & Cost
        # Heuristic Cost: Assume higher intensity = higher budget cost
        policy_cost = (fine_eff + incentive_eff + iec_intensity) / 3.0
        
        reward = (10.0 * avg_compliance) - (0.5 * total_improper) - (2.0 * policy_cost)
        
        # --- D. CHECK TERMINATION ---
        self.current_quarter += 1
        terminated = self.current_quarter >= self.max_quarters
        truncated = False
        
        info = {
            "quarter": self.current_quarter, 
            "results_breakdown": quarterly_data # Useful for debugging
        }

        return observation, reward, terminated, truncated, info

    def _get_observation(self):
        """Helper to get current state without advancing steps."""
        # Simple placeholder logic for initial reset
        return np.array([0.5, 0, 0], dtype=np.float32)