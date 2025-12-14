import mesa
import numpy as np
import random # <--- THIS IS CRITICAL. If missing, it crashes at Step 2.
import math

# --- Agent Base Class ---

class HouseholdAgent(mesa.Agent):
    """
    Represents a household making decisions based on Theory of Planned Behavior 
    AND Economic Utility (Costs/Fines).
    """
    def __init__(self, unique_id, model, income_level, initial_compliance):
        super().__init__(unique_id, model)
        
        # --- 0. Demographics ---
        self.income_level = income_level  # 1 (Low), 2 (Medium), 3 (High)

        # --- 1. TPB Internal Variables (0.0 to 1.0) ---
        # Base Attitude: Randomly assigned 
        self.attitude = np.clip(np.random.normal(0.5, 0.2), 0.1, 0.9) 
        
        # PBC: Random "ease of segregation" (Fixed for now)
        # e.g., 0.8 means they have space/time; 0.3 means it's hard for them
        self.pbc = np.clip(np.random.normal(0.7, 0.1), 0.2, 1.0)
        
        # Social Norm: Dynamic
        self.social_norm = 0.5 

        # --- 2. State Variables ---
        self.is_compliant = initial_compliance
        self.utility = 0.0

        # Ensure attitude is a float (0.0 to 1.0)
        self.attitude = 0.66 if initial_compliance else 0.3  # Baseline from Thesis Table 3.1 [cite: 449]
        self.attitude_decay_rate = 0.005  # Slow decay per tick

    def update_attitude(self):
        """
        Dynamic Attitude Update (Thesis Section 3.3.1)
        1. Natural Decay ("Public Forgetting")
        2. IEC Boost (If Barangay spends on education)
        """
        # 1. Apply Natural Decay
        self.attitude -= self.attitude_decay_rate

        # 2. Apply IEC Boost
        # We look at our local Barangay's IEC intensity (0.0 to 1.0)
        if self.barangay and hasattr(self.barangay, 'iec_intensity'):
            # Boost scales with intensity. Max boost per tick = 0.02
            boost = self.barangay.iec_intensity * 0.02
            self.attitude += boost

        # 3. Apply Reactance (Optional: High enforcement slightly lowers attitude)
        if self.barangay and self.barangay.enforcement_intensity > 0.8:
             self.attitude -= 0.002 # Reactance penalty

        # Clamp between 0 and 1
        self.attitude = max(0.0, min(1.0, self.attitude))

    def update_social_norms(self):
        """
        Calculates social pressure. 
        CRITICAL FIX: Only look at neighbors in the SAME barangay.
        """
        neighbors = self.model.grid.get_neighbors(self.pos, moore=True, radius=2)
        
        # Filter neighbors: Must be HouseholdAgent AND share my barangay_id
        household_neighbors = [
            n for n in neighbors 
            if isinstance(n, HouseholdAgent) and n.barangay_id == self.barangay_id
        ]
        
        if not household_neighbors:
            return 0.5 
            
        compliant_count = sum(1 for n in household_neighbors if n.is_compliant)
        total_neighbors = len(household_neighbors)
        raw_norm = compliant_count / total_neighbors

        # Asymmetric Influence
        if raw_norm > 0.5:
            return min(1.0, raw_norm * 1.2) # Amplify Good
        else:
            base_decency = 0.2
            return (raw_norm * 0.8) + base_decency # Buffer Bad
        
    def get_fined(self):
        """
        Called by EnforcementAgent when caught.
        """
        # 1. Financial Hit: Increases 'C_Net' for next calculation
        # We can add a temporary flag that decays
        self.caught_recently = True
        
        # 2. Immediate Behavior Correction (The "scare" factor)
        # Force them to rethink compliance immediately
        self.utility -= 0.5  # Heavy penalty to current utility

    def calculate_utility(self):
        """
        Calculates utility by reading policy parameters from the local Barangay Agent.
        """
        # --- A. TPB Score ---
        w_att, w_sn, w_pbc = 0.4, 0.3, 0.3
        tpb_score = (w_att * self.attitude) + \
                    (w_sn * self.social_norm) + \
                    (w_pbc * self.pbc)

        # --- B. Economic Costs (C_Net) ---
        c_effort = 0.1      
        c_monetary = 0.05   
        incentive = self.model.reward_value if self.is_compliant else 0.0 # Reward is still global
        
        # 🔥 FIX: Read Fine and Enforcement from local BARANGAY Agent
        prob_catch = self.barangay.enforcement_intensity 
        fine_amount = self.barangay.fine_amount 
        
        expected_fine = fine_amount * prob_catch

        # --- C. Gamma Weight (Income Sensitivity) ---
        gamma = {1: 1.5, 2: 1.2, 3: 1.0}.get(self.income_level, 1.0)

        # Scale fine for Utility calculation (normalize it)
        # Using 1000.0 as the maximum expected fine for normalization
        normalized_fine = expected_fine / 1000.0 

        # Net Cost calculation:
        c_net = ((c_effort + c_monetary - incentive) - normalized_fine) * gamma
        
        epsilon = np.random.normal(0, 0.05)
        
        return tpb_score - c_net + epsilon

    def step(self):
        # 1. Update Internal States
        self.update_attitude()
        self.social_norm = self.update_social_norms()

        # 2. Calculate Utility
        self.utility = self.calculate_utility()

        # 3. Decision
        if self.utility > 0.5:
            self.is_compliant = True
        else:
            self.is_compliant = False

        # Existing logic
        self.update_social_norms()
        self.make_decision()

    def update_attitude(self):
        # Thesis logic: Attitude decays naturally, but boosts with IEC
        decay_rate = 0.01
        
        # 1. Apply Decay
        self.attitude = max(0.0, self.attitude - decay_rate)
        
        # 2. Apply Boost (From Barangay's IEC)
        # The BarangayAgent needs to store 'iec_intensity' from the action above
        if self.barangay.iec_intensity > 0:
            boost = self.barangay.iec_intensity * 0.05
            self.attitude = min(1.0, self.attitude + boost)