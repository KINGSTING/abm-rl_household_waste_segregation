import numpy as np
import random
import copy
import json
from agents.bacolod_model import BacolodModel
import barangay_config as original_config

# --- 1. DEFINE THE SEARCH SPACE (Per-Barangay) ---
# We define ranges for "General" traits and specific ranges for each Barangay type
RANGES = {
    "decay": (0.01, 0.05),
    "w_a": (0.4, 0.7),     # Attitude range
    "w_sn": (0.4, 0.7),    # Social Norm range
    "cost_urban": (0.35, 0.50), # Harder for Poblacion
    "cost_rural": (0.15, 0.35)  # Easier for others
}

BARANGAY_NAMES = [
    "Poblacion", "Liangan_East", "Ezperanza", "Binuni", 
    "Babalaya", "Mati", "Demologan"
]

def generate_random_genome():
    genome = {
        "decay": random.uniform(*RANGES["decay"]),
        "common_w_a": random.uniform(*RANGES["w_a"]),     # Base Attitude
        "common_w_sn": random.uniform(*RANGES["w_sn"]),   # Base Social Norm
    }
    
    # Generate UNIQUE modifiers for each barangay
    for name in BARANGAY_NAMES:
        # 1. Cost (Barrier)
        if name == "Poblacion":
            genome[f"{name}_cost"] = random.uniform(*RANGES["cost_urban"])
        else:
            genome[f"{name}_cost"] = random.uniform(*RANGES["cost_rural"])
            
        # 2. Personality Variation (+/- 0.05 jitter)
        # This makes each barangay slightly different in attitude/norms
        genome[f"{name}_wa_mod"] = random.uniform(-0.05, 0.05) 
        genome[f"{name}_wsn_mod"] = random.uniform(-0.05, 0.05)

    return genome

def inject_config(genome):
    new_profiles = copy.deepcopy(original_config.BEHAVIOR_PROFILES)
    
    for name in BARANGAY_NAMES:
        # If the key doesn't exist in original config, create it
        if name not in new_profiles:
            new_profiles[name] = {}
            
        # Apply Base + Modifier
        # Clamp values between 0.0 and 1.0 to stay realistic
        final_wa = max(0.1, min(0.9, genome["common_w_a"] + genome[f"{name}_wa_mod"]))
        final_wsn = max(0.1, min(0.9, genome["common_w_sn"] + genome[f"{name}_wsn_mod"]))
        
        new_profiles[name]["w_a"] = final_wa
        new_profiles[name]["w_sn"] = final_wsn
        new_profiles[name]["w_pbc"] = 0.3 # Keep constant
        new_profiles[name]["c_effort"] = genome[f"{name}_cost"]
        new_profiles[name]["decay"] = genome["decay"]
        
    return new_profiles

# --- 2. THE FITNESS FUNCTION ---
def evaluate_genome(genome, generation_id):
    model = BacolodModel(seed=42, policy_mode="status_quo", behavior_override=inject_config(genome))
    
    compliance_history = []
    # Run for 100 steps
    for _ in range(100):
        model.step()
        agents = [a for a in model.schedule.agents if hasattr(a, 'is_compliant')]
        if agents:
            comp = sum(1 for a in agents if a.is_compliant) / len(agents)
            compliance_history.append(comp)
        else:
            compliance_history.append(0)

    # --- SCORING ---
    final_compliance = np.mean(compliance_history[-10:]) 
    score = 0
    
    # TARGET: 10% - 15% (0.10 - 0.15)
    dist_from_target = abs(final_compliance - 0.125)
    
    if 0.10 <= final_compliance <= 0.16:
        score = 2000 - (dist_from_target * 10000)
    elif final_compliance < 0.10:
        score = -1000 + (final_compliance * 5000) 
    else:
        score = -1000 - ((final_compliance - 0.16) * 5000)

    # DIVERSITY BONUS (Crucial Step)
    # We calculate the Standard Deviation between barangays.
    # If they are all identical, std_dev is 0 (Penalty).
    # If they are distinct, std_dev is high (Reward).
    final_barangay_values = [b.get_local_compliance() for b in model.barangays]
    diversity = np.std(final_barangay_values)
    
    if diversity < 0.005: # Too identical
        score -= 500
    else:
        score += diversity * 2000 # Reward uniqueness

    # Stability Bonus
    volatility = np.std(compliance_history[-30:])
    score -= volatility * 1000

    print(f"   > Gen {generation_id} | Compliance: {final_compliance:.2%} | Diversity: {diversity:.4f} | Score: {score:.0f}")
    return score

# --- 3. THE EVOLUTION LOOP ---
def run_calibration(generations=8, population_size=15):
    print(f"Starting UNIQUE Calibration: {generations} gens, {population_size} pop size")
    
    population = [generate_random_genome() for _ in range(population_size)]
    best_genome = None
    best_score = -float('inf')
    
    for gen in range(generations):
        print(f"\n--- Generation {gen+1} ---")
        scored_pop = []
        
        for genome in population:
            score = evaluate_genome(genome, gen+1)
            scored_pop.append((score, genome))
            
            if score > best_score:
                best_score = score
                best_genome = genome
        
        scored_pop.sort(key=lambda x: x[0], reverse=True)
        top_score = scored_pop[0][0]
        print(f"   >>> BEST IN GEN {gen+1}: {top_score:.0f}")
        
        if gen == generations - 1:
            break

        survivors = [g for s, g in scored_pop[:population_size//2]]
        new_population = survivors[:]
        
        while len(new_population) < population_size:
            parent = random.choice(survivors)
            child = parent.copy()
            
            # Mutate
            key = random.choice(list(child.keys()))
            child[key] *= random.uniform(0.90, 1.10) # +/- 10%
            
            # Simple clamping
            if "cost" in key:
                if "Poblacion" in key: child[key] = max(0.35, min(0.55, child[key]))
                else: child[key] = max(0.15, min(0.40, child[key]))
            
            new_population.append(child)
            
        population = new_population

    print("\n--- CALIBRATION COMPLETE ---")
    print("Paste this generated config into your barangay_config.py manually.")
    
    # Helper to print the ready-to-paste dictionary
    final_config = inject_config(best_genome)
    print(json.dumps(final_config, indent=4))
    
    return best_genome

if __name__ == "__main__":
    run_calibration()