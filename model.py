import mesa
from mesa.time import RandomActivation
from mesa.space import SingleGrid
from mesa.datacollection import DataCollector
from agent import HouseholdAgent, BarangayOfficial, CollectionVehicle
import numpy as np
import random
# --- IMPORT THE CONFIGS ---
from barangay_config import BARANGAY_CONFIGS 

class WasteModel(mesa.Model):
    """The main model environment for the Barangay waste simulation."""
    
    def __init__(self, 
                 BARANGAY_ID=1, # <--- NEW: Selector Input
                 # These defaults are kept for safety but will be overwritten by config
                 N_HOUSEHOLDS=50, N_OFFICIALS=2, N_VEHICLES=1, 
                 width=20, height=20, initial_compliance=0.5, 
                 FINE_EFFICACY=0.3, INCENTIVE_EFFICACY=0.1, IEC_INTENSITY=0.2):
        
        # --- 1. LOAD CONFIGURATION ---
        # Select the config dictionary based on the ID (subtract 1 for list index)
        # If ID is out of range, default to the first one
        try:
            config = BARANGAY_CONFIGS[BARANGAY_ID - 1]
        except IndexError:
            config = BARANGAY_CONFIGS[0]
            print(f"Warning: Barangay ID {BARANGAY_ID} not found. Defaulting to ID 1.")

        print(f"Loading Simulation for: {config['name']}")

        # Overwrite the structural parameters with the Config data
        self.N_HOUSEHOLDS = config["N_HOUSEHOLDS"]
        self.N_OFFICIALS = config["N_OFFICIALS"]
        self.N_VEHICLES = config["N_VEHICLES"]
        width = config["width"]   # Update grid size
        height = config["height"] # Update grid size
        
        # --- Policy/RL Action Parameters (These still come from sliders/RL) ---
        self.FINE_EFFICACY = FINE_EFFICACY
        self.INCENTIVE_EFFICACY = INCENTIVE_EFFICACY
        self.IEC_INTENSITY = IEC_INTENSITY
        
        # --- Fixed/Environmental Parameters ---
        self.MAX_UNCOLLECTED_TIME = 10
        self.MAX_DISPOSAL_WAIT = 15
        self.TRUST_DECAY_RATE = 0.1
        self.running = True
        self.schedule = RandomActivation(self)
        self.grid = SingleGrid(width, height, torus=False)

        # --- Data Collection ---
        self.collections_made = 0
        self.current_compliance_rate = config["initial_compliance"] # Use config compliance
        self.datacollector = self.setup_data_collector()
        
        # Create agents using the Config's initial compliance
        self.create_agents(config["initial_compliance"])

    def create_agents(self, initial_compliance):
        # Define a helper function to get a random empty position
        def get_random_empty_pos(grid):
            empty_cells = list(grid.empties)
            if not empty_cells:
                raise Exception("Grid is full! Cannot place more agents.")
            return random.choice(empty_cells)

        # 1. Household Agents
        for i in range(self.N_HOUSEHOLDS):
            comp = np.random.choice([True, False], p=[initial_compliance, 1 - initial_compliance])
            a = HouseholdAgent(i, self, comp)
            self.schedule.add(a)
            self.grid.place_agent(a, get_random_empty_pos(self.grid))
            
        # 2. Barangay Officials
        for i in range(self.N_OFFICIALS):
            o = BarangayOfficial(self.N_HOUSEHOLDS + i, self)
            self.schedule.add(o)
            self.grid.place_agent(o, get_random_empty_pos(self.grid))
            
        # 3. Collection Vehicles
        for i in range(self.N_VEHICLES):
            v = CollectionVehicle(self.N_HOUSEHOLDS + self.N_OFFICIALS + i, self)
            self.schedule.add(v)
            self.grid.place_agent(v, get_random_empty_pos(self.grid))

    def setup_data_collector(self):
        model_reporters = {
            "ComplianceRate": lambda m: sum(a.is_compliant for a in m.schedule.agents if isinstance(a, HouseholdAgent)) / m.N_HOUSEHOLDS,
            "ImproperDisposal": lambda m: sum(a.improper_disposed for a in m.schedule.agents if isinstance(a, HouseholdAgent)),
            "Collections": "collections_made",
        }
        agent_reporters = {
            "ID": "unique_id", "Compliance": "is_compliant", "Improper": "improper_disposed", "Type": lambda a: type(a).__name__
        }
        return DataCollector(model_reporters=model_reporters, agent_reporters=agent_reporters)

    def step(self):
        self.schedule.step()
        self.datacollector.collect(self)