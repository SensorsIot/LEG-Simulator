"""House simulation with load profiles and energy metering."""

import os
import random
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dataclasses import dataclass, field
from typing import Optional

import yaml

from solar import get_pv_production_kw

# Load configuration from YAML
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.yaml')
with open(CONFIG_FILE, 'r') as f:
    _config = yaml.safe_load(f)

# Extract load parameters
_load = _config.get('load', {})
BASE_LOAD_DAY_W = _load.get('base_day_w', 500)
BASE_LOAD_NIGHT_W = _load.get('base_night_w', 200)
BASE_LOAD_VARIATION = _load.get('variation', 0.2)

# Extract appliance parameters
_appliances = _config.get('appliances', {})
_washing = _appliances.get('washing_machine', {})
WASHING_MACHINE_KW = _washing.get('power_kw', 2.0)
WASHING_MACHINE_HOURS = _washing.get('duration_hours', 2.0)
WASHING_FREQUENCY_DAYS = _washing.get('frequency_days', 7)

_dishwasher = _appliances.get('dishwasher', {})
DISHWASHER_KW = _dishwasher.get('power_kw', 1.5)
DISHWASHER_HOURS = _dishwasher.get('duration_hours', 1.5)
DISHWASHER_FREQUENCY_DAYS = _dishwasher.get('frequency_days', 2)

_ev = _appliances.get('ev_charger', {})
EV_CHARGER_KW = _ev.get('power_kw', 11.0)
EV_CHARGE_KWH = _ev.get('charge_kwh', 50.0)
EV_FREQUENCY_DAYS = _ev.get('frequency_days', 3.5)


def get_simulated_time() -> datetime:
    """Get simulated time (6 months ahead, same day of month)."""
    now = datetime.now()
    return now + relativedelta(months=6)


@dataclass
class ApplianceState:
    """Tracks an appliance on/off state and schedule."""
    name: str
    power_kw: float
    duration_hours: float
    frequency_days: float
    active: bool = False
    start_time: Optional[datetime] = None
    next_scheduled: Optional[datetime] = None
    
    def schedule_next(self, now: datetime):
        """Schedule the next run."""
        days_until = random.uniform(0.5, self.frequency_days)
        self.next_scheduled = now + timedelta(days=days_until)
        # Random start hour (reasonable times)
        if self.name == "ev_day":
            hour = random.randint(10, 14)
        elif self.name == "ev_night":
            hour = random.randint(22, 23)
        elif self.name == "washing":
            hour = random.randint(8, 18)
        else:  # dishwasher
            hour = random.randint(12, 21)
        self.next_scheduled = self.next_scheduled.replace(
            hour=hour, minute=random.randint(0, 59), second=0
        )
    
    def update(self, now: datetime) -> float:
        """Update state and return current power draw in kW."""
        # Check if should turn off
        if self.active and self.start_time:
            elapsed = (now - self.start_time).total_seconds() / 3600
            if elapsed >= self.duration_hours:
                self.active = False
                self.start_time = None
                self.schedule_next(now)
        
        # Check if should turn on
        if not self.active and self.next_scheduled:
            if now >= self.next_scheduled:
                self.active = True
                self.start_time = now
        
        return self.power_kw if self.active else 0.0


