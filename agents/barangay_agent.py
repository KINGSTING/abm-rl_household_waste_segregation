import mesa
import math
from agents.household_agent import HouseholdAgent

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
