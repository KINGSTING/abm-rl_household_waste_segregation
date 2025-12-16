import mesa
from mesa.visualization.modules import CanvasGrid, ChartModule, TextElement
from mesa.visualization.ModularVisualization import ModularServer

from agents.bacolod_model import BacolodModel
from agents.household_agent import HouseholdAgent
from agents.enforcement_agent import EnforcementAgent
from agents.barangay_agent import BarangayAgent

# --- 1. Portrayal Factory ---
def make_barangay_portrayal(barangay_target_id):
    def local_portrayal(agent):
        if agent is None: return None
        if hasattr(agent, 'barangay_id') and agent.barangay_id != barangay_target_id: return None
        if isinstance(agent, BarangayAgent) and agent.unique_id != barangay_target_id: return None

        portrayal = {}
        agent_class = type(agent).__name__
        
        # HOUSEHOLDS: Use r=0.5 to fit exactly inside one grid cell
        if agent_class == "HouseholdAgent":
            portrayal["Shape"] = "circle"
            portrayal["Filled"] = "true"
            portrayal["r"] = 0.5   # FIXED: Reduced from 3.0 to 0.5
            portrayal["Layer"] = 0
            portrayal["Color"] = "green" if agent.is_compliant else "red"
            
        # ENFORCEMENT: Use w=0.8 to be distinct but contained
        elif agent_class == "EnforcementAgent":
            portrayal["Shape"] = "rect"
            portrayal["Filled"] = "true"
            portrayal["w"] = 0.8   # FIXED: Reduced from 4.0 to 0.8
            portrayal["h"] = 0.8
            portrayal["Layer"] = 1
            portrayal["Color"] = "blue"
            
        # BARANGAY CENTER: Slightly larger to stand out
        elif agent_class == "BarangayAgent":
            portrayal["Shape"] = "circle"
            portrayal["Filled"] = "true"
            portrayal["r"] = 1.0   # FIXED: Reduced from 5.0 to 1.0
            portrayal["Layer"] = 2
            portrayal["Color"] = "black"
            
        return portrayal
    return local_portrayal

# --- 2. Helper Classes ---

class Spacer(mesa.visualization.TextElement):
    def render(self, model):
        # Increased Z-index to -1 so it sits behind everything
        return '<div style="height: 650px; width: 100%; display: block; z-index: -1;"></div>'

class ViewSwitcher(mesa.visualization.TextElement):
    def render(self, model):
        return """
        <div class="switcher-box">
            <h4>Active Simulation View</h4>
            <div class="btn-group" id="bgy-btn-group">
                <button id="btn_0" class="bgy-btn" onclick="window.switchView(0)">Poblacion</button>
                <button id="btn_1" class="bgy-btn" onclick="window.switchView(1)">Liangan East</button>
                <button id="btn_2" class="bgy-btn" onclick="window.switchView(2)">Ezperanza</button>
                <button id="btn_3" class="bgy-btn" onclick="window.switchView(3)">Binuni</button>
                <button id="btn_4" class="bgy-btn" onclick="window.switchView(4)">Demologan</button> 
                <button id="btn_5" class="bgy-btn" onclick="window.switchView(5)">Mati</button>
                <button id="btn_6" class="bgy-btn" onclick="window.switchView(6)">Babalaya</button>
            </div>
            
            <img src="x" style="display:none;" onerror="
                if (!window.switchView) {
                    window.switchView = function(targetIndex) {
                        // 1. Handle Maps
                        let maps = document.getElementsByClassName('world-grid-parent');
                        if (maps.length < 7) {
                            setTimeout(() => window.switchView(targetIndex), 100);
                            return;
                        }
                        
                        targetIndex = parseInt(targetIndex);
                        for (let i = 0; i < 7; i++) {
                            let mapBox = maps[i];
                            if (i === targetIndex) {
                                mapBox.style.opacity = '1';
                                mapBox.style.zIndex = '100';
                                mapBox.style.pointerEvents = 'auto';
                                mapBox.style.border = '2px solid #007bff';
                            } else {
                                mapBox.style.opacity = '0';
                                mapBox.style.zIndex = '1';
                                mapBox.style.pointerEvents = 'none';
                                mapBox.style.border = 'none';
                            }
                        }

                        // 2. Handle Buttons (Logic Fix)
                        // We target the specific container ID to ensure we find the right buttons
                        let container = document.getElementById('bgy-btn-group');
                        if (container) {
                            let btns = container.getElementsByClassName('bgy-btn');
                            
                            // Remove 'active' class from ALL buttons
                            for(let i = 0; i < btns.length; i++) {
                                btns[i].classList.remove('active');
                            }
                            
                            // Add 'active' class to the clicked button
                            let activeBtn = document.getElementById('btn_' + targetIndex);
                            if(activeBtn) {
                                activeBtn.classList.add('active');
                            }
                        }
                    };
                    
                    // Initialize: Run once on load to set default view
                    if (!window.hasInitializedView) {
                        window.hasInitializedView = true;
                        setTimeout(() => window.switchView(0), 500);
                    }
                }
            ">
        </div>

        <style>
            #sidebar { display: none !important; }
            #elements { width: 100% !important; margin: 0 auto !important; position: relative !important; }

            .world-grid-parent {
                position: absolute !important;
                top: 150px; 
                left: 0; right: 0;
                margin-left: auto !important; margin-right: auto !important;
                width: 600px !important; height: 600px !important;
                transition: opacity 0.3s ease;
                background: white;
            }

            .switcher-box { 
                width: 100%; text-align: center; padding: 15px; 
                background: white; z-index: 9999 !important; position: relative;
            }
            .bgy-btn { 
                padding: 10px 20px; margin: 2px; border: 1px solid #aaa; 
                cursor: pointer; border-radius: 4px; background: #f8f9fa; font-weight: bold;
            }
            /* Explicit Active Style with !important to override defaults */
            .bgy-btn.active { 
                background-color: #007bff !important; 
                color: white !important; 
                border-color: #0056b3 !important; 
            }
            .bgy-btn:hover { background: #e2e6ea; }
        </style>
        """

# --- 3. Setup Elements ---
visual_elements = []
visual_elements.append(ViewSwitcher()) 
visual_elements.append(Spacer())

for i in range(7):
    portrayal_fn = make_barangay_portrayal(f"BGY_{i}")
    grid = CanvasGrid(portrayal_fn, 50, 50, 600, 600)
    visual_elements.append(grid)

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
server.port = 8522
server.launch()