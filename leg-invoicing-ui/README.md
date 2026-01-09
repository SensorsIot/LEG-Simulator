# LEG Invoicing UI

Tariff management interface and energy data collector for the Local Energy Grid.

## Components

1. **Tariff UI** (app.py) - Flask web interface for managing energy tariffs
2. **Collector** (collector.py) - Aggregates MQTT data and stores to InfluxDB

## Quick Start

```bash
cd leg-invoicing-ui
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Copy and edit config
cp config.example.yaml config.yaml

# Run UI
python app.py

# Run collector (separate terminal)
python collector.py
```

## Deployment

| Service | URL |
|---------|-----|
| Tariff UI | https://provision.dhamstack.com:8052 |

## Systemd Services

```bash
# Status
systemctl status leg-invoicing-ui leg-collector

# Logs
journalctl -u leg-collector -f
journalctl -u leg-invoicing-ui -f

# Restart
systemctl restart leg-invoicing-ui leg-collector
```

Service files:
- `/etc/systemd/system/leg-invoicing-ui.service`
- `/etc/systemd/system/leg-collector.service`

## Data Storage

The collector stores data to InfluxDB every 60 seconds:

### house_energy (per-house)
- `delta_ei_kwh` - Energy consumed this interval
- `delta_eo_kwh` - Energy exported this interval
- `ei_kwh`, `eo_kwh` - Raw cumulative values
- `net_flow_kwh` - Net energy flow
- `value_consumption_ct` - Consumption cost
- `value_pv_delivery_ct` - PV delivery credit
- `tariff_p_consumption`, `tariff_p_pv_delivery` - Applied tariffs

### community_energy (aggregated)
- `total_consumption_kwh`, `total_production_kwh`
- `grid_import_kwh`, `grid_export_kwh`
- `value_grid_import_ct`, `value_grid_export_ct`
- `tariff_p_grid_consumption`, `tariff_p_grid_delivery`

## Grafana Dashboards

| Dashboard | URL |
|-----------|-----|
| LEG Community | http://192.168.0.203:3000/d/leg-community |
| LEG Grid | http://192.168.0.203:3000/d/leg-grid |
| LEG House 1-5 | http://192.168.0.203:3000/d/leg-house-{1-5} |

## Documentation

See [../leg-invoicing/Documents/LEG-Invoicing-fsd.md](../leg-invoicing/Documents/LEG-Invoicing-fsd.md)
