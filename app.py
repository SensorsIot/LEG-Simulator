from pathlib import Path

import yaml
from dash import Dash, dcc, html, callback_context, no_update
from dash.dependencies import Input, Output, State

from layout import build_graph
from simulation import Simulation


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"
CONFIG = load_config(CONFIG_PATH)

HOUSE_COUNT = int(CONFIG.get("houses", 5))
UPDATE_INTERVAL_MS = int(CONFIG.get("update_interval_ms", 1000))

simulation = Simulation(HOUSE_COUNT)

app = Dash(__name__)
app.layout = html.Div(
    children=[
        html.H1("LEG Energy Flow Simulator", style={"textAlign": "center", "color": "#2c3e50"}),
        html.P("Click on PV, EV, or Washer to edit values", style={"textAlign": "center", "color": "#7f8c8d"}),

        # Energy price inputs
        html.Div([
            html.H3("Energy Prices (ct/kWh)", style={"marginBottom": "10px"}),
            html.Div([
                html.Div([
                    html.Label("Grid Delivery (sell):"),
                    dcc.Input(id="price-grid-delivery", type="number", value=6, min=0, step=0.1,
                              style={"width": "80px", "marginLeft": "10px"}),
                    html.Span(" ct/kWh", style={"marginLeft": "5px"}),
                ], style={"display": "inline-block", "marginRight": "30px"}),
                html.Div([
                    html.Label("Grid Consumption (buy):"),
                    dcc.Input(id="price-grid-consumption", type="number", value=30, min=0, step=0.1,
                              style={"width": "80px", "marginLeft": "10px"}),
                    html.Span(" ct/kWh", style={"marginLeft": "5px"}),
                ], style={"display": "inline-block", "marginRight": "30px"}),
                html.Div([
                    html.Label("PV Delivery:"),
                    dcc.Input(id="price-pv-delivery", type="number", value=20, min=0, step=0.1,
                              style={"width": "80px", "marginLeft": "10px"}),
                    html.Span(" ct/kWh", style={"marginLeft": "5px"}),
                ], style={"display": "inline-block", "marginRight": "30px"}),
                html.Div([
                    html.Label("House Consumption:"),
                    dcc.Input(id="price-house-consumption", type="number", value=25, min=0, step=0.1,
                              style={"width": "80px", "marginLeft": "10px"}),
                    html.Span(" ct/kWh", style={"marginLeft": "5px"}),
                ], style={"display": "inline-block"}),
            ], style={"display": "flex", "flexWrap": "wrap", "gap": "10px"}),
        ], style={"padding": "15px", "backgroundColor": "#ecf0f1", "borderRadius": "8px", "marginBottom": "20px"}),

        # Edit modal
        html.Div(id="edit-modal", children=[
            html.Div([
                html.H4(id="modal-title", style={"marginBottom": "15px"}),
                html.Div([
                    html.Label("Power (kW): "),
                    dcc.Input(id="modal-input", type="number", min=0, step=0.1,
                              style={"width": "100px", "marginLeft": "10px"}),
                ]),
                html.Div([
                    html.Button("Apply", id="modal-apply", n_clicks=0,
                                style={"marginRight": "10px", "marginTop": "15px", "padding": "8px 20px",
                                       "backgroundColor": "#3498db", "color": "white", "border": "none", "cursor": "pointer"}),
                    html.Button("Cancel", id="modal-cancel", n_clicks=0,
                                style={"marginTop": "15px", "padding": "8px 20px",
                                       "backgroundColor": "#95a5a6", "color": "white", "border": "none", "cursor": "pointer"}),
                ]),
            ], style={"backgroundColor": "white", "padding": "25px", "borderRadius": "8px",
                      "boxShadow": "0 4px 20px rgba(0,0,0,0.3)", "minWidth": "300px"}),
        ], style={"display": "none", "position": "fixed", "top": "0", "left": "0", "right": "0", "bottom": "0",
                  "backgroundColor": "rgba(0,0,0,0.5)", "zIndex": "1000",
                  "justifyContent": "center", "alignItems": "center"}),

        # Pricing table (top right)
        html.Div([
            html.H3("Energy Costs (ct/h)", style={"marginBottom": "10px"}),
            html.Div(id="pricing-table"),
        ], style={"padding": "10px", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "marginBottom": "20px"}),

        # Graph
        html.Div([
            dcc.Graph(id="energy-graph", config={"displayModeBar": False}),
        ]),

        dcc.Interval(id="tick", interval=UPDATE_INTERVAL_MS, n_intervals=0),
        dcc.Store(id="edit-store", data={"house_idx": None, "device_type": None}),
    ],
    style={"maxWidth": "1600px", "margin": "0 auto", "fontFamily": "Arial, sans-serif", "padding": "20px"},
)


