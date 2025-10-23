"""
Agent and Grouping Definitions for the Waste Segregation ABM.

This file defines two main classes:
1.  HouseholdAgent: A MESA agent representing a single household. Its decision-making
    is governed by the Theory of Planned Behavior (TPB), social influence, and
    economic incentives/penalties.
2.  Barangay: A helper class (not a MESA agent) that serves as a container
    for HouseholdAgents. It helps in grouping agents and calculating
    barangay-level aggregate data like compliance rates and socio-economic profiles.
"""

import mesa
import numpy as np
from enum import Enum
from typing import List, Dict, Any, Tuple


class BarangayType(Enum):
    """Enumeration for the types of barangays in the model."""
    URBAN_CENTER = "urban_center"
    URBAN_COASTAL = "urban_coastal"


class HouseholdAgent(mesa.Agent):
    """
    Represents a household agent in a hypothetical Mindanao municipality.
    Its primary behavior is deciding whether or not to comply with a waste
    segregation policy based on a utility calculation.
    """

    def __init__(self, unique_id: int, model: 'BacolodWasteModel', barangay_id: int,
                 barangay_name: str, income_level: float, education_level: float,
                 config: Dict[str, Any]):
        """
        Initializes a HouseholdAgent.

        Args:
            unique_id: A unique identifier for the agent.
            model: The main model instance.
            barangay_id: The ID of the barangay this agent belongs to.
            barangay_name: The name of the barangay this agent belongs to.
            income_level: A normalized value (0-1) representing income.
            education_level: A normalized value (0-1) representing education.
            config: The model's configuration dictionary.
        """
        super().__init__(unique_id, model)

        # --- Agent Identification ---
        self.barangay_id = barangay_id
        self.barangay_name = barangay_name

        # --- Socio-demographic Characteristics ---
        self.income_level = income_level
        self.education_level = education_level

        # --- Theory of Planned Behavior (TPB) Parameters ---
        # These are initialized with randomness based on ranges in the config file
        # to create a heterogeneous population.
        tpb_config = config['tpb_parameters']
        self.attitude = self.random.uniform(*tpb_config['attitude_range'])
        self.subjective_norm = self.random.uniform(*tpb_config['subjective_norm_range'])
        self.perceived_control = self.random.uniform(*tpb_config['perceived_control_range'])

        # --- Economic Sensitivity ---
        # Sensitivity to fines/incentives is scaled inversely with income.
        econ_config = config['economic_sensitivity']
        self.incentive_sensitivity = econ_config['base_incentive_sensitivity'] * (1 - self.income_level)
        self.fine_sensitivity = econ_config['base_fine_sensitivity'] * (1 - self.income_level)

        # --- Behavioral State ---
        self.is_compliant: bool = False
        self.compliance_history: List[bool] = []
        self.neighbors_compliance_rate: float = 0.0

        # --- Social Network ---
        self.neighbors: List['HouseholdAgent'] = []

        # --- For Analysis ---
        # These are updated each step to see what drove the decision.
        self.decision_components: Dict[str, float] = {}
        self.total_utility: float = 0.0

    def update_social_influence(self) -> None:
        """
        Calculates the compliance rate among the agent's social neighbors.
        This rate directly influences the 'subjective_norm' component of the
        utility calculation.
        """
        if self.neighbors:
            compliant_neighbors = sum(1 for neighbor in self.neighbors if neighbor.is_compliant)
            self.neighbors_compliance_rate = compliant_neighbors / len(self.neighbors)
        else:
            self.neighbors_compliance_rate = 0.0

    def calculate_compliance_utility(self) -> Tuple[float, float]:
        """
        Calculates the utility of both complying and not complying.

        The utility function is a core component of the agent's decision-making,
        combining psychological factors (TPB), social influence, and economic factors.

        Returns:
            A tuple containing (utility_comply, utility_not_comply).
        """
        tpb_config = self.model.config['tpb_parameters']

        # --- TPB Components ---
        # 1. Attitude: Agent's personal positive/negative evaluation of the behavior.
        attitude_component = self.attitude * tpb_config['attitude_weight']

        # 2. Social Norm: Perceived social pressure from neighbors.
        #    This is scaled by the actual observed compliance rate of neighbors.
        social_component = self.subjective_norm * self.neighbors_compliance_rate * tpb_config['subjective_norm_weight']

        # 3. Perceived Control: Agent's belief in their ability to perform the behavior.
        control_component = self.perceived_control * tpb_config['perceived_control_weight']

        # --- Economic Components (from the current active policy in the model) ---
        # 4. Incentive: Potential reward for compliance.
        incentive_utility = self.model.get_incentive_for_agent(self) * self.incentive_sensitivity

        # 5. Fine: Potential penalty for non-compliance.
        #    This is a negative utility (disutility).
        fine_disutility = -self.model.get_fine_for_agent(self) * self.fine_sensitivity

        # --- Total Utilities ---
        # The utility of complying is the sum of personal, social, and positive economic factors.
        utility_comply = (attitude_component + social_component +
                         control_component + incentive_utility)

        # The utility of not complying is primarily driven by the risk of being fined.
        utility_not_comply = fine_disutility

        # Store these components for data collection and analysis
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

    def step(self) -> None:
        """
        Executes one time step of the agent's logic.
        1. Perceive social influence.
        2. Calculate utilities for actions.
        3. Make a compliance decision.
        """
        self.update_social_influence()
        utility_comply, utility_not_comply = self.calculate_compliance_utility()

        # A stochastic decision is made using a logistic function.
        # This converts the continuous utility difference into a probability (0-1),
        # allowing for non-deterministic behavior. A larger positive difference
        # makes compliance more likely.
        utility_diff = utility_comply - utility_not_comply
        probability_comply = 1 / (1 + np.exp(-utility_diff))

        self.is_compliant = self.random.random() < probability_comply
        self.total_utility = utility_comply if self.is_compliant else utility_not_comply

        # Record history for trend analysis (capped at 50 steps for memory efficiency)
        self.compliance_history.append(self.is_compliant)
        if len(self.compliance_history) > 50:
            self.compliance_history.pop(0)


