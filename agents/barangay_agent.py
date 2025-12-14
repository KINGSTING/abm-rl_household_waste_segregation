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
    
    def update_policy(self, iec_fund, enf_fund, inc_fund):
        """
        Called by BacolodModel.apply_action().
        Translates the RL Agent's budget allocation (in Pesos) into 
        Intensity parameters (0.0 - 1.0) that affect Household behavior.
        """
        self.iec_fund = iec_fund
        self.enf_fund = enf_fund
        self.inc_fund = inc_fund

        # CONVERSION: Money -> Intensity
        # We assume ~50,000 PHP per quarter is "Maximum Saturation" (1.0 intensity)
        # Why 50k? Annual budget P1.5M / 4 quarters = P375k. 
        # Divided by 7 barangays = ~53k each. 
        # So spending 50k on ONE lever is roughly "maxing it out".
        SATURATION_POINT = 50000.0

        # Calculate IEC Intensity (Boosts Attitude)
        self.iec_intensity = min(1.0, iec_fund / SATURATION_POINT)
        
        # Calculate Enforcement Intensity (Increases Detection Probability)
        self.enforcement_intensity = min(1.0, enf_fund / SATURATION_POINT)

        # Incentive budget is just stored directly (Households check if funds exist)
        self.current_incentive_budget = inc_fund

    def step(self):
        self.get_local_compliance()