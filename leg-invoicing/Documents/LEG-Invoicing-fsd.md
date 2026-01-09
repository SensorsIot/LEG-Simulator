# LEG-Invoicing Functional Specification

## 1. Purpose

LEG-Invoicing provides billing and invoicing functionality for Local Energy Grid (LEG) communities. It generates invoices based on energy flows between houses, the community, and the external grid.

---

## 2. Scope

### 2.1 In Scope
- Invoice generation for community members
- Energy consumption/production tracking
- Pricing calculations based on LEG-Simulator pricing model
- Invoice export (PDF, CSV)
- Settlement period management

### 2.2 Out of Scope
- Real-time energy flow visualization (handled by LEG-Simulator)
- Payment processing
- Bank integration
- Tax calculations

---

## 3. Data Model

### 3.1 Invoice

```json
{
  "invoice_id": "INV-2026-001",
  "house_id": "house_1",
  "period_start": "2026-01-01T00:00:00Z",
  "period_end": "2026-01-31T23:59:59Z",
  "energy_exported_kwh": 450.5,
  "energy_imported_kwh": 120.3,
  "export_revenue_ct": 9010,
  "import_cost_ct": 3007.5,
  "net_amount_ct": 6002.5,
  "status": "pending"
}
```

### 3.2 Settlement Period

```json
{
  "period_id": "2026-01",
  "start": "2026-01-01T00:00:00Z",
  "end": "2026-01-31T23:59:59Z",
  "status": "open",
  "invoices": []
}
```

---

## 4. Pricing Integration

Uses the same pricing model as LEG-Simulator (Section 12.3):

| Parameter | Description | Default |
|-----------|-------------|---------|
| p_pv | PV Delivery (house sells to community) | 20 ct/kWh |
| p_con | House Consumption (house buys from community) | 25 ct/kWh |
| p_grid_del | Grid Delivery (community sells to grid) | 6 ct/kWh |
| p_grid_con | Grid Consumption (community buys from grid) | 30 ct/kWh |

---

## 5. Technical Architecture

### 5.1 Runtime Environment
- Python 3.10+
- Shared deployment with LEG-Simulator

### 5.2 Dependencies
- dash (web interface)
- pandas (data processing)
- weasyprint or reportlab (PDF generation)

---

## 6. Deployment

| Component | Value |
|-----------|-------|
| Server | LEG-Configurator |
| URL | https://provision.dhamstack.com:TBD |
| Path | /root/LEG-Software/leg-invoicing/ |

---

## 7. Future Extensions

- Integration with smart meter data
- Automated invoice delivery via email
- Multi-community support

---

## 8. MQTT Data Source

### 8.1 Overview

LEG-Invoicing receives energy metering data from smart meters via MQTT. One real smart meter provides data for House 1, while houses 2-5 are simulated by the `leg-mqtt-simulator` component.

### 8.2 MQTT Broker

| Parameter | Value |
|-----------|-------|
| Host | provision.dhamstack.com |
| Port (VPN) | 1883 (10.0.0.1, anonymous) |
| Port (Public) | 8883 (TLS, password auth) |
| Topic Pattern | `{MAC}/SENSOR` |

### 8.3 Message Format

```json
{
  "SMid": "60222760",
  "Pi": 1.047,
  "Po": 0.000,
  "I1": 0.392,
  "I2": 0.054,
  "I3": 0.096,
  "Ei": 4619.712,
  "Eo": 14089.216,
  "Q5": 18.862,
  "Q6": 12.491,
  "Q7": 1932.711,
  "Q8": 3664.889,
  "ts": 12589
}
```

**Key Fields:**
| Field | Description | Unit |
|-------|-------------|------|
| Pi | Instantaneous power IN (consumption) | kW |
| Po | Instantaneous power OUT (PV export) | kW |
| Ei | Cumulative energy IN (ever-increasing total) | kWh |
| Eo | Cumulative energy OUT (ever-increasing total) | kWh |
| ts | Timestamp (incrementing seconds) | s |

**Invoice Calculation:** Uses delta between consecutive `Ei`/`Eo` values over the settlement period.

