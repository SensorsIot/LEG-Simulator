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

On each update:

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

- Simulation updates on user input (no periodic refresh)
- Each update represents "now", not a future or averaged state

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
└── README.md
```

---

## 10. Dash Application Behavior

- Dash server listens on configurable port (default: 8050)
- Single-page application
- Graph updates on user input changes
- Stateless frontend; all state held in Python backend

---

## 11. Configuration

- Number of houses: hardcoded to 5 in `app.py`
- Energy prices: configurable via UI inputs

---

## 12. Load Modeling

- All values are user-settable via click-to-edit (opens modal input)
- PV generation: starts at 0, user-defined per house
- Base load: random initial value 500-2000W (rounded to 100W), user-editable
- EV charger: starts at 0, user-defined power (click to edit)
- Washer: starts at 0, user-defined power (click to edit)
- All loads can run simultaneously per house
- Values persist until changed by user or server restart

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

## 12.3 Economic Model and Break-Even Analysis

### 12.3.1 Three-Party Transaction Model

Energy flows through three parties, each with distinct buy/sell relationships:

```
┌─────────┐         ┌───────────┐         ┌──────┐
│  Houses │ ←─────→ │ Community │ ←─────→ │ Grid │
└─────────┘         └───────────┘         └──────┘
```

**Transaction Rules:**
1. Houses trade exclusively with the Community (not directly with Grid)
2. Community aggregates all house transactions
3. Community trades surplus/deficit with Grid

### 12.3.2 Price Parameters

**Unit Convention:** All prices are in ct/kWh. Energy values (P, C, N, E, I) are in kWh
per settlement interval. Assuming one calculation per hour, kW numerically equals kWh/h.
Costs in the pricing table are displayed as ct/h.

| Symbol | Description | Default | Unit |
|--------|-------------|---------|------|
| p_pv | PV Delivery (house sells to community) | 20 | ct/kWh |
| p_con | House Consumption (house buys from community) | 25 | ct/kWh |
| p_grid_del | Grid Delivery (community sells to grid) | 6 | ct/kWh |
| p_grid_con | Grid Consumption (community buys from grid) | 30 | ct/kWh |

### 12.3.3 Mathematical Formulation

**Variables:**
- n = number of houses
- P_i = PV production of house i (kWh)
- C_i = consumption of house i (kWh)
- N_i = P_i - C_i = net energy of house i (positive = export, negative = import)

**Aggregated Values:**
- E = Σ{max(0, N_i)} = total exports from houses (kWh)
- I = Σ{max(0, -N_i)} = total imports to houses (kWh)
- Community_Net = E - I = Σ N_i (positive = surplus, negative = deficit)

### 12.3.4 Community Profit Function

The community's financial position depends on the spread between buying and selling prices.

**Case 1: Community Surplus (E > I)**
```
Community_Buy  = E × p_pv                      (buying from exporting houses)
Community_Sell = I × p_con + (E - I) × p_grid_del  (selling to houses + grid)

Profit = Community_Sell - Community_Buy
       = I × p_con + (E - I) × p_grid_del - E × p_pv
       = I × (p_con - p_grid_del) - E × (p_pv - p_grid_del)
```

With default prices: `Profit = 19×I - 14×E`

**Case 2: Community Deficit (I > E)**
```
Community_Buy  = E × p_pv + (I - E) × p_grid_con  (buying from houses + grid)
Community_Sell = I × p_con                        (selling to importing houses)

Profit = Community_Sell - Community_Buy
       = I × p_con - E × p_pv - (I - E) × p_grid_con
       = I × (p_con - p_grid_con) + E × (p_grid_con - p_pv)
```

With default prices: `Profit = -5×I + 10×E`

### 12.3.5 Break-Even Conditions

For Community Profit = 0:

**Surplus Mode (E > I):**
```
I = [(p_pv - p_grid_del) / (p_con - p_grid_del)] × E
```
With default prices: `I = (14/19) × E ≈ 0.737 × E`

**Deficit Mode (I > E):**
```
I = [(p_grid_con - p_pv) / (p_grid_con - p_con)] × E
```
With default prices: `I = (10/5) × E = 2 × E`

### 12.3.6 Profit Regions

```
I (imports)
│
│     Deficit Mode
│     Community LOSS
│         ╱
│        ╱  Break-even: I = 2E
│       ╱
│      ╱
│     ╱   Community PROFIT
│    ╱         (between break-even lines)
│   ╱
│  ╱  Break-even: I = 0.737E
│ ╱
│╱    Surplus Mode
│     Community LOSS
└─────────────────────────── E (exports)
```

**Key Insight:** The community profits when imports are between 73.7% and 200% of exports, due to favorable spreads on internal trading vs. unfavorable spreads on grid trading.

### 12.3.7 Closed-Form Break-Even Optimization

The break-even house consumption price can be solved with a single closed-form equation per settlement period.

#### Inputs for the Period

From metering/forecast:
- E = Σᵢ max(0, Nᵢ) — total house exports to community (kWh)
- I = Σᵢ max(0, -Nᵢ) — total house imports from community (kWh)

Fixed parameters:
- p_pv — what community pays exporting houses (ct/kWh)
- p_grid_del — what community gets for exporting to grid (ct/kWh)
- p_grid_con — what community pays for importing from grid (ct/kWh)

**Decision variable** (the only optimized parameter):
- p_con — house consumption price (what houses pay community)

**Goal:** Community profit = 0 for that period.

#### Step 1: Unified Profit Expression

Community buys:
- From houses: E × p_pv
- From grid (if deficit): max(0, I - E) × p_grid_con

Community sells:
- To houses: I × p_con
- To grid (if surplus): max(0, E - I) × p_grid_del

Profit equation:
```
Π = I × p_con + max(0, E-I) × p_grid_del - E × p_pv - max(0, I-E) × p_grid_con
```

Break-even condition: Π = 0. Solve for p_con.

#### Step 2: Closed-Form Solution

**Case A: Surplus Period (E ≥ I)**
```
0 = I × p_con + (E - I) × p_grid_del - E × p_pv

