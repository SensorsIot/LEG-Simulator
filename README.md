# LEG-Simulator

Real-time, descriptive simulation and visualization of instantaneous electrical energy flows within a small community of houses with PV systems.

## Quick Start (venv)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:8050 in a browser.

## Configuration

Edit `config.yaml` to adjust:

- `houses`
- `update_interval_ms`
- `pv_variation` (enabled/disabled)
- `flex_load_probability`

## Project Layout

- `app.py`: Dash entry point
- `model.py`: Energy model and state updates
- `simulation.py`: Simulation loop
- `layout.py`: Graph construction
- `config.yaml`: Configuration
