"""
Agent definitions for Phase 1 ABM
"""

import mesa
import numpy as np
from enum import Enum


class BarangayType(Enum):
    URBAN_CENTER = "urban_center"
    RURAL_COASTAL = "rural_coastal"
    RESIDENTIAL = "residential"


class HouseholdAgent(mesa.Agent):
    """Represents a household in Bacolod, Lanao del Norte"""

    def __init__(self, unique_id, model, barangay_id, barangay_name, income_level, education_level, config):
        super().__init__(unique_id, model)

        # Basic identification
        self.barangay_id = barangay_id
        self.barangay_name = barangay_name
        self.agent_type = "household"

        # Socio-demographic characteristics
        self.income_level = income_level  # 0 (low) to 1 (high)
        self.education_level = education_level  # 0 (low) to 1 (high)

        # TPB Parameters - initialized with randomness within configured ranges
        tpb_config = config['tpb_parameters']
        self.attitude = self.random.uniform(tpb_config['attitude_range'][0], tpb_config['attitude_range'][1])
        self.subjective_norm = self.random.uniform(tpb_config['subjective_norm_range'][0],
                                                   tpb_config['subjective_norm_range'][1])
        self.perceived_control = self.random.uniform(tpb_config['perceived_control_range'][0],
                                                     tpb_config['perceived_control_range'][1])

        # Economic sensitivity (based on configuration)
        econ_config = config['economic_sensitivity']
        self.incentive_sensitivity = econ_config['base_incentive_sensitivity'] * (1 - self.income_level)
        self.fine_sensitivity = econ_config['base_fine_sensitivity'] * (1 - self.income_level)

        # Behavioral state
        self.is_compliant = False
        self.compliance_history = []
        self.neighbors_compliance_rate = 0.0
        self.total_utility = 0.0

        # Social network (will be initialized after all agents are created)
        self.neighbors = []

        # Track decision components for analysis
        self.decision_components = {}

    def update_social_influence(self):
        """Update the perceived social norm based on neighbors' behavior"""
        if self.neighbors:
            compliant_neighbors = sum(1 for neighbor in self.neighbors if neighbor.is_compliant)
            self.neighbors_compliance_rate = compliant_neighbors / len(self.neighbors)
        else:
            self.neighbors_compliance_rate = 0.0

    def calculate_compliance_utility(self):
        """Calculate utility of compliance vs non-compliance using TPB framework"""
        tpb_config = self.model.config['tpb_parameters']

        # TPB components
        attitude_component = self.attitude * tpb_config['attitude_weight']
        social_component = self.subjective_norm * self.neighbors_compliance_rate * tpb_config['subjective_norm_weight']
        control_component = self.perceived_control * tpb_config['perceived_control_weight']

        # Economic components (current policy)
        incentive_utility = self.model.get_incentive_for_agent(self) * self.incentive_sensitivity
        fine_disutility = -self.model.get_fine_for_agent(self) * self.fine_sensitivity

        # Total utility for compliance
        utility_comply = (attitude_component + social_component +
                          control_component + incentive_utility)

        # Utility for non-compliance (only faces potential fine)
        utility_not_comply = fine_disutility

        # Store components for analysis
        self.decision_components = {
            'attitude': attitude_component,
            'social_norm': social_component,
            'perceived_control': control_component,
            'incentive': incentive_utility,
            'fine': fine_disutility,
            'utility_comply': utility_comply,
            'utility_not_comply': utility_not_comply
        }

        return utility_comply, utility_not_comply

    def step(self):
        """Execute one time step for the household"""
        # Update social influence from neighbors
        self.update_social_influence()

        # Calculate utilities
        utility_comply, utility_not_comply = self.calculate_compliance_utility()

        # Stochastic decision using logistic function
        utility_diff = utility_comply - utility_not_comply
        probability_comply = 1 / (1 + np.exp(-utility_diff))  # Logistic function

        # Make decision with some randomness
        self.is_compliant = self.random.random() < probability_comply
        self.total_utility = utility_comply if self.is_compliant else utility_not_comply

        # Record history (keep only last 50 steps to save memory)
        self.compliance_history.append(self.is_compliant)
        if len(self.compliance_history) > 50:
            self.compliance_history.pop(0)


class Barangay:
    """Represents a barangay with its specific characteristics"""

    def __init__(self, barangay_id, name, barangay_type, model):
        self.barangay_id = barangay_id
        self.name = name
        self.type = barangay_type
        self.model = model
        self.households = []

        # Barangay-specific characteristics
        self.set_barangay_characteristics()

    def set_barangay_characteristics(self):
        """Set typical socio-economic profiles based on barangay type"""
        # Find configuration for this barangay
        brgy_config = None
        for config_brgy in self.model.config['barangays']:
            if config_brgy['name'] == self.name:
                brgy_config = config_brgy
                break

        if brgy_config:
            self.avg_income = np.mean(brgy_config['income_range'])
            self.avg_education = np.mean(brgy_config['education_range'])
            self.income_range = brgy_config['income_range']
            self.education_range = brgy_config['education_range']
        else:
            # Default values if not found in config
            self.avg_income = 0.5
            self.avg_education = 0.5
            self.income_range = [0.3, 0.7]
            self.education_range = [0.3, 0.7]

    def add_household(self, household):
        self.households.append(household)

    def calculate_compliance_rate(self):
        if not self.households:
            return 0.0
        compliant = sum(1 for h in self.households if h.is_compliant)
        return compliant / len(self.households)

    def get_socioeconomic_profile(self):
        """Return summary statistics for the barangay"""
        if not self.households:
            return {
                'avg_income': 0,
                'avg_education': 0,
                'compliance_rate': 0,
                'population': 0
            }

        incomes = [h.income_level for h in self.households]
        educations = [h.education_level for h in self.households]
        compliances = [h.is_compliant for h in self.households]

        return {
            'avg_income': np.mean(incomes),
            'avg_education': np.mean(educations),
            'compliance_rate': np.mean(compliances),
            'population': len(self.households),
            'income_std': np.std(incomes),
            'education_std': np.std(educations)
        }

    def __repr__(self):
        profile = self.get_socioeconomic_profile()
        return f"Barangay({self.name}, Type: {self.type}, Pop: {profile['population']}, Compliance: {profile['compliance_rate']:.1%})"