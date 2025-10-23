"""
Utility functions for Phase 1
"""

import json
import pandas as pd
import numpy as np
import os


def save_simulation_results(model, model_data, agent_data, output_dir="data/simulation_outputs/phase1_baseline/"):
    """Save simulation results to files"""

    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Save model data
    model_data.to_csv(f"{output_dir}/model_data.csv", index=False)

    # Save agent data
    agent_data.to_csv(f"{output_dir}/agent_data.csv")

    # Save model summary
    # --- MODIFIED: Updated to save new policy variables ---
    summary = {
        "total_households": len(model.households),
        "total_barangays": len(model.barangays),
        "final_overall_compliance": model.calculate_overall_compliance(),
        "simulation_steps": model.current_step,
        "final_policy_budgets": {
            "budget_for_incentives": model.budget_for_incentives,
            "budget_for_enforcement": model.budget_for_enforcement,
            "budget_for_education": model.budget_for_education
        },
        "final_policy_effects_per_step": {
            "p_catch": model.probability_of_getting_caught,
            "education_attitude_boost": model.education_attitude_boost,
            "education_pbc_boost": model.education_pbc_boost,
            "base_fine_value": model.base_fine_value,
            "base_incentive_value": model.base_incentive_value
        },
        "barangay_summary": {}
    }

    for barangay in model.barangays:
        # We get profile but convert float32 to float for JSON serialization
        profile = barangay.get_socioeconomic_profile()
        serializable_profile = {k: (float(v) if isinstance(v, (np.float32, np.float64)) else v) for k, v in profile.items()}
        summary["barangay_summary"][barangay.name] = serializable_profile

    with open(f"{output_dir}/simulation_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"💾 Results saved to {output_dir}")


def calculate_model_statistics(model_data, agent_data):
    """Calculate comprehensive statistics from simulation results"""

    stats = {}

    # Get the last step from the 'Step' level of the index
    try:
        last_step = agent_data.index.get_level_values('Step').max()
        last_step_agents = agent_data.xs(last_step, level='Step')
    except (IndexError, KeyError):
        print("Warning: Could not extract last step agent data. Agent stats will be empty.")
        last_step_agents = pd.DataFrame() # Create empty dataframe

    # Model-level statistics
    stats['final_compliance'] = model_data['Overall_Compliance'].iloc[-1]
    stats['mean_compliance'] = model_data['Overall_Compliance'].mean()
    stats['compliance_volatility'] = model_data['Overall_Compliance'].std()

    # Barangay-level final compliance
    barangay_columns = [col for col in model_data.columns if
                        col.endswith('_Compliance') and col != 'Overall_Compliance']
    for col in barangay_columns:
        stats[f'{col}_final'] = model_data[col].iloc[-1]
        stats[f'{col}_mean'] = model_data[col].mean()

    # --- MODIFIED: Added checks to prevent KeyError ---
    # Agent-level statistics
    if not last_step_agents.empty:
        stats['agent_compliance_rate'] = last_step_agents['Compliant'].mean()

        # Check for 'Income' column before calculating correlation
        if 'Income' in last_step_agents.columns:
            stats['income_compliance_correlation'] = last_step_agents[['Income', 'Compliant']].corr().iloc[0, 1]
        else:
            stats['income_compliance_correlation'] = np.nan

        # Check for 'Education' column before calculating correlation
        if 'Education' in last_step_agents.columns:
            stats['education_compliance_correlation'] = last_step_agents[['Education', 'Compliant']].corr().iloc[0, 1]
        else:
            stats['education_compliance_correlation'] = np.nan
    else:
        # Set default values if agent data is empty
        stats['agent_compliance_rate'] = 0.0
        stats['income_compliance_correlation'] = np.nan
        stats['education_compliance_correlation'] = np.nan

    return stats


def print_simulation_summary(model, model_data, agent_data):
    """Print a comprehensive summary of the simulation"""

    print("\n" + "=" * 60)
    print("SIMULATION SUMMARY")
    print("=" * 60)

    # Overall statistics
    final_compliance = model.calculate_overall_compliance()
    mean_compliance = model_data['Overall_Compliance'].mean()

    print(f"Overall Compliance: {final_compliance:.2%} (Final), {mean_compliance:.2%} (Average)")
    print(f"Total Households: {len(model.households)}")
    print(f"Simulation Steps: {model.current_step}")

    # Barangay statistics
    print("\nBarangay Performance:")
    for barangay in model.barangays:
        brgy_compliance = barangay.calculate_compliance_rate()
        profile = barangay.get_socioeconomic_profile()
        print(f"  {barangay.name:17} : {brgy_compliance:6.2%} compliance " # Adjusted spacing
              f"(Pop: {profile['population']:4d}, "
              f"Income: {profile['avg_income']:.2f}, "
              f"Education: {profile['avg_education']:.2f})")

    # Policy summary (This section was already correct from your last paste)
    print("\nPolicy Settings (Annual Budgets):")
    try:
        print(f"  Incentive Budget: ₱{model.budget_for_incentives:,.0f}")
        print(f"  Enforcement Budget: ₱{model.budget_for_enforcement:,.0f}")
        print(f"  Education Budget: ₱{model.budget_for_education:,.0f}")
        print(f"--- Translated Effects (Per Step) ---")
        print(f"  P(Catch) per step: {model.probability_of_getting_caught:.4%}")
        print(f"  Education Boost per step: {model.education_attitude_boost:.6f}")
    except AttributeError:
        print("  (Could not read policy budget variables from model)")

    # Calculate additional statistics
    stats = calculate_model_statistics(model_data, agent_data)
    print(f"\nAdditional Statistics:")
    print(f"  Compliance Volatility: {stats.get('compliance_volatility', np.nan):.4f}")
    print(f"  Income-Compliance Correlation: {stats.get('income_compliance_correlation', np.nan):.3f}")
    print(f"  Education-Compliance Correlation: {stats.get('education_compliance_correlation', np.nan):.3f}")

    print("=" * 60)