import math

import plotly.graph_objects as go

from simulation import SimulationSnapshot


def _format_power(watts: float) -> str:
    """Format power value with unit."""
    if abs(watts) >= 1000:
        return f"{watts/1000:.1f}kW"
    return f"{watts:.0f}W"


# Fixed line width for all connections
LINE_WIDTH = 2
ARROW_WIDTH = 2


def build_graph(snapshot: SimulationSnapshot) -> go.Figure:
    """Build the energy flow graph with house components arranged in a circle."""

    # Main nodes (text below): houses, community, grid
    main_x, main_y, main_text, main_color, main_size, main_hover, main_customdata = [], [], [], [], [], [], []

    # Component nodes (text inside): PV, base load, EV, washer
    comp_x, comp_y, comp_text, comp_color, comp_size, comp_hover, comp_customdata = [], [], [], [], [], [], []

    annotations = []
    shapes = []

    # Component arrangement around house (radius from house center)
    COMP_RADIUS = 1.2
    PV_ANGLE = math.pi / 2       # top
    BASE_ANGLE = -math.pi / 2    # bottom
    EV_ANGLE = math.pi           # left
    WASHER_ANGLE = 0             # right

    HOUSE_SPACING = 3.5

    for idx, house in enumerate(snapshot.houses):
        house_y = 6 - idx * HOUSE_SPACING
        house_x = -2

        # Main house node
        main_x.append(house_x)
        main_y.append(house_y)
        main_text.append(f"House {idx+1}")
        main_color.append("#4a90d9")
        main_size.append(40)
        main_hover.append(f"<b>House {idx+1}</b><br>Net: {_format_power(house.net_power_w)}")
        main_customdata.append({"type": "house", "id": idx})

        # PV panel (top)
        pv_x = house_x + COMP_RADIUS * math.cos(PV_ANGLE)
        pv_y = house_y + COMP_RADIUS * math.sin(PV_ANGLE)
        comp_x.append(pv_x)
        comp_y.append(pv_y)
        pv_power = house.pv_power_w
        comp_text.append(f"☀️<br>{_format_power(pv_power)}")
        comp_color.append("#f4d03f" if pv_power > 100 else "#bbb")
        comp_size.append(42)
        comp_hover.append(f"<b>PV Panel</b><br>Production: {_format_power(pv_power)}")
        comp_customdata.append({"type": "pv", "id": idx})
        # Line: PV - House
        shapes.append(dict(
            type="line", x0=pv_x, y0=pv_y, x1=house_x, y1=house_y,
            line=dict(color="#1b9e77", width=LINE_WIDTH),
        ))

        # Base load (bottom)
        base_x = house_x + COMP_RADIUS * math.cos(BASE_ANGLE)
        base_y = house_y + COMP_RADIUS * math.sin(BASE_ANGLE)
        comp_x.append(base_x)
        comp_y.append(base_y)
        base_power = house.base_load_w
        comp_text.append(f"💡<br>{_format_power(base_power)}")
        comp_color.append("#d95f02")
        comp_size.append(42)
        comp_hover.append(f"<b>Base Load</b><br>Consumption: {_format_power(base_power)}")
        comp_customdata.append({"type": "base", "id": idx, "clickable": True})
        # Line: House - Base
        shapes.append(dict(
            type="line", x0=house_x, y0=house_y, x1=base_x, y1=base_y,
            line=dict(color="#d95f02", width=LINE_WIDTH),
        ))

        # EV Charger (left)
        ev_x = house_x + COMP_RADIUS * math.cos(EV_ANGLE)
        ev_y = house_y + COMP_RADIUS * math.sin(EV_ANGLE)
        comp_x.append(ev_x)
        comp_y.append(ev_y)
        ev_power = house.ev_load_w
        ev_on = ev_power > 0
        comp_text.append(f"🚗<br>{_format_power(ev_power)}" if ev_on else "🚗<br>0kW")
        comp_color.append("#e74c3c" if ev_on else "#95a5a6")
        comp_size.append(42)
        comp_hover.append(f"<b>EV Charger</b><br>{'ON: ' + _format_power(ev_power) if ev_on else 'OFF - Click to start'}")
        comp_customdata.append({"type": "ev", "id": idx, "clickable": True})
        # Line: House - EV
        shapes.append(dict(
            type="line", x0=house_x, y0=house_y, x1=ev_x, y1=ev_y,
            line=dict(color="#e74c3c" if ev_on else "#ccc", width=LINE_WIDTH),
        ))

        # Washer (right)
        washer_x = house_x + COMP_RADIUS * math.cos(WASHER_ANGLE)
        washer_y = house_y + COMP_RADIUS * math.sin(WASHER_ANGLE)
        comp_x.append(washer_x)
        comp_y.append(washer_y)
        washer_power = house.washer_load_w
        washer_on = washer_power > 0
        comp_text.append(f"🧺<br>{_format_power(washer_power)}" if washer_on else "🧺<br>0kW")
        comp_color.append("#9b59b6" if washer_on else "#95a5a6")
        comp_size.append(42)
        comp_hover.append(f"<b>Washer</b><br>{'ON: ' + _format_power(washer_power) if washer_on else 'OFF - Click to start'}")
        comp_customdata.append({"type": "washer", "id": idx, "clickable": True})
        # Line: House - Washer
        shapes.append(dict(
            type="line", x0=house_x, y0=house_y, x1=washer_x, y1=washer_y,
            line=dict(color="#9b59b6" if washer_on else "#ccc", width=LINE_WIDTH),
        ))

        # Line from house to community (always visible)
        comm_x, comm_y = 3, 0
        flow = house.net_power_w
        flow_color = "#1b9e77" if flow > 0 else "#d95f02" if flow < 0 else "#ccc"

        # Always draw base connection line
        shapes.append(dict(
            type="line", x0=house_x, y0=house_y, x1=comm_x, y1=comm_y,
            line=dict(color="#ccc" if abs(flow) <= 10 else flow_color, width=LINE_WIDTH),
        ))

        if abs(flow) > 10:
            if flow > 0:  # Export: House -> Community
                annotations.append(dict(
                    x=comm_x, y=comm_y,
                    ax=house_x, ay=house_y,
                    xref="x", yref="y", axref="x", ayref="y",
                    showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=ARROW_WIDTH, arrowcolor=flow_color,
                ))
            else:  # Import: Community -> House
                annotations.append(dict(
                    x=house_x, y=house_y,
                    ax=comm_x, ay=comm_y,
                    xref="x", yref="y", axref="x", ayref="y",
                    showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=ARROW_WIDTH, arrowcolor=flow_color,
                ))
            # Flow label
            mid_x = (house_x + comm_x) / 2
            mid_y = (house_y + comm_y) / 2
            annotations.append(dict(
                x=mid_x + 0.3, y=mid_y,
                text=f"<b>{_format_power(abs(flow))}</b>",
                showarrow=False,
                font=dict(size=10, color=flow_color),
            ))

    # Community bus
    comm_x, comm_y = 3, 0
    main_x.append(comm_x)
    main_y.append(comm_y)
    main_text.append("Community")
    main_color.append("#3498db")
    main_size.append(60)
    main_hover.append(
        f"<b>Community Bus</b><br>"
        f"Total PV: {_format_power(snapshot.community.total_production_w)}<br>"
        f"Total Load: {_format_power(snapshot.community.total_consumption_w)}<br>"
        f"Net: {_format_power(snapshot.community.net_community_power_w)}"
    )
    main_customdata.append({"type": "community"})

    # Grid
    grid_x, grid_y = 6, 0
    main_x.append(grid_x)
    main_y.append(grid_y)
    main_text.append("Grid")
    main_color.append("#7f8c8d")
    main_size.append(55)
    main_hover.append(
        f"<b>External Grid</b><br>"
        f"Import: {_format_power(snapshot.grid.grid_import_w)}<br>"
        f"Export: {_format_power(snapshot.grid.grid_export_w)}"
    )
    main_customdata.append({"type": "grid"})

    # Community to grid connection (always visible)
    community_flow = snapshot.community.net_community_power_w
    grid_color = "#1b9e77" if community_flow > 0 else "#d95f02" if community_flow < 0 else "#ccc"

    # Always draw base connection line
    shapes.append(dict(
        type="line", x0=comm_x, y0=comm_y, x1=grid_x, y1=grid_y,
        line=dict(color="#ccc" if abs(community_flow) <= 10 else grid_color, width=LINE_WIDTH),
    ))

    if abs(community_flow) > 10:
        if community_flow > 0:  # Export
            annotations.append(dict(
                x=grid_x, y=grid_y,
                ax=comm_x, ay=comm_y,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=ARROW_WIDTH, arrowcolor=grid_color,
            ))
        else:  # Import
            annotations.append(dict(
                x=comm_x, y=comm_y,
                ax=grid_x, ay=grid_y,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=ARROW_WIDTH, arrowcolor=grid_color,
            ))
        annotations.append(dict(
            x=(comm_x + grid_x) / 2, y=0.4,
            text=f"<b>{_format_power(abs(community_flow))}</b>",
            showarrow=False,
            font=dict(size=12, color=grid_color),
        ))

    # Main nodes trace
    main_trace = go.Scatter(
        x=main_x,
        y=main_y,
        mode='markers+text',
        text=main_text,
        textposition='bottom center',
        textfont=dict(size=12, color='black', family='Arial Black'),
        hovertext=main_hover,
        hoverinfo='text',
        marker=dict(
            size=main_size,
            color=main_color,
            line=dict(width=2, color='#333'),
        ),
        customdata=main_customdata,
    )

    # Component nodes trace
    comp_trace = go.Scatter(
        x=comp_x,
        y=comp_y,
        mode='markers+text',
        text=comp_text,
        textposition='middle center',
        textfont=dict(size=10, color='black', family='Arial Black'),
        hovertext=comp_hover,
        hoverinfo='text',
        marker=dict(
            size=comp_size,
            color=comp_color,
            line=dict(width=2, color='#333'),
        ),
        customdata=comp_customdata,
    )

    # Legend with icons
    legend_annotations = [
        dict(x=7.5, y=5, text="<b>Legend</b>", showarrow=False, font=dict(size=14)),
        dict(x=7.5, y=4.2, text="☀️ PV (production)", showarrow=False, font=dict(size=13, color="#f4d03f")),
        dict(x=7.5, y=3.4, text="💡 Base load", showarrow=False, font=dict(size=13, color="#d95f02")),
        dict(x=7.5, y=2.6, text="🚗 EV 11kW", showarrow=False, font=dict(size=13, color="#e74c3c")),
        dict(x=7.5, y=1.8, text="🧺 Washer 2kW", showarrow=False, font=dict(size=13, color="#9b59b6")),
        dict(x=7.5, y=0.8, text="<b>→</b> Green = Export", showarrow=False, font=dict(size=12, color="#1b9e77")),
        dict(x=7.5, y=0.0, text="<b>→</b> Orange = Import", showarrow=False, font=dict(size=12, color="#d95f02")),
    ]

    fig = go.Figure(data=[main_trace, comp_trace])

    fig.update_layout(
        showlegend=False,
        hovermode='closest',
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-4, 9]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-10, 8], scaleanchor='x'),
        plot_bgcolor='#f8f9fa',
        paper_bgcolor='#f8f9fa',
        height=1000,
        title=dict(text="LEG Energy Flow Simulator", x=0.5, font=dict(size=20)),
        shapes=shapes,
        annotations=annotations + legend_annotations,
    )

    return fig
