import mesa
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
import numpy as np
import random
import os
from stable_baselines3 import PPO

import barangay_config as config
from agents.household_agent import HouseholdAgent
from agents.barangay_agent import BarangayAgent
from agents.enforcement_agent import EnforcementAgent

def compute_global_compliance(model):
    agents = [a for a in model.schedule.agents if isinstance(a, HouseholdAgent)]
    if not agents: return 0.0
    return sum(1 for a in agents if a.is_compliant) / len(agents)

class BacolodModel(mesa.Model):
    def __init__(self, seed=None, train_mode=False): 
        if seed is not None:
            super().__init__(seed=seed)
            self._seed = seed
            np.random.seed(seed)
            random.seed(seed)
        else:
            super().__init__()

        # --- Simulation Mode ---
        self.train_mode = train_mode
        self.rl_agent = None
        
        # Load the Trained Brain (Only if NOT training)
        if not self.train_mode:
            model_path = "models/PPO/bacolod_ppo_final.zip"
            if os.path.exists(model_path):
                print(f"Loading Trained Agent from {model_path}...")
                self.rl_agent = PPO.load(model_path)
            else:
                print("Warning: No trained model found. Running in Status Quo mode.")

        # --- Financials ---
        self.annual_budget = config.ANNUAL_BUDGET
        self.current_budget = self.annual_budget
        self.quarterly_budget = self.annual_budget / 4 
        
        self.total_fines_collected = 0
        self.total_incentives_distributed = 0
        self.total_enforcement_cost = 0
        self.total_iec_cost = 0
        self.reward_value = 100
        self.recent_fines_collected = 0

        # --- Grid Setup ---
        self.grid_width = 50   
        self.grid_height = 50 
        self.grid = MultiGrid(self.grid_width, self.grid_height, torus=False)
        self.schedule = RandomActivation(self)
        self.running = True
        
        # --- Political Capital ---
        self.political_capital = 1.0     
        self.alpha_sensitivity = 0.05    
        self.beta_recovery = 0.02        

        self.barangays = []
        agent_id_counter = 0
        
        # --- LOOP THROUGH CONFIGURATION ---
        for i, b_conf in enumerate(config.BARANGAY_CONFIGS):
            b_agent = BarangayAgent(f"BGY_{i}", self)
            b_agent.name = b_conf["name"]
            
            # Policy Initialization
            b_agent.fine_amount = 500
            b_agent.enforcement_intensity = 0.5
            b_agent.iec_intensity = 0.0

            self.schedule.add(b_agent)
            self.barangays.append(b_agent)
            
            # --- NEW: Extract Behavior Profile ---
            # 1. Get the key (e.g., "Liangan_East") from config
            profile_key = b_conf.get("behavior_profile", "Poblacion") 
            
            # 2. Get the actual dictionary of weights from BEHAVIOR_PROFILES
            if profile_key in config.BEHAVIOR_PROFILES:
                behavior_data = config.BEHAVIOR_PROFILES[profile_key]
            else:
                print(f"Warning: Profile '{profile_key}' not found. Using default.")
                # Fallback to Poblacion profile if key is missing
                behavior_data = config.BEHAVIOR_PROFILES["Poblacion"]

            # Create Households
            n_households = b_conf["N_HOUSEHOLDS"]
            profile_key_income = b_conf["income_profile"]
            income_probs = list(config.INCOME_PROFILES[profile_key_income])
            
            for _ in range(n_households):
                x = self.random.randrange(self.grid_width)
                y = self.random.randrange(self.grid_height)
                income = np.random.choice([1, 2, 3], p=income_probs)
                is_compliant = (random.random() < b_conf["initial_compliance"])
                
                # 3. Pass behavior_data to the Agent
                a = HouseholdAgent(
                    agent_id_counter, 
                    self, 
                    income_level=income, 
                    initial_compliance=is_compliant,
                    behavior_params=behavior_data  # <--- CRITICAL CALIBRATION LINK
                )
                agent_id_counter += 1
                a.barangay = b_agent
                a.barangay_id = b_agent.unique_id
                
                self.schedule.add(a)
                self.grid.place_agent(a, (x, y))

            # Create Enforcers
            n_officials = b_conf["N_OFFICIALS"]
            visual_enforcers = min(n_officials, 5) 
            for _ in range(visual_enforcers):
                e_agent = EnforcementAgent(f"ENF_{agent_id_counter}", self)
                agent_id_counter += 1
                e_agent.barangay_id = b_agent.unique_id
                
                ex = self.random.randrange(self.grid_width)
                ey = self.random.randrange(self.grid_height)
                
                self.schedule.add(e_agent)
                self.grid.place_agent(e_agent, (ex, ey))

        # Data Collector
        reporters = {
            "Global Compliance": compute_global_compliance,
            "Total Fines": lambda m: m.total_fines_collected,
        }
        
        # --- FIX: Use exact names for the Chart ---
        # The order must match BARANGAY_CONFIGS in barangay_config.py
        # 0: Poblacion, 1: Liangan East, 2: Ezperanza, 3: Binuni, 4: Babalaya, 5: Mati, 6: Demologan
        bgy_names = ["Poblacion", "Liangan East", "Ezperanza", "Binuni", "Babalaya", "Mati", "Demologan"]
        
        for i, name in enumerate(bgy_names):
            # We capture 'i' in the lambda default argument so it sticks
            reporters[name] = lambda m, idx=i: m.barangays[idx].get_local_compliance()
            
        self.datacollector = DataCollector(model_reporters=reporters)

    def update_political_capital(self):
        avg_enforcement = 0
        if self.barangays:
            avg_enforcement = sum(b.enforcement_intensity for b in self.barangays) / len(self.barangays)
        
        decay = self.alpha_sensitivity * avg_enforcement
        recovery = self.beta_recovery * (1.0 - avg_enforcement)
        
        self.political_capital = self.political_capital - decay + recovery
        self.political_capital = max(0.0, min(1.0, self.political_capital))

    def calculate_costs(self):
        enforcers = [a for a in self.schedule.agents if isinstance(a, EnforcementAgent)]
        self.total_enforcement_cost += len(enforcers) * 400 
        households = [a for a in self.schedule.agents if isinstance(a, HouseholdAgent)]
        incentive_bill = sum(self.reward_value for h in households if h.is_compliant)
        self.total_incentives_distributed += incentive_bill
        self.total_iec_cost += 500 
        total_expense = (len(enforcers)*400) + incentive_bill + 500
        self.current_budget = self.current_budget - total_expense + self.recent_fines_collected
        self.recent_fines_collected = 0

    def step(self):
        """
        Advance the model by one step.
        """
        # 1. AI INTERVENTION (Start of Quarter)
        # Check if it's time for a decision (Every 90 steps, but not step 0)
        if not self.train_mode and self.rl_agent is not None:
            if self.schedule.steps > 0 and self.schedule.steps % 90 == 0:
                print(f"\n--- Quarter {self.schedule.steps // 90} Decision Point ---")
                current_state = self.get_state()
                action, _ = self.rl_agent.predict(current_state, deterministic=True)
                self.apply_action(action)
                self.print_agent_decision(action)

        # 2. Agents Act
        for b in self.barangays: b.step()
        self.schedule.step()
        
        # 3. Update Globals
        self.update_political_capital() 
        self.calculate_costs()
        
        # 4. Collect Data
        self.datacollector.collect(self)
        
        # Stop after 1 quarter
        if self.schedule.steps >= 89: self.running = False


    def print_agent_decision(self, action):
        """Helper to print what the AI actually decided."""
        print("LGU Agent Policy Update:")
        total_iec = sum(action[0::3])
        total_enf = sum(action[1::3])
        total_inc = sum(action[2::3])
        print(f"  Total Allocated to IEC:        P {total_iec:,.2f}")
        print(f"  Total Allocated to Enforcement: P {total_enf:,.2f}")
        print(f"  Total Allocated to Incentives:  P {total_inc:,.2f}")
        print(f"  Remaining Budget: P {self.current_budget:,.2f}")

    def get_state(self):
        """
        Returns the State Vector (S_t) for the Reinforcement Learning Agent.
        """
        # 1. Compliance Rates (7 numbers)
        compliance_rates = [b.get_local_compliance() for b in self.barangays]
        
        # 2. Remaining Budget (Normalized 0-1)
        norm_budget = self.current_budget / self.annual_budget
        norm_budget = max(0.0, min(1.0, norm_budget)) 
        
        # 3. Time Index (Quarter 1-12)
        current_quarter = (self.schedule.steps // 90) + 1
        norm_time = current_quarter / 12.0            
        norm_time = max(0.0, min(1.0, norm_time))     
        
        # 4. Political Capital (0-1)
        p_cap = max(0.0, min(1.0, self.political_capital)) 
        
        # Combine into one list (Size: 10)
        state = compliance_rates + [norm_budget, norm_time, p_cap]
        return np.array(state, dtype=np.float32)
    
    def apply_action(self, action_vector):
        """
        Applies the RL Agent's decision.
        action_vector: List of 21 floats (3 levers * 7 barangays)
        """
        total_alloc = sum(action_vector)
        
        if total_alloc == 0:
            return 

        if total_alloc > self.quarterly_budget:
            scale_factor = self.quarterly_budget / total_alloc
            action_vector = [a * scale_factor for a in action_vector]

        for i, bgy in enumerate(self.barangays):
            idx = i * 3
            iec_fund = action_vector[idx]
            enf_fund = action_vector[idx+1]
            inc_fund = action_vector[idx+2]
            
            bgy.update_policy(iec_fund, enf_fund, inc_fund)

    def calculate_reward(self):
        """
        Calculates the Multi-Objective Reward (Thesis Eq 3.11).
        """
        w1 = 1.0  # Priority: Compliance
        w2 = 0.5  # Priority: Budget Safety
        w3 = 0.8  # Priority: Political Stability

        # 1. COMPLIANCE REWARD
        if not self.barangays:
            avg_compliance = 0.0
        else:
            avg_compliance = sum(b.get_local_compliance() for b in self.barangays) / len(self.barangays)
        
        # 2. SUSTAINABILITY REWARD
        total_steps = 1080 
        ideal_remaining_pct = max(0.0, 1.0 - (self.schedule.steps / total_steps))
        actual_remaining_pct = self.current_budget / self.annual_budget
        sustainability_penalty = abs(actual_remaining_pct - ideal_remaining_pct)
        r_sustainability = -sustainability_penalty 

        # 3. POLITICAL BACKLASH PENALTY
        avg_enforcement = 0.0
        if self.barangays:
            avg_enforcement = sum(b.enforcement_intensity for b in self.barangays) / len(self.barangays)
            
        p_backlash = 0.0
        if avg_enforcement > 0.7 and avg_compliance < 0.3:
            p_backlash = 1.0 

        # TOTAL REWARD CALCULATION
        r_total = (w1 * avg_compliance) + (w2 * r_sustainability) - (w3 * p_backlash)
        
        return r_total