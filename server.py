from mesa.visualization.modules import CanvasGrid, ChartModule
from mesa.visualization.UserParam import Slider, NumberInput 
from mesa.visualization.ModularVisualization import ModularServer

from model import WasteModel
from agent import HouseholdAgent, BarangayOfficial, CollectionVehicle

def agent_portrayal(agent):
    if isinstance(agent, HouseholdAgent):
        portrayal = {"Shape": "circle", "r": 0.8, "Filled": "true"}
        
        if agent.improper_disposed:
            portrayal["Color"] = "Black"
            portrayal["Layer"] = 2
        elif agent.is_compliant:
            portrayal["Color"] = "Green"
            portrayal["Layer"] = 0
        else:
            portrayal["Color"] = "Red"
            portrayal["Layer"] = 1
            
        return portrayal

    elif isinstance(agent, BarangayOfficial):
        return {"Shape": "rect", "w": 0.5, "h": 0.5, "Color": "Blue", "Filled": "true", "Layer": 3}

    elif isinstance(agent, CollectionVehicle):
        return {"Shape": "circle", "r": 0.9, "Color": "Yellow", "Filled": "true", "Layer": 4}

# --- 1. Define the Visualization Grid ---
# IMPORTANT: This must be large enough to fit your LARGEST Barangay config.
# If Barangay 1 is 30x30, set this to 30. Smaller barangays will just look smaller on the canvas.
MAX_GRID_WIDTH = 40
MAX_GRID_HEIGHT = 40
canvas_element = CanvasGrid(agent_portrayal, MAX_GRID_WIDTH, MAX_GRID_HEIGHT, 500, 500)

# --- 2. Define the Charts ---
chart_element = ChartModule([
    {"Label": "ComplianceRate", "Color": "Green"},
    {"Label": "ImproperDisposal", "Color": "Black"},
], data_collector_name='datacollector')

# --- 3. Define the Interactive Parameters ---
model_params = {
    # --- THE SELECTOR ---
    # This Slider allows you to switch between Barangay 1, 2, 3...
    # When you change this and click 'Reset', the model reloads with that Barangay's config.
    "BARANGAY_ID": Slider("Select Barangay Scenario", 1, 1, 7, 1),

    # --- Policy Levers (Global) ---
    "FINE_EFFICACY": Slider("Fine Efficacy", 0.3, 0.0, 1.0, 0.1),
    "INCENTIVE_EFFICACY": Slider("Incentive Efficacy", 0.1, 0.0, 1.0, 0.1),
    "IEC_INTENSITY": Slider("IEC Intensity", 0.2, 0.0, 1.0, 0.1),
    
    # --- REMOVED: N_HOUSEHOLDS, N_OFFICIALS, etc. ---
    # These are now determined automatically by the BARANGAY_ID in model.py
    
    # Fixed Grid Size (Required by ModularServer, but model uses its own config)
    "width": MAX_GRID_WIDTH,
    "height": MAX_GRID_HEIGHT,
}

# --- 4. Launch the Server ---
server = ModularServer(
    WasteModel, 
    [canvas_element, chart_element], 
    "ABM Waste Policy: Barangay Selector Mode", 
    model_params
)

server.launch(port=8521)