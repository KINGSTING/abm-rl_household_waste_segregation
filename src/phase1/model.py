"""
Main ABM model for Bacolod waste segregation simulation
LGU (Model) acts as Supervisor, Barangay (Helper Class) acts as Implementor.
"""

import mesa
import numpy as np
import pandas as pd
from .agents import HouseholdAgent, Barangay, BarangayType
from .config import CONFIG
from typing import Dict, Optional, Tuple


class BacolodWasteModel(mesa.Model):
    """
    Main ABM for Bacolod, Lanao del Norte waste segregation simulation.
    This class represents the LGU (Supervisor), which sets policy and
    allocates budgets. It manages the Barangay helper classes (Implementors).
    """

    def __init__(self, total_households: Optional[int] = None, config: Optional[Dict] = None):
        super().__init__()

        # --- 1. Configuration ---
        self.config = config or CONFIG
        model_config = self.config['model']
        self.policy_config = self.config['policy']

        # --- 2. Model Parameters ---
        self.total_households = total_households or model_config['total_households']
        self.schedule = mesa.time.RandomActivation(self)
        self.grid = mesa.space.MultiGrid(50, 50, True) # Grid for visualization, not logic
        self.current_step = 0
        self.running = True

        # Set random seed for reproducibility
        if model_config.get('random_seed'):
            self.random.seed(model_config['random_seed'])
            np.random.seed(model_config['random_seed'])

        # --- 3. LGU Policy & Budget Parameters (Supervisor Role) ---
        self.total_lgu_budget = self.policy_config['total_lgu_annual_budget']

        # Budgets (These are the "knobs" the RL agent will turn)
        # Budgets are annual, but simulation steps are daily (365 steps)
        self.budget_for_incentives = 0.0
        self.budget_for_enforcement = 0.0
        self.budget_for_education = 0.0

        # Translated Policy Effects (These are the *results* of budget allocation)
        self.base_incentive_value = self.policy_config['base_incentive_php']
        self.base_fine_value = self.policy_config['base_fine_php']
        self.probability_of_getting_caught = 0.0 # (P_catch) Per step
        self.education_attitude_boost = 0.0     # (att_boost) Per step
        self.education_pbc_boost = 0.0          # (pbc_boost) Per step

        # --- 4. Initialization ---
        # Initialize barangays first, as households will be assigned to them
        self.barangays: list[Barangay] = []
        self.barangay_lookup: Dict[int, Barangay] = {}
        self.initialize_barangays()

        # Create synthetic population of HouseholdAgents (Citizens)
        self.households: list[HouseholdAgent] = []
        self.create_synthetic_population()

        # Initialize social networks
        self.initialize_social_networks()

        # Data collection setup
        self.setup_data_collection()

        print(f"✅ Model initialized with {len(self.households)} households across {len(self.barangays)} barangays")

    def initialize_barangays(self) -> None:
        """Create the Barangay manager objects based on config."""
        for i, brgy_config in enumerate(self.config['barangays']):
            try:
                brgy_type = BarangayType(brgy_config['type'])
            except ValueError:
                print(f"Warning: Unknown barangay type {brgy_config['type']}. Defaulting to urban_coastal.")
                brgy_type = BarangayType.URBAN_COASTAL

            barangay = Barangay(
                barangay_id=i,
                name=brgy_config['name'],
                barangay_type=brgy_type,
                model=self
            )
            self.barangays.append(barangay)
            self.barangay_lookup[i] = barangay

        print(f"🏢 {len(self.barangays)} Barangay Implementors initialized.")

    def get_barangay_by_id(self, barangay_id: int) -> Optional[Barangay]:
        """Helper function for agents to find their Barangay manager."""
        return self.barangay_lookup.get(barangay_id)

    def create_synthetic_population(self) -> None:
        """Create a synthetic population based on barangay characteristics."""
        households_created = 0
        agent_id = 0

        # Calculate household distribution across barangays
        total_weight = sum(brgy['weight'] for brgy in self.config['barangays'])

        for i, barangay in enumerate(self.barangays):
            brgy_config = self.config['barangays'][i]

            # Allocate households based on weight
            if i == len(self.barangays) - 1:
                # Ensure last barangay gets all remaining households to match total
                brgy_household_count = self.total_households - households_created
            else:
                brgy_household_count = int(self.total_households * (brgy_config['weight'] / total_weight))

            households_created += brgy_household_count

            for _ in range(brgy_household_count):
                # Generate socio-demographic attributes from config ranges
                income = self.random.uniform(*brgy_config['income_range'])
                education = self.random.uniform(*brgy_config['education_range'])

                # Create household agent (Citizen)
                household = HouseholdAgent(
                    unique_id=agent_id,
                    model=self,
                    barangay_id=barangay.barangay_id,
                    barangay_name=barangay.name,
                    income_level=income,
                    education_level=education,
                    location_type=barangay.type, # CRITICAL: Pass the enum type
                    config=self.config
                )

                self.schedule.add(household)
                barangay.add_household(household) # Assign citizen to its implementor
                self.households.append(household)

                # Place agent on grid (optional, for visualization)
                x = self.random.randint(0, 49)
                y = self.random.randint(0, 49)
                self.grid.place_agent(household, (x, y))

                agent_id += 1

    def initialize_social_networks(self) -> None:
        """Initialize social networks, strongly weighted by barangay."""
        network_config = self.config['social_network']
        same_brgy_prob = network_config['same_barangay_probability']

        for household in self.households:
            num_neighbors = self.random.randint(
                network_config['min_neighbors'],
                network_config['max_neighbors'] + 1
            )

            # Get potential neighbors
            same_brgy_neighbors = [h for h in self.barangays[household.barangay_id].households if h != household]
            other_brgy_neighbors = [h for h in self.households if h.barangay_id != household.barangay_id]

            neighbors = []

            for _ in range(num_neighbors):
                if self.random.random() < same_brgy_prob and same_brgy_neighbors:
                    neighbor = self.random.choice(same_brgy_neighbors)
                    neighbors.append(neighbor)
                    same_brgy_neighbors.remove(neighbor) # Don't pick same neighbor twice
                elif other_brgy_neighbors:
                    neighbor = self.random.choice(other_brgy_neighbors)
                    neighbors.append(neighbor)
                    other_brgy_neighbors.remove(neighbor)

            household.neighbors = list(set(neighbors)) # Ensure unique neighbors

    # --- POLICY TRANSLATOR FUNCTIONS (LGU SUPERVISOR LOGIC) ---

    def convert_enforcement_budget_to_p_catch(self, annual_budget: float) -> float:
        """
        Translates annual enforcement ₱ budget into a per-step (daily)
        probability of getting caught (P_catch).
        Models hiring 'Eco-warriors' (E.1).
        """
        budget_for_max_p = self.policy_config['enforcement_budget_for_max_p_catch']
        max_p_catch_per_step = self.policy_config['max_p_catch_per_step']

        if budget_for_max_p == 0:
            return 0.0

        # Simple linear scaling with a cap (diminishing returns)
        budget_ratio = min(annual_budget / budget_for_max_p, 1.0)
        return max_p_catch_per_step * budget_ratio

    def convert_education_budget_to_boost(self, annual_budget: float) -> Tuple[float, float]:
        """
        Translates annual education ₱ budget into a per-step (daily)
        boost for Attitude (A) and PBC.
        Models 'IEC campaigns' and 'radio ads' (E.1).
        """
        budget_for_max_boost = self.policy_config['education_budget_for_max_boost']
        max_boost_per_step = self.policy_config['education_max_boost_per_step']

        if budget_for_max_boost == 0:
            return (0.0, 0.0)

        # Simple linear scaling with a cap
        budget_ratio = min(annual_budget / budget_for_max_boost, 1.0)
        total_boost = max_boost_per_step * budget_ratio

        # Split the boost 50/50 between Attitude and PBC
        att_boost = total_boost * 0.5
        pbc_boost = total_boost * 0.5

        return (att_boost, pbc_boost)

    # --- MAIN POLICY AND SIMULATION FUNCTIONS ---

    def set_policy(self, budget_for_incentives: float, budget_for_enforcement: float, budget_for_education: float) -> None:
        """
        The main Supervisor function. Sets the LGU's policy by allocating its
        annual budget and distributing the policy to Barangay Implementors.
        """
        # 1. Store the budgets
        self.budget_for_incentives = budget_for_incentives
        self.budget_for_enforcement = budget_for_enforcement
        self.budget_for_education = budget_for_education

        # 2. Translate budgets into simulation effects
        self.probability_of_getting_caught = self.convert_enforcement_budget_to_p_catch(self.budget_for_enforcement)
        self.education_attitude_boost, self.education_pbc_boost = self.convert_education_budget_to_boost(self.budget_for_education)

        # 3. Distribute the policy to all Barangay Implementors
        # (This is a uniform policy. A smarter RL agent could differentiate)
        for barangay in self.barangays:
            barangay.set_lgu_policy(
                incentive_val=self.base_incentive_value,
                fine_val=self.base_fine_value,
                p_catch=self.probability_of_getting_caught,
                edu_att_boost=self.education_attitude_boost,
                edu_pbc_boost=self.education_pbc_boost
            )

        print(f"POLICY SET: P_Catch={self.probability_of_getting_caught:.4%}, "
              f"Edu_Boost={self.education_attitude_boost:.6f}, "
              f"Incentive_Budget={self.budget_for_incentives:,.0f}")

    def setup_data_collection(self) -> None:
        """Setup Mesa's data collection for monitoring model outcomes."""

        def get_brgy_compliance(model: BacolodWasteModel, barangay_name: str) -> float:
            for brgy in model.barangays:
                if brgy.name == barangay_name:
                    return brgy.calculate_compliance_rate()
            return 0.0

        model_reporters = {
            "Step": lambda m: m.current_step,
            "Overall_Compliance": lambda m: m.calculate_overall_compliance(),

            # --- Report on Budgets and Translated Effects ---
            "Incentive_Budget_Remaining": lambda m: m.budget_for_incentives,
            "Enforcement_Budget_Set": lambda m: m.budget_for_enforcement,
            "Education_Budget_Set": lambda m: m.budget_for_education,
            "P_Catch_Set": lambda m: m.probability_of_getting_caught,
            "Edu_Boost_Set": lambda m: m.education_attitude_boost
        }

        # Add barangay-specific compliance reporters
        for brgy_config in self.config['barangays']:
            brgy_name = brgy_config['name']
            model_reporters[f"{brgy_name}_Compliance"] = lambda m, name=brgy_name: get_brgy_compliance(m, name)

        self.datacollector = mesa.DataCollector(
            model_reporters=model_reporters,
            agent_reporters={
                # --- THESE ARE THE MISSING KEYS ---
                "Compliant": "is_compliant",
                "Income": "income_level",
                "Education": "education_level",
                "Barangay": "barangay_name",
                "Attitude": "attitude",
                "Subjective_Norm": "subjective_norm",
                "PBC": "perceived_control",
                "Neighbors_Compliance_Rate": "neighbors_compliance_rate"
            }
        )

    def calculate_overall_compliance(self) -> float:
        """Calculate overall compliance rate across all households."""
        if not self.households:
            return 0.0
        compliant = sum(1 for h in self.households if h.is_compliant)
        return compliant / len(self.households)

    def step(self) -> None:
        """Advance the model by one step (simulating one day)."""
        self.current_step += 1
        total_incentives_paid_this_step = 0.0

        # 1. Reset step-level metrics for all Implementors
        for barangay in self.barangays:
            barangay.reset_step_metrics()

        # 2. Apply "Education" policy (if active)
        # The Supervisor tells the Implementors to boost their Citizens
        if self.education_attitude_boost > 0 or self.education_pbc_boost > 0:
            for barangay in self.barangays:
                att_boost, pbc_boost = barangay.get_education_boosts()
                for household in barangay.households:
                    household.receive_education_boost(att_boost, pbc_boost)

        # 3. Agents make decisions
        # This calls HouseholdAgent.step() for all agents
        self.schedule.step()

        # 4. Track LGU Budget (Supervisor checks spending)
        # Aggregate incentive payouts from all Implementors
        if self.policy_config['track_incentive_budget']:
            for barangay in self.barangays:
                total_incentives_paid_this_step += barangay.incentive_payout_this_step

            # Deplete the LGU's incentive budget
            self.budget_for_incentives = max(0.0, self.budget_for_incentives - total_incentives_paid_this_step)

        # 5. Collect data
        self.datacollector.collect(self)

    def run_simulation(self, steps: Optional[int] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Run the simulation for a given number of steps."""
        if steps is None:
            steps = self.config['model']['simulation_steps']

        print(f"🔄 Running simulation for {steps} steps...")
        for step in range(steps):
            self.step()

            # Print progress every 5% of steps
            if step % max(1, steps // 20) == 0 or step == steps - 1:
                compliance = self.calculate_overall_compliance()
                print(f"  Step {step+1}/{steps}: Overall Compliance = {compliance:.2%}, "
                      f"Incentive Budget: ₱{self.budget_for_incentives:,.0f}")

        final_compliance = self.calculate_overall_compliance()
        print(f"🎯 Simulation completed. Final compliance: {final_compliance:.2%}")

        return self.datacollector.get_model_vars_dataframe(), self.datacollector.get_agent_vars_dataframe()