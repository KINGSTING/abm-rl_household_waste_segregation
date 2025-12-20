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
    # FIX: Added 'policy_mode' to __init__ arguments
    def __init__(self, seed=None, train_mode=False, policy_mode="status_quo"): 
        """
        policy_mode options:
          "status_quo"       -> 100% IEC (Default)
          "pure_incentives"  -> 100% Incentives
          "pure_enforcement" -> 100% Enforcement
          "ppo"              -> AI / Hybrid Policy
        """
        if seed is not None:
            super().__init__(seed=seed)
            self._seed = seed
            np.random.seed(seed)
            random.seed(seed)
        else:
            super().__init__()

        # --- Simulation Mode ---
        self.train_mode = train_mode
        self.policy_mode = policy_mode # Store the user choice
        self.rl_agent = None
        
        # --- CSV Logging Setup ---
        self.log_filename = f"bacolod_report_{self.policy_mode}.csv"
        
        with open(self.log_filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Quarter", 
                "Tick", 
                "Barangay_ID", 
                "Barangay_Name", 
                "Total_Allocation_PHP", 
                "IEC_Percent", 
                "Enforcement_Percent", 
                "Incentives_Percent",
                "Compliance_Rate",
                "Active_Enforcers"
            ])

        # Load the Trained Brain (Only if needed for PPO mode)
        if not self.train_mode and self.policy_mode == "ppo":
            model_path = "models/PPO/bacolod_ppo_final.zip"
            if os.path.exists(model_path):
                print(f"Loading Trained Agent from {model_path}...")
                self.rl_agent = PPO.load(model_path)
            else:
                print("Warning: No trained model found. Fallback behavior may occur.")

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
            
            # Policy Initialization (Defaults)
            b_agent.fine_amount = 500
            b_agent.enforcement_intensity = 0.5
            b_agent.iec_intensity = 0.0

            self.schedule.add(b_agent)
            self.barangays.append(b_agent)
            
            # --- Extract Behavior Profile ---
            profile_key = b_conf.get("behavior_profile", "Poblacion") 
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
                    behavior_params=behavior_data  
                )
                self.agent_id_counter += 1
                a.barangay = b_agent
                a.barangay_id = b_agent.unique_id
                
                self.schedule.add(a)
                self.grid.place_agent(a, (x, y))

        # Data Collector
        reporters = {
            "Global Compliance": compute_global_compliance,
            "Total Fines": lambda m: m.total_fines_collected,
        }
        bgy_names = ["Poblacion", "Liangan East", "Ezperanza", "Binuni", "Babalaya", "Mati", "Demologan"]
        for i, name in enumerate(bgy_names):
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
        total_iec_alloc = sum(b.iec_fund for b in self.barangays)
        total_enf_alloc = sum(b.enf_fund for b in self.barangays)
        total_inc_alloc = sum(b.inc_fund for b in self.barangays)

        daily_iec_spend = total_iec_alloc / 90.0
        daily_enf_spend = total_enf_alloc / 90.0
        daily_inc_spend = total_inc_alloc / 90.0
        
        self.total_enforcement_cost += daily_enf_spend
        self.total_incentives_distributed += daily_inc_spend
        self.total_iec_cost += daily_iec_spend
        
        total_daily_expense = daily_iec_spend + daily_enf_spend + daily_inc_spend
        
        self.current_budget = self.current_budget - total_daily_expense + self.recent_fines_collected
        self.recent_fines_collected = 0

    def adjust_enforcement_agents(self, barangay):
        COST_PER_ENFORCER_QUARTER = 36000.0
        target_count = int(barangay.enf_fund / COST_PER_ENFORCER_QUARTER)
        
        current_agents = [
            a for a in self.schedule.agents 
            if isinstance(a, EnforcementAgent) and a.barangay_id == barangay.unique_id
        ]
        current_count = len(current_agents)
        diff = target_count - current_count
        
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
                if agent.pos:
                    self.grid.remove_agent(agent)
                self.schedule.remove(agent)

    def log_quarterly_report(self, quarter):
        """
        Writes the breakdown of each Barangay's budget allocation to CSV.
        """
        with open(self.log_filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            
            for b in self.barangays:
                total = b.iec_fund + b.enf_fund + b.inc_fund
                
                if total > 0:
                    iec_pct = (b.iec_fund / total) * 100
                    enf_pct = (b.enf_fund / total) * 100
                    inc_pct = (b.inc_fund / total) * 100
                else:
                    iec_pct, enf_pct, inc_pct = 0.0, 0.0, 0.0

                active_enforcers = len([
                    a for a in self.schedule.agents 
                    if isinstance(a, EnforcementAgent) and a.barangay_id == b.unique_id
                ])
                
                writer.writerow([
                    quarter,
                    self.schedule.steps,
                    b.unique_id,
                    b.name,
                    f"{total:.2f}",
                    f"{iec_pct:.2f}%",
                    f"{enf_pct:.2f}%",
                    f"{inc_pct:.2f}%",
                    f"{b.get_local_compliance():.2%}",
                    active_enforcers
                ])
        
        print(f" > Report for Quarter {quarter} saved to {self.log_filename}")

    def step(self):
        """
        Advance the model by one step.
        """
        # 1. QUARTERLY DECISION POINT (Every 90 steps)
        if self.schedule.steps % 90 == 0:
            current_quarter = (self.schedule.steps // 90) + 1
            print(f"\n--- Quarter {current_quarter} Decision Point ({self.policy_mode.upper()}) ---")
            
            # A. Get State
            current_state = self.get_state()
            
            # B. Decide Action based on Policy Mode
            action = []
            
            if self.policy_mode == "ppo" and self.rl_agent is not None:
                # #4 HYBRID: PPO Agent
                action, _ = self.rl_agent.predict(current_state, deterministic=True)
                
            elif self.policy_mode == "pure_incentives":
                # #2 POLICY: 100% Incentives
                print("Running Policy: Pure Incentives (100% Incentives)")
                for _ in range(7): 
                    action.extend([0.0, 0.0, 1.0]) # [IEC, ENF, INC]

            elif self.policy_mode == "pure_enforcement":
                # #3 POLICY: 100% Enforcement
                print("Running Policy: Pure Enforcement (100% Enforcement)")
                for _ in range(7): 
                    action.extend([0.0, 1.0, 0.0]) # [IEC, ENF, INC]
            
            else:
                # #1 POLICY: Status Quo (Default) - 100% IEC
                print("Running Policy: Status Quo (100% IEC)")
                for _ in range(7): 
                    action.extend([1.0, 0.0, 0.0]) # [IEC, ENF, INC]
            
            # C. Apply Action
            self.apply_action(action)
            self.print_agent_decision(action)
            
            # D. Log Data
            self.log_quarterly_report(current_quarter)

        # 2. Agents Act
        for b in self.barangays: b.step()
        self.schedule.step()
        
        # 3. Update Globals
        self.update_political_capital() 
        self.calculate_costs()
        
        # 4. Collect Data
        self.datacollector.collect(self)
        
        # Stop after 3 years (approx 1080 steps)
        if self.schedule.steps >= 1080: self.running = False

    def print_agent_decision(self, action):
        """Helper to print what the AI/Policy decided."""
        print("LGU Policy Update:")
        actual_iec = sum(b.iec_fund for b in self.barangays)
        actual_enf = sum(b.enf_fund for b in self.barangays)
        actual_inc = sum(b.inc_fund for b in self.barangays)
        
        print(f"  Total Allocated to IEC:         P {actual_iec:,.2f}")
        print(f"  Total Allocated to Enforcement: P {actual_enf:,.2f}")
        print(f"  Total Allocated to Incentives:  P {actual_inc:,.2f}")
        
        enforcers = [a for a in self.schedule.agents if isinstance(a, EnforcementAgent)]
        print(f"  Active Enforcers Deployed:      {len(enforcers)}")
        print(f"  Remaining LGU Budget:           P {self.current_budget:,.2f}")

    def get_state(self):
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
        
        state = compliance_rates + [norm_budget, norm_time, p_cap]
        return np.array(state, dtype=np.float32)
    
    def apply_action(self, action_vector):
        """
        Applies the decision.
        """
        total_desire = sum(action_vector)
        
        if total_desire > 0:
            scale_factor = self.quarterly_budget / total_desire
        else:
            scale_factor = 0

        for i, bgy in enumerate(self.barangays):
            idx = i * 3
            
            # Allocate Funds
            iec_fund = action_vector[idx] * scale_factor
            enf_fund = action_vector[idx+1] * scale_factor
            inc_fund = action_vector[idx+2] * scale_factor
            
            # Update Barangay Policy
            bgy.update_policy(iec_fund, enf_fund, inc_fund)
            
            # DYNAMIC AGENT UPDATE
            self.adjust_enforcement_agents(bgy)

    def calculate_reward(self):
        w1 = 1.0  # Priority: Compliance
        w2 = 0.5  # Priority: Budget Safety
        w3 = 0.8  # Priority: Political Stability

        if not self.barangays:
            avg_compliance = 0.0
        else:
            avg_compliance = sum(b.get_local_compliance() for b in self.barangays) / len(self.barangays)
        
        total_steps = 1080 
        ideal_remaining_pct = max(0.0, 1.0 - (self.schedule.steps / total_steps))
        actual_remaining_pct = self.current_budget / self.annual_budget
        sustainability_penalty = abs(actual_remaining_pct - ideal_remaining_pct)
        r_sustainability = -sustainability_penalty 

        avg_enforcement = 0.0
        if self.barangays:
            avg_enforcement = sum(b.enforcement_intensity for b in self.barangays) / len(self.barangays)
            
        p_backlash = 0.0
        if avg_enforcement > 0.7 and avg_compliance < 0.3:
            p_backlash = 1.0 

        r_total = (w1 * avg_compliance) + (w2 * r_sustainability) - (w3 * p_backlash)
        return r_total