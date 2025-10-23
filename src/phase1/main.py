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
from src.phase1.config import print_config_summary


def run_phase1_simulation():
    """Run the complete Phase 1 simulation"""
    print("🎯" + "=" * 60)
    print("PHASE 1: ABM SIMULATION FOR BACOLOD WASTE SEGREGATION")
    print("=" * 60)

    # Print configuration summary
    print_config_summary()

    # Initialize model
    print("🚀 Initializing model...")
    model = BacolodWasteModel(total_households=6110)

    # Test initial compliance
    initial_compliance = model.calculate_overall_compliance()
    print(f"📈 Initial compliance rate: {initial_compliance:.2%}")

    # Run simulation
    print("\n🔄 Running simulation...")
    model_data, agent_data = model.run_simulation(steps=100)

    # Generate outputs
    print("\n📊 Generating results and visualizations...")

    # Print summary
    print_simulation_summary(model, model_data, agent_data)

    # Create visualizations
    create_summary_dashboard(model, model_data, agent_data, "outputs/figures/phase1/")

    # Save results
    save_simulation_results(model, model_data, agent_data, "data/simulation_outputs/phase1_baseline/")

    print("\n✅ Phase 1 completed successfully!")
    return model, model_data, agent_data


def test_different_policies():
    """Test the model with different policy configurations"""
    print("\n🧪 Testing different policy scenarios...")

    policies = [
        {"name": "No Policy", "incentive": 0, "fine": 0},
        {"name": "Incentive Only", "incentive": 200, "fine": 0},
        {"name": "Fine Only", "incentive": 0, "fine": 500},
        {"name": "Hybrid", "incentive": 100, "fine": 250},
    ]

    results = []

    for policy in policies:
        print(f"\nTesting: {policy['name']}")
        model = BacolodWasteModel(total_households=1200)  # Smaller for quick testing
        model.set_policy(incentive=policy['incentive'], fine=policy['fine'])

        model_data, agent_data = model.run_simulation(steps=100)
        final_compliance = model.calculate_overall_compliance()

        results.append({
            'policy': policy['name'],
            'incentive': policy['incentive'],
            'fine': policy['fine'],
            'final_compliance': final_compliance
        })

        print(f"  Final compliance: {final_compliance:.2%}")

    # Print policy comparison
    print("\n" + "=" * 50)
    print("POLICY COMPARISON RESULTS")
    print("=" * 50)
    for result in results:
        print(f"{result['policy']:15} : {result['final_compliance']:6.2%} "
              f"(Incentive: {result['incentive']:3d}, Fine: {result['fine']:3d})")

    return results


if __name__ == "__main__":
    # Run main simulation
    model, model_data, agent_data = run_phase1_simulation()

    # Test different policies
    policy_results = test_different_policies()

    print("\n🎉 ABM implementation complete!")