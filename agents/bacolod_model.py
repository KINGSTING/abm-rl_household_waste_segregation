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
                print("Warning: No trained model found. Running in 'IEC Policy' Mode.")

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
        # We make this a class attribute to track IDs across dynamic spawning
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

            # Note: We do NOT spawn static Enforcers here anymore. 
            # They are now spawned dynamically in apply_action based on budget.

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
        """
        Calculates daily expenses based on the actual AI-allocated quarterly budget.
        Funds are amortized over 90 days.
        """
        # 1. FIXED COSTS (Base Salaries could go here, but we focus on discretionary funds)
        # We track dynamic enforcer costs via the 'enf_fund' allocation below.
        
        # 2. VARIABLE COSTS (The AI's Allocation)
        # The AI allocates a Quarterly Budget (90 days). 
        # We amortize this daily: Daily Cost = Total Allocation / 90.
        
        # Sum up funds across all barangays
        total_iec_alloc = sum(b.iec_fund for b in self.barangays)
        total_enf_alloc = sum(b.enf_fund for b in self.barangays)
        total_inc_alloc = sum(b.inc_fund for b in self.barangays)

        daily_iec_spend = total_iec_alloc / 90.0
        daily_enf_spend = total_enf_alloc / 90.0
        daily_inc_spend = total_inc_alloc / 90.0
        
        # 3. UPDATE TOTALS (For Analysis/Charts)
        self.total_enforcement_cost += daily_enf_spend
        self.total_incentives_distributed += daily_inc_spend
        self.total_iec_cost += daily_iec_spend
        
        # 4. DEDUCT FROM CURRENT BUDGET
        total_daily_expense = daily_iec_spend + daily_enf_spend + daily_inc_spend
        
        self.current_budget = self.current_budget - total_daily_expense + self.recent_fines_collected
        self.recent_fines_collected = 0

    def adjust_enforcement_agents(self, barangay):
        """
        Dynamically adds or removes EnforcementAgents based on the Barangay's 'enf_fund'.
        Assumption: 1 Enforcer cost ~ P400/day * 90 days = P36,000 per quarter.
        """
        COST_PER_ENFORCER_QUARTER = 36000.0
        
        # Calculate how many agents the budget can support
        target_count = int(barangay.enf_fund / COST_PER_ENFORCER_QUARTER)
        
        # Get current agents in this specific barangay
        current_agents = [
            a for a in self.schedule.agents 
            if isinstance(a, EnforcementAgent) and a.barangay_id == barangay.unique_id
        ]
        current_count = len(current_agents)
        
        diff = target_count - current_count
        
        if diff > 0:
            # SPAWN new agents
            for _ in range(diff):
                # Use a unique ID based on global counter
                e_id = f"ENF_{self.agent_id_counter}"
                self.agent_id_counter += 1
                
                new_agent = EnforcementAgent(e_id, self)
                new_agent.barangay_id = barangay.unique_id
                
                self.schedule.add(new_agent)
                # Place randomly in grid
                x = self.random.randrange(self.grid_width)
                y = self.random.randrange(self.grid_height)
                self.grid.place_agent(new_agent, (x, y))
                
        elif diff < 0:
            # REMOVE agents (Budget cuts)
            # Remove from the end of the list
            agents_to_remove = current_agents[:abs(diff)]
            for agent in agents_to_remove:
                if agent.pos:
                    self.grid.remove_agent(agent)
                self.schedule.remove(agent)

    def step(self):
        """
        Advance the model by one step.
        """
        # 1. QUARTERLY DECISION POINT (Every 90 steps)
        if self.schedule.steps % 90 == 0:
            current_quarter = (self.schedule.steps // 90) + 1
            print(f"\n--- Quarter {current_quarter} Decision Point ---")
            
            # A. Get State
            current_state = self.get_state()
            
            # B. Decide Action
            if not self.train_mode and self.rl_agent is not None:
                # AI Mode
                action, _ = self.rl_agent.predict(current_state, deterministic=True)
            else:
                # DEFAULT / MANUAL MODE (Requested "IEC Policy")
                # Distribute 375k equally across 7 barangays (~53.5k each).
                # Split: 36k for Enforcer (1 agent), 17.5k for IEC/Incentives.
                print("Running Default IEC Policy (375k Split)...")
                
                # Create a manual action vector of size 21 (7 barangays * 3 levers)
                # We normalize inputs to [0, 1] relative to the total budget later in apply_action,
                # but apply_action handles scaling. We just need ratios here.
                # Let's try to pass rough amounts.
                
                # Logic: We want approx P36,000 for Enforcers (to get 1 agent) and P17,000 for IEC.
                # Total per bgy = 53,000.
                # Ratios: IEC=0.3, Enf=0.7, Inc=0.0
                
                action = []
                for _ in range(7):
                    action.extend([0.3, 0.7, 0.0]) # [IEC, Enf, Inc]
                
                # This vector is normalized by apply_action to fit the quarterly budget constraint.
            
            # C. Apply Action (This triggers budget updates and agent spawning)
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
        
        # Stop after 3 years (approx 1080 steps)
        if self.schedule.steps >= 1080: self.running = False

    def print_agent_decision(self, action):
        """Helper to print what the AI actually decided."""
        print("LGU Agent Policy Update:")
        total_iec = sum(action[0::3])
        total_enf = sum(action[1::3])
        total_inc = sum(action[2::3])
        
        # Note: 'action' values here are raw from the AI/Manual. 
        # The ACTUAL spent amount is stored in the barangay agents after apply_action scales it.
        actual_iec = sum(b.iec_fund for b in self.barangays)
        actual_enf = sum(b.enf_fund for b in self.barangays)
        actual_inc = sum(b.inc_fund for b in self.barangays)
        
        print(f"  Total Allocated to IEC:         P {actual_iec:,.2f}")
        print(f"  Total Allocated to Enforcement: P {actual_enf:,.2f}")
        print(f"  Total Allocated to Incentives:  P {actual_inc:,.2f}")
        
        # Count total active enforcers
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
        Applies the RL Agent's decision.
        action_vector: List of 21 floats (3 levers * 7 barangays)
        """
        # Convert action vector (fractions/ratios) into Real Pesos relative to Quarterly Budget
        
        # 1. Sum up the raw "desires" from the vector
        total_desire = sum(action_vector)
        
        # 2. Scale to fit exactly into the Quarterly Budget (Use it or lose it logic)
        # If total_desire is 0, we spend nothing.
        # If total_desire > 0, we scale so that Sum(Allocations) == QUARTERLY_BUDGET
        if total_desire > 0:
            scale_factor = self.quarterly_budget / total_desire
        else:
            scale_factor = 0

        # 3. Apply to Barangays
        for i, bgy in enumerate(self.barangays):
            idx = i * 3
            
            # Allocate Funds
            iec_fund = action_vector[idx] * scale_factor
            enf_fund = action_vector[idx+1] * scale_factor
            inc_fund = action_vector[idx+2] * scale_factor
            
            # Update Barangay Policy
            bgy.update_policy(iec_fund, enf_fund, inc_fund)
            
            # DYNAMIC AGENT UPDATE:
            # Based on the new 'enf_fund', hire/fire enforcers
            self.adjust_enforcement_agents(bgy)

    def calculate_reward(self):
        """
        Calculates the Multi-Objective Reward (Thesis Eq 3.11).
        """
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