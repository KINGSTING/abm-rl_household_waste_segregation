from mesa.visualization.modules import CanvasGrid, ChartModule
from mesa.visualization.UserParam import Slider
from mesa.visualization.ModularVisualization import ModularServer

from model import WasteModel
from agent import HouseholdAgent, BarangayOfficial, CollectionVehicle

def agent_portrayal(agent):
    """
    Determines how agents are rendered on the grid.
    """
    if isinstance(agent, HouseholdAgent):
        portrayal = {"Shape": "circle", "r": 0.8, "Filled": "true"}
        
        # Green = Compliant (Good Behavior)
        if agent.is_compliant:
            portrayal["Color"] = "Green"
            portrayal["Layer"] = 0
        # Red = Non-Compliant (Risk)
        else:
            portrayal["Color"] = "Red"
            portrayal["Layer"] = 0
            
        return portrayal

    elif isinstance(agent, BarangayOfficial):
        # Blue Square = Enforcement/IEC Agent
        # Layer 2 ensures it draws ON TOP of houses
        return {"Shape": "rect", "w": 0.6, "h": 0.6, "Color": "Blue", "Filled": "true", "Layer": 2}

    elif isinstance(agent, CollectionVehicle):
        # Yellow Circle = Garbage Truck
        # Layer 3 ensures it draws ON TOP of everything
        return {"Shape": "circle", "r": 0.9, "Color": "Yellow", "Filled": "true", "Layer": 3}

# --- 1. Define Visual Settings ---
# We define a fixed MAX size so the visualization doesn't break when switching Barangays.
MAX_WIDTH = 50
MAX_HEIGHT = 50

# Create the Grid Visualization Element
canvas_element = CanvasGrid(agent_portrayal, MAX_WIDTH, MAX_HEIGHT, 500, 500)

# --- 2. Define Charts ---
# Tracks the result of the TPB decisions over time
chart_element = ChartModule([
    {"Label": "ComplianceRate", "Color": "Green"},
    {"Label": "ImproperDisposal", "Color": "Black"},
], data_collector_name='datacollector')

# --- 3. Define Interactive Parameters ---
model_params = {
    # The Selector: Switches between the 7 different scenarios in barangay_config.py
    "BARANGAY_ID": Slider("Select Barangay Scenario", 1, 1, 7, 1),

    # --- TPB Policy Levers ---
    # These sliders allow you to test your Thesis Interventions in real-time
    "FINE_EFFICACY": Slider("Fine Efficacy (Social Norms)", 0.3, 0.0, 1.0, 0.1),
    "INCENTIVE_EFFICACY": Slider("Incentive Efficacy (Threshold)", 0.1, 0.0, 1.0, 0.1),
    "IEC_INTENSITY": Slider("IEC Intensity (Attitude)", 0.2, 0.0, 1.0, 0.1),
    
    # Required Fixed Dimensions for the Server
    "width": MAX_WIDTH,
    "height": MAX_HEIGHT,
}

# --- 4. Launch the Server ---
server = ModularServer(
    WasteModel, 
    [canvas_element, chart_element], 
    "Waste Policy ABM (Theory of Planned Behavior)", 
    model_params
)

server.launch(port=8521)