import mesa   # <--- THIS WAS MISSING
import math
from agents.household_agent import HouseholdAgent

class EnforcementAgent(mesa.Agent):
    """
    Represents a Barangay Official or Tanod who patrols for non-compliance.
    """
    def __init__(self, unique_id, model, patrol_range=5):
        super().__init__(unique_id, model)
        self.patrol_range = patrol_range
        self.fine_amount = 500  

    def get_distance(self, pos_1, pos_2):
        x1, y1 = pos_1
        x2, y2 = pos_2
        return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

    def step(self):
        # 1. SENSING
        neighbors = self.model.grid.get_neighbors(self.pos, moore=True, radius=self.patrol_range)
        violators = [
            a for a in neighbors 
            if isinstance(a, HouseholdAgent) and not a.is_compliant
        ]

        # 2. MOVEMENT
        next_position = self.pos 
        if violators:
            closest_violator = min(violators, key=lambda a: self.get_distance(self.pos, a.pos))
            possible_steps = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
            if possible_steps:
                next_position = min(possible_steps, key=lambda p: self.get_distance(p, closest_violator.pos))
        else:
            possible_steps = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
            if possible_steps:
                next_position = self.random.choice(possible_steps)

        self.model.grid.move_agent(self, next_position)

        # 3. ENFORCEMENT
        catch_zone = self.model.grid.get_neighbors(self.pos, moore=True, radius=1)
        for agent in catch_zone:
            if isinstance(agent, HouseholdAgent):
                if not agent.is_compliant:
                    if hasattr(agent, 'get_fined'):
                        agent.get_fined()
                    else:
                        agent.utility -= 1.0