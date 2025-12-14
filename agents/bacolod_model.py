import mesa
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
import numpy as np
import random
import barangay_config as config
from agents.household_agent import HouseholdAgent
from agents.barangay_agent import BarangayAgent
from agents.enforcement_agent import EnforcementAgent

def compute_global_compliance(model):
    agents = [a for a in model.schedule.agents if isinstance(a, HouseholdAgent)]
    if not agents: return 0.0
    return sum(1 for a in agents if a.is_compliant) / len(agents)

class BacolodModel(mesa.Model):
    def __init__(self, seed=None): 
        if seed is not None:
            super().__init__(seed=seed)
            self._seed = seed
            np.random.seed(seed)
            random.seed(seed)
        else:
            super().__init__()

        # Financials
        self.annual_budget = config.ANNUAL_BUDGET
        self.current_budget = self.annual_budget
        self.quarterly_budget = self.annual_budget / 4  # Fixed: Needed for apply_action scaling
        
        self.total_fines_collected = 0
        self.total_incentives_distributed = 0
        self.total_enforcement_cost = 0
        self.total_iec_cost = 0
        self.reward_value = 100
        self.recent_fines_collected = 0

        # Grid Setup (Standard 50x50 independent space)
        self.grid_width = 50   
        self.grid_height = 50 
        self.grid = MultiGrid(self.grid_width, self.grid_height, torus=False)
        self.schedule = RandomActivation(self)
        self.running = True
        
        # Political Capital Parameters (Thesis Eq 3.7)
        self.political_capital = 1.0     # Starts at 100%
        self.alpha_sensitivity = 0.05    # Fixed: Renamed from self.alpha to match update function
        self.beta_recovery = 0.02        # Fixed: Renamed from self.beta to match update function

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
            
            # Create Households
            n_households = b_conf["N_HOUSEHOLDS"]
            profile_key = b_conf["income_profile"]
            income_probs = list(config.INCOME_PROFILES[profile_key])
            
            for _ in range(n_households):
                x = self.random.randrange(self.grid_width)
                y = self.random.randrange(self.grid_height)
                income = np.random.choice([1, 2, 3], p=income_probs)
                is_compliant = (random.random() < b_conf["initial_compliance"])
                
                a = HouseholdAgent(agent_id_counter, self, income_level=income, initial_compliance=is_compliant)
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
        for i in range(7):
            reporters[f"Bgy {i}"] = lambda m, b_idx=i: m.barangays[b_idx].get_local_compliance()
        self.datacollector = DataCollector(model_reporters=reporters)

    def update_political_capital(self):
        """
        Updates the LGU's Political Capital based on enforcement intensity.
        Thesis Eq 3.7: P_cap(t+1) = P_cap(t) - (alpha * E) + (beta * Decay)
        """
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
        # 1. Agents Act
        for b in self.barangays: b.step()
        self.schedule.step()
        
        # 2. Update Globals
        self.update_political_capital() 
        self.calculate_costs()
        
        # 3. Collect Data
        self.datacollector.collect(self)
        
        if self.schedule.steps >= 90: self.running = False

    def get_state(self):
        """
        Returns the State Vector (S_t) for the Reinforcement Learning Agent.
        Format: [CB_1...7, B_Rem, M_Index, P_Cap] (Size 10)
        """
        # 1. Compliance Rates (7 numbers)
        compliance_rates = [b.get_local_compliance() for b in self.barangays]
        
        # 2. Remaining Budget (Normalized 0-1)
        norm_budget = self.current_budget / self.annual_budget
        
        # 3. Time Index (Quarter 1-4)
        current_quarter = (self.schedule.steps // 90) + 1
        norm_time = current_quarter / 4.0
        
        # 4. Political Capital (0-1)
        p_cap = self.political_capital
        
        # Combine into one list (Size: 10)
        state = compliance_rates + [norm_budget, norm_time, p_cap]
        return np.array(state, dtype=np.float32)
    
    def apply_action(self, action_vector):
        """
        Applies the RL Agent's decision.
        action_vector: List of 21 floats (3 levers * 7 barangays)
        """
        # 1. Decode Action (Scale to Quarterly Budget)
        total_alloc = sum(action_vector)
        
        # Prevent division by zero
        if total_alloc == 0:
            return 

        # If AI tries to spend more than allowed, scale it down
        if total_alloc > self.quarterly_budget:
            scale_factor = self.quarterly_budget / total_alloc
            action_vector = [a * scale_factor for a in action_vector]

        # 2. Apply to Each Barangay
        for i, bgy in enumerate(self.barangays):
            idx = i * 3
            iec_fund = action_vector[idx]
            enf_fund = action_vector[idx+1]
            inc_fund = action_vector[idx+2]
            
            bgy.update_policy(iec_fund, enf_fund, inc_fund)

    def calculate_reward(self):
        """
        Calculates the Multi-Objective Reward (Thesis Eq 3.11).
        R_total = w1*Compliance + w2*Sustainability - w3*Backlash
        """
        # Weights (Calibrated based on thesis Section 3.4.4)
        w1 = 1.0  # Priority: Compliance
        w2 = 0.5  # Priority: Budget Safety
        w3 = 0.8  # Priority: Political Stability

        # 1. COMPLIANCE REWARD (R_Compliance)
        # Average compliance across all 7 barangays
        if not self.barangays:
            avg_compliance = 0.0
        else:
            avg_compliance = sum(b.get_local_compliance() for b in self.barangays) / len(self.barangays)
        
        # 2. SUSTAINABILITY REWARD (R_Sustainability) (Thesis Eq 3.12)
        # Penalty for spending too fast. Ideal burn rate is ~25% per quarter.
        # We calculate deviation from the ideal remaining budget.
        
        # Total steps in a year = 4 quarters * 90 days = 360 ticks
        total_steps = 360 
        # Calculate where we SHOULD be (e.g., at step 90, we should have 75% budget left)
        ideal_remaining_pct = max(0.0, 1.0 - (self.schedule.steps / total_steps))
        
        # Calculate where we ACTUALLY are
        actual_remaining_pct = self.current_budget / self.annual_budget
        
        # Penalty increases as gap between Actual and Ideal widens
        # We use negative absolute error so it becomes a penalty
        sustainability_penalty = abs(actual_remaining_pct - ideal_remaining_pct)
        r_sustainability = -sustainability_penalty 

        # 3. POLITICAL BACKLASH PENALTY (P_Backlash) (Thesis Section 3.4.4)
        # Triggered if Enforcement is High (>0.7) but Compliance is Low (<0.3)
        # "Penalizing all households is unfeasible"
        avg_enforcement = 0.0
        if self.barangays:
            avg_enforcement = sum(b.enforcement_intensity for b in self.barangays) / len(self.barangays)
            
        p_backlash = 0.0
        if avg_enforcement > 0.7 and avg_compliance < 0.3:
            p_backlash = 1.0  # Heavy penalty for "Draconian" measures on unprepared people

        # TOTAL REWARD CALCULATION
        r_total = (w1 * avg_compliance) + (w2 * r_sustainability) - (w3 * p_backlash)
        
        return r_total