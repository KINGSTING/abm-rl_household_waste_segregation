"""
Main ABM model for Bacolod waste segregation simulation
"""

import mesa
import numpy as np
import pandas as pd
from .agents import HouseholdAgent, Barangay, BarangayType
from .config import CONFIG


class BacolodWasteModel(mesa.Model):
    """Main ABM for Bacolod, Lanao del Norte waste segregation simulation"""

    def __init__(self, total_households=None, config=None):
        super().__init__()

        # Configuration
        self.config = config or CONFIG
        model_config = self.config['model']

        # Model parameters
        self.total_households = total_households or model_config['total_households']
        self.schedule = mesa.time.RandomActivation(self)
        self.grid = mesa.space.MultiGrid(50, 50, True)
        self.current_step = 0
        self.running = True

        # Set random seed for reproducibility
        if model_config.get('random_seed'):
            self.random.seed(model_config['random_seed'])
            np.random.seed(model_config['random_seed'])

        # Policy parameters (initially neutral)
        self.base_incentive = 0  # PHP
        self.base_fine = 0  # PHP

        # Initialize barangays
        self.barangays = self.initialize_barangays()

        # Create synthetic population
        self.households = self.create_synthetic_population()

        # Initialize social networks
        self.initialize_social_networks()

        # Data collection setup
        self.setup_data_collection()

        print(f"✅ Model initialized with {len(self.households)} households across {len(self.barangays)} barangays")

    def initialize_barangays(self):
        """Create the hypothetical municipality with 9 barangays"""
        barangays = []
        for i, brgy_config in enumerate(self.config['barangays']):
            # Convert string type to Enum
            try:
                brgy_type = BarangayType(brgy_config['type'])
            except ValueError:
                print(f"Warning: Unknown barangay type {brgy_config['type']}. Using residential as default.")
                brgy_type = BarangayType.RESIDENTIAL

            barangay = Barangay(
                barangay_id=i,
                name=brgy_config['name'],
                barangay_type=brgy_type,
                model=self
            )
            barangays.append(barangay)

        return barangays

    def create_synthetic_population(self):
        """Create a synthetic population based on barangay characteristics"""
        households = []
        agent_id = 0

        # Calculate household distribution across barangays
        total_weight = sum(brgy['weight'] for brgy in self.config['barangays'])
        barangay_allocations = {}

        for i, barangay in enumerate(self.barangays):
            brgy_config = self.config['barangays'][i]
            brgy_household_count = int(self.total_households * (brgy_config['weight'] / total_weight))
            barangay_allocations[barangay.name] = brgy_household_count

        # Create households for each barangay
        for i, barangay in enumerate(self.barangays):
            brgy_config = self.config['barangays'][i]
            brgy_household_count = barangay_allocations[barangay.name]

            for _ in range(brgy_household_count):
                # Generate socio-demographic attributes with barangay-specific distributions
                income = np.clip(
                    np.random.normal(barangay.avg_income, 0.15),
                    brgy_config['income_range'][0],
                    brgy_config['income_range'][1]
                )
                education = np.clip(
                    np.random.normal(barangay.avg_education, 0.2),
                    brgy_config['education_range'][0],
                    brgy_config['education_range'][1]
                )

                # Create household agent
                household = HouseholdAgent(
                    unique_id=agent_id,
                    model=self,
                    barangay_id=barangay.barangay_id,
                    barangay_name=barangay.name,
                    income_level=income,
                    education_level=education,
                    config=self.config
                )

                # Add to schedule and barangay
                self.schedule.add(household)
                barangay.add_household(household)
                households.append(household)

                # Place agent on grid (roughly by barangay)
                x = self.random.randint(0, 49)
                y = self.random.randint(0, 49)
                self.grid.place_agent(household, (x, y))

                agent_id += 1

        print(f"📊 Population distribution: {barangay_allocations}")
        return households

    def initialize_social_networks(self):
        """Initialize social networks within each barangay"""
        network_config = self.config['social_network']

        for barangay in self.barangays:
            brgy_households = [h for h in self.households if h.barangay_id == barangay.barangay_id]

            for household in brgy_households:
                # Find potential neighbors (prefer same barangay)
                same_brgy_neighbors = [h for h in brgy_households if h != household]
                other_brgy_neighbors = [h for h in self.households if h.barangay_id != barangay.barangay_id]

                # Select neighbors
                num_neighbors = self.random.randint(
                    network_config['min_neighbors'],
                    network_config['max_neighbors'] + 1
                )

                neighbors = []
                remaining_slots = num_neighbors

                # First, try to get neighbors from same barangay
                if same_brgy_neighbors:
                    num_same_brgy = min(
                        int(remaining_slots * network_config['same_barangay_probability']),
                        len(same_brgy_neighbors)
                    )
                    if num_same_brgy > 0:
                        neighbors.extend(self.random.sample(same_brgy_neighbors, num_same_brgy))
                        remaining_slots -= num_same_brgy

                # Fill remaining slots with neighbors from other barangays
                if remaining_slots > 0 and other_brgy_neighbors:
                    num_other_brgy = min(remaining_slots, len(other_brgy_neighbors))
                    if num_other_brgy > 0:
                        neighbors.extend(self.random.sample(other_brgy_neighbors, num_other_brgy))

                household.neighbors = neighbors

        print("✅ Social networks initialized")

    def get_incentive_for_agent(self, agent):
        """Get the incentive value for a specific agent"""
        return self.base_incentive

    def get_fine_for_agent(self, agent):
        """Get the fine value for a specific agent"""
        return self.base_fine

    def set_policy(self, incentive=None, fine=None):
        """Set the policy parameters"""
        if incentive is not None:
            self.base_incentive = max(0, incentive)
        if fine is not None:
            self.base_fine = max(0, fine)

    def setup_data_collection(self):
        """Setup Mesa's data collection for monitoring model outcomes"""

        def get_brgy_compliance(barangay_index):
            def reporter(model):
                if model.barangays and len(model.barangays) > barangay_index:
                    return model.barangays[barangay_index].calculate_compliance_rate()
                return 0.0

            return reporter

        # Create reporters for each barangay
        model_reporters = {
            "Overall_Compliance": lambda m: m.calculate_overall_compliance(),
            "Base_Incentive": lambda m: m.base_incentive,
            "Base_Fine": lambda m: m.base_fine,
            "Step": lambda m: m.current_step
        }

        # Add barangay-specific reporters
        for i, barangay in enumerate(self.barangays):
            model_reporters[f"{barangay.name}_Compliance"] = get_brgy_compliance(i)
            model_reporters[f"{barangay.name}_Population"] = lambda m, idx=i: len(m.barangays[idx].households)

        self.datacollector = mesa.DataCollector(
            model_reporters=model_reporters,
            agent_reporters={
                "Compliant": "is_compliant",
                "Income": "income_level",
                "Education": "education_level",
                "Barangay": "barangay_name",
                "Total_Utility": "total_utility",
                "Neighbors_Compliance_Rate": "neighbors_compliance_rate"
            }
        )

    def calculate_overall_compliance(self):
        """Calculate overall compliance rate across all barangays"""
        if not self.households:
            return 0.0
        compliant = sum(1 for h in self.households if h.is_compliant)
        return compliant / len(self.households)

    def step(self):
        """Advance the model by one step"""
        self.schedule.step()
        self.datacollector.collect(self)
        self.current_step += 1

    def run_simulation(self, steps=None):
        """Run the simulation for a given number of steps"""
        if steps is None:
            steps = self.config['model']['simulation_steps']

        for step in range(steps):
            self.step()

            # Print progress every 10% of steps
            if step % max(1, steps // 10) == 0:
                compliance = self.calculate_overall_compliance()
                print(f"Step {step}/{steps}: Overall Compliance = {compliance:.2%}")

        final_compliance = self.calculate_overall_compliance()
        print(f"🎯 Simulation completed. Final compliance: {final_compliance:.2%}")

        return self.datacollector.get_model_vars_dataframe(), self.datacollector.get_agent_vars_dataframe()