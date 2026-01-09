"""
MQTT Collector Service for LEG-Invoicing

Subscribes to smart meter MQTT topics, calculates energy deltas,
applies break-even tariffs, and stores all values in InfluxDB.
"""

import json
import os
import ssl
import logging
from datetime import datetime
from typing import Dict
import yaml
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Load configuration
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(CONFIG_FILE, "r") as f:
    config = yaml.safe_load(f)

# Extract config values
MQTT_BROKER = config["mqtt"]["broker"]
MQTT_PORT = config["mqtt"]["port"]
MQTT_USE_TLS = config["mqtt"].get("use_tls", False)
MQTT_USERNAME = config["mqtt"].get("username", "")
MQTT_PASSWORD = config["mqtt"].get("password", "")

INFLUX_URL = config["influxdb"]["url"]
INFLUX_TOKEN = config["influxdb"]["token"]
INFLUX_ORG = config["influxdb"]["org"]
INFLUX_BUCKET = config["influxdb"]["bucket"]

HOUSE_CONFIG = config["houses"]
DEFAULT_TARIFFS = config["tariffs"]
COLLECTOR_INTERVAL = config["collector"]["interval"]

LOG_LEVEL = config["logging"]["level"]
LOG_FILE = config["logging"].get("file")

# Configure logging
handlers = [logging.StreamHandler()]
if LOG_FILE:
    try:
        handlers.append(logging.FileHandler(LOG_FILE))
    except PermissionError:
        pass

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=handlers
)
logger = logging.getLogger(__name__)

# Tariffs file path
TARIFFS_FILE = os.path.join(os.path.dirname(__file__), "tariffs.json")


