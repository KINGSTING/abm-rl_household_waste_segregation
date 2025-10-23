"""
src/phase2/rl_environment.py

Implements the RL environment wrapper for the Waste Segregation ABM.
This class, `WastePolicyEnv`, follows the gymnasium.Env interface.
It connects the RL agent (the policymaker) with the ABM (the simulation).

-   **Agent:** The RL agent is the Municipality/LGU.
-   **Action:** A vector of policy decisions (e.g., info campaign intensity,
    enforcement level) for EACH barangay.
-   **Observation:** The current state of the system (e.g., compliance rates
    per barangay).
-   **Reward:** A function balancing compliance (positive) and policy cost (negative).
"""

import gymnasium as gym
import numpy as np
from gymnasium.spaces import Box, Dict
from typing import Optional, Dict as GymDict, Any

# --- Placeholder Import ---
# This class (BacolodWasteModel) is expected to be defined in Phase 1.
# We'll mock it for now so this file is self-contained for development.
# TODO: Replace this with the actual import:
from src.phase1.model import BacolodWasteModel

class BacolodWasteModel:
    """
    A placeholder/mock for the ABM from Phase 1.
    This allows us to develop the RL environment logic independently.
    """
    def __init__(self, config: dict):
        self.num_barangays = config.get('num_barangays', 5)
        self.num_households_per_barangay = config.get('num_households_per_barangay', 100)
        self.current_policies = np.zeros((self.num_barangays, 2))
        self.compliance_rates = np.zeros(self.num_barangays)
        self.rng = np.random.default_rng()
        print(f"[MockABM] Initialized with {self.num_barangays} barangays.")

    def update_policies(self, policy_action: np.ndarray):
        """ The RL agent calls this to set the new policies in the ABM. """
        self.current_policies = policy_action
        # In a real model, this would update parameters for HouseholdAgents
        # (e.g., their TPB model inputs)

    def step(self):
        """
        Run one simulation step (e.g., one day) of the ABM.
        The households make decisions based on self.current_policies.
        """
        # --- Mock Logic ---
        # Simulate that compliance slowly increases with higher policies
        # and has some randomness.
        policy_effect = (self.current_policies[:, 0] + self.current_policies[:, 1]) / 2
        noise = self.rng.normal(0, 0.01, self.num_barangays)

        # Compliance drifts towards the policy effect
        self.compliance_rates += (policy_effect - self.compliance_rates) * 0.05 + noise
        self.compliance_rates = np.clip(self.compliance_rates, 0.0, 1.0)
        # --- End Mock Logic ---

    def get_compliance_rates_per_barangay(self) -> np.ndarray:
        """ Returns the current average compliance for each barangay. """
        return self.compliance_rates

    def reset(self):
        """ Resets the simulation to its initial state. """
        self.compliance_rates = np.zeros(self.num_barangays)
        self.current_policies = np.zeros((self.num_barangays, 2))
        print("[MockABM] Reset.")

    def close(self):
        """ Any cleanup. """
        print("[MockABM] Closed.")
# --- End Placeholder Import ---


