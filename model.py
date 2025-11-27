import mesa
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
from agent import HouseholdAgent, BarangayOfficial, CollectionVehicle
import numpy as np
import random
import traceback # This helps us see errors!
from barangay_config import BARANGAY_CONFIGS 

class WasteModel(mesa.Model):
    
    def __init__(self, 
                 BARANGAY_ID=1, 
                 width=50, height=50, 
                 N_HOUSEHOLDS=50, N_OFFICIALS=2, N_VEHICLES=1, 
                 initial_compliance=0.5, 
                 FINE_EFFICACY=0.3, INCENTIVE_EFFICACY=0.1, IEC_INTENSITY=0.2):
        
        BARANGAY_ID = int(BARANGAY_ID)

        # 1. Load Config
        try:
            config = BARANGAY_CONFIGS[BARANGAY_ID - 1]
        except IndexError:
            config = BARANGAY_CONFIGS[0]

        # 2. Set Parameters
        self.N_HOUSEHOLDS = config["N_HOUSEHOLDS"]
        self.N_OFFICIALS = config["N_OFFICIALS"]
        self.N_VEHICLES = config["N_VEHICLES"]
        
        # 3. Setup Grid
        self.grid_width = width
        self.grid_height = height
        self.grid = MultiGrid(self.grid_width, self.grid_height, torus=False)
        
        self.schedule = RandomActivation(self)
        self.running = True 

        # Policy & Env Parameters
        self.FINE_EFFICACY = FINE_EFFICACY
        self.INCENTIVE_EFFICACY = INCENTIVE_EFFICACY
        self.IEC_INTENSITY = IEC_INTENSITY
        self.MAX_UNCOLLECTED_TIME = 10
        self.MAX_DISPOSAL_WAIT = 15
        self.TRUST_DECAY_RATE = 0.1
        self.FINE_DURATION = 5 # How long fines last
        
        # Data Collection
        self.collections_made = 0
        self.datacollector = self.setup_data_collector()

        # 4. Create Agents
        self.create_agents(config["initial_compliance"])

    def create_agents(self, initial_compliance):
        def get_random_empty_pos(grid):
            empty_cells = list(grid.empties)
            if not empty_cells:
                return (random.randrange(grid.width), random.randrange(grid.height))
            return random.choice(empty_cells)

        # 1. Households
        for i in range(self.N_HOUSEHOLDS):
            comp = np.random.choice([True, False], p=[initial_compliance, 1 - initial_compliance])
            a = HouseholdAgent(i, self, comp)
            self.schedule.add(a)
            self.grid.place_agent(a, get_random_empty_pos(self.grid))
            
        # 2. Officials
        for i in range(self.N_OFFICIALS):
            o = BarangayOfficial(self.N_HOUSEHOLDS + i, self)
            self.schedule.add(o)
            self.grid.place_agent(o, get_random_empty_pos(self.grid))
            
        # 3. Vehicles
        for i in range(self.N_VEHICLES):
            v = CollectionVehicle(self.N_HOUSEHOLDS + self.N_OFFICIALS + i, self)
            self.schedule.add(v)
            self.grid.place_agent(v, get_random_empty_pos(self.grid))

    def setup_data_collector(self):
        model_reporters = {
            "ComplianceRate": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, HouseholdAgent) and a.is_compliant) / (m.N_HOUSEHOLDS if m.N_HOUSEHOLDS > 0 else 1),
            "ImproperDisposal": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, HouseholdAgent) and a.improper_disposed),
            "Collections": "collections_made",
        }
        return DataCollector(model_reporters=model_reporters)

    def step(self):
        """Advance the model by one step."""
        try:
            self.schedule.step()
            self.datacollector.collect(self)
            
            # --- STOP AT 100 STEPS ---
            if self.schedule.steps >= 100:
                self.running = False
                print("100 Steps Reached. Simulation Paused.")
                
        except Exception as e:
            # THIS WILL PRINT THE ERROR TO YOUR TERMINAL IF IT CRASHES
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("CRASH DETECTED IN MODEL.STEP")
            print(e)
            traceback.print_exc()
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            self.running = False

def compute_compliance(model):
    """Calculates percentage of compliant households"""
    agents = [a for a in model.schedule.agents if isinstance(a, HouseholdAgent)]
    compliant = sum([1 for a in agents if a.is_compliant])
    return compliant / len(agents) if agents else 0

def compute_dumping(model):
    """Calculates percentage of households doing illegal dumping"""
    agents = [a for a in model.schedule.agents if isinstance(a, HouseholdAgent)]
    dumping = sum([1 for a in agents if a.improper_disposed])
    return dumping / len(agents) if agents else 0