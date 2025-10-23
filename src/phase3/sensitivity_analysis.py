"""
src/phase3/sensitivity_analysis.py

Performs sensitivity analysis on the core ABM (Phase 1) to understand
which parameters most influence the model's outcomes (e.g., final compliance).

Uses the SALib library for Sobol analysis.
https://salib.readthedocs.io/en/latest/
"""
import os
import numpy as np
import pandas as pd
from SALib.sample import saltelli
from SALib.analyze import sobol

# Import your core ABM
# TODO: Replace with actual import
from src.phase2.rl_environment import BacolodWasteModel


def run_abm_for_sa(abm_config: dict, n_steps: int) -> float:
    """
    A wrapper function to run the ABM with a given config
    and return a single scalar output for sensitivity analysis.

    Args:
        abm_config (dict): The configuration for the ABM, containing
                           the parameters to be varied.
        n_steps (int): How long to run the simulation.

    Returns:
        float: The mean compliance rate over the last 50 steps.
    """
    # Initialize the ABM with the specific parameters
    model = BacolodWasteModel(abm_config)

    # Apply a standard, fixed policy for the analysis
    # We want to test model parameters, not policy
    n_barangays = abm_config.get('num_barangays', 5)
    fixed_policy = np.tile([0.1, 0.1], (n_barangays, 1))
    model.update_policies(fixed_policy)

    compliance_history = []
    for _ in range(n_steps):
        model.step()
        compliance_history.append(np.mean(model.get_compliance_rates_per_barangay()))

    # Return the average compliance in the final period (e.g., last 50 steps)
    final_compliance = np.mean(compliance_history[-50:])
    return final_compliance


def main():
    """
    Main function to set up and run the Sobol sensitivity analysis.
    """
    print("--- [Sensitivity Analysis] Starting ---")

    # 1. Define the Problem
    # List the parameters of your ABM that you want to test.
    # This MUST match the parameter names your BacolodWasteModel expects
    # in its config.
    problem = {
        'num_vars': 3,
        'names': [
            'household_social_influence_weight',  # Example param 1
            'household_cost_sensitivity',  # Example param 2
            'household_perceived_control_mean'  # Example param 3
        ],
        'bounds': [
            [0.0, 1.0],  # Bounds for param 1
            [0.1, 5.0],  # Bounds for param 2
            [0.2, 0.8]  # Bounds for param 3
        ]
    }

    # 2. Generate Parameter Samples
    # We use Saltelli sampling, which is standard for Sobol analysis.
    # N is the number of samples. Total runs = N * (2D + 2)
    N = 64  # This will result in N * (2*3 + 2) = 64 * 8 = 512 model runs
    param_values = saltelli.sample(problem, N)
    print(f"Generated {len(param_values)} parameter sets for {problem['names']}")

    # 3. Run the Model for each parameter set
    n_simulation_steps = 365  # Run for 1 year
    Y = np.zeros(len(param_values))  # Array to store results

    print(f"Running {len(param_values)} simulations...")
    for i, params in enumerate(param_values):
        if i % 50 == 0:
            print(f"  ...running simulation {i}/{len(param_values)}")

        # Create a config for this specific run
        run_config = {
            'num_barangays': 5,
            'num_households_per_barangay': 50,  # Use a smaller pop for speed

            # Map the sampled parameters to the config keys
            'household_social_influence_weight': params[0],
            'household_cost_sensitivity': params[1],
            'household_perceived_control_mean': params[2]
        }

        # Run the model and store the single output
        Y[i] = run_abm_for_sa(run_config, n_simulation_steps)

    print("All simulations complete.")

    # 4. Analyze the Results
    print("Analyzing results with Sobol...")
    Si = sobol.analyze(problem, Y, print_to_console=True)

    # 5. Save Results
    # Convert results to a pandas DataFrame
    total_indices = Si['S_T']
    first_order_indices = Si['S1']

    df_sobol = pd.DataFrame({
        'parameter': problem['names'],
        'S1': first_order_indices,  # First-order (main effect)
        'S1_conf': Si['S1_conf'],
        'ST': total_indices,  # Total-order (main + interactions)
        'ST_conf': Si['ST_conf']
    })

    df_sobol = df_sobol.sort_values(by='ST', ascending=False)

    # Save to file
    output_dir = "outputs/reports"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "sensitivity_analysis_sobol.csv")
    df_sobol.to_csv(output_path, index=False)

    print(f"\n--- [Sensitivity Analysis] Complete ---")
    print(f"Results saved to {output_path}")
    print("\nFinal Sobol Indices (Total Order):")
    print(df_sobol[['parameter', 'ST']])


if __name__ == "__main__":
    main()