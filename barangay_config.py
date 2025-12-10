ANNUAL_BUDGET = 1500000
QUARTERLY_BUDGET = 375000
MIN_WAGE = 400

BARANGAY_CONFIGS = [
    {"id": 1, "name": "Bgy Poblacion", "N_HOUSEHOLDS": 800, "N_OFFICIALS": 22, "initial_compliance": 0.4, "width": 25, "height": 25, "income_profile": middle},
    {"id": 2, "name": "Bgy Rural", "N_HOUSEHOLDS": 30, "N_OFFICIALS": 1, "initial_compliance": 0.8, "width": 15, "height": 15, "income_profile": middle},
    {"id": 3, "name": "Bgy Coastal", "N_HOUSEHOLDS": 80, "N_OFFICIALS": 2, "initial_compliance": 0.3, "width": 20, "height": 20, "income_profile": middle},
    {"id": 4, "name": "Bgy 4", "N_HOUSEHOLDS": 50, "N_OFFICIALS": 2, "initial_compliance": 0.5, "width": 20, "height": 20, "income_profile": middle},
    {"id": 5, "name": "Bgy 5", "N_HOUSEHOLDS": 50, "N_OFFICIALS": 2, "initial_compliance": 0.5, "width": 20, "height": 20, "income_profile": middle},
    {"id": 6, "name": "Bgy 6", "N_HOUSEHOLDS": 50, "N_OFFICIALS": 2, "initial_compliance": 0.5, "width": 20, "height": 20, "income_profile": middle},
    {"id": 7, "name": "Bgy 7", "N_HOUSEHOLDS": 50, "N_OFFICIALS": 2, "initial_compliance": 0.5, "width": 20, "height": 20. "income_profile": middle}
]

# Behavioral Parameters (Global)
base_attitude = 0.66 # derived from Paigalan et al.(2025)
base_compliance = 0.58
training_sensitivity = 0.68