p_con = [E × p_pv - (E - I) × p_grid_del] / I
```

Equivalent form:
```
p_con = p_grid_del + (E/I) × (p_pv - p_grid_del)
```

**Case B: Deficit Period (I > E)**
```
0 = I × p_con - E × p_pv - (I - E) × p_grid_con

p_con = [E × p_pv + (I - E) × p_grid_con] / I
```

Equivalent form:
```
p_con = p_grid_con + (E/I) × (p_pv - p_grid_con)
```

#### Compact Single Expression

Define:
```
p_grid(E, I) = p_grid_del  if E ≥ I (surplus)
             = p_grid_con  if I > E (deficit)
```

Then:
```
p_con = p_grid(E,I) + (E/I) × (p_pv - p_grid(E,I))
```

**Interpretation:** p_con is a weighted blend between p_pv and the relevant grid price, weighted by the ratio E/I.

#### Step 3: Edge Cases

**If I = 0** (no house imports):
- Cannot finance payments to exporters via p_con
- Break-even is impossible unless p_pv = p_grid_del
- In code: return "undefined" or settle via grid only

**If E = 0** (no PV exports):
- Deficit formula gives p_con = p_grid_con
- Community is just pass-through from grid

#### Step 4: Interpretation (Sanity Check)

- In deficit: p_con lies between p_grid_con and p_pv (since typically p_pv < p_grid_con), pulled toward p_pv as PV share increases
- In surplus: p_con can rise above p_pv if E/I is large (few consumers must cover many exporters) — economically correct but may need policy caps/floors

#### Algorithm per Period

```
1. Compute E and I from metering
2. If I == 0: declare infeasible (or apply fallback)
3. Else:
   - If E ≥ I: p_con = p_grid_del + (E/I) × (p_pv - p_grid_del)
   - Else:     p_con = p_grid_con + (E/I) × (p_pv - p_grid_con)
4. Optionally clamp p_con to allowed tariff bounds
```

### 12.3.8 Worked Example

Given pricing table with fixed p_con = 25 ct/kWh:

| House | Buy (ct/h) | Sell (ct/h) |
|-------|------------|-------------|
| House 1 | 0.0 | 200.0 |
| House 2 | 275.0 | 0.0 |
| Grid | 30.0 (buy) | 0.0 |

**Step 1: Derive E and I**

House 1 (exporter): sells 200 ct/h at p_pv = 20 ct/kWh
```
E = 200 / 20 = 10 kWh
```

House 2 (importer): buys 275 ct/h at p_con = 25 ct/kWh
```
I = 275 / 25 = 11 kWh
```

Deficit from grid: I - E = 1 kWh (matches Grid row: 30 ct/h ÷ 30 ct/kWh = 1 kWh)

**Step 2: Calculate Break-Even p_con**

Since I > E (deficit period):
```
I × p_con = E × p_pv + (I - E) × p_grid_con
11 × p_con = 10 × 20 + 1 × 30 = 200 + 30 = 230
p_con = 230 / 11 = 20.909... ≈ 20.91 ct/kWh
```

**Step 3: Verify**

At p_con = 20.91 ct/kWh:
- Community sells to houses: 11 × 20.91 ≈ 230 ct/h
- Community buys: 200 + 30 = 230 ct/h
- **Profit = 0** ✓

**Result:** With the fixed price of 25 ct/kWh, community makes 45 ct/h profit. The true break-even price is **20.91 ct/kWh**.

---

## 13. Extensibility Hooks

The design must allow later addition of:
- Price signals
- Control signals (e.g., "start EV charging now")

These must not be implemented in this version.

---

## 14. Success Criteria

- System runs on a headless VM
- Accessible via browser
- Energy flows update in real time
- Visualization clearly shows:
  - Who produces
  - Who consumes
  - Where surplus or deficit goes
- Interactive toggles affect house load and flows
