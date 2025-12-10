import mesa
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
import numpy as np

# Import your agents
from .household_agent import HouseholdAgent
from .barangay_agent import BarangayAgent
from .enforcement_agent import EnforcementAgent

class BacolodModel(mesa.Model):
    """
    The main simulation engine for the Bacolod Waste Segregation Policy.
    """
    def __init__(self, num_households=200, width=50, height=50):
        super().__init__()
        self.num_households = num_households
        self.grid = MultiGrid(width, height, torus=False)
        self.schedule = RandomActivation(self)
        self.running = True

        # --- Global Policy Parameters (Defaults) ---
        # These can be overwritten by the RL Agent later
        self.fine_amount = 500
        self.reward_value = 100
        
        # --- 1. Create Barangay Managers (The 7 Regions) ---
        self.barangays = []
        # Define center points for 7 clusters on a 50x50 grid
        barangay_centers = [
            (10, 10), (25, 10), (40, 10),
            (10, 25), (25, 25), (40, 25),
            (25, 40)
        ]
        
        for i, pos in enumerate(barangay_centers):
            b_agent = BarangayAgent(f"BGY_{i}", self)
            self.schedule.add(b_agent)
            self.barangays.append(b_agent)
            # Note: Barangay Agents don't need to be on the grid, 
            # but we keep them in the schedule to update stats.

        # --- 2. Create Households (Clusters) ---
        # We distribute households around the barangay centers
        households_per_bgy = num_households // len(self.barangays)
        
        agent_id_counter = 0
        
        for b_agent in self.barangays:
            center_x, center_y = barangay_centers[self.barangays.index(b_agent)]
            
            for _ in range(households_per_bgy):
                # Random location around the center (Cluster logic)
                x = int(np.clip(np.random.normal(center_x, 5), 0, width-1))
                y = int(np.clip(np.random.normal(center_y, 5), 0, height-1))
                
                # Create Agent
                # Income level: 1=Low (50%), 2=Mid (30%), 3=High (20%)
                income = np.random.choice([1, 2, 3], p=[0.5, 0.3, 0.2])
                
                a = HouseholdAgent(agent_id_counter, self, income_level=income, initial_compliance=False)
                agent_id_counter += 1
                
                # LINKING: Important! Tell the household which Barangay it belongs to
                a.barangay = b_agent 
                a.barangay_id = b_agent.unique_id
                
                self.schedule.add(a)
                self.grid.place_agent(a, (x, y))

        # --- 3. Create Enforcers (Tanods) ---
        # Start with 0 enforcers; the RL agent will hire them later.
        # But for testing, let's spawn 1 per barangay
        for b_agent in self.barangays:
            center_x, center_y = barangay_centers[self.barangays.index(b_agent)]
            e_agent = EnforcementAgent(f"ENF_{b_agent.unique_id}", self)
            self.schedule.add(e_agent)
            self.grid.place_agent(e_agent, (center_x, center_y))

        # --- 4. Data Collector ---
        self.datacollector = DataCollector(
            model_reporters={
                "Average Compliance": compute_global_compliance,
                # specific barangay stats can be added here
            }
        )

    def step(self):
        """Advance the model by one step."""
        self.datacollector.collect(self)
        self.schedule.step()

# --- Helper Function for DataCollection ---
def compute_global_compliance(model):
    agents = [a for a in model.schedule.agents if isinstance(a, HouseholdAgent)]
    if not agents:
        return 0.0
    compliant = sum(1 for a in agents if a.is_compliant)
    return compliant / len(agents)