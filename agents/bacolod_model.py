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
        self.total_fines_collected = 0
        self.total_incentives_distributed = 0
        self.total_enforcement_cost = 0
        self.total_iec_cost = 0
        self.reward_value = 100
        self.current_budget = config.ANNUAL_BUDGET
        self.recent_fines_collected = 0

        # 1. SETUP GRID (Standard Size for ONE Barangay)
        # We use a standard size (e.g., 50x50). All 7 barangays will use this SAME coordinate space independently.
        self.grid_width = 50   
        self.grid_height = 50 
        self.grid = MultiGrid(self.grid_width, self.grid_height, torus=False)
        self.schedule = RandomActivation(self)
        self.running = True
        
        self.political_capital = 1.0  # Starts at 100% (Eq 3.6)
        self.alpha = 0.05  # Sensitivity to enforcement (Eq 3.7)
        self.beta = 0.02   # Recovery rate (Eq 3.7)

        self.barangays = []
        agent_id_counter = 0
        
        # --- LOOP THROUGH CONFIGURATION ---
        for i, b_conf in enumerate(config.BARANGAY_CONFIGS):
            b_agent = BarangayAgent(f"BGY_{i}", self)
            b_agent.name = b_conf["name"]
            
            # Policy Initialization
            b_agent.fine_amount = 500
            b_agent.enforcement_intensity = 0.5

            self.schedule.add(b_agent)
            self.barangays.append(b_agent)
            
            # Create Households
            n_households = b_conf["N_HOUSEHOLDS"]
            profile_key = b_conf["income_profile"]
            
            # Ensure income_probs is a proper list
            income_probs = list(config.INCOME_PROFILES[profile_key])
            
            for _ in range(n_households):
                # 2. Position: Randomly place across the WHOLE grid
                # Since agents filter by ID, overlapping coordinates doesn't matter for logic
                x = self.random.randrange(self.grid_width)
                y = self.random.randrange(self.grid_height)

                # 3. Income
                income = np.random.choice([1, 2, 3], p=income_probs)
                
                # 4. Initial Compliance
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
                
                # Place enforcers randomly or in center
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
        for b in self.barangays: b.step()
        self.calculate_costs()
        self.datacollector.collect(self)
        self.schedule.step()
        if self.schedule.steps >= 90: self.running = False

    def update_political_capital(self):
        # Calculate average enforcement intensity across all barangays
        avg_enforcement = sum(b.enforcement_intensity for b in self.barangays) / 7
        
        # Equation 3.7: P_cap(t+1) = P_cap(t) - (alpha * E) + (beta * Decay)
        decay = self.alpha * avg_enforcement
        recovery = self.beta * (1.0 - avg_enforcement) # Simplified recovery
        
        self.political_capital = max(0.0, min(1.0, self.political_capital - decay + recovery))

    def get_state(self):
        # 1. Compliance Rates (7 numbers)
        compliance_rates = [b.get_local_compliance() for b in self.barangays]
        
        # 2. Remaining Budget (Normalized 0-1)
        # Assuming annual budget is P1,500,000
        norm_budget = self.current_budget / 1500000.0
        
        # 3. Time Index (Quarter 1-4)
        # Assuming 90 ticks per quarter
        current_quarter = (self.schedule.steps // 90) + 1
        norm_time = current_quarter / 4.0
        
        # 4. Political Capital (0-1)
        p_cap = self.political_capital
        
        # Combine into one list (Size: 10)
        state = compliance_rates + [norm_budget, norm_time, p_cap]
        return np.array(state, dtype=np.float32)
    
    def apply_action(self, action_vector):
        """
        Args:
            action_vector: List of 21 numbers (3 levers per barangay * 7 barangays)
                        Outputted by the Neural Network.
        """
        # 1. Decode Action (Ensure budget constraint Eq 3.10)
        # This scaling usually happens outside, but good to double check
        total_alloc = sum(action_vector)
        if total_alloc > self.quarterly_budget:
            scale_factor = self.quarterly_budget / total_alloc
            action_vector = [a * scale_factor for a in action_vector]

        # 2. Apply to Each Barangay
        for i, bgy in enumerate(self.barangays):
            # Slice the vector: indices 0-2 for Bgy 0, 3-5 for Bgy 1...
            idx = i * 3
            iec_fund = action_vector[idx]
            enf_fund = action_vector[idx+1]
            inc_fund = action_vector[idx+2]
            
            # UPDATE AGENT PARAMETERS
            bgy.update_policy(iec_fund, enf_fund, inc_fund)