### 8.4 House Configuration

| House | MAC Address | Data Source | PV | EV |
|-------|-------------|-------------|-----|-----|
| 1 | B0-81-84-25-22-5C | Real smart meter | Yes | No |
| 2 | AA-11-BB-22-CC-01 | Simulated | 10 kWp | Yes (day) |
| 3 | AA-11-BB-22-CC-02 | Simulated | 20 kWp | Yes (night) |
| 4 | AA-11-BB-22-CC-03 | Simulated | None | No |
| 5 | AA-11-BB-22-CC-04 | Simulated | None | No |

---

## 9. MQTT Simulator (leg-mqtt-simulator)

### 9.1 Purpose

Generates realistic smart meter data for 4 simulated houses to complement the real House 1 data, enabling full LEG community simulation.

### 9.2 Update Frequency

- **Interval:** 10 seconds
- **Topic:** `{MAC}/SENSOR` per house

### 9.3 Simulated Components

| Component | Details |
|-----------|---------|
| Base load | 500W day / 200W night (±20% random variation) |
| PV production | Based on Swiss solar irradiance data for Basel, scaled by kWp |
| Washing machine | 2 kW × 2 hours, once per week |
| Dishwasher | 1.5 kW × 1.5 hours, every 2 days |
| EV charger | 11 kW × ~4.5 hours (50 kWh), twice per week |

### 9.4 House Configuration

| House | PV | EV |
|-------|-----|-----|
| 2 | 10 kWp | Day charging (10:00-15:00) |
| 3 | 20 kWp | Night charging (22:00-03:00) |
| 4 | None | None |
| 5 | None | None |

### 9.5 Time Simulation

The simulator operates with a **6-month time offset** to enable realistic summer PV production testing:

| Real Time | Simulated Time |
|-----------|----------------|
| January | July |
| February | August |

This ensures full PV production curves during winter testing.

### 9.6 Energy Accumulator Logic

The simulator maintains cumulative `Ei` and `Eo` counters per house:

```python
# Every 10 seconds:
net_power = base_load + appliances - pv_production

if net_power > 0:
    Ei += net_power * (10 / 3600)  # Importing (kWh)
else:
    Eo += abs(net_power) * (10 / 3600)  # Exporting (kWh)
```

### 9.8 State Storage (InfluxDB)

The simulator writes appliance state directly to InfluxDB at startup and on every change.

**Measurement:** `simulator_state`

| Field | Type | Description |
|-------|------|-------------|
| pv_kwp | float | PV system size |
| has_ev | int | 1 if house has EV, 0 otherwise |
| washing_active | int | 1 if washing machine running |
| dishwasher_active | int | 1 if dishwasher running |
| ev_active | int | 1 if EV charging |

**Tag:** house_id


### 9.7 Deployment

| Parameter | Value |
|-----------|-------|
| Location | /root/LEG-Software/leg-mqtt-simulator/ |
| Broker | 10.0.0.1:1883 |
| Service | leg-mqtt-simulator.service |


---

## 10. Data Storage (InfluxDB)

### 10.1 Overview

Energy data is stored in InfluxDB, a time-series database optimized for high-volume measurements.

### 10.2 Connection Details

| Parameter | Value |
|-----------|-------|
| Server | provision.dhamstack.com |
| Port (Internal) | 8086 |
| Port (External/HTTPS) | 8087 |
| Organization | LEG |
| Bucket | energy |
| User | admin |

### 10.3 Measurements

#### house_energy (per-house data)

| Field | Type | Description |
|-------|------|-------------|
| delta_ei_kwh | float | Energy consumed this interval |
| delta_eo_kwh | float | Energy exported this interval |
| value_consumption_ct | float | delta_ei × p_con |
| value_pv_delivery_ct | float | delta_eo × p_pv |
| tariff_p_con | float | Applied consumption tariff |
| tariff_p_pv | float | Applied PV delivery tariff |

**Tags:** house_id, mac

#### community_energy (aggregated data)

