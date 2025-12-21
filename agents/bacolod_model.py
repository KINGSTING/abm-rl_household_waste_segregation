import mesa
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
import numpy as np
import random
import os
import csv 
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
    # 1. MODIFIED INIT: Added behavior_override parameter
    def __init__(self, seed=None, train_mode=False, policy_mode="status_quo", behavior_override=None): 
        if seed is not None:
            super().__init__(seed=seed)
            self._seed = seed
            np.random.seed(seed)
            random.seed(seed)
        else:
            super().__init__()

        self.train_mode = train_mode
        self.policy_mode = policy_mode 
        self.rl_agent = None
        
        # 2. STORE OVERRIDE: Save the injected genome
        self.behavior_override = behavior_override

        if self.behavior_override:
            print(f"\n[INIT] Calibration Mode Active. Overriding config.")
        else:
            print(f"\n[INIT] BacolodModel created with Policy Mode: {self.policy_mode.upper()}")
        
        # --- CSV Logging Setup (UPDATED) ---
        # Create a 'results' folder if it doesn't exist
        results_dir = "results"
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)

        # Update filename to save inside the folder
        self.log_filename = os.path.join(results_dir, f"bacolod_report_{self.policy_mode}.csv")
        
        # Only create/wipe the CSV if we are NOT calibrating (to avoid spamming files)
        if not self.behavior_override:
            with open(self.log_filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "Quarter", "Tick", "Barangay_ID", "Barangay_Name", 
                    "Total_Allocation_PHP", "IEC_Percent", "Enforcement_Percent", 
                    "Incentives_Percent", "Compliance_Rate", "Active_Enforcers"
                ])

        # Load Brain (Only if PPO mode AND not calibrating)
        if not self.train_mode and self.policy_mode == "ppo" and not self.behavior_override:
            model_path = "models/PPO/bacolod_ppo_final.zip"
            if os.path.exists(model_path):
                print(f"Loading Trained Agent from {model_path}...")
                self.rl_agent = PPO.load(model_path)
            else:
                print("Warning: No trained model found. Will default to Status Quo.")

        # --- Financials ---
        self.annual_budget = config.ANNUAL_BUDGET
        self.current_budget = self.annual_budget
        self.quarterly_budget = self.annual_budget / 4 
        
        self.total_fines_collected = 0
        self.total_incentives_distributed = 0
        self.total_enforcement_cost = 0
        self.total_iec_cost = 0
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
        self.agent_id_counter = 0 
        
        # --- LOOP THROUGH CONFIGURATION ---
        for i, b_conf in enumerate(config.BARANGAY_CONFIGS):
            b_agent = BarangayAgent(f"BGY_{i}", self)
            b_agent.name = b_conf["name"]
            b_agent.n_households = b_conf["N_HOUSEHOLDS"]
            
            # Policy Initialization
            b_agent.fine_amount = 500
            b_agent.enforcement_intensity = 0.5
            b_agent.iec_intensity = 0.0

            self.schedule.add(b_agent)
            self.barangays.append(b_agent)
            
            # --- 3. MODIFIED BEHAVIOR EXTRACTION LOGIC ---
            # Determine which profile this barangay uses (e.g., "Poblacion", "Liangan_East")
            profile_key = b_conf.get("behavior_profile", "Poblacion") 
            
            if self.behavior_override:
                # OPTION A: CALIBRATION MODE
                # We use the evolved parameters passed from calibrate_config.py
                # The override dictionary should match the structure of config.BEHAVIOR_PROFILES
                if profile_key in self.behavior_override:
                    behavior_data = self.behavior_override[profile_key]
                else:
                    # Fallback if key missing in genome
                    behavior_data = config.BEHAVIOR_PROFILES["Poblacion"]
            else:
                # OPTION B: NORMAL MODE (Use static file)
                if profile_key in config.BEHAVIOR_PROFILES:
                    behavior_data = config.BEHAVIOR_PROFILES[profile_key]
                else:
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
                
                a = HouseholdAgent(
                    self.agent_id_counter, 
                    self, 
                    income_level=income, 
                    initial_compliance=is_compliant,
                    behavior_params=behavior_data  # Uses the injected data if calibrating
                )
                self.agent_id_counter += 1
                a.barangay = b_agent
                a.barangay_id = b_agent.unique_id
                
                self.schedule.add(a)
                self.grid.place_agent(a, (x, y))

        # Data Collector Setup
        reporters = {
            "Global Compliance": compute_global_compliance,
            "Total Fines": lambda m: m.total_fines_collected,
        }
        
        def make_reporter(b_id):
            return lambda m: next(
                (b.get_local_compliance() for b in m.barangays if b.unique_id == b_id), 
                0.0
            )

        barangay_map = {
            "Poblacion": "BGY_0",
            "Liangan East": "BGY_1",
            "Ezperanza": "BGY_2",
            "Binuni": "BGY_3",
            "Babalaya": "BGY_4",
            "Mati": "BGY_5",
            "Demologan": "BGY_6"
        }

        for name, b_id in barangay_map.items():
            reporters[name] = make_reporter(b_id)
            
        self.datacollector = DataCollector(model_reporters=reporters)

    # ... [Keep your update_political_capital, calculate_costs, etc. exactly the same] ...
    
    def update_political_capital(self):
        avg_enforcement = 0
        if self.barangays:
            avg_enforcement = sum(b.enforcement_intensity for b in self.barangays) / len(self.barangays)
        
        decay = self.alpha_sensitivity * avg_enforcement
        recovery = self.beta_recovery * (1.0 - avg_enforcement)
        self.political_capital = max(0.0, min(1.0, self.political_capital - decay + recovery))

    def calculate_costs(self):
        # 1. Calculate Allocations (Daily Burn)
        # Note: We ONLY calculate burn for IEC and Enforcement.
        # Incentives are now handled dynamically by BarangayAgent.give_reward()
        total_iec_alloc = sum(b.iec_fund for b in self.barangays)
        total_enf_alloc = sum(b.enf_fund for b in self.barangays)
        
        # 2. Calculate Daily Operational Cost (Fixed costs / 90 days)
        daily_fixed_cost = (total_iec_alloc + total_enf_alloc) / 90.0
        
        # 3. Update Global Trackers
        self.total_enforcement_cost += (total_enf_alloc / 90.0)
        self.total_iec_cost += (total_iec_alloc / 90.0)
        # Note: self.total_incentives_distributed is no longer updated here.
        # It is updated inside BarangayAgent.give_reward() when money actually moves.

        # 4. Deduct from City Budget
        self.current_budget = self.current_budget - daily_fixed_cost + self.recent_fines_collected
        self.recent_fines_collected = 0

    def adjust_enforcement_agents(self, barangay):
        COST_PER_ENFORCER_QUARTER = 36000.0
        target_count = int(barangay.enf_fund / COST_PER_ENFORCER_QUARTER)
        
        current_agents = [
            a for a in self.schedule.agents 
            if isinstance(a, EnforcementAgent) and a.barangay_id == barangay.unique_id
        ]
        diff = target_count - len(current_agents)
        
        if diff > 0:
            for _ in range(diff):
                e_id = f"ENF_{self.agent_id_counter}"
                self.agent_id_counter += 1
                new_agent = EnforcementAgent(e_id, self)
                new_agent.barangay_id = barangay.unique_id
                self.schedule.add(new_agent)
                x = self.random.randrange(self.grid_width)
                y = self.random.randrange(self.grid_height)
                self.grid.place_agent(new_agent, (x, y))
        elif diff < 0:
            agents_to_remove = current_agents[:abs(diff)]
            for agent in agents_to_remove:
                if agent.pos: self.grid.remove_agent(agent)
                self.schedule.remove(agent)

    def log_quarterly_report(self, quarter):
        # Only log if NOT in calibration mode
        if self.behavior_override: return

        # Ensure we append to the file created in __init__ (which includes the 'results/' path)
        with open(self.log_filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            for b in self.barangays:
                total = b.iec_fund + b.enf_fund + b.inc_fund
                iec_pct = (b.iec_fund / total * 100) if total > 0 else 0
                enf_pct = (b.enf_fund / total * 100) if total > 0 else 0
                inc_pct = (b.inc_fund / total * 100) if total > 0 else 0

                active_enforcers = len([a for a in self.schedule.agents if isinstance(a, EnforcementAgent) and a.barangay_id == b.unique_id])
                
                writer.writerow([
                    quarter, self.schedule.steps, b.unique_id, b.name,
                    f"{total:.2f}", f"{iec_pct:.2f}%", f"{enf_pct:.2f}%", f"{inc_pct:.2f}%",
                    f"{b.get_local_compliance():.2%}", active_enforcers
                ])
        print(f" > Report for Quarter {quarter} saved to {self.log_filename}")

    def step(self):
        # 1. QUARTERLY DECISION POINT (Every 90 steps)
        if self.schedule.steps % 90 == 0:
            current_quarter = (self.schedule.steps // 90) + 1
            if not self.behavior_override: # Reduce spam during calibration
                print(f"\n--- Quarter {current_quarter} Decision Point ({self.policy_mode.upper()}) ---")
            
            current_state = self.get_state()
            action = []

            if self.policy_mode == "ppo" and self.rl_agent is not None:
                action, _ = self.rl_agent.predict(current_state, deterministic=True)
            else:
                # --- HYBRID ALLOCATION FIX (To Prevent Poblacion Spikes) ---
                base_share = 0 # 10% split evenly
                pop_share = 1  # 90% split by population
                total_hh = sum(b.n_households for b in self.barangays)

                for b in self.barangays:
                    share_base = (1.0 / len(self.barangays)) * base_share
                    share_pop = (b.n_households / total_hh) * pop_share
                    total_weight = share_base + share_pop

                    if self.policy_mode == "pure_incentives":
                         action.extend([0.0, 0.0, total_weight])
                    elif self.policy_mode == "pure_enforcement":
                         action.extend([0.0, total_weight, 0.0])
                    else: # Status Quo
                         action.extend([total_weight, 0.0, 0.0])
            
            self.apply_action(action)
            self.log_quarterly_report(current_quarter)

            # --- NEW: RESET REDEMPTION FLAGS FOR THE NEW QUARTER ---
            # This allows households to claim the incentive again in the new quarter
            if not self.behavior_override:
                print(" >> New Quarter: Resetting Redemption Flags")
            
            for a in self.schedule.agents:
                if isinstance(a, HouseholdAgent):
                    a.redeemed_this_quarter = False

        # 2. Agents Act
        for b in self.barangays: b.step()
        self.schedule.step()
        
        # 3. Update Globals
        self.update_political_capital() 
        self.calculate_costs()
        self.datacollector.collect(self)
        
        if self.schedule.steps >= 1080: self.running = False

    def get_state(self):
        compliance_rates = [b.get_local_compliance() for b in self.barangays]
        norm_budget = max(0.0, min(1.0, self.current_budget / self.annual_budget))
        norm_time = max(0.0, min(1.0, ((self.schedule.steps // 90) + 1) / 12.0))
        p_cap = max(0.0, min(1.0, self.political_capital)) 
        state = compliance_rates + [norm_budget, norm_time, p_cap]
        return np.array(state, dtype=np.float32)
    
    def apply_action(self, action_vector):
        total_desire = sum(action_vector)
        scale_factor = (self.quarterly_budget / total_desire) if total_desire > 0 else 0

        for i, bgy in enumerate(self.barangays):
            idx = i * 3
            iec_fund = action_vector[idx] * scale_factor
            enf_fund = action_vector[idx+1] * scale_factor
            inc_fund = action_vector[idx+2] * scale_factor
            
            bgy.update_policy(iec_fund, enf_fund, inc_fund)
            self.adjust_enforcement_agents(bgy)