# LEG-Simulator Functional Specification

## 1. Purpose

LEG-Simulator is a real-time, descriptive simulation and visualization of
instantaneous electrical energy flows within a small community of houses with
photovoltaic (PV) systems. It is explicitly **not** an optimizer. It shows what
is happening now in terms of production, consumption, and exchange of energy.

The output should be understandable to humans and precise enough to implement by
an AI coding agent.

---

## 2. Scope

### 2.1 In Scope
- Real-time (momentary) simulation of energy flows
- Community of multiple houses
- Per house:
  - PV generation
  - Baseline household consumption
  - Occasional large loads (e.g., dishwasher, EV wallbox)
- Visualization of:
  - Energy flows between houses
  - Energy exchange with an external grid / energy company
- Headless deployment on a virtual machine
- Browser-based visualization

### 2.2 Out of Scope
- Forecasting (daily, weekly, or longer)
- Optimization or scheduling logic
- Battery storage (can be added later)
- Billing, accounting, or settlement
- User authentication

---

## 3. Conceptual Model

### 3.1 Entities (Nodes)
1. **House**
   - Produces solar energy
   - Consumes energy
   - Net power may be positive (export) or negative (import)

2. **Community Bus**
   - Logical aggregation point
   - Balances surplus and deficit among houses

3. **External Grid / Energy Company**
   - Supplies energy if community is short
   - Absorbs energy if community has surplus

---

## 4. Energy Flow Logic (Non-Optimizing)

At every simulation tick:

1. Each house reports:
   - Current PV production (W)
   - Current consumption (W)

2. Net power per house is computed:

```text
net_power = production - consumption
```

3. Community aggregation:
   - All positive net powers contribute to community surplus
   - All negative net powers contribute to community demand

4. External grid interaction:
   - If community surplus > 0: export to grid
   - If community deficit > 0: import from grid

No decisions are made to shift loads or change behavior.

---

## 5. Time Model

- Simulation operates in real time
- Typical update interval: 0.5 s to 2 s (configurable)
- Each update represents “now”, not a future or averaged state

---

## 6. Data Model

### 6.1 House State

```json
{
  "house_id": "house_1",
  "pv_power_w": 3200,
  "base_load_w": 450,
  "flex_load_w": 0,
  "net_power_w": 2750
}
```

### 6.2 Community State

```json
{
  "total_production_w": 12500,
  "total_consumption_w": 9800,
  "net_community_power_w": 2700
}
```

### 6.3 Grid Exchange

```json
{
  "grid_import_w": 0,
  "grid_export_w": 2700
}
```

---

## 7. Visualization Requirements

### 7.1 Visual Metaphor
Directed graph (network diagram)

**Nodes**
- Houses
- Community bus
- External grid

**Edges**
- Represent power flow direction
- Thickness proportional to absolute power

**Color**
- Green: export
- Red: import
- Grey: zero / idle

### 7.2 Interactivity
- Hover on nodes:
  - Show production, consumption, net power
- Hover on edges:
  - Show instantaneous power flow (W)
- Live updates without page reload

---

## 8. Technical Architecture

### 8.1 Runtime Environment
- Python 3.10+
- Headless Linux VM
- No local GUI required

### 8.2 Python Libraries
**Mandatory**
- dash
- plotly

**Optional**
- networkx (graph layout)
- asyncio (timing loop)

---

## 9. Application Structure

```text
energy-flow-sim/
├── app.py              # Dash application entry point
├── model.py            # Energy model and state update logic
├── simulation.py       # Real-time simulation loop
├── layout.py           # Dash layout and graph definition
├── config.yaml         # Number of houses, update rate
└── README.md
```

---

## 10. Dash Application Behavior

- Dash server listens on configurable port (default: 8050)
- Single-page application
- Graph auto-refreshes based on simulation ticks
- Stateless frontend; all state held in Python backend

---

## 11. Configuration Parameters

```yaml
houses: 5
update_interval_ms: 1000
pv_variation: enabled
flex_load_probability: 0.1
```

---

## 12. Extensibility Hooks

The design must allow later addition of:
- Batteries
- Price signals
- Optimization layer
- Control signals (e.g., “start EV charging now”)

These must not be implemented in this version.

---

## 13. Success Criteria

- System runs on a headless VM
- Accessible via browser
- Energy flows update in real time
- Visualization clearly shows:
  - Who produces
  - Who consumes
  - Where surplus or deficit goes
