# LEG-Simulator

Real-time visualization of electrical energy flows within a Local Energy Grid (LEG).

## Quick Start

```bash
cd leg-simulator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:8050

## Deployment

Production: https://provision.dhamstack.com:8051

## Systemd Service

```bash
# Status
systemctl status leg-simulator

# Logs
journalctl -u leg-simulator -f

# Restart
systemctl restart leg-simulator
```

Service file: `/etc/systemd/system/leg-simulator.service`

## Documentation

See [../docs/LEG-Simulator-fsd.md](../docs/LEG-Simulator-fsd.md)
