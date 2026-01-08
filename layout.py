import math

import plotly.graph_objects as go

from simulation import SimulationSnapshot


def _node_trace(nodes: list[dict]) -> go.Scatter:
    return go.Scatter(
        x=[node["x"] for node in nodes],
        y=[node["y"] for node in nodes],
        mode="markers+text",
        text=[node["label"] for node in nodes],
        textposition="bottom center",
        hovertext=[node["hover"] for node in nodes],
        hoverinfo="text",
        marker=dict(size=30, color="#1f6f8b", line=dict(width=2, color="#0b2b3b")),
    )


def _edge_traces(edges: list[dict]) -> list[go.Scatter]:
    traces = []
    for edge in edges:
        traces.append(
            go.Scatter(
                x=[edge["x0"], edge["x1"]],
                y=[edge["y0"], edge["y1"]],
                mode="lines",
                line=dict(width=edge["width"], color=edge["color"]),
                hovertext=edge["hover"],
                hoverinfo="text",
            )
        )
    return traces


def _layout_positions(house_count: int) -> dict[str, tuple[float, float]]:
    positions: dict[str, tuple[float, float]] = {}
    radius = 2.8
    angle_step = math.tau / max(house_count, 1)
    for idx in range(house_count):
        angle = math.pi + idx * angle_step
        positions[f"house_{idx + 1}"] = (
            radius * math.cos(angle) - 2.5,
            radius * math.sin(angle),
        )
    positions["community"] = (0.0, 0.0)
    positions["grid"] = (4.0, 0.0)
    return positions


def build_graph(snapshot: SimulationSnapshot) -> go.Figure:
    positions = _layout_positions(len(snapshot.houses))
    nodes = []
    edges = []

    for house in snapshot.houses:
        x, y = positions[house.house_id]
        nodes.append(
            {
                "x": x,
                "y": y,
                "label": house.house_id.replace("_", " "),
                "hover": (
                    f"{house.house_id}<br>PV: {house.pv_power_w} W"
                    f"<br>Base: {house.base_load_w} W"
                    f"<br>Flex: {house.flex_load_w} W"
                    f"<br>Net: {house.net_power_w} W"
                ),
            }
        )

        flow = house.net_power_w
        if abs(flow) < 1.0:
            color = "#b0b0b0"
            width = 1
        elif flow > 0:
            color = "#1b9e77"
            width = 2 + min(flow / 800.0, 8)
        else:
            color = "#d95f02"
            width = 2 + min(abs(flow) / 800.0, 8)

        x0, y0 = (x, y)
        x1, y1 = positions["community"]
        edges.append(
            {
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1,
                "color": color,
                "width": width,
                "hover": f"{house.house_id} -> bus: {flow} W",
            }
        )

    nodes.append(
        {
            "x": positions["community"][0],
            "y": positions["community"][1],
            "label": "Community Bus",
            "hover": (
                f"Community Bus<br>Total PV: {snapshot.community.total_production_w} W"
                f"<br>Total Load: {snapshot.community.total_consumption_w} W"
                f"<br>Net: {snapshot.community.net_community_power_w} W"
            ),
        }
    )
    nodes.append(
        {
            "x": positions["grid"][0],
            "y": positions["grid"][1],
            "label": "External Grid",
            "hover": (
                f"External Grid<br>Import: {snapshot.grid.grid_import_w} W"
                f"<br>Export: {snapshot.grid.grid_export_w} W"
            ),
        }
    )

    community_flow = snapshot.community.net_community_power_w
    if abs(community_flow) < 1.0:
        color = "#b0b0b0"
        width = 1
    elif community_flow > 0:
        color = "#1b9e77"
        width = 2 + min(community_flow / 800.0, 10)
    else:
        color = "#d95f02"
        width = 2 + min(abs(community_flow) / 800.0, 10)

    edges.append(
        {
            "x0": positions["community"][0],
            "y0": positions["community"][1],
            "x1": positions["grid"][0],
            "y1": positions["grid"][1],
            "color": color,
            "width": width,
            "hover": f"Bus -> Grid: {community_flow} W",
        }
    )

    fig = go.Figure(data=_edge_traces(edges) + [_node_trace(nodes)])
    fig.update_layout(
        showlegend=False,
        hovermode="closest",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="#f5f3ea",
        paper_bgcolor="#f5f3ea",
        annotations=[],
    )

    return fig
