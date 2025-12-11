import mesa
import numpy as np
import random 
import math

# --- Agent Base Class ---

class HouseholdAgent(mesa.Agent):
    """
    Represents a household making decisions based on Theory of Planned Behavior.
    State is driven by Intention, not just timers.
    """
    def __init__(self, unique_id, model, initial_compliance):
        super().__init__(unique_id, model)
        
        # --- 1. TPB Internal Variables (0.0 to 1.0) ---
        # Base Attitude: Randomly assigned based on the barangay's profile
        self.attitude = np.clip(np.random.normal(0.5, 0.2), 0.1, 0.9) 
        
        # Perceived Control starts high, drops if truck doesn't come
        self.pbc = 0.9 
        
        # Social Norm is calculated dynamically based on neighbors
        self.social_norm = 0.5 

        # --- 2. State Variables ---
        self.is_compliant = initial_compliance
        self.has_garbage = True
        self.days_uncollected = 0 # Replaces the 'timer', now acts as a PBC modifier
        self.improper_disposed = False

    def update_social_norms(self):
        """
        Calculates social pressure.
        FIX: We add 'Resistance' so that a bad neighborhood doesn't 
        immediately drag the score to 0.
        """
        neighbors = self.model.grid.get_neighbors(self.pos, moore=True, radius=2)
        
        # Filter for only HouseholdAgents (ignore Officials)
        household_neighbors = [n for n in neighbors if isinstance(n, HouseholdAgent)]
        
        if not household_neighbors:
            return 0.5 # Neutral if isolated
            
        compliant_count = sum(1 for n in household_neighbors if n.is_compliant)
        total_neighbors = len(household_neighbors)
        
        # Raw percentage of good neighbors
        raw_norm = compliant_count / total_neighbors

        # --- THE FIX: ASYMMETRIC INFLUENCE ---
        
        # Scenario A: Majority are COMPLIANT (Green)
        # We amplify this to encourage spreading the good behavior.
        if raw_norm > 0.5:
            # Boost the signal. e.g., 0.6 becomes 0.7
            adjusted_norm = min(1.0, raw_norm * 1.2)
            
        # Scenario B: Majority are NON-COMPLIANT (Red)
        # We dampen this. We assume people have some self-respect.
        # Even if 0% are compliant, the pressure only drops to 0.2, not 0.0.
        else:
            # "Base Decency" buffer. 
            # Logic: "Just because everyone jumps off a bridge, doesn't mean I will."
            base_decency = 0.2
            adjusted_norm = (raw_norm * 0.8) + base_decency

        return adjusted_norm

    def step(self):
        """TPB Decision Logic"""
        
        # --- A. Update Logistics (Influence on PBC) ---
        if self.has_garbage:
            self.days_uncollected += 1
            
        # If garbage sits too long, Perceived Control drops (Agent feels the system is failing)
        # Decay PBC by 0.05 for every day uncollected beyond 3 days
        if self.days_uncollected > 3:
            self.pbc = max(0.0, self.pbc - 0.05)
        else:
            # If collected recently, PBC slowly recovers
            self.pbc = min(1.0, self.pbc + 0.01)

        # --- B. Update TPB Factors ---
        
        # 1. Social Norms: Look at neighbors + Fine Intensity (Enforcement creates pressure)
        local_pressure = self.update_social_norms()
        # Policy Lever: Higher fines increase the weight of social pressure
        self.social_norm = (local_pressure * 0.7) + (self.model.FINE_EFFICACY * 0.3)

        # 2. Attitude: Base Attitude + IEC Intensity (Education boosts attitude)
        # Policy Lever: IEC directly boosts attitude
        current_attitude = min(1.0, self.attitude + (self.model.IEC_INTENSITY * 0.1))
        
        # --- C. Calculate Intention ---
        # Weights (can be tuned, or made into model parameters)
        w_att = 0.4
        w_sn = 0.3
        w_pbc = 0.3
        
        intention = (w_att * current_attitude) + (w_sn * self.social_norm) + (w_pbc * self.pbc)
        
        # --- D. The Decision (Behavior) ---
        # Agent compares Intention against a threshold to decide compliance
        # We add a small noise factor to represent human unpredictability
        threshold = 0.5 - (self.model.INCENTIVE_EFFICACY * 0.2) # Incentives lower the barrier to comply
        
        if intention > threshold:
            self.is_compliant = True
        else:
            self.is_compliant = False

        # --- E. Consequence: Improper Disposal ---
        # If agent is Non-Compliant AND has waited too long, they dump it (Black State)
        if not self.is_compliant and self.days_uncollected > self.model.MAX_DISPOSAL_WAIT:
            self.improper_disposed = True

