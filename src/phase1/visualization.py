"""
Visualization functions for Phase 1 ABM
"""

# Set the backend BEFORE importing pyplot
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os


def set_visualization_style():
    """Set consistent visualization style"""
    plt.style.use('default')
    sns.set_palette("colorblind")
    plt.rcParams['figure.figsize'] = (12, 8)
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.titlesize'] = 14
    plt.rcParams['axes.labelsize'] = 12


def plot_compliance_trends(model_data, save_path=None):
    """Plot compliance trends over time"""
    set_visualization_style()

    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    # Overall compliance trend
    axes[0, 0].plot(model_data['Step'], model_data['Overall_Compliance'], linewidth=2)
    axes[0, 0].set_title('Overall Compliance Rate Over Time')
    axes[0, 0].set_xlabel('Simulation Step')
    axes[0, 0].set_ylabel('Compliance Rate')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].set_ylim(0, 1)

    # Barangay-level compliance trends
    barangay_columns = [col for col in model_data.columns if
                        col.endswith('_Compliance') and col != 'Overall_Compliance']

    for col in barangay_columns:
        barangay_name = col.replace('_Compliance', '')
        axes[0, 1].plot(model_data['Step'], model_data[col], label=barangay_name, linewidth=2)

    axes[0, 1].set_title('Compliance Rate by Barangay')
    axes[0, 1].set_xlabel('Simulation Step')
    axes[0, 1].set_ylabel('Compliance Rate')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].set_ylim(0, 1)

    # Final compliance distribution by barangay
    final_compliance = [model_data[col].iloc[-1] for col in barangay_columns]
    barangay_names = [col.replace('_Compliance', '') for col in barangay_columns]

    bars = axes[1, 0].bar(barangay_names, final_compliance, color=sns.color_palette()[:len(barangay_names)])
    axes[1, 0].set_title('Final Compliance Rate by Barangay')
    axes[1, 0].set_ylabel('Compliance Rate')
    axes[1, 0].set_ylim(0, 1)

    # Add value labels on bars
    for bar, value in zip(bars, final_compliance):
        axes[1, 0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                        f'{value:.1%}', ha='center', va='bottom')

    # Compliance distribution histogram
    overall_final = model_data['Overall_Compliance'].iloc[-1]
    axes[1, 1].axvline(overall_final, color='red', linestyle='--', linewidth=2, label=f'Overall: {overall_final:.1%}')
    axes[1, 1].hist(final_compliance, bins=10, alpha=0.7, edgecolor='black')
    axes[1, 1].set_title('Distribution of Final Barangay Compliance Rates')
    axes[1, 1].set_xlabel('Compliance Rate')
    axes[1, 1].set_ylabel('Frequency')
    axes[1, 1].legend()
    axes[1, 1].set_xlim(0, 1)

    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"💾 Compliance trends plot saved to {save_path}")

    plt.show()
    return fig


def plot_agent_characteristics(agent_data, save_path=None):
    """Plot distributions of agent characteristics and their relationship with compliance"""
    set_visualization_style()

    fig, axes = plt.subplots(2, 3, figsize=(18, 12))

    # Get data from the last simulation step
    last_step = agent_data.index.get_level_values('Step').max()
    last_step_data = agent_data.xs(last_step, level='Step')

    # Income distribution by compliance
    compliant_income = last_step_data[last_step_data['Compliant'] == 1]['Income']
    non_compliant_income = last_step_data[last_step_data['Compliant'] == 0]['Income']

    axes[0, 0].hist([compliant_income, non_compliant_income],
                    bins=20, alpha=0.7, label=['Compliant', 'Non-compliant'],
                    color=['green', 'red'])
    axes[0, 0].set_title('Income Distribution by Compliance Status')
    axes[0, 0].set_xlabel('Income Level')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].legend()

    # Education distribution by compliance
    compliant_education = last_step_data[last_step_data['Compliant'] == 1]['Education']
    non_compliant_education = last_step_data[last_step_data['Compliant'] == 0]['Education']

    axes[0, 1].hist([compliant_education, non_compliant_education],
                    bins=20, alpha=0.7, label=['Compliant', 'Non-compliant'],
                    color=['green', 'red'])
    axes[0, 1].set_title('Education Distribution by Compliance Status')
    axes[0, 1].set_xlabel('Education Level')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].legend()

    # Compliance rate by income quartile
    last_step_data['Income_Quartile'] = pd.qcut(last_step_data['Income'], 4,
                                                labels=['Q1 (Low)', 'Q2', 'Q3', 'Q4 (High)'])
    income_compliance = last_step_data.groupby('Income_Quartile')['Compliant'].mean()

    bars = axes[0, 2].bar(income_compliance.index, income_compliance.values,
                          color=sns.color_palette("Blues", 4))
    axes[0, 2].set_title('Compliance Rate by Income Quartile')
    axes[0, 2].set_xlabel('Income Quartile')
    axes[0, 2].set_ylabel('Compliance Rate')
    axes[0, 2].set_ylim(0, 1)

    for bar, value in zip(bars, income_compliance.values):
        axes[0, 2].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                        f'{value:.1%}', ha='center', va='bottom')

    # Compliance rate by barangay
    barangay_compliance = last_step_data.groupby('Barangay')['Compliant'].mean()
    bars = axes[1, 0].bar(barangay_compliance.index, barangay_compliance.values,
                          color=sns.color_palette("viridis", len(barangay_compliance)))
    axes[1, 0].set_title('Compliance Rate by Barangay')
    axes[1, 0].set_xlabel('Barangay')
    axes[1, 0].set_ylabel('Compliance Rate')
    axes[1, 0].set_ylim(0, 1)
    axes[1, 0].tick_params(axis='x', rotation=45)

    for bar, value in zip(bars, barangay_compliance.values):
        axes[1, 0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                        f'{value:.1%}', ha='center', va='bottom')

    # Scatter plot: Income vs Education colored by compliance
    scatter = axes[1, 1].scatter(last_step_data['Income'], last_step_data['Education'],
                                 c=last_step_data['Compliant'], alpha=0.6, cmap='coolwarm')
    axes[1, 1].set_title('Income vs Education (Color: Compliance)')
    axes[1, 1].set_xlabel('Income Level')
    axes[1, 1].set_ylabel('Education Level')
    plt.colorbar(scatter, ax=axes[1, 1], label='Compliant (0/1)')

    # Neighbors' influence
    axes[1, 2].scatter(last_step_data['Neighbors_Compliance_Rate'], last_step_data['Compliant'],
                       alpha=0.5)
    axes[1, 2].set_title("Effect of Neighbors' Compliance on Behavior")
    axes[1, 2].set_xlabel("Neighbors' Compliance Rate")
    axes[1, 2].set_ylabel('Compliant (0/1)')
    axes[1, 2].set_yticks([0, 1])

    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"💾 Agent characteristics plot saved to {save_path}")

    plt.show()
    return fig


def create_summary_dashboard(model, model_data, agent_data, save_dir="outputs/figures/"):
    """Create a comprehensive dashboard of simulation results"""
    os.makedirs(save_dir, exist_ok=True)

    # Create all visualizations
    plot_compliance_trends(model_data, f"{save_dir}/compliance_trends.png")
    plot_agent_characteristics(agent_data, f"{save_dir}/agent_characteristics.png")

    print(f"📊 Dashboard created and saved to {save_dir}")