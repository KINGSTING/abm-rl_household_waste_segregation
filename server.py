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
        
        if agent_class == "HouseholdAgent":
            portrayal["Shape"] = "circle"; portrayal["Filled"] = "true"; portrayal["r"] = 4.0; portrayal["Layer"] = 0
            portrayal["Color"] = "green" if agent.is_compliant else "red"
        elif agent_class == "EnforcementAgent":
            portrayal["Shape"] = "rect"; portrayal["Filled"] = "true"; portrayal["w"] = 5.0; portrayal["h"] = 5.0; portrayal["Layer"] = 1
            portrayal["Color"] = "blue"
        elif agent_class == "BarangayAgent":
            portrayal["Shape"] = "circle"; portrayal["Filled"] = "true"; portrayal["r"] = 6.0; portrayal["Layer"] = 2
            portrayal["Color"] = "black"
        return portrayal
    return local_portrayal

# --- 2. Helper Classes ---

# A. The Phantom Spacer (Creates room for the maps)
class Spacer(mesa.visualization.TextElement):
    def render(self, model):
        return '<div style="height: 620px; width: 100%; display: block;"></div>'

# B. The View Switcher
class ViewSwitcher(mesa.visualization.TextElement):
    def render(self, model):
        return """
        <div class="switcher-box">
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
                let maps = document.getElementsByClassName('world-grid-parent');
                if (maps.length < 7) return; 

                for (let i = 0; i < 7; i++) {
                    let mapBox = maps[i];
                    if (i === targetIndex) {
                        mapBox.style.opacity = '1';
                        mapBox.style.zIndex = '100';
                        mapBox.style.pointerEvents = 'auto';
                        mapBox.style.border = '3px solid #007bff';
                    } else {
                        mapBox.style.opacity = '0';
                        mapBox.style.zIndex = '1';
                        mapBox.style.pointerEvents = 'none';
                        mapBox.style.border = 'none';
                    }
                }

                let btns = document.querySelectorAll('.bgy-btn');
                btns.forEach(b => b.classList.remove('active'));
                let btn = document.getElementById('btn_' + targetIndex);
                if(btn) btn.classList.add('active');
            }
            setTimeout(() => { switchView(0); }, 1000); 
        </script>
        
        <style>
            #sidebar { display: none !important; }
            #elements { width: 100% !important; margin: 0 auto !important; position: relative !important; }

            .world-grid-parent {
                position: absolute !important;
                top: 130px; 
                left: 0; right: 0;
                margin-left: auto !important; margin-right: auto !important;
                width: 600px !important; height: 600px !important;
                transition: opacity 0.3s ease;
                background: white;
            }

            .switcher-box { width: 100%; text-align: center; padding: 10px; background: white; z-index: 1000; position: relative;}
            .bgy-btn { padding: 8px 15px; margin: 2px; border: 1px solid #aaa; cursor: pointer; border-radius: 4px; background: #f8f9fa;}
            .bgy-btn.active { background: #007bff; color: white; }
        </style>
        """

# --- 3. Setup Elements ---
visual_elements = []

# 1. Switcher (Top)
visual_elements.append(ViewSwitcher()) 

# 2. Spacer (Middle - Invisible, creates the "hole" for the maps)
visual_elements.append(Spacer())

# 3. Maps (Floating on top of the Spacer)
for i in range(7):
    portrayal_fn = make_barangay_portrayal(f"BGY_{i}")
    grid = CanvasGrid(portrayal_fn, 100, 100, 600, 600)
    visual_elements.append(grid)

# 4. Chart (Bottom - Sits naturally after the Spacer)
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