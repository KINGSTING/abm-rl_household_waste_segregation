import mesa
# REMOVED: from agents.household_agent import HouseholdAgent (Avoids circular import)

class BarangayAgent(mesa.Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        
        # --- 1. Identity & Demographics ---
        self.name = ""
        self.n_households = 1  
        
        # --- 2. State Metrics ---
        self.compliance_rate = 0.0
        self.total_households = 0
        self.compliant_count = 0
        
        # --- 3. Policy Variables ---
        self.iec_fund = 0.0
        self.enf_fund = 0.0
        self.inc_fund = 0.0
        self.fine_amount = 500
        
        # --- 4. Intensities ---
        self.enforcement_intensity = 0.5
        self.iec_intensity = 0.0
        self.incentive_val = 0.0  

    def update_policy(self, iec_fund, enf_fund, inc_fund):
        self.iec_fund = iec_fund
        self.enf_fund = enf_fund
        # FIX: The inc_fund is now a "Pot of Money" that drains over time
        self.inc_fund = inc_fund 
        self.current_cash_on_hand = inc_fund 

        # --- CALIBRATION FIX FOR STATUS QUO ---
        # OLD: Fixed Cost (Unrealistic for large vs small barangays)
        # SATURATION_POINT = 375000.0 
        
        # NEW: Variable Cost (Door-to-Door Logic)
        # We estimate it costs ~P650 per household per quarter to achieve 100% IEC saturation
        # Calculation: P93 budget/head / 0.14 target intensity ~= 664
        IEC_COST_PER_HEAD = 650.0 
        
        if self.n_households > 0:
            saturation_target = self.n_households * IEC_COST_PER_HEAD
        else:
            saturation_target = 375000.0 # Fallback

        self.iec_intensity = min(1.0, iec_fund / saturation_target)
        
        # Enforcement still uses fixed cost (patrols cover area, not people)
        # You can keep this fixed or scale it by area if you wish.
        ENF_SATURATION = 375000.0
        self.enforcement_intensity = min(1.0, enf_fund / ENF_SATURATION)

        # Incentive Logic
        if self.n_households > 0:
            self.incentive_val = self.inc_fund / self.n_households
        else:
            self.incentive_val = 0

    def get_local_compliance(self):
        """
        Calculates compliance for the DataCollector.
        ROBUST FIX: Checks attributes instead of Class Type to avoid import errors.
        """
        self.total_households = 0
        self.compliant_count = 0
        
        for a in self.model.schedule.agents:
            # 1. Check if agent belongs to this Barangay
            if getattr(a, 'barangay_id', None) == self.unique_id:
                
                # 2. Check if agent is a Household (has 'is_compliant' attr)
                # This excludes Enforcers automatically.
                if hasattr(a, 'is_compliant'):
                    self.total_households += 1
                    if a.is_compliant:
                        self.compliant_count += 1
        
        # Avoid division by zero
        if self.total_households == 0:
            self.compliance_rate = 0.0
        else:
            self.compliance_rate = self.compliant_count / self.total_households
            
        return self.compliance_rate

    def step(self):
        self.get_local_compliance()

    def give_reward(self, amount):
        """
        Attempt to give a reward to a household.
        Returns TRUE if successful (budget exists), FALSE if bankrupt.
        """
        if self.current_cash_on_hand >= amount:
            self.current_cash_on_hand -= amount
            # Update the global tracker for reporting
            self.model.total_incentives_distributed += amount
            return True
        return False