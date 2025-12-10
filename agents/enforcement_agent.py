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