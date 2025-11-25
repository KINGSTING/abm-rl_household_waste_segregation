import mesa
import numpy as np

# --- Agent Base Class ---

class HouseholdAgent(mesa.Agent):
    """
    Represents a household in a Barangay, with compliance status.
    Color: Green (Compliant) or Red (Non-Compliant) or Black (Improper Disposal)
    """
    def __init__(self, unique_id, model, initial_compliance):
        super().__init__(unique_id, model)
        # Core State Variables
        self.is_compliant = initial_compliance
        self.uncollected_timer = 0  # Time since last collection (or time since disposal attempt)
        self.fine_timer = 0         # Timer for non-compliant behavior fine duration
        self.has_garbage = True     # Needs collection
        self.improper_disposed = False # Black state

    def step(self):
        """Logic for household behavior each time step (e.g., a day)."""
        
        # 1. Update Timers
        if self.has_garbage:
            self.uncollected_timer += 1
        
        # 2. Compliance Decay (Trust Issue)
        # Agents may stop complying if uncollected for too long
        if self.is_compliant and self.uncollected_timer > self.model.MAX_UNCOLLECTED_TIME:
            if np.random.random() < self.model.TRUST_DECAY_RATE:
                self.is_compliant = False 
                self.has_garbage = True # New non-compliant waste pile
                
        # 3. Non-Compliant Disposal (Turning Black/Environmental Impact)
        # Non-compliant agents improperly dispose if their wait time is too high
        if not self.is_compliant and self.uncollected_timer > self.model.MAX_DISPOSAL_WAIT:
            self.improper_disposed = True
            # The model's data collector tracks this 'Black' state

class BarangayOfficial(mesa.Agent):
    """
    Represents a moving official who checks compliance, fines, and provides incentives/IEC.
    Color: Blue
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.patrol_range = 5 # How far the official checks

    def step(self):
        """Official patrols and checks compliance in range."""
        
        # 1. Movement (Random Walk)
        possible_steps = self.model.grid.get_neighborhood(
            self.pos, moore=True, include_center=False
        )
        new_position = self.random.choice(possible_steps)
        self.model.grid.move_agent(self, new_position)
        
        # 2. Check and Enforce Policy
        neighbors = self.model.grid.get_neighbors(self.pos, moore=True, radius=self.patrol_range)
        
        for agent in neighbors:
            if isinstance(agent, HouseholdAgent):
                # Apply Enforcement (Policy levers used here)
                if not agent.is_compliant:
                    # Fine + IEC
                    agent.fine_timer = self.model.FINE_DURATION
                    
                    # Apply policy logic: Increase compliance chance based on FINE_EFFICACY
                    if np.random.random() < self.model.FINE_EFFICACY:
                         agent.is_compliant = True 
                    
                elif agent.is_compliant:
                    # Incentive
                    # Apply policy logic: Reinforce compliance based on INCENTIVE_EFFICACY
                    if np.random.random() < self.model.INCENTIVE_EFFICACY:
                         pass # Placeholder for incentive logic (e.g., increase compliance loyalty)

class CollectionVehicle(mesa.Agent):
    """
    Moves to compliant households to 'collect' garbage.
    Color: Yellow
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)

    def step(self):
        """Finds the closest compliant household with garbage and moves toward it."""
        
        # 1. Find Target (Closest Compliant Household with garbage)
        compliant_targets = [
            agent for agent in self.model.schedule.agents
            if isinstance(agent, HouseholdAgent) and agent.is_compliant and agent.has_garbage
        ]
        
        if compliant_targets:
            # Simple movement logic: target the random compliant household
            target = self.random.choice(compliant_targets) 
            
            # --- FIX: Use move_agent for teleportation to target coordinates ---
            # Teleport the agent to the target position
            self.model.grid.move_agent(self, target.pos) 
            
            # 2. Collection
            # Since the vehicle teleports to the target, the condition is guaranteed to be met
            if self.pos == target.pos:
                target.has_garbage = False
                target.uncollected_timer = 0
                self.model.collections_made += 1