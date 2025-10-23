"""
Main script for Phase 1 ABM simulation
"""

import sys
import os

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.phase1.model import BacolodWasteModel
from src.phase1.visualization import plot_compliance_trends, plot_agent_characteristics, create_summary_dashboard
from src.phase1.utils import save_simulation_results, print_simulation_summary
from src.phase1.config import print_config_summary, CONFIG # Import CONFIG directly


def run_phase1_simulation():
    """Run the complete Phase 1 simulation (Baseline Scenario)"""
    print("🎯" + "=" * 60)
    print("PHASE 1: ABM SIMULATION FOR BACOLOD WASTE SEGREGATION (BASELINE)")
    print("=" * 60)

    # Print configuration summary
    print_config_summary()

    # Initialize model
    print("🚀 Initializing model...")
    # Use config's total households and pass config for full setup
    model = BacolodWasteModel(total_households=CONFIG['model']['total_households'], config=CONFIG)

    # Test initial compliance
    initial_compliance = model.calculate_overall_compliance()
    print(f"📈 Initial compliance rate (before policy): {initial_compliance:.2%}")

    # For the baseline, we set a 'no policy' state.
    # The LGU has a budget, but it's not actively deployed in this baseline run.
    # We pass 0 budgets for incentives, enforcement, and education.
    model.set_policy(
        budget_for_incentives=0,
        budget_for_enforcement=0,
        budget_for_education=0
    )


    # Run simulation
    print("\n🔄 Running simulation for baseline...")
    # Use simulation steps from config
    model_data, agent_data = model.run_simulation(steps=CONFIG['model']['simulation_steps'])

    # Generate outputs
    print("\n📊 Generating results and visualizations...")

    # Print summary
    print_simulation_summary(model, model_data, agent_data)

    # Create visualizations
    create_summary_dashboard(model, model_data, agent_data, "outputs/figures/phase1_baseline/")

    # Save results
    save_simulation_results(model, model_data, agent_data, "data/simulation_outputs/phase1_baseline/")

    print("\n✅ Phase 1 Baseline completed successfully!")
    return model, model_data, agent_data


def test_different_policies():
    """Test the model with different policy configurations based on LGU budget allocation."""
    print("\n🧪 Testing different policy scenarios based on LGU budget allocation...")

    # Define the total LGU budget (from Appendix E.1: ~1.5 million PHP annually)
    TOTAL_LGU_BUDGET = CONFIG['policy']['total_lgu_annual_budget']

    # Define policy scenarios as budget allocations
    # Note: These allocations should sum up to TOTAL_LGU_BUDGET (or less)
    policies = [
        # Scenario 0: Baseline (No Active Policy beyond standard operations)
        {"name": "No Active Policy", "incentive_b": 0, "enforcement_b": 0, "education_b": 0},

        # Scenario 1: Pure Incentive (Allocate full budget to incentives)
        {"name": "Pure Incentive", "incentive_b": TOTAL_LGU_BUDGET, "enforcement_b": 0, "education_b": 0},

        # Scenario 2: Pure Enforcement (Allocate full budget to enforcement)
        {"name": "Pure Enforcement", "incentive_b": 0, "enforcement_b": TOTAL_LGU_BUDGET, "education_b": 0},

        # Scenario 3: Pure Education (Allocate full budget to education)
        {"name": "Pure Education", "incentive_b": 0, "enforcement_b": 0, "education_b": TOTAL_LGU_BUDGET},

        # Scenario 4: Balanced Hybrid 1 (Equal split)
        {"name": "Balanced Hybrid 1",
         "incentive_b": TOTAL_LGU_BUDGET / 3,
         "enforcement_b": TOTAL_LGU_BUDGET / 3,
         "education_b": TOTAL_LGU_BUDGET / 3},

        # Scenario 5: Balanced Hybrid 2 (MENRO preference, e.g., more enforcement, some education)
        {"name": "Balanced Hybrid 2",
         "incentive_b": TOTAL_LGU_BUDGET * 0.2,  # 20%
         "enforcement_b": TOTAL_LGU_BUDGET * 0.6, # 60%
         "education_b": TOTAL_LGU_BUDGET * 0.2},  # 20%
    ]

    results = []

    for policy in policies:
        print(f"\n--- Testing Policy: {policy['name']} ---")
        # Initialize a new model for each policy run to ensure a clean slate
        # Use a smaller household count for quicker testing of scenarios if needed
        model = BacolodWasteModel(total_households=1200, config=CONFIG)

        # Set the policy using budget allocations
        model.set_policy(
            budget_for_incentives=policy['incentive_b'],
            budget_for_enforcement=policy['enforcement_b'],
            budget_for_education=policy['education_b']
        )

        # Run simulation for a specified number of steps (e.g., a year)
        model_data, agent_data = model.run_simulation(steps=CONFIG['model']['simulation_steps'])
        final_compliance = model.calculate_overall_compliance()

        results.append({
            'policy': policy['name'],
            'incentive_budget': policy['incentive_b'],
            'enforcement_budget': policy['enforcement_b'],
            'education_budget': policy['education_b'],
            'final_compliance': final_compliance,
            'model_data': model_data # Optionally store full data for later plotting
        })

        print(f"  Final compliance: {final_compliance:.2%}")
        # Optionally, save results for each policy if needed
        # save_simulation_results(model, model_data, agent_data, f"data/simulation_outputs/phase1_policy_{policy['name'].replace(' ', '_')}/")

    # Print policy comparison
    print("\n" + "=" * 50)
    print("POLICY COMPARISON RESULTS")
    print("=" * 50)
    for result in results:
        print(f"{result['policy']:20} : {result['final_compliance']:6.2%} "
              f"(I-Budget: {result['incentive_budget']:,.0f}, "
              f"E-Budget: {result['enforcement_budget']:,.0f}, "
              f"Ed-Budget: {result['education_budget']:,.0f})")

    # Optionally, create a comparison plot of compliance trends for all policies
    # You would need to add a function in visualization.py for this.
    # plot_policy_comparison_trends(results, "outputs/figures/phase1/policy_comparison_trends.png")

    return results


if __name__ == "__main__":
    # Run main baseline simulation
    baseline_model, baseline_model_data, baseline_agent_data = run_phase1_simulation()

    # Test different policies
    policy_results = test_different_policies()

    print("\n🎉 ABM implementation complete!")