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

# --- BEHAVIORAL PARAMETERS (STRICTER CALIBRATION) ---
# FIX APPLIED:
# 1. Poblacion & Liangan East: Increased c_effort (0.28 - 0.32). 
#    This ensures that "Education alone" isn't enough to reach 100%. 
#    They now need Incentives or Enforcement to break the 50% barrier.
# 2. Binuni: Increased c_effort to 0.28 to stop the jump to 69%.

BEHAVIOR_PROFILES = {
    "Poblacion": {
        # Urban: High Attitude, but HIGH Cost (Traffic, Time, Space).
        # Previous: 0.25 (Too easy) -> New: 0.32
        "w_a": 0.60, "w_sn": 0.3, "w_pbc": 0.3, "c_effort": 0.32, "decay": 0.008
    },
    "Liangan_East": {
        # Model Barangay: High Norms, but we need to curb the 100% spike.
        # Previous: 0.15 (Way too easy) -> New: 0.25
        "w_a": 0.65, "w_sn": 0.5, "w_pbc": 0.4, "c_effort": 0.4, "decay": 0.008
    },
    "Ezperanza": {
        # Resistant: Very High Cost. (Your data showed 0%, which is realistic).
        # Kept strict.
        "w_a": 0.64, "w_sn": 0.2, "w_pbc": 0.2, "c_effort": 0.35, "decay": 0.008
    },
    "Binuni": {
        # Riverside: Moderate.
        # Previous: 0.22 -> New: 0.28 (To lower the 69% spike)
        "w_a": 0.61, "w_sn": 0.3, "w_pbc": 0.3, "c_effort": 0.28, "decay": 0.008
    },
    "Demologan": {
        # Transition area. (Your data showed ~10%, which is good/realistic).
        "w_a": 0.62, "w_sn": 0.3, "w_pbc": 0.3, "c_effort": 0.35, "decay": 0.008
    },
    "Mati": {
        # Small community. (Data showed ~8%, good).
        "w_a": 0.64, "w_sn": 0.5, "w_pbc": 0.3, "c_effort": 0.8, "decay": 0.008
    },
    "Babalaya": {
        # Remote area. (Data showed ~2%, good).
        "w_a": 0.63, "w_sn": 0.3, "w_pbc": 0.3, "c_effort": 0.30, "decay": 0.008
    }
}

# --- BARANGAY DEFINITIONS ---
BARANGAY_CONFIGS = [
    {
        "id": 0,
        "name": "Brgy Poblacion", 
        "N_HOUSEHOLDS": 1530, 
        "N_OFFICIALS": 0, 
        "initial_compliance": 0.15, 
        "income_profile": "middle",
        "behavior_profile": "Poblacion"
    },
    {
        "id": 1, 
        "name": "Brgy Liangan East", 
        "N_HOUSEHOLDS": 584, 
        "N_OFFICIALS": 0, 
        "initial_compliance": 0.10,
        "income_profile": "middle",
        "behavior_profile": "Liangan_East"
    },
    {
        "id": 2, 
        "name": "Brgy Ezperanza", 
        "N_HOUSEHOLDS": 678, 
        "N_OFFICIALS": 0, 
        "initial_compliance": 0.1,
        "income_profile": "low",
        "behavior_profile": "Ezperanza"
    },
    {
        "id": 3, 
        "name": "Brgy Binuni", 
        "N_HOUSEHOLDS": 476, 
        "N_OFFICIALS": 0, 
        "initial_compliance": 0.15, 
        "income_profile": "middle",
        "behavior_profile": "Binuni"
    },
    {
        "id": 4, 
        "name": "Brgy Babalaya", 
        "N_HOUSEHOLDS": 169, 
        "N_OFFICIALS": 0, 
        "initial_compliance": 0.10, 
        "income_profile": "middle",
        "behavior_profile": "Babalaya"
    },
    {
        "id": 5, 
        "name": "Brgy Mati", 
        "N_HOUSEHOLDS": 160, 
        "N_OFFICIALS": 0, 
        "initial_compliance": 0.10, 
        "income_profile": "middle",
        "behavior_profile": "Mati"
    },
    {
        "id": 6, 
        "name": "Brgy Demologan", 
        "N_HOUSEHOLDS": 496, 
        "N_OFFICIALS": 0, 
        "initial_compliance": 0.15, 
        "income_profile": "middle",
        "behavior_profile": "Demologan"
    }
]