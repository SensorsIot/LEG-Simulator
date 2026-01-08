# ⚡ LEG-Simulator

[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?logo=python&logoColor=white)](https://python.org)
[![Dash](https://img.shields.io/badge/Dash-2.15+-00d4aa?logo=plotly&logoColor=white)](https://dash.plotly.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen)]()

## 🎯 Purpose

LEG-Simulator provides **real-time visualization of electrical energy flows** within a Local Energy Grid (LEG) - a small community of houses with photovoltaic (PV) systems.

It answers the question: *"What is happening right now with energy in our community?"*

> ⚠️ This is a **descriptive simulator**, not an optimizer. It shows current state, not recommendations.

## ✨ What You See

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   House 1   │────▶│  Community  │────▶│  External   │
│   House 2   │────▶│     Bus     │◀────│    Grid     │
│   House N   │────▶│             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
     ☀️ PV              ⚡ Balance           🔌 Import/Export
     🔌 Load
```

- 🏠 **Houses**: Each with solar panels and consumption (click to edit)
- ☀️ **PV Production**: User-defined values per house
- 🔌 **Loads**: Base load (random 0.5-2kW initial) + EV + Washer - all click-to-edit
- 🔄 **Energy Flows**: Net flows visualized with colored arrows
- 📊 **Pricing Table**: Buy/Sell costs for House, Community, Grid
- 📈 **Break-Even**: Calculates optimal house consumption price for community profit = 0

## 🎨 Visual Indicators

| Color | Meaning |
|-------|---------|
| 🟢 Green | Energy export (surplus) |
| 🟠 Orange | Energy import (deficit) |
| ⚪ Grey | No significant flow |

---

## 🚀 Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

🌐 Open http://localhost:8050

## ⚙️ Configuration

Energy prices are configurable in the UI (ct/kWh):
- Grid Delivery: 6 | Grid Consumption: 30
- PV Delivery: 20 | House Consumption: 25

## 📁 Files

| File | Purpose |
|------|---------|
| `app.py` | Dash entry point |
| `model.py` | Energy model logic |
| `simulation.py` | Simulation loop |
| `layout.py` | Graph visualization |

## 🔮 Future Extensions

- 💰 Price signals

---

<p align="center">Made with ⚡ for the energy community</p>
