import mesa
from mesa.visualization.modules import CanvasGrid, ChartModule, TextElement
from mesa.visualization.ModularVisualization import ModularServer

# Import your model and agents
from agents.bacolod_model import BacolodModel
from agents.household_agent import HouseholdAgent
from agents.enforcement_agent import EnforcementAgent
from agents.barangay_agent import BarangayAgent

# --- 1. Define How Agents Look ---
# Function to generate a view focused on a SPECIFIC Barangay
def make_barangay_portrayal(barangay_target_id):
    
    def local_portrayal(agent):
        if agent is None:
            return

        # --- 1. FILTER: Only show agents from the target Barangay ---
        should_draw = False
        
        # Check Household/Enforcement Agents
        if hasattr(agent, 'barangay_id'):
            if agent.barangay_id == barangay_target_id:
                should_draw = True
        
        # Check the Barangay Center Agent itself
        elif isinstance(agent, BarangayAgent):
            if agent.unique_id == barangay_target_id:
                should_draw = True
                
        if not should_draw:
            return None # Hide this agent from this specific map

        # --- 2. DRAW: Standard styling (Same as before) ---
        portrayal = {}
        agent_class = type(agent).__name__

        if agent_class == "HouseholdAgent":
            portrayal["Shape"] = "circle"
            portrayal["Filled"] = "true"
            portrayal["r"] = 0.8  # Make them slightly larger for mini-maps
            portrayal["Layer"] = 0
            portrayal["Color"] = "green" if agent.is_compliant else "red"
            
        elif agent_class == "EnforcementAgent":
            portrayal["Shape"] = "rect"
            portrayal["Filled"] = "true"
            portrayal["w"] = 0.8
            portrayal["h"] = 0.8
            portrayal["Layer"] = 1
            portrayal["Color"] = "blue"
            
        elif agent_class == "BarangayAgent":
            portrayal["Shape"] = "circle"
            portrayal["Filled"] = "true"
            portrayal["r"] = 1.0
            portrayal["Layer"] = 2
            portrayal["Color"] = "black"

        return portrayal

    return local_portrayal

class CssLayout(mesa.visualization.TextElement):
    def __init__(self):
        pass

    def render(self, model):
        return """
        <style>
            /* --- 1. FORCE FULL WIDTH CONTAINER --- */
            .container-fluid {
                max-width: 100vw !important;
                padding: 0 !important;
                margin: 0 !important;
            }
            
            /* --- 2. MOVE SIDEBAR TO BOTTOM --- */
            .col-md-3 {
                order: 10 !important; 
                width: 100% !important;
                max-width: 100% !important;
                flex: 0 0 100% !important;
                background: #f8f9fa;
                border-top: 4px solid #333;
                padding: 10px !important;
                display: flex;
                justify-content: center;
                gap: 15px;
            }

            .col-md-9 {
                width: 100% !important;
                max-width: 100% !important;
                flex: 0 0 100% !important;
                padding: 0 !important;
            }

            /* --- 3. THE MAP CONTAINER --- */
            #elements {
                display: flex !important;
                flex-wrap: wrap !important;
                justify-content: center !important;
                width: 98vw !important; /* Force to fit screen */
                margin-left: 1vw !important;
                gap: 0 !important; /* We handle spacing via margins */
            }
            
            #elements > div {
                box-sizing: border-box !important;
                border: 1px solid #ccc;
                background: white;
                margin: 5px !important; /* Small uniform margin */
            }

            /* --- ROW 1: 3 MAPS --- */
            /* 30% * 3 = 90%. Leaves 10% for margins/scrollbars. Safe! */
            #elements > div:nth-child(2),
            #elements > div:nth-child(3),
            #elements > div:nth-child(4) {
                flex: 0 0 30% !important;
                max-width: 30% !important;
                min-width: 150px !important; /* Allow shrinking */
            }

            /* --- ROW 2: 4 MAPS --- */
            /* 22% * 4 = 88%. Leaves 12% for margins. Very Safe! */
            #elements > div:nth-child(5),
            #elements > div:nth-child(6),
            #elements > div:nth-child(7),
            #elements > div:nth-child(8) {
                flex: 0 0 22% !important;
                max-width: 22% !important;
                min-width: 150px !important; /* Allow shrinking */
            }

            /* --- ROW 3: CHART --- */
            #elements > div:last-child {
                flex: 0 0 95% !important;
                max-width: 95% !important;
                border: 2px solid green;
                margin-top: 10px !important;
            }

            /* --- TITLE --- */
            #elements > div:nth-child(1) {
                flex: 0 0 100% !important;
                border: none !important;
                background: transparent !important;
                text-align: center;
                font-weight: bold;
                font-size: 20px;
                margin-bottom: 5px !important;
            }
        </style>
        <div style="display:none">Layout Loaded</div>
        <div>Bacolod 7-Barangay Dashboard</div>
        """

# --- Setup Visualization Elements ---
visual_elements = []

# 1. ADD LAYOUT STYLE FIRST (Crucial!)
visual_elements.append(CssLayout()) 

# 2. Add 7 Mini-Maps
for i in range(7):
    target_id = f"BGY_{i}"
    portrayal_method = make_barangay_portrayal(target_id)
    grid = CanvasGrid(portrayal_method, 80, 80, 300, 300)
    visual_elements.append(grid)

# 3. Add Chart
chart = ChartModule([{"Label": "Average Compliance", "Color": "Green"}], data_collector_name='datacollector')
visual_elements.append(chart)

# --- Launch Server ---
server = ModularServer(
    BacolodModel,
    visual_elements,
    "Bacolod Waste Policy", # This title appears in the browser tab
    {
        "seed": 42
    }
)
server.port = 8521
server.launch()