class WastePolicyEnv(gym.Env):
    """
    A Gymnasium Environment for Optimizing Waste Segregation Policy.

    This environment wraps the `BacolodWasteModel` ABM. The RL agent
    interacts with this environment to learn an optimal policy.
    """
    metadata = {'render_modes': ['human', 'ansi']}

    def __init__(self, config: dict, abm_model: BacolodWasteModel = None):
        """
        Initializes the RL environment.

        Args:
            config (dict): A configuration dictionary containing parameters for
                           the environment and the underlying ABM.
            abm_model (BacolodWasteModel, optional): An already-initialized ABM.
                           If None, one will be created using the config.
        """
        super().__init__()
        self.config = config

        # --- Core Simulation Parameters ---
        self.num_barangays = int(config.get('num_barangays', 5))

        # How many ABM steps (e.g., days) to run per single RL step (e.g., quarter)
        self.abm_steps_per_rl_step = int(config.get('abm_steps_per_rl_step', 90))

        # How many RL steps (e.g., quarters) compose one full episode
        self.max_rl_steps = int(config.get('max_rl_steps', 20)) # e.g., 20 quarters = 5 years

        # --- Reward Function Parameters ---
        self.compliance_weight = config.get('compliance_weight', 1000.0)
        self.cost_weight = config.get('cost_weight', 1.0)
        self.info_cost_factor = config.get('info_cost_factor', 100.0)      # Cost per unit of info policy
        self.enforcement_cost_factor = config.get('enforcement_cost_factor', 200.0) # Cost per unit of enforcement

        # --- Define Action Space ---
        # The agent chooses 2 continuous values for each barangay:
        # [:, 0] = Information Campaign Intensity (0.0 to 1.0)
        # [:, 1] = Enforcement Level (0.0 to 1.0)
        self.action_space = Box(
            low=0.0,
            high=1.0,
            shape=(self.num_barangays, 2),
            dtype=np.float32
        )

        # --- Define Observation Space ---
        # The agent observes the state of all barangays. We use a Dict
        # space for clarity.
        self.observation_space = Dict({
            # Current compliance rate for each barangay
            "compliance_rates": Box(
                low=0.0, high=1.0, shape=(self.num_barangays,), dtype=np.float32
            ),
            # The policy currently in effect (the last action taken)
            "current_policies": Box(
                low=0.0, high=1.0, shape=(self.num_barangays, 2), dtype=np.float32
            )
        })

        # --- Initialize the ABM ---
        if abm_model:
            self.abm = abm_model
        else:
            abm_config = config.get('abm_config', {'num_barangays': self.num_barangays})
            self.abm = BacolodWasteModel(abm_config)

        # Internal step counter
        self.current_rl_step = 0
        self.last_action = np.zeros((self.num_barangays, 2), dtype=np.float32)

        print(f"[WastePolicyEnv] Initialized.")
        print(f"  - Barangays: {self.num_barangays}")
        print(f"  - ABM steps/RL step: {self.abm_steps_per_rl_step}")
        print(f"  - Max RL steps/episode: {self.max_rl_steps}")


    def _get_obs(self) -> GymDict[str, np.ndarray]:
        """
        Gathers the current observation from the ABM.
        """
        compliance = self.abm.get_compliance_rates_per_barangay()
        return {
            "compliance_rates": compliance.astype(np.float32),
            "current_policies": self.last_action.astype(np.float32)
        }

    def _calculate_reward(self, obs: GymDict[str, np.ndarray], action: np.ndarray) -> (float, dict):
        """
        Calculates the reward based on the action taken and the resulting state.
        Reward = (Weighted Compliance) - (Weighted Cost)
        """
        # 1. Calculate weighted compliance
        # We use the mean compliance across all barangays
        mean_compliance = np.mean(obs["compliance_rates"])
        compliance_reward = self.compliance_weight * mean_compliance

        # 2. Calculate weighted cost
        # Cost is the sum of all policy actions, scaled by their cost factors
        info_cost = np.sum(action[:, 0]) * self.info_cost_factor
        enforcement_cost = np.sum(action[:, 1]) * self.enforcement_cost_factor
        total_cost = info_cost + enforcement_cost
        cost_penalty = self.cost_weight * total_cost

        # 3. Final Reward
        reward = compliance_reward - cost_penalty

        info = {
            "reward_compliance": compliance_reward,
            "penalty_cost": cost_penalty,
            "total_cost": total_cost,
            "mean_compliance": mean_compliance
        }
        return reward, info


    def reset(self, *, seed: Optional[int] = None, options: Optional[dict] = None) -> (GymDict[str, np.ndarray], dict):
        """
        Resets the environment to an initial state.
        """
        # Seed the random number generator
        super().reset(seed=seed)

        # Reset the underlying ABM
        self.abm.reset()

        # Reset internal counters
        self.current_rl_step = 0
        self.last_action = np.zeros((self.num_barangays, 2), dtype=np.float32)

        # Get the initial observation
        obs = self._get_obs()
        info = {} # No extra info on reset

        if self.config.get('verbose', False):
            print(f"[WastePolicyEnv] Environment Reset.")

        return obs, info

    def step(self, action: np.ndarray) -> (GymDict[str, np.ndarray], float, bool, bool, dict):
        """
        Advances the environment by one RL time step.

        1.  Applies the `action` (policy) to the ABM.
        2.  Runs the ABM for `abm_steps_per_rl_step` (e.g., 90 days).
        3.  Gathers the new observation (compliance rates).
        4.  Calculates the reward for this period.
        5.  Checks if the episode is done.

        Args:
            action (np.ndarray): The policy action from the RL agent.

        Returns:
            (observation, reward, terminated, truncated, info)
        """
        # 1. Apply the new policy to the ABM
        self.abm.update_policies(action)
        self.last_action = action

        # 2. Run the ABM simulation for the specified number of micro-steps
        for _ in range(self.abm_steps_per_rl_step):
            self.abm.step()

        # 3. Get the new observation from the ABM
        obs = self._get_obs()

        # 4. Calculate the reward
        reward, reward_info = self._calculate_reward(obs, action)

        # 5. Check for termination
        self.current_rl_step += 1
        terminated = self.current_rl_step >= self.max_rl_steps
        truncated = False # We don't have an early truncation condition

        # 6. Compile info dictionary
        info = {
            "rl_step": self.current_rl_step,
            **reward_info  # Include components of reward
        }

        if self.config.get('verbose', False):
            print(f"[WastePolicyEnv] Step {self.current_rl_step}")
            print(f"  - Action (Mean): Info={np.mean(action[:,0]):.2f}, Enforce={np.mean(action[:,1]):.2f}")
            print(f"  - Obs (Mean): Compliance={info['mean_compliance']:.3f}")
            print(f"  - Reward: {reward:.2f} (Compliance: {info['reward_compliance']:.2f}, Cost: -{info['penalty_cost']:.2f})")

        return obs, reward, terminated, truncated, info

    def render(self, mode: str = 'human') -> None:
        """
        Renders the current state of the environment.
        """
        if mode == 'human' or mode == 'ansi':
            obs = self.abg.get_compliance_rates_per_barangay()
            mean_compliance = np.mean(obs)

            print(f"--- RL Step {self.current_rl_step} / {self.max_rl_steps} ---")
            print(f"  Overall Compliance: {mean_compliance:.3f}")
            print(f"  Compliance by Barangay: {[round(c, 3) for c in obs]}")
            print(f"  Last Policies (Info):   {[round(p, 2) for p in self.last_action[:, 0]]}")
            print(f"  Last Policies (Enforce): {[round(p, 2) for p in self.last_action[:, 1]]}")
        else:
            super().render(mode=mode)

    def close(self):
        """
        Cleans up any open resources.
        """
        self.abm.close()
        print("[WastePolicyEnv] Closed.")


