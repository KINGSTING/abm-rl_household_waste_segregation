import mesa
from household_agent import HouseholdAgent

class BarangayAgent(mesa.Agent):
    """
    Represents a Barangay (Local District).
    Acts as a container for local policy implementation and statistics.
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        
        # --- 1. State Variables ---
        self.compliance_rate = 0.0
        self.total_households = 0
        self.compliant_count = 0
        
        # --- 2. Policy/Budget Variables (Allocated by LGU/RL) ---
        # These values determine the intensity of interventions in this specific barangay
        self.iec_budget = 0.0          # For Education campaigns
        self.enforcement_budget = 0.0  # For hiring enforcers
        self.incentive_budget = 0.0    # For rewards
        
        # Derived intensities (converted from budget to 0.0-1.0 effect)
        self.enforcement_intensity = 0.0
        self.iec_intensity = 0.0

    def receive_budget(self, budget_allocation):
        """
        Called by the Model (RL Agent) at the start of a quarter.
        Updates the local policy parameters based on the allocation.
        
        Args:
            budget_allocation (dict): {
                'iec': float, 
                'enforcement': float, 
                'incentive': float 
            }
        """
        self.iec_budget = budget_allocation.get('iec', 0.0)
        self.enforcement_budget = budget_allocation.get('enforcement', 0.0)
        self.incentive_budget = budget_allocation.get('incentive', 0.0)
        
        # --- Convert Budget to Intensity (Simplified Logic) ---
        # Example: 10,000 pesos might be "1.0" intensity.
        # This normalization depends on your calibration data.
        MAX_IEC_BUDGET = 50000 
        MAX_ENFORCEMENT_BUDGET = 50000
        
        self.iec_intensity = min(1.0, self.iec_budget / MAX_IEC_BUDGET)
        self.enforcement_intensity = min(1.0, self.enforcement_budget / MAX_ENFORCEMENT_BUDGET)

    def get_compliance_rate(self):
        """
        Scans all households in this Barangay to calculate current compliance.
        Returns:
            float: Compliance rate (0.0 to 1.0)
        """
        # 1. Identify "my" households
        # Assuming households have a 'barangay_id' attribute or are linked spatially.
        # Here we iterate through the model's agents and filter.
        
        my_households = [
            a for a in self.model.schedule.agents 
            if isinstance(a, HouseholdAgent) and getattr(a, 'barangay_id', None) == self.unique_id
        ]
        
        self.total_households = len(my_households)
        
        if self.total_households == 0:
            self.compliance_rate = 0.0
            return 0.0
            
        # 2. Count Compliant
        self.compliant_count = sum(1 for a in my_households if a.is_compliant)
        
        # 3. Calculate Rate
        self.compliance_rate = self.compliant_count / self.total_households
        return self.compliance_rate

    def step(self):
        """
        Update stats at every step.
        """
        self.get_compliance_rate()

import mesa
import math
from household_agent import HouseholdAgent

class EnforcementAgent(mesa.Agent):
    """
    Represents a Barangay Official or Tanod who patrols for non-compliance.
    """
    def __init__(self, unique_id, model, patrol_range=5):
        super().__init__(unique_id, model)
        self.patrol_range = patrol_range
        self.fine_amount = 500  # Default fine in Pesos (or model units)

    def get_distance(self, pos_1, pos_2):
        """Helper to calculate Euclidean distance between two points."""
        x1, y1 = pos_1
        x2, y2 = pos_2
        return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

    def step(self):
        # --- 1. SENSING (Find Targets) ---
        # Get all neighbors within patrol range
        neighbors = self.model.grid.get_neighbors(self.pos, moore=True, radius=self.patrol_range)
        
        # Filter: Only households that are NOT compliant
        violators = [
            a for a in neighbors 
            if isinstance(a, HouseholdAgent) and not a.is_compliant
        ]

        # --- 2. MOVEMENT LOGIC ---
        next_position = self.pos # Default to staying put if stuck

        if violators:
            # --- TARGET MODE: Chase the closest violator ---
            closest_violator = min(violators, key=lambda a: self.get_distance(self.pos, a.pos))
            
            # Get valid steps (up/down/left/right/diagonals)
            possible_steps = self.model.grid.get_neighborhood(
                self.pos, moore=True, include_center=False
            )
            
            if possible_steps:
                # Move to the square that minimizes distance to target
                next_position = min(possible_steps, key=lambda p: self.get_distance(p, closest_violator.pos))
        
        else:
            # --- PATROL MODE: Random Walk ---
            possible_steps = self.model.grid.get_neighborhood(
                self.pos, moore=True, include_center=False
            )
            if possible_steps:
                next_position = self.random.choice(possible_steps)

        # Execute Move
        self.model.grid.move_agent(self, next_position)

        # --- 3. ENFORCEMENT (Apply Penalties) ---
        # Now check IMMEDIATE surroundings (Radius=1) for anyone to fine
        catch_zone = self.model.grid.get_neighbors(self.pos, moore=True, radius=1)
        
        for agent in catch_zone:
            if isinstance(agent, HouseholdAgent):
                if not agent.is_compliant:
                    # PENALIZE THE AGENT
                    # We assume HouseholdAgent has a method 'get_fined()' 
                    # or we modify its state directly.
                    if hasattr(agent, 'get_fined'):
                        agent.get_fined()
                    else:
                        # Fallback if method doesn't exist yet
                        agent.utility -= 1.0 # Immediate utility penalty