| Field | Type | Description |
|-------|------|-------------|
| total_consumption_kwh | float | Sum of all house consumption |
| total_production_kwh | float | Sum of all house production |
| grid_import_kwh | float | Energy bought from grid |
| grid_export_kwh | float | Energy sold to grid |
| value_grid_import_ct | float | grid_import × p_grid_con |
| value_grid_export_ct | float | grid_export × p_grid_del |
| tariff_p_grid_con | float | Applied grid consumption tariff |
| tariff_p_grid_del | float | Applied grid delivery tariff |

### 10.4 Data Flow

```
MQTT Messages → Collector → InfluxDB
     ↓              ↓
  Ei/Eo        Calculate deltas
  values       Apply tariffs
               Store every 10s
```

---

## 11. Configuration

### 11.1 Overview

All services use a centralized YAML configuration file (`config.yaml`). A template is provided in `config.example.yaml`.

### 11.2 Configuration File Structure

```yaml
mqtt:
  broker: "provision.dhamstack.com"
  port: 8883
  use_tls: true
  username: "..."
  password: "..."

influxdb:
  url: "https://provision.dhamstack.com:8087"
  token: "..."
  org: "LEG"
  bucket: "energy"

houses:
  "B0-81-84-25-22-5C":
    id: 1
    name: "House 1"
    type: "real"
  # ... more houses

tariffs:
  p_pv: 20.0
  p_grid_del: 6.0
  p_grid_con: 30.0

collector:
  interval: 60

web:
  host: "0.0.0.0"
  port: 8060

logging:
  level: "INFO"
  file: null
```

### 11.3 Environment-Specific Settings

| Setting | Local Development | Remote Server |
|---------|-------------------|---------------|
| MQTT Broker | provision.dhamstack.com:8883 | 10.0.0.1:1883 |
| MQTT TLS | Yes | No |
| InfluxDB URL | https://provision...:8087 | http://localhost:8086 |

### 11.4 Git Strategy

- `config.example.yaml` - Committed (template)
- `config.yaml` - Ignored (contains secrets)

---

## 12. Development Environment

### 12.1 Local Development

Development is performed on the local machine with deployment to the remote server.

| Component | Local Path |
|-----------|------------|
| Repository | /home/energymanagement/LEG-Software/ |
| Invoicing UI | leg-invoicing-ui/ |
| MQTT Simulator | leg-mqtt-simulator/ |
| Documentation | leg-invoicing/Documents/ |

### 12.2 Deployment Workflow

```
1. Edit code locally
2. git commit && git push
3. SSH to remote: git pull
4. Restart services
```

### 12.3 Remote Server

| Service | URL | Port |
|---------|-----|------|
| Tariff UI | https://provision.dhamstack.com:8052 | 8052 |
| InfluxDB | https://provision.dhamstack.com:8087 | 8087 |
| LEG-Simulator | https://provision.dhamstack.com:8051 | 8051 |
| Provisioning | https://provision.dhamstack.com:5000 | 5000 |

---

## 13. Tariff UI (leg-invoicing-ui)

### 13.1 Purpose

Web interface for managing energy tariffs used in invoice calculations.

### 13.2 Features

- Input table for configurable tariffs (p_pv, p_grid_del, p_grid_con)
- Auto-calculated house tariff: p_con = (p_pv + p_grid_con) / 2
- REST API for tariff management
- Real-time updates via JavaScript

### 13.3 Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| / | GET | Tariff management UI |
| /api/tariffs | GET | Get current tariffs |
| /api/tariffs | POST | Update tariffs |

### 13.4 Technology Stack

- Flask (Python web framework)
- HTML/CSS/JavaScript frontend
- tariffs.json (persistent storage)

---

## 14. Grafana Dashboards

### 14.1 Overview

Energy data is visualized through Grafana dashboards accessible at http://192.168.0.203:3000

### 14.2 Dashboards

| Dashboard | UID | Description |
|-----------|-----|-------------|
| LEG Community | leg-community | Aggregated community energy and value flows, price signal |
| LEG Grid | leg-grid | Grid import/export energy and value flows |
| LEG House 1-5 | leg-house-{1-5} | Per-house energy and value flows |

