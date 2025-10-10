"""
Configuration loader for Phase 1 ABM parameters
"""

# src/phase1/config.py
import yaml
from pathlib import Path


def load_config():
    """Load configuration from YAML file using an absolute path"""
    # Get the root directory of your project (two levels up from this file)
    project_root = Path(__file__).parent.parent.parent
    # Build the full path to the config file
    config_path = project_root / "config" / "model_parameters.yaml"

    # Convert to absolute path and resolve any ".." or "."
    config_path = config_path.resolve()

    print(f"🕵️ Looking for config at: {config_path}")  # Helpful debug print
    print(f"📁 Does the path exist? {config_path.exists()}")  # Check if file is found

    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        print("✅ Configuration loaded successfully")
        return config
    except FileNotFoundError:
        print(f"❌ Config file not found at {config_path}")
        raise
    except yaml.YAMLError as e:
        print(f"❌ Error parsing YAML config: {e}")
        raise


# Global config instance
CONFIG = load_config()

def get_barangay_config(barangay_name):
    """Get configuration for a specific barangay"""
    for brgy in CONFIG['barangays']:
        if brgy['name'] == barangay_name:
            return brgy
    raise ValueError(f"Barangay {barangay_name} not found in configuration")

def print_config_summary():
    """Print a summary of the loaded configuration"""
    print("\n" + "="*50)
    print("PHASE 1 CONFIGURATION SUMMARY")
    print("="*50)
    print(f"Total households: {CONFIG['model']['total_households']}")
    print(f"Simulation steps: {CONFIG['model']['simulation_steps']}")
    print(f"Barangays: {[brgy['name'] for brgy in CONFIG['barangays']]}")
    print(f"TPB Weights - Attitude: {CONFIG['tpb_parameters']['attitude_weight']}, "
          f"Social Norm: {CONFIG['tpb_parameters']['subjective_norm_weight']}, "
          f"Control: {CONFIG['tpb_parameters']['perceived_control_weight']}")
    print("="*50 + "\n")

if __name__ == "__main__":
    print_config_summary()