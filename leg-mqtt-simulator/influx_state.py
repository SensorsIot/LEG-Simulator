"""InfluxDB state writer for simulator."""

import os
import logging
import yaml
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger(__name__)

# Load configuration
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(CONFIG_FILE, "r") as f:
    _config = yaml.safe_load(f)

_influx = _config.get("influxdb", {})
INFLUX_URL = _influx.get("url", "http://localhost:8086")
INFLUX_TOKEN = _influx.get("token", "")
INFLUX_ORG = _influx.get("org", "LEG")
INFLUX_BUCKET = _influx.get("bucket", "energy")


class StateWriter:
    """Writes simulator state to InfluxDB."""
    
    def __init__(self):
        self.client = None
        self.write_api = None
        self._last_state = {}  # Track last state per house to detect changes
        
        if INFLUX_TOKEN:
            try:
                self.client = InfluxDBClient(
                    url=INFLUX_URL,
                    token=INFLUX_TOKEN,
                    org=INFLUX_ORG,
                    verify_ssl=False
                )
                self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
                logger.info(f"Connected to InfluxDB at {INFLUX_URL}")
            except Exception as e:
                logger.error(f"Failed to connect to InfluxDB: {e}")
    
    def write_state(self, house, force: bool = False):
        """Write house state to InfluxDB if changed or forced."""
        if not self.write_api:
            return
        
        # Get current appliance power values (kW)
        washing_kw = 0.0
        dishwasher_kw = 0.0
        ev_kw = 0.0
        
        for a in house.appliances:
            if a.name == "washing" and a.active:
                washing_kw = a.power_kw
            elif a.name == "dishwasher" and a.active:
                dishwasher_kw = a.power_kw
            elif a.name.startswith("ev_") and a.active:
                ev_kw = a.power_kw
        
        # Build current state tuple for comparison
        current_state = (washing_kw, dishwasher_kw, ev_kw)
        
        # Check if state changed
        last = self._last_state.get(house.id)
        if not force and last == current_state:
            return  # No change
        
        self._last_state[house.id] = current_state
        
        try:
            point = Point("simulator_state") \
                .tag("house_id", str(house.id)) \
                .field("pv_kwp", float(house.pv_kwp)) \
                .field("washing_kw", float(washing_kw)) \
                .field("dishwasher_kw", float(dishwasher_kw)) \
                .field("ev_kw", float(ev_kw))
            
            self.write_api.write(bucket=INFLUX_BUCKET, record=point)
            
            if washing_kw > 0 or dishwasher_kw > 0 or ev_kw > 0:
                logger.info(f"House {house.id} state: washing={washing_kw}kW, dishwasher={dishwasher_kw}kW, ev={ev_kw}kW")
            
        except Exception as e:
            logger.error(f"Failed to write state for house {house.id}: {e}")
    
    def close(self):
        """Close InfluxDB connection."""
        if self.client:
            self.client.close()
