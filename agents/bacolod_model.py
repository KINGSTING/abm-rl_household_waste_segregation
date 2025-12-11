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