# --- Main block for testing ---
if __name__ == "__main__":
    """
    This block allows you to run this file directly to test the environment.
    It uses the `env_checker` utility from Gymnasium to ensure your
    environment is compliant with the API.
    """
    from gymnasium.utils.env_checker import check_env

    print("--- [1] Initializing Environment ---")
    env_config = {
        'num_barangays': 3,          # A smaller number for testing
        'abm_steps_per_rl_step': 30, # 30 days
        'max_rl_steps': 10,          # 10 months
        'compliance_weight': 1000.0,
        'cost_weight': 1.0,
        'info_cost_factor': 50.0,
        'enforcement_cost_factor': 100.0,
        'verbose': True,
        'abm_config': {
             'num_barangays': 3,
             'num_households_per_barangay': 50
        }
    }
    env = WastePolicyEnv(env_config)

    print("\n--- [2] Running Environment Checker ---")
    # This check is crucial. It will raise errors if your
    # spaces, reset, or step methods are not implemented correctly.
    try:
        check_env(env)
        print("✅ Gymnasium API Compliance Check PASSED!")
    except Exception as e:
        print(f"❌ Gymnasium API Compliance Check FAILED: {e}")


    print("\n--- [3] Running a Manual Episode ---")
    obs, info = env.reset()
    print(f"Initial Observation: {obs}")

    terminated = False
    total_reward = 0

    while not terminated:
        # Take a random action
        action = env.action_space.sample()

        # Take a step
        obs, reward, terminated, truncated, info = env.step(action)

        total_reward += reward

        if terminated or truncated:
            print("Episode finished.")
            break

    print(f"\nEpisode complete after {info['rl_step']} steps.")
    print(f"Total Reward: {total_reward:.2f}")
    env.close()