@app.callback(
    [Output("edit-modal", "style"),
     Output("modal-title", "children"),
     Output("modal-input", "value"),
     Output("edit-store", "data")],
    [Input("energy-graph", "clickData"),
     Input("modal-cancel", "n_clicks")],
    [State("edit-store", "data")],
    prevent_initial_call=True
)
def handle_click(click_data, cancel_clicks, edit_store):
    """Handle clicks on components to open edit modal."""
    ctx = callback_context
    trigger = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

    modal_hidden = {"display": "none", "position": "fixed", "top": "0", "left": "0", "right": "0", "bottom": "0",
                    "backgroundColor": "rgba(0,0,0,0.5)", "zIndex": "1000",
                    "justifyContent": "center", "alignItems": "center"}
    modal_visible = {**modal_hidden, "display": "flex"}

    if "modal-cancel" in trigger:
        return modal_hidden, "", 0, {"house_idx": None, "device_type": None}

    if click_data and "points" in click_data:
        point = click_data["points"][0]
        if "customdata" in point:
            custom = point["customdata"]
            if isinstance(custom, dict):
                device_type = custom.get("type")
                house_idx = custom.get("id")

                if device_type in ["pv", "ev", "washer", "base"]:
                    house = simulation.model._houses[house_idx]

                    if device_type == "pv":
                        title = f"Edit PV Power - House {house_idx + 1}"
                        current_value = house["pv_power_w"] / 1000
                    elif device_type == "ev":
                        title = f"Edit EV Power - House {house_idx + 1}"
                        current_value = 11.0 if house["ev_on"] else 0
                    elif device_type == "washer":
                        title = f"Edit Washer Power - House {house_idx + 1}"
                        current_value = 2.0 if house["washer_on"] else 0
                    elif device_type == "base":
                        title = f"Edit Base Load - House {house_idx + 1}"
                        current_value = house["base_load_w"] / 1000

                    return modal_visible, title, current_value, {"house_idx": house_idx, "device_type": device_type}

    return no_update, no_update, no_update, no_update


@app.callback(
    Output("edit-modal", "style", allow_duplicate=True),
    [Input("modal-apply", "n_clicks")],
    [State("modal-input", "value"),
     State("edit-store", "data")],
    prevent_initial_call=True
)
def apply_edit(apply_clicks, new_value, edit_store):
    """Apply the edited value."""
    if apply_clicks and edit_store and edit_store.get("house_idx") is not None:
        house_idx = edit_store["house_idx"]
        device_type = edit_store["device_type"]
        house = simulation.model._houses[house_idx]

        if new_value is not None and new_value >= 0:
            if device_type == "pv":
                house["pv_power_w"] = new_value * 1000  # Convert kW to W
            elif device_type == "ev":
                house["ev_on"] = new_value > 0
            elif device_type == "washer":
                house["washer_on"] = new_value > 0
            elif device_type == "base":
                house["base_load_w"] = new_value * 1000  # Convert kW to W

    return {"display": "none", "position": "fixed", "top": "0", "left": "0", "right": "0", "bottom": "0",
            "backgroundColor": "rgba(0,0,0,0.5)", "zIndex": "1000",
            "justifyContent": "center", "alignItems": "center"}


