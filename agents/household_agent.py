import mesa
import random

class HouseholdAgent(mesa.Agent):
    """
    Household Agent based on Theory of Planned Behavior (TPB).
    Decides to segregate based on Attitude, Social Norms, and PBC.
    """
    def __init__(self, unique_id, model, income_level, initial_compliance):
        super().__init__(unique_id, model)
        self.income_level = income_level  # 1 (Low), 2 (Mid), 3 (High)
        self.is_compliant = initial_compliance
        self.barangay = None    
        self.barangay_id = None 

        # --- TPB Internal States ---
        self.attitude = 0.66 if initial_compliance else 0.3 
        self.sn = 0.5  
        self.pbc = 0.5 
        self.utility = 0.0  # <--- FIXED: Added attribute so Enforcers can modify it
        
        # Weights 
        self.w_a = 0.4
        self.w_sn = 0.3
        self.w_pbc = 0.3
        
        self.attitude_decay_rate = 0.005

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
        c_effort = 0.2
        c_net = c_effort - (gamma * monetary_impact / 1000.0) 

        # 2. Calculate Utility (TPB Formula)
        epsilon = self.random.gauss(0, 0.1)
        
        # <--- FIXED: Saved to self.utility instead of local variable
        self.utility = (self.w_a * self.attitude) + \
                       (self.w_sn * self.sn) + \
                       (self.w_pbc * self.pbc) - \
                       c_net + epsilon

        # 3. Threshold Decision
        self.is_compliant = (self.utility > 0.5)

    def get_fined(self):
        """
        Called by EnforcementAgent when caught non-compliant.
        Applies immediate penalty to utility and attitude.
        """
        # 1. Economic Hit (Reduces utility for this step)
        self.utility -= 0.5 
        
        # 2. Psychological Reactance (Being fined makes them grumpy)
        # However, it also proves enforcement is real (increases Prob_Detection perception in future)
        self.attitude -= 0.05
        
        # 3. Report to Model
        if hasattr(self.model, 'total_fines_collected'):
            self.model.total_fines_collected += 500 # Assume P500 fine
            self.model.recent_fines_collected += 500

    def step(self):
        self.update_attitude()
        self.update_social_norms()
        self.make_decision()