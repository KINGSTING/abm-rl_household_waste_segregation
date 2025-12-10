import mesa
from mesa.visualization.modules import CanvasGrid, ChartModule, TextElement
from mesa.visualization.ModularVisualization import ModularServer

# Import your model and agents
from bacolod_model import BacolodModel
from household_agent import HouseholdAgent
from enforcement_agent import EnforcementAgent
from barangay_agent import BarangayAgent

# --- 1. Define How Agents Look ---
def agent_portrayal(agent):
    """
    Determines the color, shape, and size of agents on the grid.
    """
    if agent is None:
        return

    portrayal = {}

    # --- Household Agents ---
    if isinstance(agent, HouseholdAgent):
        portrayal["Shape"] = "circle"
        portrayal["Filled"] = "true"
        portrayal["r"] = 0.5
        portrayal["Layer"] = 0
        
        # Color Logic: Green if Compliant, Red if Non-Compliant
        if agent.is_compliant:
            portrayal["Color"] = "green"
            portrayal["r"] = 0.4 # Slightly smaller for neatness
        else:
            portrayal["Color"] = "red"
            # If they have improperly disposed garbage (Black state), make them darker
            if agent.improper_disposed:
                portrayal["Color"] = "black"

        # Optional: Tooltip to see details when hovering
        portrayal["text"] = f"U:{agent.utility:.2f}"
        portrayal["text_color"] = "white"

    # --- Enforcement Agents ---
    elif isinstance(agent, EnforcementAgent):
        portrayal["Shape"] = "rect"
        portrayal["Filled"] = "true"
        portrayal["w"] = 0.8
        portrayal["h"] = 0.8
        portrayal["Layer"] = 1 # Draw on top of households
        portrayal["Color"] = "blue"
        portrayal["text"] = "POLICE"
        portrayal["text_color"] = "white"

    return portrayal

# --- 2. Setup the Visualization Elements ---

# The Grid: 50x50 size, 500x500 pixels on screen
grid = CanvasGrid(agent_portrayal, 50, 50, 500, 500)

# The Chart: Tracks "Average Compliance" over time
chart = ChartModule([
    {"Label": "Average Compliance", "Color": "Green"}
], data_collector_name='datacollector')

# --- 3. Launch the Server ---
server = ModularServer(
    BacolodModel,
    [grid, chart],
    "Bacolod Waste Segregation Model",
    # Model parameters user can change in the browser:
    {
        "num_households": mesa.visualization.UserSettableParameter(
            "slider", "Number of Households", 200, 50, 500, 10
        ),
        "width": 50,
        "height": 50
    }
)

server.port = 8521 # The default Mesa port