### 14.3 Dashboard Panels

**Community Dashboard:**
- Energy Flow (kWh) - Total consumption (negative), total production
- Value Flow (ct) - Consumption cost (negative), PV delivery credit
- Price Signal (ct/kWh) - Calculated house consumption tariff (p_consumption)

**Grid Dashboard:**
- Energy Flow (kWh) - Grid import (negative), grid export
- Value Flow (ct) - Grid import cost (negative), grid export revenue

**House Dashboards:**
- Energy Flow (kWh) - Consumption (negative), production, net flow
- Value Flow (ct) - Consumption cost (negative), PV delivery credit

### 14.4 Grafana Access

| Parameter | Value |
|-----------|-------|
| URL | http://192.168.0.203:3000 |
| Username | admin |
| Datasource | InfluxDB (uid: af9l1jbyffri8c) |

---

## 15. Systemd Services

### 15.1 Service Overview

All components run as systemd services with auto-restart on failure.

| Service | Description | Working Directory |
|---------|-------------|-------------------|
| leg-mqtt-simulator | MQTT data generator | /root/LEG-Software/leg-mqtt-simulator |
| leg-collector | Data aggregation to InfluxDB | /root/LEG-Software/leg-invoicing-ui |
| leg-invoicing-ui | Tariff management UI | /root/LEG-Software/leg-invoicing-ui |
| leg-simulator | Energy visualization | /root/LEG-Software/leg-simulator |

### 15.2 Service Management

```bash
# Check all services
systemctl status leg-mqtt-simulator leg-collector leg-invoicing-ui leg-simulator

# Restart a service
systemctl restart leg-collector

# View logs
journalctl -u leg-collector -f

# Enable on boot
systemctl enable leg-mqtt-simulator leg-collector leg-invoicing-ui leg-simulator
```

### 15.3 Service Files

Location: `/etc/systemd/system/`

