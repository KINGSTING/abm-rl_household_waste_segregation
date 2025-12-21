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

# --- BEHAVIORAL PARAMETERS (HARDENED CALIBRATION) ---
# FIX APPLIED: "The 0.40 Rule"
# 1. w_a (Attitude) is capped at 0.30 - 0.40. 
#    Even with 100% IEC (Attitude=1.0), the Utility gain is only 0.40.
#    This is BELOW the 0.50 threshold, so they WON'T comply on education alone.
# 2. They need Social Norms (w_sn) or low Cost (c_effort) to bridge the gap.

BEHAVIOR_PROFILES = {
    "Poblacion": {
        # Urban: High Hassle (0.35 Cost).
        # Even if they know better (IEC), traffic/time stops them.
        "w_a": 0.65, "w_sn": 0.5, "w_pbc": 0.3, "c_effort": 0.20, "decay": 0.0028
    },
    "Liangan_East": {
        # Model Barangay: Lower Cost (0.25).
        # With IEC (0.35 boost) + Low Cost (-0.25) + Norms, they hit ~30% but not 100%.
        "w_a": 0.65, "w_sn": 0.5, "w_pbc": 0.3, "c_effort": 0.20, "decay": 0.0028
    },
    "Ezperanza": {
        # Resistant: High Cost (0.40).
        # IEC will raise them from 0% to maybe 5%, but barriers are too high.
        "w_a": 0.60, "w_sn": 0.45, "w_pbc": 0.3, "c_effort": 0.20, "decay": 0.0028
    },
    "Binuni": {
        # Riverside: Moderate.
        "w_a": 0.65, "w_sn": 0.45, "w_pbc": 0.3, "c_effort": 0.20, "decay": 0.0028
    },
    "Demologan": {
        # Transition area.
        "w_a": 0.65, "w_sn": 0.45, "w_pbc": 0.3, "c_effort": 0.2, "decay": 0.0028
    },
    "Mati": {
        # Small community.
        "w_a": 0.60, "w_sn": 0.5, "w_pbc": 0.4, "c_effort": 0.33, "decay": 0.0030
    },
    "Babalaya": {
        # Remote area.
        "w_a": 0.60, "w_sn": 0.5, "w_pbc": 0.4, "c_effort": 0.33, "decay": 0.0030
    }
}

# --- BARANGAY DEFINITIONS ---
BARANGAY_CONFIGS = [
    {
        "id": 0,
        "name": "Brgy Poblacion", 
        "N_HOUSEHOLDS": 1530, 
        "N_OFFICIALS": 0, 
        "initial_compliance": 0.13, 
        "income_profile": "middle",
        "behavior_profile": "Poblacion"
    },
    {
        "id": 1, 
        "name": "Brgy Liangan East", 
        "N_HOUSEHOLDS": 584, 
        "N_OFFICIALS": 0, 
        "initial_compliance": 0.13, 
        "income_profile": "middle",
        "behavior_profile": "Liangan_East"
    },
    {
        "id": 2, 
        "name": "Brgy Ezperanza", 
        "N_HOUSEHOLDS": 678, 
        "N_OFFICIALS": 0, 
        "initial_compliance": 0.13, 
        "income_profile": "low",
        "behavior_profile": "Ezperanza"
    },
    {
        "id": 3, 
        "name": "Brgy Binuni", 
        "N_HOUSEHOLDS": 476, 
        "N_OFFICIALS": 0, 
        "initial_compliance": 0.13, 
        "income_profile": "middle",
        "behavior_profile": "Binuni"
    },
    {
        "id": 4, 
        "name": "Brgy Babalaya", 
        "N_HOUSEHOLDS": 169, 
        "N_OFFICIALS": 0, 
        "initial_compliance": 0.13, 
        "income_profile": "middle",
        "behavior_profile": "Babalaya"
    },
    {
        "id": 5, 
        "name": "Brgy Mati", 
        "N_HOUSEHOLDS": 160, 
        "N_OFFICIALS": 0, 
        "initial_compliance": 0.13, 
        "income_profile": "middle",
        "behavior_profile": "Mati"
    },
    {
        "id": 6, 
        "name": "Brgy Demologan", 
        "N_HOUSEHOLDS": 496, 
        "N_OFFICIALS": 0, 
        "initial_compliance": 0.13, 
        "income_profile": "middle",
        "behavior_profile": "Demologan"
    }
]