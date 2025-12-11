import mesa
from mesa.visualization.modules import CanvasGrid, ChartModule, TextElement
from mesa.visualization.ModularVisualization import ModularServer

from agents.bacolod_model import BacolodModel
from agents.household_agent import HouseholdAgent
from agents.enforcement_agent import EnforcementAgent
from agents.barangay_agent import BarangayAgent

# --- 1. Portrayal Factory (INCREASED SIZE for 600x600 grid) ---
def make_barangay_portrayal(barangay_target_id):
    def local_portrayal(agent):
        if agent is None: return None
        if hasattr(agent, 'barangay_id') and agent.barangay_id != barangay_target_id: return None
        if isinstance(agent, BarangayAgent) and agent.unique_id != barangay_target_id: return None

        portrayal = {}
        agent_class = type(agent).__name__
        
        # HOUSEHOLDS (Circles) - Set radius to 3.0 (from 1.2) for visibility
        if agent_class == "HouseholdAgent":
            portrayal["Shape"] = "circle"; portrayal["Filled"] = "true"; portrayal["r"] = 3.0; portrayal["Layer"] = 0
            portrayal["Color"] = "green" if agent.is_compliant else "red"
            
        # ENFORCEMENT AGENTS (Squares) - Set w/h to 4.0 (from 1.5)
        elif agent_class == "EnforcementAgent":
            portrayal["Shape"] = "rect"; portrayal["Filled"] = "true"; portrayal["w"] = 4.0; portrayal["h"] = 4.0; portrayal["Layer"] = 1
            portrayal["Color"] = "blue"
            
        # BARANGAY CENTER
        elif agent_class == "BarangayAgent":
            portrayal["Shape"] = "circle"; portrayal["Filled"] = "true"; portrayal["r"] = 5.0; portrayal["Layer"] = 2
            portrayal["Color"] = "black"
            
        return portrayal
    return local_portrayal

# --- 2. The Absolute Positioning Fix (Deck of Cards) ---
class ViewSwitcher(mesa.visualization.TextElement):
    def render(self, model):
        return """
        <div class="switcher-box" id="switcher-box">
            <h4>Active Simulation View</h4>
            <div class="btn-group">
                <button id="btn_0" class="bgy-btn active" onclick="switchView(0)">Poblacion</button>
                <button id="btn_1" class="bgy-btn" onclick="switchView(1)">Rural</button>
                <button id="btn_2" class="bgy-btn" onclick="switchView(2)">Coastal</button>
                <button id="btn_3" class="bgy-btn" onclick="switchView(3)">Bgy 4</button>
                <button id="btn_4" class="bgy-btn" onclick="switchView(4)">Bgy 5</button>
                <button id="btn_5" class="bgy-btn" onclick="switchView(5)">Bgy 6</button>
                <button id="btn_6" class="bgy-btn" onclick="switchView(6)">Bgy 7</button>
            </div>
        </div>

        <script>
            function switchView(targetIndex) {
                let mainContainer = document.getElementById('elements');
                if (!mainContainer) return;
                let children = mainContainer.children;
                if (children.length < 9) return; 

                let mapStartIndex = 2; // Maps start at Index 2

                for (let i = 0; i < 7; i++) {
                    let mapBox = children[mapStartIndex + i];
                    
                    if (mapBox) {
                        if (i === targetIndex) {
                            // SHOW: Bring to front and make opaque
                            mapBox.style.opacity = '1';
                            mapBox.style.zIndex = '100';
                            mapBox.style.pointerEvents = 'auto';
                            mapBox.style.border = '3px solid #007bff';
                        } else {
                            // HIDE: Make transparent and send to background
                            mapBox.style.opacity = '0';
                            mapBox.style.zIndex = '1';
                            mapBox.style.pointerEvents = 'none';
                            mapBox.style.border = 'none';
                        }
                    }
                }

                // Update Buttons
                let btns = document.querySelectorAll('.bgy-btn');
                btns.forEach(b => b.classList.remove('active'));
                let btn = document.getElementById('btn_' + targetIndex);
                if(btn) btn.classList.add('active');
            }

            // Initialize on load
            setTimeout(() => { switchView(0); }, 800); 
        </script>
        
        <style>
            /* --- THE CRITICAL STYLES --- */
            /* 1. ANCHOR THE MAIN CONTAINER */
            #elements {
                position: relative !important; 
                min-height: 750px; /* Reserves vertical space */
                margin-top: 10px;
            }
            
            /* 2. FORCE ALL MAP CONTAINERS INTO A SINGLE OVERLAPPING STACK */
            /* Targets children from Index 2 to 8 */
            #elements > div:nth-child(n+2):nth-child(-n+8) {
                position: absolute !important;
                top: 100px;    /* Push map down below the button bar */
                left: 50%;
                transform: translateX(-50%); /* Center horizontally */
                width: 600px !important; 
                height: 600px !important; 
                transition: opacity 0.3s ease; 
                margin: 0 auto !important;
                border: 1px solid #ccc; /* Border to see the map box area */
            }
            
            /* 3. CHART POSITION (Push it down to the bottom of the reserved space) */
            #elements > div:nth-child(9) {
                margin-top: 720px !important; /* Pushes chart below the 600px map area */
                position: relative; 
            }

            /* General Styling */
            .switcher-box { width: 100%; text-align: center; padding: 10px; background: white; border-bottom: 2px solid #ccc; position: relative; z-index: 1000;}
            .bgy-btn { padding: 8px 15px; margin: 2px; border: 1px solid #aaa; cursor: pointer; border-radius: 4px; background: #f8f9fa;}
            .bgy-btn.active { background: #007bff; color: white; }
        </style>
        """

# --- 3. Setup Elements ---
visual_elements = []

# A. Add Switcher (Index 1)
visual_elements.append(ViewSwitcher()) 

# B. Add 7 Grids (Indices 2 through 8)
for i in range(7):
    portrayal_fn = make_barangay_portrayal(f"BGY_{i}")
    # Size: 50x50 Logical size, 600x600 Pixel size
    grid = CanvasGrid(portrayal_fn, 50, 50, 600, 600)
    visual_elements.append(grid)


# C. Add Chart (Index 9)
chart = ChartModule([{"Label": "Global Compliance", "Color": "Black"}] + 
                    [{"Label": f"Bgy {i}", "Color": c} for i, c in enumerate(["red","orange","gold","green","cyan","blue","purple"])],
                    data_collector_name='datacollector')
visual_elements.append(chart)

# --- 4. Launch ---
server = ModularServer(
    BacolodModel,
    visual_elements,
    "Bacolod Multi-View Simulation",
    {"seed": 42}
)
server.port = 8521
server.launch()