**leg-collector.service:**
```ini
[Unit]
Description=LEG Energy Collector
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/LEG-Software/leg-invoicing-ui
ExecStart=/usr/bin/python3 collector.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 15.4 Data Collection Interval

The collector aggregates MQTT messages and stores to InfluxDB every **60 seconds**.

### 12.3.9 Surplus Edge Case: Capped House Price with Adjusted PV Tariff

In surplus periods (E > I), the standard break-even formula may yield a house consumption price exceeding the grid import price, which is economically undesirable. In this case, we cap the house price and instead adjust the PV tariff to achieve break-even.

#### Problem

When E >> I (large surplus), the break-even p_con can exceed p_grid_con, making community energy more expensive than grid energy for consumers.

#### Solution

**Step 1:** Cap house consumption tariff to grid import price:
```
p_con := min(p_con_policy, p_grid_con)
```

**Step 2:** Compute PV tariff that yields community profit = 0:
```
p_pv_BE = [I × p_con + (E - I) × p_grid_del] / E
```

**Step 3:** Apply PV tariff (cap to policy maximum):
```
p_pv := min(p_pv_policy, p_pv_BE)
```

#### Intuition

In surplus periods, the communitys PV payout must equal the average revenue per PV kWh, which is a blend of:

#### Problem

When E >> I (large surplus), the break-even p_con can exceed p_grid_con, making community energy more expensive than grid energy for consumers.

#### Solution

**Step 1:** Cap house consumption tariff to grid import price:

    p_con := min(p_con_policy, p_grid_con)

**Step 2:** Compute PV tariff that yields community profit = 0:

    p_pv_BE = [I * p_con + (E - I) * p_grid_del] / E

**Step 3:** Apply PV tariff (cap to policy maximum):

    p_pv := min(p_pv_policy, p_pv_BE)

#### Intuition

In surplus periods, the community PV payout must equal the average revenue per PV kWh, which is a blend of:

* Internal revenue from the I kWh sold to houses at p_con
* Grid-export revenue for the (E - I) kWh at p_grid_del

That average is exactly:

    p_pv_BE = [I * p_con + (E - I) * p_grid_del] / E

#### Worked Example

Given: E = 100 kWh, I = 20 kWh, p_grid_con = 30 ct/kWh, p_grid_del = 6 ct/kWh, p_pv_policy = 20 ct/kWh

**Standard formula would give:**

    p_con = p_grid_del + (E/I) * (p_pv - p_grid_del)
          = 6 + (100/20) * (20 - 6)
          = 6 + 5 * 14 = 76 ct/kWh  <-- exceeds grid price!

**With capped house price:**

    p_con = min(76, 30) = 30 ct/kWh

    p_pv_BE = [20 * 30 + 80 * 6] / 100
            = [600 + 480] / 100
            = 10.8 ct/kWh

    p_pv = min(20, 10.8) = 10.8 ct/kWh

**Verification:**

* Community buys from houses: 100 * 10.8 = 1080 ct
* Community sells to houses: 20 * 30 = 600 ct
* Community sells to grid: 80 * 6 = 480 ct
* Total revenue: 600 + 480 = 1080 ct
* Profit = 0 (verified)

#### Algorithm Update

    1. Compute E and I from metering
    2. If I == 0: declare infeasible (or apply fallback)
    3. If E >= I (surplus):
       a. p_con_calc = p_grid_del + (E/I) * (p_pv_policy - p_grid_del)
       b. If p_con_calc > p_grid_con:
          - p_con = p_grid_con
          - p_pv = [I * p_con + (E - I) * p_grid_del] / E
       c. Else:
          - p_con = p_con_calc
          - p_pv = p_pv_policy
    4. Else (deficit):
       - p_con = p_grid_con + (E/I) * (p_pv_policy - p_grid_con)
       - p_pv = p_pv_policy

---

## 16. Layman Summary: How House Tariffs Work

### The Community Energy Market

Think of the community as a small energy market where:
- **Houses with solar panels** sell their excess electricity
- **Houses without solar** (or using more than they produce) buy electricity
- **The community** acts as the middleman, balancing supply and demand

### The Goal: Break-Even Pricing

The community does not aim to make profit. Instead, it sets prices so that:
- Money paid by consumers = Money paid to PV producers

### Two Scenarios

**Scenario 1: Sunny Day (More Solar Than Needed)**

When the community produces more solar than it consumes:
- Extra energy is sold to the external grid (at a low price, ~6 ct/kWh)
- To break even, PV producers receive less than if all energy was used internally
- House purchase price stays reasonable (capped at grid price of 30 ct/kWh)

*Example: If the community produces 100 kWh but only uses 20 kWh, the PV producers get a blend of: the good internal price for 20 kWh + the low grid price for 80 kWh.*

**Scenario 2: Cloudy Day (Need Grid Power)**

When the community needs more energy than solar provides:
- Extra energy is bought from the grid (at a high price, ~30 ct/kWh)
- House purchase price is adjusted between PV price and grid price
- More solar in the mix = lower house price

*Example: If houses need 100 kWh but solar only provides 50 kWh, the house price is a blend based on the 50/50 mix.*

### The Simple Rule

**House purchase price** is always between:
- The PV producer price (what we pay solar owners)
- The grid price (what we pay the utility company)

The exact price depends on how much of the energy comes from local solar vs. the grid.

### Why Cap the House Price?

In extreme surplus (lots of sun, little demand), the math could produce a house price higher than the grid price - which makes no sense. Nobody would pay more than the grid charges!

So we cap the house price at the grid price, and instead reduce what we pay PV producers. They still earn more than selling directly to the grid, but not as much as on a balanced day.

### Summary Formula

| Situation | House Price | PV Payout |
|-----------|-------------|-----------|
| Deficit (need grid) | Blend toward grid price | Policy rate (e.g., 20 ct) |
| Surplus (excess PV) | Blend toward PV price | Policy rate (e.g., 20 ct) |
| Extreme surplus | Capped at grid price | Reduced to break even |

**In plain English:** The more local solar you use, the cheaper your electricity. But we never charge more than the grid, and PV owners always earn more than grid export rates.
