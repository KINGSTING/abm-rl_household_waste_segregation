# barangay_config.py

# --- FINANCIAL CONSTANTS ---
ANNUAL_BUDGET = 1500000
QUARTERLY_BUDGET = 375000
MIN_WAGE = 400

# --- INCOME DISTRIBUTIONS ---
INCOME_PROFILES = {
    "low":    [0.7, 0.2, 0.1],
    "middle": [0.3, 0.5, 0.2],
    "high":   [0.1, 0.3, 0.6]
}

# --- BEHAVIORAL PARAMETERS (RE-CALIBRATED FOR 15% BASELINE) ---
# Logic Update:
# We lowered 'c_effort' to the 0.05 - 0.25 range.
# Math Check: 
#   Top Agents (High Attitude) -> Utility ~0.75. Minus Cost (0.15) = 0.60. (>0.5 PASS)
#   Avg Agents (Avg Attitude)  -> Utility ~0.50. Minus Cost (0.15) = 0.35. (<0.5 FAIL)
# This mathematically guarantees ~20% Compliance.

# barangay_config.py

# ... (Financial constants remain same) ...

# --- BEHAVIORAL PARAMETERS (STABLE BASELINE) ---
# FIX APPLIED: 
# 1. Decay rates reduced by 100x (0.02 -> 0.0005). 
#    This prevents the "Crash to Zero" seen in your graphs.
# 2. c_effort lowered significantly to allow ~15% survival rate.

BEHAVIOR_PROFILES = {
    "Poblacion": {
        "w_a": 0.65 , "w_sn": 0.4, "w_pbc": 0.5, "c_effort": 0.02, "decay": 0.0005
    },
    "Liangan_East": {
        "w_a": 0.65, "w_sn": 0.6, "w_pbc": 0.5, "c_effort": 0.03, "decay": 0.0006
    },
    "Ezperanza": {
        "w_a": 0.6, "w_sn": 0.5, "w_pbc": 0.6, "c_effort": 0.03, "decay": 0.0004
    },
    "Binuni": {
        # Riverside: Moderate/Standard profile based on Paigalan et al. (2025)
        "w_a": 0.6, "w_sn": 0.6, "w_pbc": 0.5, "c_effort": 0.02, "decay": 0.0005
    },
    "Demologan": {
        "w_a": 0.65, "w_sn": 0.5, "w_pbc": 0.5, "c_effort": 0.03, "decay": 0.0005
    },
    "Mati": {
        "w_a": 0.5, "w_sn": 0.7, "w_pbc": 0.4, "c_effort": 0.07, "decay": 0.0005
    },
    "Babalaya": {
        # Remote
        "w_a": 0.5, "w_sn": 0.6, "w_pbc": 0.5, "c_effort": 0.08, "decay": 0.0006
    }
}

# --- BARANGAY DEFINITIONS ---
BARANGAY_CONFIGS = [
    {
        "id": 0,
        "name": "Brgy Poblacion", 
        "N_HOUSEHOLDS": 1530, 
        "N_OFFICIALS": 22, 
        "initial_compliance": 0.18, # Target: ~15%
        "income_profile": "middle",
        "behavior_profile": "Poblacion"
    },
    {
        "id": 1, 
        "name": "Brgy Liangan East", 
        "N_HOUSEHOLDS": 584, 
        "N_OFFICIALS": 10, 
        "initial_compliance": 0.15, # Target: ~30-35% (Model Brgy)
        "income_profile": "middle",
        "behavior_profile": "Liangan_East"
    },
    {
        "id": 2, 
        "name": "Brgy Ezperanza", 
        "N_HOUSEHOLDS": 678, 
        "N_OFFICIALS": 2, 
        "initial_compliance": 0.15, # Target: ~5%
        "income_profile": "low",
        "behavior_profile": "Ezperanza"
    },
    {
        "id": 3, 
        "name": "Brgy Binuni", 
        "N_HOUSEHOLDS": 476, 
        "N_OFFICIALS": 2, 
        "initial_compliance": 0.15, # Target: ~10%
        "income_profile": "middle",
        "behavior_profile": "Binuni"
    },
    {
        "id": 4, 
        "name": "Brgy Babalaya", 
        "N_HOUSEHOLDS": 169, 
        "N_OFFICIALS": 2, 
        "initial_compliance": 0.1, 
        "income_profile": "middle",
        "behavior_profile": "Babalaya"
    },
    {
        "id": 5, 
        "name": "Brgy Mati", 
        "N_HOUSEHOLDS": 160, 
        "N_OFFICIALS": 2, 
        "initial_compliance": 0.10, 
        "income_profile": "middle",
        "behavior_profile": "Mati"
    },
    {
        "id": 6, 
        "name": "Brgy Demologan", 
        "N_HOUSEHOLDS": 496, 
        "N_OFFICIALS": 2, 
        "initial_compliance": 0.15, 
        "income_profile": "middle",
        "behavior_profile": "Demologan"
    }
]