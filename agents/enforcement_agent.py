import mesa
import math
from agents.household_agent import HouseholdAgent

class EnforcementAgent(mesa.Agent):
    """
    Represents a Barangay Official or Tanod who patrols for non-compliance.
    Modified to systematically visit the nearest unvisited household.
    """
    def __init__(self, unique_id, model, patrol_range=5):
        super().__init__(unique_id, model)
        self.patrol_range = patrol_range
        self.fine_amount = 500
        # Memory to track which households have been visited
        self.visited_households = set()

    def get_distance(self, pos_1, pos_2):
        x1, y1 = pos_1
        x2, y2 = pos_2
        return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)

    def step(self):
        # 1. MARK VISITED (Update Memory)
        # Check immediate surroundings (including own cell) to mark households as visited
        nearby_agents = self.model.grid.get_neighbors(self.pos, moore=True, radius=1, include_center=True)
        for agent in nearby_agents:
            if isinstance(agent, HouseholdAgent):
                self.visited_households.add(agent.unique_id)

        # 2. DETERMINE TARGET & MOVEMENT
        # Get list of all HouseholdAgents in the model
        all_households = [a for a in self.model.schedule.agents if isinstance(a, HouseholdAgent)]
        
        # Filter for those NOT in the visited set
        unvisited_households = [h for h in all_households if h.unique_id not in self.visited_households]

        next_position = self.pos
        possible_steps = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)

        if unvisited_households:
            # Find the nearest unvisited household
            target_household = min(unvisited_households, key=lambda h: self.get_distance(self.pos, h.pos))
            
            # Move towards the target
            if possible_steps:
                next_position = min(possible_steps, key=lambda p: self.get_distance(p, target_household.pos))
        else:
            # If all households visited, clear memory to restart patrol pattern
            self.visited_households.clear()
            # Move randomly for this step while resetting
            if possible_steps:
                next_position = self.random.choice(possible_steps)

        self.model.grid.move_agent(self, next_position)

        # 3. ENFORCEMENT (Apply Fines)
        # Check agents in the immediate vicinity (catch zone)
        catch_zone = self.model.grid.get_neighbors(self.pos, moore=True, radius=1, include_center=True)
        for agent in catch_zone:
            if isinstance(agent, HouseholdAgent):
                if not agent.is_compliant:
                    if hasattr(agent, 'get_fined'):
                        agent.get_fined()
                    else:
                        # Fallback if method doesn't exist
                        agent.utility -= 1.0