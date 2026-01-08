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
  - Interactive toggles for EV charger and washer
- Visualization of:
  - Energy flows between houses
  - Energy exchange with an external grid / energy company
- Headless deployment on a virtual machine
- Browser-based visualization
- CSV logging of simulation data for later analysis

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
   - Contains toggleable flex loads (EV charger, washer)

2. **Community Bus**
   - Logical aggregation point
   - Balances surplus and deficit among houses

3. **External Grid / Energy Company**
   - Supplies energy if community is short
   - Absorbs energy if community has surplus
   - Unlimited capacity (no upper bounds on import/export)

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
- Update interval: 10 seconds (configurable in config.yaml)
- Each update represents “now”, not a future or averaged state
- Configuration is loaded at simulation start from config.yaml (no runtime reload)

---

## 6. Data Model

### 6.1 House State

```json
{
  "house_id": "house_1",
  "pv_power_w": 3200,
  "base_load_w": 450,
  "flex_load_w": 0,
  "net_power_w": 2750,
  "ev_on": false,
  "washer_on": false,
  "ev_load_w": 11000,
  "washer_load_w": 2000
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

**Labels**
- Numeric labels on nodes and edges by default
- Hover still shows full details
- Display kW for production, consumption, and net values

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
- Click on a house node to access controls with one button per EV charger/washer toggle

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
```

Configuration is read once at startup.

---

## 12. Load Modeling

- All values start at 0 and are user-settable via click-to-edit
- No random variation - values remain fixed until changed by user
- PV generation: user-defined per house (click on PV icon)
- Base load: user-defined per house (click on base load icon)
- EV charger draw: 11 kW when enabled (click to toggle)
- Washer draw: 2 kW when enabled (click to toggle)
- EV and washer can run simultaneously per house

---

## 12.1 Energy Pricing

User-configurable energy prices (ct/kWh):
- Grid Delivery (sell to grid): default 6 ct/kWh
- Grid Consumption (buy from grid): default 30 ct/kWh
- PV Delivery (sell PV to community): default 20 ct/kWh
- House Consumption (buy from community): default 25 ct/kWh

---

## 12.2 Pricing Table

The pricing table shows costs (ct/h) with 7 columns:
- **House Buy/Sell**: Net exchange between house and community
- **Community Buy/Sell**: What community pays/earns from houses and grid
- **Grid Buy/Sell**: External grid exchange (shown in Grid row and TOTAL)

Row structure:
- Individual house rows (House 1, House 2, ...)
- Grid row (showing community-grid exchange)
- TOTAL row (aggregated values)

---

## 13. Data Logging

- Append simulation data to a CSV file for future analysis.
- Logged values should include timestamp, per-house values, and community/grid totals.
- Append cadence: every simulation tick.
- Default log path: data/leg_simulator_log.csv.
- Row format: one row per house per tick.

---

## 14. Layout

- Preferred layout: use networkx for node positioning when available.
- Fallback: deterministic layout if networkx is unavailable.

---

## 15. Extensibility Hooks

The design must allow later addition of:
- Batteries
- Price signals
- Optimization layer
- Control signals (e.g., “start EV charging now”)

These must not be implemented in this version.

---

## 16. Success Criteria

- System runs on a headless VM
- Accessible via browser
- Energy flows update in real time
- Visualization clearly shows:
  - Who produces
  - Who consumes
  - Where surplus or deficit goes
- Interactive toggles affect house load and flows
- CSV log grows over time without interrupting the UI
