from pathlib import Path

import yaml
from dash import Dash, dcc, html
from dash.dependencies import Input, Output

from layout import build_graph
from simulation import Simulation


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"
CONFIG = load_config(CONFIG_PATH)

HOUSE_COUNT = int(CONFIG.get("houses", 5))
UPDATE_INTERVAL_MS = int(CONFIG.get("update_interval_ms", 1000))
PV_VARIATION = CONFIG.get("pv_variation", "enabled") == "enabled"
FLEX_LOAD_PROB = float(CONFIG.get("flex_load_probability", 0.1))

simulation = Simulation(HOUSE_COUNT, FLEX_LOAD_PROB, PV_VARIATION)

app = Dash(__name__)
app.layout = html.Div(
    children=[
        html.H1("LEG-Simulator Energy Flow", style={"textAlign": "center"}),
        dcc.Graph(id="energy-graph"),
        dcc.Interval(id="tick", interval=UPDATE_INTERVAL_MS, n_intervals=0),
    ],
    style={"maxWidth": "1000px", "margin": "0 auto"},
)


@app.callback(Output("energy-graph", "figure"), Input("tick", "n_intervals"))
def update_graph(_n_intervals: int):
    snapshot = simulation.tick()
    return build_graph(snapshot)


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8050, debug=False)