class House:
    """Simulates a house with PV, appliances, and energy metering."""
    
    def __init__(self, config: dict, initial_ei: float = 1000.0, initial_eo: float = 500.0):
        self.id = config["id"]
        self.mac = config["mac"]
        self.smid = config["smid"]
        self.pv_kwp = config["pv_kwp"]
        self.has_ev = config["has_ev"]
        self.ev_schedule = config["ev_schedule"]
        
        # Energy counters (ever-increasing)
        self.ei = initial_ei  # kWh imported
        self.eo = initial_eo  # kWh exported
        
        # Timestamp counter (simulates meter uptime in seconds)
        self.ts = random.randint(1000, 100000)
        
        # Initialize appliances
        now = get_simulated_time()
        
        self.appliances = [
            ApplianceState(
                name="washing",
                power_kw=WASHING_MACHINE_KW,
                duration_hours=WASHING_MACHINE_HOURS,
                frequency_days=WASHING_FREQUENCY_DAYS,
            ),
            ApplianceState(
                name="dishwasher",
                power_kw=DISHWASHER_KW,
                duration_hours=DISHWASHER_HOURS,
                frequency_days=DISHWASHER_FREQUENCY_DAYS,
            ),
        ]
        
        # Add EV if house has one
        if self.has_ev:
            ev_duration = EV_CHARGE_KWH / EV_CHARGER_KW
            self.appliances.append(ApplianceState(
                name=f"ev_{self.ev_schedule}",
                power_kw=EV_CHARGER_KW,
                duration_hours=ev_duration,
                frequency_days=EV_FREQUENCY_DAYS,
            ))
        
        # Schedule initial runs
        for appliance in self.appliances:
            appliance.schedule_next(now)
    
    def get_base_load_kw(self, now: datetime) -> float:
        """Get base load with time-of-day variation."""
        hour = now.hour
        
        # Day: 06:00-22:00, Night: 22:00-06:00
        if 6 <= hour < 22:
            base = BASE_LOAD_DAY_W
        else:
            base = BASE_LOAD_NIGHT_W
        
        # Add random variation
        variation = random.uniform(-BASE_LOAD_VARIATION, BASE_LOAD_VARIATION)
        load_w = base * (1 + variation)
        
        return load_w / 1000.0  # Convert to kW
    
    def get_appliance_load_kw(self, now: datetime) -> float:
        """Get total appliance load."""
        total = 0.0
        for appliance in self.appliances:
            total += appliance.update(now)
        return total
    
    def get_pv_production_kw(self, now: datetime) -> float:
        """Get current PV production."""
        return get_pv_production_kw(self.pv_kwp, now)
    
    def update(self, interval_seconds: float = 10.0) -> dict:
        """
        Update house state and return MQTT message payload.
        
        Args:
            interval_seconds: Time since last update
        
        Returns:
            Dict matching smart meter JSON format
        """
        # Use simulated time (6 months ahead)
        now = get_simulated_time()
        
        # Calculate current power flows
        base_load = self.get_base_load_kw(now)
        appliance_load = self.get_appliance_load_kw(now)
        pv_production = self.get_pv_production_kw(now)
        
        total_consumption = base_load + appliance_load
        net_power = total_consumption - pv_production
        
        # Determine Pi (power in) and Po (power out)
        if net_power > 0:
            pi = net_power  # Importing
            po = 0.0
        else:
            pi = 0.0
            po = abs(net_power)  # Exporting
        
        # Update energy counters
        hours = interval_seconds / 3600.0
        if pi > 0:
            self.ei += pi * hours
        if po > 0:
            self.eo += po * hours
        
        # Increment timestamp
        self.ts += int(interval_seconds)
        
        # Generate random values for other fields
        i1 = random.uniform(0.1, 0.5)
        i2 = random.uniform(0.02, 0.1)
        i3 = random.uniform(0.05, 0.15)
        
        return {
            "SMid": self.smid,
            "Pi": round(pi, 3),
            "Po": round(po, 3),
            "I1": round(i1, 3),
            "I2": round(i2, 3),
            "I3": round(i3, 3),
            "Ei": round(self.ei, 3),
            "Eo": round(self.eo, 3),
            "Q5": round(random.uniform(10, 30), 3),
            "Q6": round(random.uniform(10, 20), 3),
            "Q7": round(random.uniform(1000, 2000), 3),
            "Q8": round(random.uniform(3000, 4000), 3),
            "ts": self.ts,
        }
    
    def get_state(self) -> dict:
        """Get state for persistence."""
        return {
            "ei": self.ei,
            "eo": self.eo,
            "ts": self.ts,
        }
    
    def load_state(self, state: dict):
        """Load state from persistence."""
        self.ei = state.get("ei", self.ei)
        self.eo = state.get("eo", self.eo)
        self.ts = state.get("ts", self.ts)