class BarangayOfficial(mesa.Agent):
    """
    Represents an official who hunts for non-compliance.
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.patrol_range = 5  # How far they can "see" or "smell" garbage

    def get_distance(self, pos_1, pos_2):
        """Helper to calculate Euclidean distance between two points."""
        x1, y1 = pos_1
        x2, y2 = pos_2
        return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

    def step(self):
        # --- 1. SENSING (Find Targets) ---
        neighbors = self.model.grid.get_neighbors(self.pos, moore=True, radius=self.patrol_range)
        
        # Filter: Only non-compliant households
        violators = [
            a for a in neighbors 
            if isinstance(a, HouseholdAgent) and not a.is_compliant
        ]

        # --- 2. MOVEMENT LOGIC ---
        next_position = None

        if violators:
            # --- TARGET MODE: Find closest violator ---
            # Sort violators by distance to current position
            closest_violator = min(violators, key=lambda a: self.get_distance(self.pos, a.pos))
            
            # Get all possible steps I can take right now (Moore neighborhood)
            possible_steps = self.model.grid.get_neighborhood(
                self.pos, moore=True, include_center=False
            )
            
            # Choose the step that minimizes distance to the closest_violator
            # This creates the "moving towards" effect
            next_position = min(possible_steps, key=lambda p: self.get_distance(p, closest_violator.pos))
        
        else:
            # --- PATROL MODE: Random Walk ---
            possible_steps = self.model.grid.get_neighborhood(
                self.pos, moore=True, include_center=False
            )
            next_position = self.random.choice(possible_steps)

        # Move the agent
        self.model.grid.move_agent(self, next_position)

        # --- 3. ENFORCEMENT (Apply Fines) ---
        # Now that we have moved, check immediate surroundings (Radius=1 or 2) for enforcement
        # Note: We enforce on everyone nearby, not just the target we chased.
        nearby_agents = self.model.grid.get_neighbors(self.pos, moore=True, radius=2)
        
        for agent in nearby_agents:
            if isinstance(agent, HouseholdAgent):
                if not agent.is_compliant:
                    # Apply Fine
                    agent.fine_timer = self.model.FINE_DURATION
                    # Chance to force compliance
                    if self.random.random() < self.model.FINE_EFFICACY:
                        agent.is_compliant = True 
                
                # Apply Incentive (Optional, keeping your original logic)
                elif agent.is_compliant:
                    if self.random.random() < self.model.INCENTIVE_EFFICACY:
                        pass # Add incentive logic here if needed

class CollectionVehicle(mesa.Agent):
    """
    Moves to compliant households to 'collect' garbage.
    Color: Yellow
    """
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)

    def step(self):
        # 1. Find Target (Closest Compliant Household with garbage)
        compliant_targets = [
            agent for agent in self.model.schedule.agents
            if isinstance(agent, HouseholdAgent) and agent.is_compliant and agent.has_garbage
        ]
        
        if compliant_targets:
            target = self.random.choice(compliant_targets) 
            
            # Teleport to target
            self.model.grid.move_agent(self, target.pos) 
            
            # 2. Collection
            if self.pos == target.pos:
                target.has_garbage = False
                target.uncollected_timer = 0
                self.model.collections_made += 1