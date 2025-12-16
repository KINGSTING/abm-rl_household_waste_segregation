import mesa
import random

class HouseholdAgent(mesa.Agent):
    """
    Household Agent based on Theory of Planned Behavior (TPB).
    Decides to segregate based on Attitude, Social Norms, and PBC.
    """
    # --- UPDATE: Accepted 'behavior_params' in init ---
    def __init__(self, unique_id, model, income_level, initial_compliance, behavior_params=None):
        super().__init__(unique_id, model)
        self.income_level = income_level
        self.is_compliant = initial_compliance
        self.barangay = None    
        self.barangay_id = None 

        # --- Use Configured Parameters or Defaults ---
        if behavior_params is None:
            # Default fallback (Standard)
            behavior_params = {"w_a": 0.4, "w_sn": 0.3, "w_pbc": 0.3, "c_effort": 0.2, "decay": 0.005}

        # --- Dynamic TPB Weights ---
        self.w_a = behavior_params["w_a"]
        self.w_sn = behavior_params["w_sn"]
        self.w_pbc = behavior_params["w_pbc"]
        self.c_effort_base = behavior_params["c_effort"]
        self.attitude_decay_rate = behavior_params["decay"]

        # --- Initial Internal States ---
        # Stronger start for compliant agents
        self.attitude = 0.85 if initial_compliance else 0.2 
        self.sn = 0.7 if initial_compliance else 0.4 
        self.pbc = 0.7 if initial_compliance else 0.4
        self.utility = 0.0  

    def update_social_norms(self):
        neighbors = self.model.grid.get_neighbors(self.pos, moore=True, radius=2)
        household_neighbors = [
            n for n in neighbors 
            if isinstance(n, HouseholdAgent) and n.barangay_id == self.barangay_id
        ]
        
        if not household_neighbors:
            return 
            
        compliant_count = sum(1 for n in household_neighbors if n.is_compliant)
        local_compliance_rate = compliant_count / len(household_neighbors)
        self.sn = (self.sn * 0.8) + (local_compliance_rate * 0.2)

    def update_attitude(self):
        self.attitude -= self.attitude_decay_rate
        if self.barangay and hasattr(self.barangay, 'iec_intensity'):
            boost = self.barangay.iec_intensity * 0.02
            self.attitude += boost
        if self.barangay and self.barangay.enforcement_intensity > 0.8:
             self.attitude -= 0.002 
        self.attitude = max(0.0, min(1.0, self.attitude))

    def make_decision(self):
        """
        Calculates Utility and sets Compliance.
        """
        # 1. Calculate Net Cost (C_Net)
        gamma = 1.5 if self.income_level == 1 else (1.0 if self.income_level == 2 else 0.8)
        
        fine = self.barangay.fine_amount if self.barangay else 0
        incentive = self.barangay.inc_fund / 1000.0 if self.barangay else 0 
        prob_detection = self.barangay.enforcement_intensity if self.barangay else 0
        
        monetary_impact = incentive - (fine * prob_detection)
        
        # USE DYNAMIC EFFORT COST
        c_net = self.c_effort_base - (gamma * monetary_impact / 1000.0) 

        # 2. Calculate Utility (TPB Formula with dynamic weights)
        epsilon = self.random.gauss(0, 0.1)
        
        self.utility = (self.w_a * self.attitude) + \
                       (self.w_sn * self.sn) + \
                       (self.w_pbc * self.pbc) - \
                       c_net + epsilon

        # 3. Threshold Decision
        self.is_compliant = (self.utility > 0.5)

    def get_fined(self):
        self.utility -= 0.5 
        self.attitude -= 0.05
        if hasattr(self.model, 'total_fines_collected'):
            self.model.total_fines_collected += 500 
            self.model.recent_fines_collected += 500

    def step(self):
        self.update_attitude()
        self.update_social_norms()
        self.make_decision()