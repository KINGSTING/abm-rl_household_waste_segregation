# barangay_config.py

# --- FINANCIAL CONSTANTS ---
ANNUAL_BUDGET = 1500000
QUARTERLY_BUDGET = 375000
MIN_WAGE = 400

# --- INCOME DISTRIBUTIONS (Probabilities for Low, Mid, High) ---
# Format: [Prob_Low, Prob_Mid, Prob_High]
INCOME_PROFILES = {
    "low":    [0.7, 0.2, 0.1],
    "middle": [0.3, 0.5, 0.2],
    "high":   [0.1, 0.3, 0.6]
}

# --- BARANGAY DEFINITIONS ---
BARANGAY_CONFIGS = [
    {
        "id": 0,
        "name": "Bgy Poblacion", 
        "N_HOUSEHOLDS": 1530, 
        "N_OFFICIALS": 22, 
        "initial_compliance": 0.4, 
        "width": 50, 
        "height": 50, 
        "income_profile": "middle"
    },
    {
        "id": 1, 
        "name": "Bgy Lingan_East", 
        "N_HOUSEHOLDS": 584, 
        "N_OFFICIALS": 10, 
        "initial_compliance": 0.8, 
        "width": 50, 
        "height": 50, 
        "income_profile": "middle"
    },
    {
        "id": 2, 
        "name": "Bgy Ezperanza", 
        "N_HOUSEHOLDS": 678, 
        "N_OFFICIALS": 2, 
        "initial_compliance": 0.3, 
        "width": 50, 
        "height": 50, 
        "income_profile": "middle"
    },
    {
        "id": 3, 
        "name": "Bgy Binuni", 
        "N_HOUSEHOLDS": 476, 
        "N_OFFICIALS": 2, 
        "initial_compliance": 0.5, 
        "width": 50, 
        "height": 50, 
        "income_profile": "middle"
    },
    {
        "id": 4, 
        "name": "Bgy Babalaya", 
        "N_HOUSEHOLDS": 169, 
        "N_OFFICIALS": 2, 
        "initial_compliance": 0.5, 
        "width": 25, 
        "height": 25, 
        "income_profile": "middle"
    },
    {
        "id": 5, 
        "name": "Bgy Mati", 
        "N_HOUSEHOLDS": 160, 
        "N_OFFICIALS": 2, 
        "initial_compliance": 0.5, 
        "width": 20, 
        "height": 20, 
        "income_profile": "middle"
    },
    {
        "id": 6, 
        "name": "Bgy Demologan", 
        "N_HOUSEHOLDS": 496, 
        "N_OFFICIALS": 2, 
        "initial_compliance": 0.5, 
        "width": 20, 
        "height": 20, 
        "income_profile": "middle"
    }
]

# --- BEHAVIORAL PARAMETERS ---
GLOBAL_PARAMS = {
    "base_attitude": 0.66,          # Paigalan et al.(2025)
    "base_compliance": 0.58,
    "training_sensitivity": 0.68
}
