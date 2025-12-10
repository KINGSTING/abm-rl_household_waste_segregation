import mesa
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
import numpy as np
import random

# IMPORT YOUR NEW CONFIG
import barangay_config as config

from agents.household_agent import HouseholdAgent
from agents.barangay_agent import BarangayAgent
from agents.enforcement_agent import EnforcementAgent

class BacolodModel(mesa.Model):
    def __init__(self, seed=None):
        if seed is not None:
            super().__init__(seed=seed)
            self._seed = seed
            np.random.seed(seed)
            random.seed(seed)
        else:
            super().__init__()

        # 1. Setup Grid
        # We need a big enough map to hold 800+ agents. 
        # Let's increase standard width to 100x100 to accommodate Poblacion.
        self.grid_width = 100
        self.grid_height = 100
        self.grid = MultiGrid(self.grid_width, self.grid_height, torus=False)
        self.schedule = RandomActivation(self)
        self.running = True
        
        # 2. Define Cluster Centers (Spatial Layout)
        # We spread them out on the larger 100x100 map
        cluster_centers = [
            (20, 20), (50, 20), (80, 20),
            (20, 50), (50, 50), (80, 50),
            (50, 80) 
        ]

        self.barangays = []
        agent_id_counter = 0

        # --- LOOP THROUGH CONFIGURATION ---
        for i, b_conf in enumerate(config.BARANGAY_CONFIGS):
            
            # A. Create Barangay Agent
            # Note: We use the 'name' from config now
            b_agent = BarangayAgent(f"BGY_{i}", self)
            
            # Load specific parameters
            # (You can expand BarangayAgent later to store N_OFFICIALS etc.)
            b_agent.name = b_conf["name"]
            
            # Default policy for now (can be randomized or set later)
            b_agent.fine_amount = 500
            b_agent.enforcement_intensity = 0.5

            self.schedule.add(b_agent)
            self.barangays.append(b_agent)
            
            # B. Create Households (Exact Count from Config)
            center_x, center_y = cluster_centers[i]
            n_households = b_conf["N_HOUSEHOLDS"]
            profile_key = b_conf["income_profile"]
            income_probs = config.INCOME_PROFILES[profile_key]
            
            # Adjust cluster spread based on population size
            # (Poblacion needs a wider spread than Rural)
            spread = 3 if n_households < 100 else 10 

            for _ in range(n_households):
                # 1. Position
                x = int(np.clip(np.random.normal(center_x, spread), 0, self.grid_width-1))
                y = int(np.clip(np.random.normal(center_y, spread), 0, self.grid_height-1))
                
                # 2. Income
                income = np.random.choice([1, 2, 3], p=income_probs)
                
                # 3. Create Agent
                # Use initial_compliance from config as a probability
                is_compliant = (random.random() < b_conf["initial_compliance"])
                
                a = HouseholdAgent(agent_id_counter, self, income_level=income, initial_compliance=is_compliant)
                agent_id_counter += 1
                
                a.barangay = b_agent
                a.barangay_id = b_agent.unique_id
                
                self.schedule.add(a)
                self.grid.place_agent(a, (x, y))

            # C. Create Officials (Enforcers)
            # Use N_OFFICIALS from config
            n_officials = b_conf["N_OFFICIALS"]
            
            # To save performance, maybe we don't spawn ALL 22 officials for Poblacion visually?
            # For now, let's spawn a maximum of 3 visual enforcers per barangay
            # but keep the logic that they have "strength" of 22.
            visual_enforcers = min(n_officials, 5) 
            
            for _ in range(visual_enforcers):
                e_agent = EnforcementAgent(f"ENF_{agent_id_counter}", self)
                agent_id_counter += 1
                e_agent.barangay_id = b_agent.unique_id
                self.schedule.add(e_agent)
                self.grid.place_agent(e_agent, (center_x, center_y))

        # 3. Data Collector
        self.datacollector = DataCollector(
            model_reporters={"Average Compliance": compute_global_compliance}
        )

    def step(self):
        self.datacollector.collect(self)
        self.schedule.step()
        if self.schedule.steps >= 90:
            self.running = False

def compute_global_compliance(model):
    agents = [a for a in model.schedule.agents if isinstance(a, HouseholdAgent)]
    if not agents: return 0.0
    return sum(1 for a in agents if a.is_compliant) / len(agents)