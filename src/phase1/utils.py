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
    summary = {
        "total_households": len(model.households),
        "total_barangays": len(model.barangays),
        "final_overall_compliance": model.calculate_overall_compliance(),
        "simulation_steps": model.current_step,
        "final_policy": {
            "incentive": model.base_incentive,
            "fine": model.base_fine
        },
        "barangay_summary": {}
    }

    for barangay in model.barangays:
        profile = barangay.get_socioeconomic_profile()
        summary["barangay_summary"][barangay.name] = profile

    with open(f"{output_dir}/simulation_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"💾 Results saved to {output_dir}")


def calculate_model_statistics(model_data, agent_data):
    """Calculate comprehensive statistics from simulation results"""

    stats = {}

    # Get the last step from the 'Step' level of the index
    last_step = agent_data.index.get_level_values('Step').max()
    last_step_agents = agent_data.xs(last_step, level='Step')

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

    # Agent-level statistics - USE THE last_step_agents WE ALREADY DEFINED ABOVE
    stats['agent_compliance_rate'] = last_step_agents['Compliant'].mean()
    stats['income_compliance_correlation'] = last_step_agents[['Income', 'Compliant']].corr().iloc[0, 1]
    stats['education_compliance_correlation'] = last_step_agents[['Education', 'Compliant']].corr().iloc[0, 1]

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
        print(f"  {barangay.name:12} : {brgy_compliance:6.2%} compliance "
              f"(Pop: {profile['population']:3d}, "
              f"Income: {profile['avg_income']:.2f}, "
              f"Education: {profile['avg_education']:.2f})")

    # Policy summary
    print(f"\nPolicy Settings:")
    print(f"  Incentive: {model.base_incentive} PHP")
    print(f"  Fine: {model.base_fine} PHP")

    # Calculate additional statistics
    stats = calculate_model_statistics(model_data, agent_data)
    print(f"\nAdditional Statistics:")
    print(f"  Compliance Volatility: {stats['compliance_volatility']:.4f}")
    print(f"  Income-Compliance Correlation: {stats['income_compliance_correlation']:.3f}")
    print(f"  Education-Compliance Correlation: {stats['education_compliance_correlation']:.3f}")

    print("=" * 60)