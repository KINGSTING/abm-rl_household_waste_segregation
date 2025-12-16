import mesa
from agents.household_agent import HouseholdAgent

class BarangayAgent(mesa.Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        
        # --- 1. State Variables ---
        self.compliance_rate = 0.0
        self.total_households = 0
        self.compliant_count = 0
        
        # --- 2. Policy/Budget Variables (CRITICAL FIX) ---
        # We initialize the exact variable names that HouseholdAgent looks for:
        self.iec_fund = 0.0        # Matches update_policy
        self.enf_fund = 0.0        # Matches update_policy
        self.inc_fund = 0.0        # Matches HouseholdAgent check
        
        # --- 3. Derived Policy Parameters ---
        self.enforcement_intensity = 0.5
        self.iec_intensity = 0.0
        self.fine_amount = 500
        
        # Optional: Spatial bounds (if used for visualization later)
        self.x_min = 0
        self.x_max = 0
        self.y_min = 0
        self.y_max = 0

    def get_local_compliance(self):
        """
        Calculates compliance for the DataCollector.
        """
        # Filter agents that belong to this barangay
        my_households = [
            a for a in self.model.schedule.agents 
            if isinstance(a, HouseholdAgent) and getattr(a, 'barangay_id', None) == self.unique_id
        ]
        
        self.total_households = len(my_households)
        
        # Avoid division by zero
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
        # 1. Update Financial Storage (Syncs with __init__)
        self.iec_fund = iec_fund
        self.enf_fund = enf_fund
        self.inc_fund = inc_fund

        # 2. CONVERSION: Money -> Intensity
        # We assume ~50,000 PHP per quarter is "Maximum Saturation" (1.0 intensity)
        SATURATION_POINT = 50000.0

        # Calculate IEC Intensity (Boosts Attitude)
        self.iec_intensity = min(1.0, iec_fund / SATURATION_POINT)
        
        # Calculate Enforcement Intensity (Increases Detection Probability)
        self.enforcement_intensity = min(1.0, enf_fund / SATURATION_POINT)

    def step(self):
        # Update metrics every step so the dashboard sees live data
        self.get_local_compliance()