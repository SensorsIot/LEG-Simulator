# LEG MQTT Simulator

Generates realistic smart meter data for 4 simulated houses in a Local Energy Grid.

## Quick Start

```bash
cd leg-mqtt-simulator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python simulator.py
```

## Houses

| House | MAC | PV | EV |
|-------|-----|-----|-----|
| 2 | AA-11-BB-22-CC-01 | 10 kWp | Day |
| 3 | AA-11-BB-22-CC-02 | 20 kWp | Night |
| 4 | AA-11-BB-22-CC-03 | None | No |
| 5 | AA-11-BB-22-CC-04 | None | No |

## MQTT

- Broker: 10.0.0.1:1883 (VPN) or provision.dhamstack.com:8883 (TLS)
- Topic: `{MAC}/SENSOR`
- Interval: 10 seconds

## Systemd Service

```bash
# Status
systemctl status leg-mqtt-simulator

# Logs
journalctl -u leg-mqtt-simulator -f

# Restart
systemctl restart leg-mqtt-simulator
```

Service file: `/etc/systemd/system/leg-mqtt-simulator.service`

## State Persistence

Energy counters (Ei, Eo) persist in `state.json` to survive restarts.
