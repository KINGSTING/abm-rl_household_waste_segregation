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
    RURAL_INLAND = "rural_inland" # ADDED: Matches your config


class HouseholdAgent(mesa.Agent):
    """
    Represents a household agent (citizen) in a hypothetical Mindanao municipality.
    Its primary behavior is deciding whether or not to comply with a waste
    segregation policy based on a utility calculation.
    """

    def __init__(self, unique_id: int, model: 'BacolodWasteModel', barangay_id: int,
                 barangay_name: str, income_level: float, education_level: float,
                 location_type: BarangayType, # ADDED: To apply PBC penalties from interview data
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
            location_type: The type of barangay (e.g., URBAN_COASTAL, RURAL_INLAND).
            config: The model's configuration dictionary.
        """
        super().__init__(unique_id, model)

        # --- Agent Identification ---
        self.barangay_id = barangay_id
        self.barangay_name = barangay_name
        self.location_type = location_type # Store the barangay type

        # --- Socio-demographic Characteristics ---
        self.income_level = income_level
        self.education_level = education_level

        # --- Theory of Planned Behavior (TPB) Parameters ---
        tpb_config = config['tpb_parameters']

        # Initial Attitude (A): Modulated by education_level
        # Educated might have higher initial awareness/attitude, but this doesn't guarantee compliance
        self.attitude = self.random.uniform(*tpb_config['attitude_range'])
        self.attitude = (self.attitude * 0.7) + (self.education_level * 0.3) # Education gives a slight boost to initial attitude

        # Initial Subjective Norm (SN): CRITICAL FOR BASELINE CALIBRATION (Appendix E)
        if self.barangay_name == "Liangan East":
            # Brgy. Liangan East has observed 60-70% compliance (E.2)
            self.subjective_norm = self.random.uniform(
                *tpb_config['initial_sn_range_liangan_east']
            )
        else:
            # Other barangays generally have low compliance (~10% from MENRO E.1)
            self.subjective_norm = self.random.uniform(
                *tpb_config['initial_sn_range_non_liangan']
            )

        # Initial Perceived Behavioral Control (PBC): CRITICAL FOR BASELINE CALIBRATION (Appendix E)
        pbc_penalties = config['pbc_penalties'] # Load specific penalties from config
        base_pbc = self.random.uniform(*tpb_config['perceived_control_range'])

        # Apply penalties based on interview data
        pbc_penalty_total = 0.0
        # "Sako is expensive" for low-income households (E.2)
        if self.income_level < pbc_penalties['income_threshold']:
            pbc_penalty_total += pbc_penalties['income_penalty']

        # "Layo na kaayo" for rural/inland barangays (E.1)
        if self.location_type == BarangayType.RURAL_INLAND:
            pbc_penalty_total += pbc_penalties['inland_penalty']

        self.perceived_control = max(0.0, base_pbc - pbc_penalty_total) # PBC cannot go below 0

        # --- Economic Sensitivity ---
        # Sensitivity to fines/incentives is scaled inversely with income.
        # This models the 'economic_sensitivity' effect from your config.
        # Lower income -> Higher sensitivity to both fines and incentives
        econ_config = config['economic_sensitivity']
        self.economic_multiplier = 1.0 + (econ_config['income_effect_magnitude'] * (1 - self.income_level))
        self.incentive_sensitivity = econ_config['base_incentive_sensitivity'] * self.economic_multiplier
        self.fine_sensitivity = econ_config['base_fine_sensitivity'] * self.economic_multiplier

        # --- Behavioral State ---
        self.is_compliant: bool = False
        self.compliance_history: List[bool] = []
        self.neighbors_compliance_rate: float = 0.0

        # --- Social Network ---
        self.neighbors: List['HouseholdAgent'] = []

        # --- For Analysis ---
        self.decision_components: Dict[str, float] = {}
        self.total_utility: float = 0.0

    def update_social_influence(self) -> None:
        """
        Calculates the compliance rate among the agent's social neighbors.
        This rate directly influences the 'subjective_norm' component of the
        utility calculation.
        """
        if self.neighbors:
            # We assume agent observes recent compliance history of neighbors, not just current step
            # For simplicity, let's use current step for now, but a more complex model could average history
            compliant_neighbors = sum(1 for neighbor in self.neighbors if neighbor.is_compliant)
            self.neighbors_compliance_rate = compliant_neighbors / len(self.neighbors)
        else:
            self.neighbors_compliance_rate = 0.0

        # Agent's subjective norm slowly adjusts towards what it observes
        # This creates inertia and makes norms change gradually
        sn_decay_rate = self.model.config['tpb_parameters']['sn_decay_rate'] # e.g., 0.9 (retains 90%)
        self.subjective_norm = (self.subjective_norm * sn_decay_rate) + \
                               (self.neighbors_compliance_rate * (1 - sn_decay_rate))

    def receive_education_boost(self, attitude_boost: float, pbc_boost: float) -> None:
        """
        Applies a boost to the agent's TPB parameters from an LGU
        Information, Education, and Communication (IEC) campaign.
        """
        self.attitude = min(self.attitude + attitude_boost, 1.0)
        self.perceived_control = min(self.perceived_control + pbc_boost, 1.0)

    def calculate_compliance_utility(self) -> Tuple[float, float]:
        """
        Calculates the utility of both complying and not complying.
        This new logic treats PBC as the *inverse* of effort cost.
        """
        tpb_config = self.model.config['tpb_parameters']

        # Agent asks its Barangay for current policy values
        current_barangay: Barangay = self.model.get_barangay_by_id(self.barangay_id)

        incentive_value = current_barangay.get_incentive_value()
        fine_value = current_barangay.get_fine_value()
        p_catch = current_barangay.get_probability_of_getting_caught()

        # --- Benefits of Complying ---
        attitude_component = self.attitude * tpb_config['attitude_weight']
        social_component = self.subjective_norm * tpb_config['subjective_norm_weight']
        incentive_utility = incentive_value * self.incentive_sensitivity

        # --- Cost of Complying (Effort) ---
        # Effort is the *inverse* of Perceived Behavioral Control.
        # High PBC (1.0) = 0 cost. Low PBC (0.1) = 0.9 cost.
        effort_cost_component = (1.0 - self.perceived_control) * tpb_config['perceived_control_weight']

        # --- Cost of NOT Complying (Fine) ---
        # This is a negative utility (disutility).
        fine_disutility = -(fine_value * p_catch) * self.fine_sensitivity

        # --- Total Utilities ---
        # Utility of Complying = Benefits - Costs
        utility_comply = (attitude_component + social_component + incentive_utility) - effort_cost_component

        # Utility of Not Complying = 0 (baseline) + any disutility (fine)
        utility_not_comply = fine_disutility

        # Store these components for data collection and analysis
        self.decision_components = {
            'attitude_benefit': attitude_component,
            'social_norm_benefit': social_component,
            'effort_cost': effort_cost_component,  # Store the cost
            'incentive_utility_perceived': incentive_utility,
            'fine_disutility_perceived': fine_disutility,
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
        4. Record incentive if compliant.
        """
        self.update_social_influence()
        utility_comply, utility_not_comply = self.calculate_compliance_utility()

        # A stochastic decision is made using a logistic function.
        # This converts the continuous utility difference into a probability (0-1),
        # allowing for non-deterministic behavior. A larger positive difference
        # makes compliance more likely.
        utility_diff = utility_comply - utility_not_comply

        # Add a small random jitter to the utility difference to ensure some stochasticity
        stochastic_factor = self.random.uniform(
            self.model.config['tpb_parameters']['stochastic_epsilon_range'][0],
            self.model.config['tpb_parameters']['stochastic_epsilon_range'][1]
        )
        utility_diff += stochastic_factor

        probability_comply = 1 / (1 + np.exp(-utility_diff * self.model.config['tpb_parameters']['utility_conversion_factor'])) # Utility conversion factor added

        self.is_compliant = self.random.random() < probability_comply
        self.total_utility = utility_comply if self.is_compliant else utility_not_comply

        # If compliant and incentives are offered, record a payout with the barangay
        if self.is_compliant and utility_comply > 0 and self.model.config['policy']['track_incentive_budget']:
            current_barangay: Barangay = self.model.get_barangay_by_id(self.barangay_id)
            current_barangay.record_incentive_payout(current_barangay.get_incentive_value())

        # Record history for trend analysis (capped at 50 steps for memory efficiency)
        self.compliance_history.append(self.is_compliant)
        if len(self.compliance_history) > 50: # Adjust length as needed
            self.compliance_history.pop(0)


class Barangay:
    """
    Represents a barangay as a container for households, a data aggregator (Reporter),
    and an implementor of LGU policies (Implementor).

    NOTE: This is NOT a MESA agent. It does not have a step() method and is not
    placed on the grid or in the scheduler. It is a helper object managed by the
    main Model class to organize agents and calculate group-level statistics.
    """

    def __init__(self, barangay_id: int, name: str, barangay_type: BarangayType, model: 'BacolodWasteModel'):
        self.barangay_id = barangay_id
        self.name = name
        self.type = barangay_type # Stores the enum directly
        self.model = model
        self.households: List[HouseholdAgent] = []

        # --- Policy Implementor Variables (Managed by LGU) ---
        # These are the actual policy parameters the LGU (model) passes down to this barangay
        self.lgu_incentive_value: float = 0.0  # ₱ value per compliant act
        self.lgu_fine_value: float = 0.0      # ₱ value per violation
        self.lgu_p_catch: float = 0.0         # Probability of getting caught for non-compliance

        # LGU Education boost values specific to this barangay (could be uniform or differentiated)
        self.lgu_education_attitude_boost: float = 0.0
        self.lgu_education_pbc_boost: float = 0.0

        # --- Barangay's Own Local Budget/Policies (Appendix E.2: "₱20 thousand budget") ---
        self.barangay_own_budget: float = model.config['barangay_parameters']['base_barangay_budget'] # e.g., 30,000 PHP
        self.incentive_payout_this_step: float = 0.0 # Track spending for reporting

        self.set_barangay_characteristics()

    def set_barangay_characteristics(self) -> None:
        """
        Loads and sets the barangay's socio-economic profile from the main config file.
        This ensures that even if default ranges are used for agent generation,
        the barangay itself retains its configured properties.
        """
        brgy_config = next((b for b in self.model.config['barangays'] if b['name'] == self.name), None)

        if not brgy_config:
            raise ValueError(f"Configuration for Barangay '{self.name}' not found in config file.")

        # Store these for agent generation in the model and for reporting
        self.income_range = brgy_config['income_range']
        self.education_range = brgy_config['education_range']
        self.has_garbage_collection = brgy_config['has_garbage_collection']
        # Add other specific characteristics if needed (e.g., population density)

    def set_lgu_policy(self, incentive_val: float, fine_val: float, p_catch: float,
                       edu_att_boost: float = 0.0, edu_pbc_boost: float = 0.0) -> None:
        """
        The LGU (model) supervisor sets the policy parameters for this barangay (implementor).
        """
        self.lgu_incentive_value = incentive_val
        self.lgu_fine_value = fine_val
        self.lgu_p_catch = p_catch
        self.lgu_education_attitude_boost = edu_att_boost
        self.lgu_education_pbc_boost = edu_pbc_boost

    def get_incentive_value(self) -> float:
        """
        Returns the effective incentive value for a household in this barangay.
        Can combine LGU incentive with local barangay incentives (e.g., ecobrick program).
        """
        # Example: LGU incentive + a small local barangay incentive if its budget allows
        # For now, let's just return the LGU's incentive value
        # In future, could add logic for barangay's own budget for incentives
        return self.lgu_incentive_value

    def get_fine_value(self) -> float:
        """Returns the effective fine value for a household in this barangay."""
        return self.lgu_fine_value

    def get_probability_of_getting_caught(self) -> float:
        """
        Returns the effective probability of getting caught for non-compliance.
        This reflects the barangay's enforcement effort (BPATs, Officials - E.2).
        """
        return self.lgu_p_catch

    def get_education_boosts(self) -> Tuple[float, float]:
        """Returns the education boosts to apply to households in this barangay."""
        return (self.lgu_education_attitude_boost, self.lgu_education_pbc_boost)

    def record_incentive_payout(self, amount: float) -> None:
        """
        Records an incentive payment by a compliant household.
        This helps track how much the LGU's incentive budget is being used.
        """
        self.incentive_payout_this_step += amount # Track for current step's reporting

    def reset_step_metrics(self) -> None:
        """Resets metrics that are specific to a single simulation step."""
        self.incentive_payout_this_step = 0.0

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
                'population': 0, 'income_std': 0, 'education_std': 0,
                'total_incentive_payout_current_step': 0.0 # NEW
            }

        incomes = [h.income_level for h in self.households]
        educations = [h.education_level for h in self.households]

        return {
            'population': len(self.households),
            'compliance_rate': self.calculate_compliance_rate(),
            'avg_income': np.mean(incomes),
            'avg_education': np.mean(educations),
            'income_std': np.std(incomes),
            'education_std': np.std(educations),
            'total_incentive_payout_current_step': self.incentive_payout_this_step # NEW
        }

    def __repr__(self) -> str:
        """Provides a user-friendly string representation of the Barangay object."""
        profile = self.get_socioeconomic_profile()
        return (f"Barangay(Name: {self.name}, Type: {self.type.value}, "
                f"Population: {profile['population']}, "
                f"Compliance: {profile['compliance_rate']:.2%})")