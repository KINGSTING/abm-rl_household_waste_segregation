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

        # 1. SETUP GRID (100x100)
        self.grid_width = 100   
        self.grid_height = 100 
        self.grid = MultiGrid(self.grid_width, self.grid_height, torus=False)
        self.schedule = RandomActivation(self)
        self.running = True
        
        self.barangays = []
        agent_id_counter = 0
        
        # 2. DEFINE ZONES (100x100 Scale)
        zones = [
            (20, 80, 30, 30), # Bgy 0
            (50, 80, 30, 30), # Bgy 1
            (80, 80, 30, 30), # Bgy 2
            (20, 50, 30, 30), # Bgy 3
            (50, 50, 30, 30), # Bgy 4
            (80, 50, 30, 30), # Bgy 5
            (50, 20, 30, 30)  # Bgy 6
        ]

        # --- LOOP THROUGH CONFIGURATION ---
        for i, b_conf in enumerate(config.BARANGAY_CONFIGS):
            b_agent = BarangayAgent(f"BGY_{i}", self)
            b_agent.name = b_conf["name"]
            
            # Assign Spatial Boundaries
            cx, cy, w, h = zones[i]
            b_agent.x_min = cx - (w // 2)
            b_agent.x_max = cx + (w // 2)
            b_agent.y_min = cy - (h // 2)
            b_agent.y_max = cy + (h // 2)
            
            # Policy (NOTE: These should ideally come from b_conf, but are hardcoded here for safety)
            b_agent.fine_amount = 500
            b_agent.enforcement_intensity = 0.5

            self.schedule.add(b_agent)
            self.barangays.append(b_agent)
            
            # Create Households
            n_households = b_conf["N_HOUSEHOLDS"]
            profile_key = b_conf["income_profile"]
            
            # FIX: Ensure income_probs is a proper list before use
            income_probs = list(config.INCOME_PROFILES[profile_key])
            
            for _ in range(n_households):
                # 1. Position
                x = random.randint(b_agent.x_min + 1, b_agent.x_max - 1)
                y = random.randint(b_agent.y_min + 1, b_agent.y_max - 1)
                x = max(0, min(x, self.grid_width - 1))
                y = max(0, min(y, self.grid_height - 1))

                # 2. Income (Using np.random.choice correctly)
                income = np.random.choice([1, 2, 3], p=income_probs)
                
                # 3. Initial Compliance
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
                self.schedule.add(e_agent)
                self.grid.place_agent(e_agent, (cx, cy))

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