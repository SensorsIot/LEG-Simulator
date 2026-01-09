# LEG-Software

Local Energy Grid software suite for community energy management.

## Projects

| Project | Description | Systemd Service |
|---------|-------------|-----------------|
| [leg-simulator](leg-simulator/) | Real-time energy flow visualization (Dash) | `leg-simulator` |
| [leg-mqtt-simulator](leg-mqtt-simulator/) | MQTT data generator for 4 simulated houses | `leg-mqtt-simulator` |
| [leg-invoicing-ui](leg-invoicing-ui/) | Tariff management UI and data collector | `leg-invoicing-ui`, `leg-collector` |
| [leg-invoicing](leg-invoicing/) | Invoice generation (planned) | - |

## Deployment

**Server:** provision.dhamstack.com (LEG-Configurator)

### Web Services

| Service | URL | Description |
|---------|-----|-------------|
| LEG Simulator | https://provision.dhamstack.com:8051 | Energy flow visualization |
| LEG Invoicing UI | https://provision.dhamstack.com:8052 | Tariff management |
| InfluxDB | https://provision.dhamstack.com:8087 | Time-series database |
| Grafana | http://192.168.0.203:3000 | Dashboards |

### Grafana Dashboards

| Dashboard | URL |
|-----------|-----|
| LEG Community | http://192.168.0.203:3000/d/leg-community |
| LEG Grid | http://192.168.0.203:3000/d/leg-grid |
| LEG House 1-5 | http://192.168.0.203:3000/d/leg-house-{1-5} |

### Systemd Services

```bash
# Check status
systemctl status leg-mqtt-simulator leg-collector leg-invoicing-ui leg-simulator

# Restart all
systemctl restart leg-mqtt-simulator leg-collector leg-invoicing-ui leg-simulator

# View logs
journalctl -u leg-collector -f
```

| Service | Description | Auto-restart |
|---------|-------------|--------------|
| `leg-mqtt-simulator` | Simulates 4 houses via MQTT | Yes |
| `leg-collector` | Collects data every 60s to InfluxDB | Yes |
| `leg-invoicing-ui` | Flask tariff UI on port 8060 | Yes |
| `leg-simulator` | Dash visualization on port 8050 | Yes |

## Documentation

See [docs/](docs/) for functional specifications:
- [LEG-Simulator FSD](docs/LEG-Simulator-fsd.md)
- [LEG-Invoicing FSD](leg-invoicing/Documents/LEG-Invoicing-fsd.md)

## Data Flow

```
┌─────────────────┐     MQTT      ┌─────────────┐     InfluxDB    ┌─────────┐
│ leg-mqtt-       │ ──────────────▶ │ leg-        │ ───────────────▶ │ Grafana │
│ simulator       │               │ collector   │                │         │
│ (4 houses)      │               │ (60s agg)   │                │         │
└─────────────────┘               └─────────────┘                └─────────┘
                                        │
                                        ▼
                                 ┌─────────────┐
                                 │ leg-        │
                                 │ invoicing-  │
                                 │ ui          │
                                 │ (tariffs)   │
                                 └─────────────┘
```

## Configuration

Each service uses `config.yaml` (gitignored). Copy from `config.example.yaml`:
```bash
cp config.example.yaml config.yaml
# Edit with your credentials
```

## License

MIT
