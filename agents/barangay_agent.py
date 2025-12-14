import mesa
from agents.household_agent import HouseholdAgent

class BarangayAgent(mesa.Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        
        # --- 1. State Variables ---
        self.compliance_rate = 0.0
        self.total_households = 0
        self.compliant_count = 0
        
        # --- 2. Policy/Budget Variables (CRITICAL FIX: Initialize all variables) ---
        self.iec_budget = 0.0          # ADD THIS LINE (or ensure it's present)
        self.enforcement_budget = 0.0  # ADD THIS LINE (or ensure it's present)
        self.incentive_budget = 0.0    # ADD THIS LINE (or ensure it's present)
        
        self.enforcement_intensity = 0.5
        self.iec_intensity = 0.0
        self.reward_value = 0.0 
        
        # Add spatial bounds for logic safety (if not done already)
        self.x_min = 0
        self.x_max = 0
        self.y_min = 0
        self.y_max = 0
        self.fine_amount = 500

    def receive_budget(self, budget_allocation):
        # (Budget logic remains the same)
        MAX_IEC_BUDGET = 50000 
        MAX_ENFORCEMENT_BUDGET = 50000
        self.iec_intensity = min(1.0, self.iec_budget / MAX_IEC_BUDGET)
        self.enforcement_intensity = min(1.0, self.enforcement_budget / MAX_ENFORCEMENT_BUDGET)

    def get_local_compliance(self):
        """Calculates compliance for the DataCollector."""
        my_households = [
            a for a in self.model.schedule.agents 
            if isinstance(a, HouseholdAgent) and getattr(a, 'barangay_id', None) == self.unique_id
        ]
        
        self.total_households = len(my_households)
        if self.total_households == 0:
            self.compliance_rate = 0.0
            return 0.0
            
        compliant_count = sum(1 for h in my_households if h.is_compliant)
        self.compliant_count = compliant_count
        self.compliance_rate = self.compliant_count / self.total_households
        return self.compliance_rate

    def step(self):
        self.get_local_compliance()