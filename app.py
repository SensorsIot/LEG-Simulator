from dash import Dash, dcc, html, callback_context, no_update
from dash.dependencies import Input, Output, State

from layout import build_graph
from simulation import Simulation

HOUSE_COUNT = 5

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
                    dcc.Input(id="price-grid-delivery", type="number", value=6, min=0, step=0.01,
                              style={"width": "80px", "marginLeft": "10px"}),
                    html.Span(" ct/kWh", style={"marginLeft": "5px"}),
                ], style={"display": "inline-block", "marginRight": "30px"}),
                html.Div([
                    html.Label("Grid Consumption (buy):"),
                    dcc.Input(id="price-grid-consumption", type="number", value=30, min=0, step=0.01,
                              style={"width": "80px", "marginLeft": "10px"}),
                    html.Span(" ct/kWh", style={"marginLeft": "5px"}),
                ], style={"display": "inline-block", "marginRight": "30px"}),
                html.Div([
                    html.Label("PV Delivery:"),
                    dcc.Input(id="price-pv-delivery", type="number", value=20, min=0, step=0.01,
                              style={"width": "80px", "marginLeft": "10px"}),
                    html.Span(" ct/kWh", style={"marginLeft": "5px"}),
                ], style={"display": "inline-block", "marginRight": "30px"}),
                html.Div([
                    html.Label("House Consumption:"),
                    dcc.Input(id="price-house-consumption", type="number", value=25, min=0, step=0.01,
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
            html.Div(id="breakeven-indicator", style={"marginTop": "15px", "padding": "10px",
                      "backgroundColor": "#e8f4f8", "borderRadius": "5px", "borderLeft": "4px solid #3498db"}),
        ], style={"padding": "10px", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "marginBottom": "20px"}),

        # Graph
        html.Div([
            dcc.Graph(id="energy-graph", config={"displayModeBar": False}),
        ]),

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
                        current_value = house["ev_load_w"] / 1000
                    elif device_type == "washer":
                        title = f"Edit Washer Power - House {house_idx + 1}"
                        current_value = house["washer_load_w"] / 1000
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
                house["ev_load_w"] = new_value * 1000  # Convert kW to W
            elif device_type == "washer":
                house["washer_load_w"] = new_value * 1000  # Convert kW to W
            elif device_type == "base":
                house["base_load_w"] = new_value * 1000  # Convert kW to W

    return {"display": "none", "position": "fixed", "top": "0", "left": "0", "right": "0", "bottom": "0",
            "backgroundColor": "rgba(0,0,0,0.5)", "zIndex": "1000",
            "justifyContent": "center", "alignItems": "center"}


@app.callback(
    [Output("energy-graph", "figure"), Output("pricing-table", "children"), Output("breakeven-indicator", "children")],
    [Input("price-grid-delivery", "value"),
     Input("price-grid-consumption", "value"),
     Input("price-pv-delivery", "value"),
     Input("price-house-consumption", "value"),
     Input("modal-apply", "n_clicks")],
)
def update_graph(price_grid_del, price_grid_con, price_pv_del, price_house_con, apply_clicks):
    """Update graph and pricing table."""
    snapshot = simulation.tick()
    fig = build_graph(snapshot)

    # Calculate E (total exports) and I (total imports) for break-even optimization
    E_total = 0.0  # Total exports from houses (kWh)
    I_total = 0.0  # Total imports to houses (kWh)
    for house in snapshot.houses:
        net_kw = house.net_power_w / 1000
        if net_kw > 0:
            E_total += net_kw
        else:
            I_total += abs(net_kw)

    # Calculate optimal p_con (break-even house consumption price) BEFORE building table
    # Formula: p_con = p_grid + (E/I) * (p_pv - p_grid)
    p_pv = price_pv_del or 20
    p_grid_del = price_grid_del or 6
    p_grid_con = price_grid_con or 30

    if I_total == 0:
        # No imports - use default price
        optimal_p_con = price_house_con or 25
    elif E_total == 0:
        # No exports - pass-through from grid
        optimal_p_con = p_grid_con
    else:
        # Normal case: calculate break-even price
        if E_total >= I_total:
            p_grid = p_grid_del  # Surplus mode
        else:
            p_grid = p_grid_con  # Deficit mode
        optimal_p_con = p_grid + (E_total / I_total) * (p_pv - p_grid)

    # Build pricing table with 7 columns: Title, House Buy/Sell, Community Buy/Sell, Grid Buy/Sell
    # Logic: House sells to Community (same kWh), Community sells to Grid (same kWh)
    # Build pricing table using user's price settings
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
            house_sell = net_kw * p_pv  # House sells at PV rate
            comm_buy = house_sell  # Community buys same amount
            comm_sell = 0
        else:  # House imports from community
            house_buy = abs(net_kw) * (price_house_con or 25)  # House buys at user-set rate
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
        grid_buy = community_net_kw * p_grid_del  # Grid buys at delivery rate
        grid_sell = 0
        # Community earns from selling to grid
        totals["comm_sell"] += grid_buy  # Community sells to grid (same amount grid buys)
    else:  # Community imports from grid
        grid_buy = 0
        grid_sell = abs(community_net_kw) * p_grid_con  # Grid sells at consumption rate
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
        html.Td(f"{grid_sell:.1f}" if grid_sell > 0 else "-", style={**cell_buy, "backgroundColor": "#e8e8e8"}),
        html.Td(f"{grid_buy:.1f}" if grid_buy > 0 else "-", style={**cell_sell, "backgroundColor": "#e8e8e8"}),
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

    # Community Profit row - prominent display with large font
    community_profit = totals["comm_sell"] - totals["comm_buy"]
    profit_color = "#27ae60" if abs(community_profit) < 0.1 else ("#27ae60" if community_profit > 0 else "#e74c3c")
    table_rows.append(html.Tr([
        html.Td("Community Profit:", colSpan=5, style={"fontWeight": "bold", "fontSize": "24px",
                "padding": "12px 4px", "textAlign": "right", "borderTop": "2px solid #333"}),
        html.Td(f"{community_profit:.1f} ct/h", colSpan=2, style={"fontWeight": "bold", "fontSize": "28px",
                "padding": "12px 20px 12px 4px", "textAlign": "right", "color": profit_color,
                "borderTop": "2px solid #333", "backgroundColor": "#f0f8f0" if abs(community_profit) < 0.1 else "#fff"}),
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

    # Break-even indicator: show the optimal p_con being used
    if I_total == 0:
        mode = "No imports"
        breakeven_content = [
            html.Strong("Break-Even Optimization"),
            html.Br(),
            html.Span("No house imports (I=0) - using default price", style={"color": "#7f8c8d"}),
        ]
    elif E_total == 0:
        mode = "Grid pass-through"
        breakeven_content = [
            html.Strong("Break-Even Optimization"),
            html.Br(),
            html.Span(f"E = {E_total:.1f} kWh | I = {I_total:.1f} kWh | Mode: {mode}"),
            html.Br(),
            html.Span(f"p_con = {optimal_p_con:.2f} ct/kWh", style={"fontWeight": "bold", "color": "#2980b9", "fontSize": "14px"}),
            html.Span(" (= grid price)", style={"color": "#7f8c8d"}),
        ]
    else:
        mode = "Surplus" if E_total >= I_total else "Deficit"
        breakeven_content = [
            html.Strong("Break-Even Optimization"),
            html.Br(),
            html.Span(f"E = {E_total:.1f} kWh | I = {I_total:.1f} kWh | Mode: {mode}"),
            html.Br(),
            html.Span(f"p_con = ", style={"fontWeight": "bold"}),
            html.Span(f"{optimal_p_con:.2f} ct/kWh", style={"fontWeight": "bold", "color": "#2980b9", "fontSize": "14px"}),
        ]

    return fig, pricing_table, breakeven_content


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
