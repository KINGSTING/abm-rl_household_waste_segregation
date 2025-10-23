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
    axes[0, 1].legend(loc='best') # Use 'best' location
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].set_ylim(0, 1)

    # Final compliance distribution by barangay
    final_compliance = [model_data[col].iloc[-1] for col in barangay_columns]
    barangay_names = [col.replace('_Compliance', '') for col in barangay_columns]

    bars = axes[1, 0].bar(barangay_names, final_compliance, color=sns.color_palette()[:len(barangay_names)])
    axes[1, 0].set_title('Final Compliance Rate by Barangay')
    axes[1, 0].set_ylabel('Compliance Rate')
    axes[1, 0].set_ylim(0, 1)
    axes[1, 0].tick_params(axis='x', labelrotation=45) # Use 'labelrotation'

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

    # plt.show() # --- REMOVED to prevent UserWarning in non-interactive mode ---
    plt.close(fig) # Close the figure to free up memory
    return fig


def plot_agent_characteristics(agent_data, save_path=None):
    """Plot distributions of agent characteristics and their relationship with compliance"""
    set_visualization_style()

    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Agent Characteristics Analysis (Final Step)', fontsize=16)

    # Get data from the last simulation step
    try:
        last_step = agent_data.index.get_level_values('Step').max()
        last_step_data = agent_data.xs(last_step, level='Step')
    except (IndexError, KeyError):
        print("Error: Could not extract last step agent data for visualization.")
        plt.close(fig)
        return None # Return early if data is bad

    # --- Plot 1: Income distribution by compliance ---
    if 'Income' in last_step_data.columns:
        compliant_income = last_step_data[last_step_data['Compliant'] == 1]['Income']
        non_compliant_income = last_step_data[last_step_data['Compliant'] == 0]['Income']

        sns.histplot(compliant_income, ax=axes[0, 0], color='green', label='Compliant', kde=True, stat='density', alpha=0.6, binwidth=0.05)
        sns.histplot(non_compliant_income, ax=axes[0, 0], color='red', label='Non-compliant', kde=True, stat='density', alpha=0.6, binwidth=0.05)

        axes[0, 0].set_title('Income Distribution by Compliance Status')
        axes[0, 0].set_xlabel('Income Level (Normalized)')
        axes[0, 0].set_ylabel('Density')
        axes[0, 0].legend()
        axes[0, 0].set_xlim(0, 1)
    else:
        axes[0, 0].set_title('Income Distribution (Data Not Found)')

    # --- Plot 2: Education distribution by compliance ---
    if 'Education' in last_step_data.columns:
        compliant_education = last_step_data[last_step_data['Compliant'] == 1]['Education']
        non_compliant_education = last_step_data[last_step_data['Compliant'] == 0]['Education']

        sns.histplot(compliant_education, ax=axes[0, 1], color='green', label='Compliant', kde=True, stat='density', alpha=0.6, binwidth=0.05)
        sns.histplot(non_compliant_education, ax=axes[0, 1], color='red', label='Non-compliant', kde=True, stat='density', alpha=0.6, binwidth=0.05)

        axes[0, 1].set_title('Education Distribution by Compliance Status')
        axes[0, 1].set_xlabel('Education Level (Normalized)')
        axes[0, 1].set_ylabel('Density')
        axes[0, 1].legend()
        axes[0, 1].set_xlim(0, 1)
    else:
        axes[0, 1].set_title('Education Distribution (Data Not Found)')

    # --- Plot 3: Compliance rate by income quartile ---
    if 'Income' in last_step_data.columns:
        try:
            last_step_data['Income_Quartile'] = pd.qcut(last_step_data['Income'], 4,
                                                        labels=['Q1 (Low)', 'Q2', 'Q3', 'Q4 (High)'])
            income_compliance = last_step_data.groupby('Income_Quartile', observed=True)['Compliant'].mean()

            bars = axes[0, 2].bar(income_compliance.index, income_compliance.values,
                                  color=sns.color_palette("Blues", 4))
            axes[0, 2].set_title('Compliance Rate by Income Quartile')
            axes[0, 2].set_xlabel('Income Quartile')
            axes[0, 2].set_ylabel('Compliance Rate')
            axes[0, 2].set_ylim(0, 1)

            for bar, value in zip(bars, income_compliance.values):
                axes[0, 2].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                                f'{value:.1%}', ha='center', va='bottom')
        except ValueError:
             axes[0, 2].set_title('Compliance Rate by Income (Not enough data for quartiles)')
    else:
        axes[0, 2].set_title('Compliance Rate by Income (Data Not Found)')

    # --- Plot 4: Compliance rate by barangay ---
    if 'Barangay' in last_step_data.columns:
        barangay_compliance = last_step_data.groupby('Barangay')['Compliant'].mean().sort_values(ascending=False)

        sns.barplot(x=barangay_compliance.index, y=barangay_compliance.values,
                    ax=axes[1, 0], palette="viridis")

        axes[1, 0].set_title('Final Compliance Rate by Barangay')
        axes[1, 0].set_xlabel('Barangay')
        axes[1, 0].set_ylabel('Compliance Rate')
        axes[1, 0].set_ylim(0, 1)
        axes[1, 0].tick_params(axis='x', labelrotation=45)

        for i, (bar, value) in enumerate(zip(axes[1, 0].patches, barangay_compliance.values)):
            axes[1, 0].text(i, bar.get_height() + 0.02,
                            f'{value:.1%}', ha='center', va='bottom')
    else:
        axes[1, 0].set_title('Compliance Rate by Barangay (Data Not Found)')

    # --- Plot 5: Scatter plot: Income vs Education ---
    if 'Income' in last_step_data.columns and 'Education' in last_step_data.columns:
        sns.scatterplot(data=last_step_data.sample(min(len(last_step_data), 1000)), # Sample to avoid overplotting
                        x='Income', y='Education', hue='Compliant',
                        alpha=0.6, ax=axes[1, 1], palette={0: 'red', 1: 'green'})
        axes[1, 1].set_title('Income vs Education (Color: Compliance)')
        axes[1, 1].set_xlabel('Income Level')
        axes[1, 1].set_ylabel('Education Level')
        axes[1, 1].legend(title='Compliant', loc='best')
    else:
        axes[1, 1].set_title('Income vs Education (Data Not Found)')

    # --- Plot 6: Neighbors' influence ---
    if 'Neighbors_Compliance_Rate' in last_step_data.columns:
        # Jitter plot for better visibility of 0/1 data
        # Convert 'Compliant' to integer if it's not already, for consistent palette mapping
        plot_data_compliant_int = last_step_data['Compliant'].astype(int)
        sns.stripplot(x=last_step_data['Neighbors_Compliance_Rate'], y=plot_data_compliant_int,
                      ax=axes[1, 2], alpha=0.2, jitter=0.1, orient='h',
                      palette=['red', 'green'])  # Changed palette to a list

        axes[1, 2].set_title("Effect of Neighbors' Compliance on Behavior")
        axes[1, 2].set_xlabel("Observed Neighbors' Compliance Rate")
        axes[1, 2].set_ylabel('Compliant (0/1)')
        axes[1, 2].set_yticks([0, 1])
    else:
        axes[1, 2].set_title("Neighbors' Influence (Data Not Found)")

    plt.tight_layout(rect=[0, 0.03, 1, 0.96]) # Adjust for suptitle

    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"💾 Agent characteristics plot saved to {save_path}")

    # plt.show() # --- REMOVED to prevent UserWarning in non-interactive mode ---
    plt.close(fig) # Close the figure to free up memory
    return fig


def create_summary_dashboard(model, model_data, agent_data, save_dir="outputs/figures/"):
    """Create a comprehensive dashboard of simulation results"""
    os.makedirs(save_dir, exist_ok=True)

    # Create all visualizations
    plot_compliance_trends(model_data, f"{save_dir}/compliance_trends.png")
    plot_agent_characteristics(agent_data, f"{save_dir}/agent_characteristics.png")

    print(f"📊 Dashboard created and saved to {save_dir}")