class EnergyCollector:
    def __init__(self):
        self.previous_values: Dict[str, Dict[str, float]] = {}
        self.current_interval: Dict[str, Dict] = {}

        self.influx_client = InfluxDBClient(
            url=INFLUX_URL,
            token=INFLUX_TOKEN,
            org=INFLUX_ORG,
            verify_ssl=False
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
        logger.info(f"Connected to InfluxDB at {INFLUX_URL}")

    def load_base_tariffs(self) -> Dict[str, float]:
        """Load policy tariffs from file or use defaults."""
        if os.path.exists(TARIFFS_FILE):
            with open(TARIFFS_FILE, "r") as f:
                return json.load(f)
        return DEFAULT_TARIFFS.copy()

    def calculate_breakeven_tariffs(self, E: float, I: float, base_tariffs: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate break-even tariffs based on community energy balance.
        
        The community acts as intermediary between PV producers and consumers.
        Break-even means: community revenue = community costs
        
        E = total_production (PV exports from houses to community)
        I = total_consumption (imports from community to houses)
        
        SURPLUS (E > I): More PV than needed, excess goes to grid
          - Revenue: houses pay for I kWh + grid pays for (E-I) kWh
          - Cost: pay PV producers for E kWh
          - Formula: p_con = p_grid_del + (E/I) * (p_pv - p_grid_del)
          - Edge case: if p_con > p_grid_con, cap house price and reduce PV payout
        
        DEFICIT (E < I): Need grid power to cover shortfall  
          - Revenue: houses pay for I kWh
          - Cost: pay PV producers for E kWh + pay grid for (I-E) kWh
          - Formula: p_con = p_grid_con + (E/I) * (p_pv - p_grid_con)
        """
        p_pv_policy = base_tariffs["p_pv"]        # Policy PV payout rate
        p_grid_con = base_tariffs["p_grid_con"]   # Grid import price  
        p_grid_del = base_tariffs["p_grid_del"]   # Grid export price
        
        tariffs = base_tariffs.copy()
        
        if I == 0:
            # No consumption - use policy defaults
            tariffs["p_con"] = p_grid_con
            tariffs["p_pv"] = p_pv_policy
            logger.debug(f"Break-even: No consumption, using defaults p_con={p_grid_con}")
            return tariffs
        
        if E >= I:
            # SURPLUS: Community has more PV than consumption
            # Standard break-even formula:
            p_con_calc = p_grid_del + (E / I) * (p_pv_policy - p_grid_del)
            
            if p_con_calc > p_grid_con:
                # EDGE CASE: House price would exceed grid price
                # Cap house price and reduce PV payout to break even
                tariffs["p_con"] = p_grid_con
                # PV payout = weighted average of house revenue and grid export revenue
                tariffs["p_pv"] = (I * p_grid_con + (E - I) * p_grid_del) / E
                logger.info(
                    f"Break-even SURPLUS (capped): E={E:.4f} I={I:.4f} "
                    f"p_con={tariffs['p_con']:.2f} p_pv={tariffs['p_pv']:.2f} (reduced from {p_pv_policy})"
                )
            else:
                tariffs["p_con"] = p_con_calc
                tariffs["p_pv"] = p_pv_policy
                logger.info(
                    f"Break-even SURPLUS: E={E:.4f} I={I:.4f} "
                    f"p_con={tariffs['p_con']:.2f} p_pv={tariffs['p_pv']:.2f}"
                )
        else:
            # DEFICIT: Community needs grid power
            tariffs["p_con"] = p_grid_con + (E / I) * (p_pv_policy - p_grid_con)
            tariffs["p_pv"] = p_pv_policy
            logger.info(
                f"Break-even DEFICIT: E={E:.4f} I={I:.4f} "
                f"p_con={tariffs['p_con']:.2f} p_pv={tariffs['p_pv']:.2f}"
            )
        
        return tariffs

    def process_message(self, mac: str, payload: Dict):
        """Process incoming MQTT message and calculate energy delta."""
        if mac not in HOUSE_CONFIG:
            return

        house_info = HOUSE_CONFIG[mac]
        house_id = house_info["id"]
        ei = payload.get("Ei", 0)
        eo = payload.get("Eo", 0)

        # Check if we have valid previous values (ei/eo are never 0 in reality)
        # If previous is 0, we just started up - wait for next reading
        if mac not in self.previous_values or self.previous_values[mac]["Ei"] == 0:
            self.previous_values[mac] = {"Ei": ei, "Eo": eo}
            logger.info(f"Startup: storing baseline for house {house_id} (Ei={ei}, Eo={eo})")
            return
        
        prev = self.previous_values[mac]
        delta_ei = max(0, ei - prev["Ei"])
        delta_eo = max(0, eo - prev["Eo"])
        
        # Update previous values
        self.previous_values[mac] = {"Ei": ei, "Eo": eo}
        
        # Sanity check: skip unreasonably large deltas (>0.1 kWh = ~36kW for 10s)
        MAX_DELTA = 0.1
        if delta_ei > MAX_DELTA or delta_eo > MAX_DELTA:
            logger.warning(f"Skipping invalid delta: ei={delta_ei:.4f}, eo={delta_eo:.4f} kWh (house {house_id})")
            return
        
        if mac in self.current_interval:
            self.current_interval[mac]["delta_ei"] += delta_ei
            self.current_interval[mac]["delta_eo"] += delta_eo
            self.current_interval[mac]["ei"] = ei
            self.current_interval[mac]["eo"] = eo
        else:
            self.current_interval[mac] = {
                "house_id": house_id,
                "delta_ei": delta_ei,
                "delta_eo": delta_eo,
                "ei": ei,
                "eo": eo,
            }

    def store_interval_data(self):
        """Store all collected data for this interval to InfluxDB."""
        if not self.current_interval:
            return

        # Step 1: Calculate totals (E and I)
        total_consumption = 0  # I = total imports to houses
        total_production = 0   # E = total exports from houses (PV)

        for mac, data in self.current_interval.items():
            total_consumption += data["delta_ei"]
            total_production += data["delta_eo"]

        # Step 2: Calculate break-even tariffs based on E and I
        base_tariffs = self.load_base_tariffs()
        tariffs = self.calculate_breakeven_tariffs(total_production, total_consumption, base_tariffs)

        # Step 3: Create house data points with calculated tariffs
        points = []

        for mac, data in self.current_interval.items():
            delta_ei = data["delta_ei"]
            delta_eo = data["delta_eo"]

            value_consumption = delta_ei * tariffs["p_con"]
            value_pv_delivery = delta_eo * tariffs["p_pv"]

            # Net flow per home: positive = exporting, negative = importing
            net_flow_home = delta_eo - delta_ei

            point = Point("house_energy") \
                .tag("house_id", str(data["house_id"])) \
                .tag("mac", mac) \
                .field("ei_kwh", float(data["ei"])) \
                .field("eo_kwh", float(data["eo"])) \
                .field("delta_ei_kwh", float(delta_ei)) \
                .field("delta_eo_kwh", float(delta_eo)) \
                .field("net_flow_kwh", float(net_flow_home)) \
                .field("value_consumption_ct", float(value_consumption)) \
                .field("value_pv_delivery_ct", float(value_pv_delivery)) \
                .field("tariff_p_consumption", float(tariffs["p_con"])) \
                .field("tariff_p_pv_delivery", float(tariffs["p_pv"]))

            points.append(point)

        # Step 4: Calculate grid exchange
        net_energy = total_production - total_consumption

        if net_energy > 0:
            grid_export = net_energy
            grid_import = 0.0
        else:
            grid_export = 0.0
            grid_import = abs(net_energy)

        value_grid_export = grid_export * tariffs["p_grid_del"]
        value_grid_import = grid_import * tariffs["p_grid_con"]

        # Step 5: Create community data point
        community_point = Point("community_energy") \
            .field("total_consumption_kwh", total_consumption) \
            .field("total_production_kwh", total_production) \
            .field("grid_import_kwh", float(grid_import)) \
            .field("grid_export_kwh", float(grid_export)) \
            .field("value_grid_import_ct", float(value_grid_import)) \
            .field("value_grid_export_ct", float(value_grid_export)) \
            .field("tariff_p_grid_consumption", float(tariffs["p_grid_con"])) \
            .field("tariff_p_grid_delivery", float(tariffs["p_grid_del"]))

        points.append(community_point)

        # Step 6: Write all points to InfluxDB
        self.write_api.write(bucket=INFLUX_BUCKET, record=points)

        logger.info(
            f"Stored: cons={total_consumption:.4f}kWh, prod={total_production:.4f}kWh, "
            f"p_con={tariffs['p_con']:.2f}, p_pv={tariffs['p_pv']:.2f}"
        )

        self.current_interval.clear()


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe("+/SENSOR")
        logger.info("Subscribed to +/SENSOR")
    else:
        logger.error(f"Failed to connect, return code {rc}")


def on_message(client, userdata, msg):
    try:
        mac = msg.topic.split("/")[0]
        payload = json.loads(msg.payload.decode())
        userdata["collector"].process_message(mac, payload)
    except Exception as e:
        logger.error(f"Error processing message: {e}")


def main():
    import time

    collector = EnergyCollector()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata={"collector": collector})
    client.on_connect = on_connect
    client.on_message = on_message

    if MQTT_USE_TLS:
        client.tls_set(cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)
        logger.info("TLS enabled for MQTT connection")

    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        logger.info(f"MQTT authentication configured for user: {MQTT_USERNAME}")

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    logger.info(f"Starting collector - storing data every {COLLECTOR_INTERVAL} seconds to InfluxDB")

    try:
        while True:
            time.sleep(COLLECTOR_INTERVAL)
            collector.store_interval_data()
    except KeyboardInterrupt:
        logger.info("Shutting down collector")
        client.loop_stop()
        client.disconnect()
        collector.influx_client.close()


if __name__ == "__main__":
    main()
