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

# --- BEHAVIORAL PARAMETERS (CALIBRATED) ---
# Logic: 
#   If Target Compliance is High (>70%), c_effort must be LOW (<0.15) and weights HIGH.
#   If Target Compliance is Low (<40%), c_effort must be HIGH (>0.35).

BEHAVIOR_PROFILES = {
    "Poblacion": {
        "w_a": 0.6, "w_sn": 0.6, "w_pbc": 0.4, "c_effort": 0.03, "decay": 0.001  
    },
    "Liangan_East": {
        "w_a": 0.6, "w_sn": 0.6, "w_pbc": 0.4, "c_effort": 0.05, "decay": 0.001
    },
    "Binuni": {
        # Average
        "w_a": 0.4, "w_sn": 0.3, "w_pbc": 0.3, "c_effort": 0.2, "decay": 0.005
    },
    "Demologan": {
        # Average
        "w_a": 0.4, "w_sn": 0.3, "w_pbc": 0.3, "c_effort": 0.2, "decay": 0.005
    },
    "Mati": {
        # Average
        "w_a": 0.4, "w_sn": 0.3, "w_pbc": 0.3, "c_effort": 0.2, "decay": 0.005
    },
    "Babalaya": {
        # Average
        "w_a": 0.4, "w_sn": 0.3, "w_pbc": 0.3, "c_effort": 0.2, "decay": 0.005
    },
    "Ezperanza": {
        # Low Compliance Area: High barriers to action (High c_effort)
        "w_a": 0.3, "w_sn": 0.2, "w_pbc": 0.5, "c_effort": 0.4, "decay": 0.006
    },
}

# --- BARANGAY DEFINITIONS ---
BARANGAY_CONFIGS = [
    {
        "id": 0,
        "name": "Bgy Poblacion", 
        "N_HOUSEHOLDS": 1530, 
        "N_OFFICIALS": 22, 
        "initial_compliance": 0.4, 
        "income_profile": "middle",
        "behavior_profile": "Poblacion"
    },
    {
        "id": 1, 
        "name": "Bgy Liangan East", 
        "N_HOUSEHOLDS": 584, 
        "N_OFFICIALS": 10, 
        "initial_compliance": 0.8, # TARGET: 80% (Matches Profile)
        "income_profile": "middle",
        "behavior_profile": "Liangan_East"
    },
    {
        "id": 2, 
        "name": "Bgy Ezperanza", 
        "N_HOUSEHOLDS": 678, 
        "N_OFFICIALS": 2, 
        "initial_compliance": 0.3, # TARGET: 30% (Matches Profile)
        "income_profile": "low",
        "behavior_profile": "Ezperanza"
    },
    {
        "id": 3, 
        "name": "Bgy Binuni", 
        "N_HOUSEHOLDS": 476, 
        "N_OFFICIALS": 2, 
        "initial_compliance": 0.5, 
        "income_profile": "middle",
        "behavior_profile": "Binuni"
    },
    {
        "id": 4, 
        "name": "Bgy Babalaya", 
        "N_HOUSEHOLDS": 169, 
        "N_OFFICIALS": 2, 
        "initial_compliance": 0.5, 
        "income_profile": "middle",
        "behavior_profile": "Babalaya"
    },
    {
        "id": 5, 
        "name": "Bgy Mati", 
        "N_HOUSEHOLDS": 160, 
        "N_OFFICIALS": 2, 
        "initial_compliance": 0.5, 
        "income_profile": "middle",
        "behavior_profile": "Mati"
    },
    {
        "id": 6, 
        "name": "Bgy Demologan", 
        "N_HOUSEHOLDS": 496, 
        "N_OFFICIALS": 2, 
        "initial_compliance": 0.5, 
        "income_profile": "middle",
        "behavior_profile": "Demologan"
    }
]