@app.callback(
    [Output("energy-graph", "figure"), Output("pricing-table", "children")],
    [Input("tick", "n_intervals"),
     Input("price-grid-delivery", "value"),
     Input("price-grid-consumption", "value"),
     Input("price-pv-delivery", "value"),
     Input("price-house-consumption", "value"),
     Input("modal-apply", "n_clicks")],
)
def update_graph(n_intervals, price_grid_del, price_grid_con, price_pv_del, price_house_con, apply_clicks):
    """Update graph and pricing table."""
    snapshot = simulation.tick()
    fig = build_graph(snapshot)

    # Build pricing table with 7 columns: Title, House Buy/Sell, Community Buy/Sell, Grid Buy/Sell
    # Logic: House sells to Community (same kWh), Community sells to Grid (same kWh)
    table_rows = []
    totals = {"house_buy": 0, "house_sell": 0, "comm_buy": 0, "comm_sell": 0}

    for idx, house in enumerate(snapshot.houses):
        # Convert W to kW for calculations
        net_kw = house.net_power_w / 1000

        # House: Net exchange with community
        # If net > 0: House exports (sells) to community
        # If net < 0: House imports (buys) from community
        if net_kw > 0:  # House exports to community
            house_buy = 0
            house_sell = net_kw * (price_pv_del or 0)  # House sells at PV rate
            comm_buy = house_sell  # Community buys same amount
            comm_sell = 0
        else:  # House imports from community
            house_buy = abs(net_kw) * (price_house_con or 0)  # House buys at consumption rate
            house_sell = 0
            comm_buy = 0
            comm_sell = house_buy  # Community sells same amount

        totals["house_buy"] += house_buy
        totals["house_sell"] += house_sell
        totals["comm_buy"] += comm_buy
        totals["comm_sell"] += comm_sell

        # Cell styling with borders to group columns
        cell_buy = {"color": "#d95f02", "padding": "2px 4px", "textAlign": "right", "borderLeft": "2px solid #333"}
        cell_sell = {"color": "#1b9e77", "padding": "2px 4px", "textAlign": "right", "borderRight": "2px solid #333"}
        cell_na = {"color": "#999", "padding": "2px 4px", "textAlign": "right"}

        table_rows.append(html.Tr([
            html.Td(f"House {idx + 1}", style={"fontWeight": "bold", "padding": "4px"}),
            html.Td(f"{house_buy:.1f}", style=cell_buy),
            html.Td(f"{house_sell:.1f}", style=cell_sell),
            html.Td(f"{comm_buy:.1f}", style=cell_buy),
            html.Td(f"{comm_sell:.1f}", style=cell_sell),
            html.Td("-", style={**cell_na, "borderLeft": "2px solid #333"}),
            html.Td("-", style={**cell_na, "borderRight": "2px solid #333"}),
        ]))

    # Grid: same kWh as community net, at grid prices
    community_net_kw = snapshot.community.net_community_power_w / 1000
    if community_net_kw > 0:  # Community exports to grid
        grid_buy = community_net_kw * (price_grid_del or 0)  # Grid buys at delivery rate
        grid_sell = 0
        # Community earns from selling to grid
        totals["comm_sell"] += grid_buy  # Community sells to grid (same amount grid buys)
    else:  # Community imports from grid
        grid_buy = 0
        grid_sell = abs(community_net_kw) * (price_grid_con or 0)  # Grid sells at consumption rate
        # Community pays for buying from grid
        totals["comm_buy"] += grid_sell  # Community buys from grid (same amount grid sells)

    # Grid row (between houses and total)
    cell_buy = {"color": "#d95f02", "padding": "2px 4px", "textAlign": "right", "borderLeft": "2px solid #333"}
    cell_sell = {"color": "#1b9e77", "padding": "2px 4px", "textAlign": "right", "borderRight": "2px solid #333"}
    cell_na = {"color": "#999", "padding": "2px 4px", "textAlign": "right"}

    table_rows.append(html.Tr([
        html.Td("Grid", style={"fontWeight": "bold", "padding": "4px", "backgroundColor": "#e8e8e8"}),
        html.Td("-", style={**cell_na, "borderLeft": "2px solid #333", "backgroundColor": "#e8e8e8"}),
        html.Td("-", style={**cell_na, "borderRight": "2px solid #333", "backgroundColor": "#e8e8e8"}),
        html.Td(f"{grid_buy:.1f}" if grid_buy > 0 else "-", style={**cell_buy, "backgroundColor": "#e8e8e8"}),
        html.Td(f"{grid_sell:.1f}" if grid_sell > 0 else "-", style={**cell_sell, "backgroundColor": "#e8e8e8"}),
        html.Td(f"{grid_buy:.1f}", style={**cell_buy, "backgroundColor": "#e8e8e8"}),
        html.Td(f"{grid_sell:.1f}", style={**cell_sell, "backgroundColor": "#e8e8e8"}),
    ]))

    # Total row with matching borders
    tot_base = {"fontWeight": "bold", "borderTop": "2px solid #333", "padding": "2px 4px", "textAlign": "right"}
    tot_buy = {**tot_base, "color": "#d95f02", "borderLeft": "2px solid #333"}
    tot_sell = {**tot_base, "color": "#1b9e77", "borderRight": "2px solid #333"}

    table_rows.append(html.Tr([
        html.Td("TOTAL", style={**tot_base, "textAlign": "left"}),
        html.Td(f"{totals['house_buy']:.1f}", style=tot_buy),
        html.Td(f"{totals['house_sell']:.1f}", style=tot_sell),
        html.Td(f"{totals['comm_buy']:.1f}", style=tot_buy),
        html.Td(f"{totals['comm_sell']:.1f}", style=tot_sell),
        html.Td(f"{grid_buy:.1f}", style=tot_buy),
        html.Td(f"{grid_sell:.1f}", style=tot_sell),
    ]))

    # Column group styling
    group_style = {"textAlign": "center", "padding": "4px 2px", "borderLeft": "2px solid #333", "backgroundColor": "#e8e8e8"}
    sub_buy = {"color": "#d95f02", "padding": "2px 4px", "textAlign": "right", "fontSize": "11px"}
    sub_sell = {"color": "#1b9e77", "padding": "2px 4px", "textAlign": "right", "fontSize": "11px", "borderRight": "2px solid #333"}

    pricing_table = html.Table([
        html.Thead([
            html.Tr([
                html.Th("", rowSpan=2, style={"padding": "4px", "width": "70px"}),
                html.Th("House", colSpan=2, style={**group_style}),
                html.Th("Community", colSpan=2, style={**group_style}),
                html.Th("Grid", colSpan=2, style={**group_style}),
            ]),
            html.Tr([
                html.Th("Buy", style={**sub_buy, "borderLeft": "2px solid #333"}),
                html.Th("Sell", style=sub_sell),
                html.Th("Buy", style={**sub_buy, "borderLeft": "2px solid #333"}),
                html.Th("Sell", style=sub_sell),
                html.Th("Buy", style={**sub_buy, "borderLeft": "2px solid #333"}),
                html.Th("Sell", style=sub_sell),
            ]),
        ]),
        html.Tbody(table_rows),
    ], style={"width": "100%", "borderCollapse": "collapse", "fontSize": "12px"})

    return fig, pricing_table


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