class Barangay:
    """
    Represents a barangay as a container for households and a data aggregator.

    NOTE: This is NOT a MESA agent. It does not have a step() method and is not
    placed on the grid or in the scheduler. It is a helper object managed by the
    main Model class to organize agents and calculate group-level statistics.
    """

    def __init__(self, barangay_id: int, name: str, barangay_type: BarangayType, model: 'BacolodWasteModel'):
        self.barangay_id = barangay_id
        self.name = name
        self.type = barangay_type
        self.model = model
        self.households: List[HouseholdAgent] = []

        # Barangay-specific parameters loaded from config
        self.income_range: List[float] = [0.3, 0.7]
        self.education_range: List[float] = [0.3, 0.7]
        self.set_barangay_characteristics()

    def set_barangay_characteristics(self) -> None:
        """
        Loads and sets the barangay's socio-economic profile from the main config file.
        Raises a ValueError if the barangay's configuration is not found.
        """
        brgy_config = next((b for b in self.model.config['barangays'] if b['name'] == self.name), None)

        if not brgy_config:
            raise ValueError(f"Configuration for Barangay '{self.name}' not found in config file.")

        self.income_range = brgy_config['income_range']
        self.education_range = brgy_config['education_range']

    def add_household(self, household: HouseholdAgent) -> None:
        """Adds a household agent to this barangay's internal list."""
        self.households.append(household)

    def calculate_compliance_rate(self) -> float:
        """Calculates the current compliance rate for all households in the barangay."""
        if not self.households:
            return 0.0
        compliant_count = sum(1 for h in self.households if h.is_compliant)
        return compliant_count / len(self.households)

    def get_socioeconomic_profile(self) -> Dict[str, Any]:
        """
        Computes and returns a dictionary of summary statistics for the barangay.

        Returns:
            A dictionary containing aggregate data like population, average income,
            compliance rate, etc.
        """
        if not self.households:
            return {
                'avg_income': 0, 'avg_education': 0, 'compliance_rate': 0,
                'population': 0, 'income_std': 0, 'education_std': 0
            }

        incomes = [h.income_level for h in self.households]
        educations = [h.education_level for h in self.households]

        return {
            'population': len(self.households),
            'compliance_rate': self.calculate_compliance_rate(),
            'avg_income': np.mean(incomes),
            'avg_education': np.mean(educations),
            'income_std': np.std(incomes),
            'education_std': np.std(educations)
        }

    def __repr__(self) -> str:
        """Provides a user-friendly string representation of the Barangay object."""
        profile = self.get_socioeconomic_profile()
        return (f"Barangay(Name: {self.name}, Type: {self.type.value}, "
                f"Population: {profile['population']}, "
                f"Compliance: {profile['compliance_rate']:.2%})")
