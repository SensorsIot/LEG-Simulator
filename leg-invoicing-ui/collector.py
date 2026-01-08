"""
MQTT Collector Service for LEG-Invoicing

Subscribes to smart meter MQTT topics, calculates energy deltas,
applies tariffs, and stores all values in InfluxDB.
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
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.yaml')
with open(CONFIG_FILE, 'r') as f:
    config = yaml.safe_load(f)

# Extract config values
MQTT_BROKER = config['mqtt']['broker']
MQTT_PORT = config['mqtt']['port']
MQTT_USE_TLS = config['mqtt'].get('use_tls', False)
MQTT_USERNAME = config['mqtt'].get('username', '')
MQTT_PASSWORD = config['mqtt'].get('password', '')

INFLUX_URL = config['influxdb']['url']
INFLUX_TOKEN = config['influxdb']['token']
INFLUX_ORG = config['influxdb']['org']
INFLUX_BUCKET = config['influxdb']['bucket']

HOUSE_CONFIG = config['houses']
DEFAULT_TARIFFS = config['tariffs']
COLLECTOR_INTERVAL = config['collector']['interval']

LOG_LEVEL = config['logging']['level']
LOG_FILE = config['logging'].get('file')

# Configure logging
handlers = [logging.StreamHandler()]
if LOG_FILE:
    try:
        handlers.append(logging.FileHandler(LOG_FILE))
    except PermissionError:
        pass

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)

# Tariffs file path
TARIFFS_FILE = os.path.join(os.path.dirname(__file__), 'tariffs.json')


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

    def load_tariffs(self) -> Dict[str, float]:
        """Load current tariffs from file or use defaults."""
        if os.path.exists(TARIFFS_FILE):
            with open(TARIFFS_FILE, 'r') as f:
                tariffs = json.load(f)
                if 'p_con' not in tariffs:
                    tariffs['p_con'] = (tariffs['p_pv'] + tariffs['p_grid_con']) / 2
                return tariffs
        tariffs = DEFAULT_TARIFFS.copy()
        tariffs['p_con'] = (tariffs['p_pv'] + tariffs['p_grid_con']) / 2
        return tariffs

    def process_message(self, mac: str, payload: Dict):
        """Process incoming MQTT message and calculate energy delta."""
        if mac not in HOUSE_CONFIG:
            return

        house_info = HOUSE_CONFIG[mac]
        house_id = house_info['id']
        ei = payload.get('Ei', 0)
        eo = payload.get('Eo', 0)

        if mac in self.previous_values:
            prev = self.previous_values[mac]
            delta_ei = max(0, ei - prev['Ei'])
            delta_eo = max(0, eo - prev['Eo'])

            # Accumulate deltas over the interval
            if mac in self.current_interval:
                self.current_interval[mac]['delta_ei'] += delta_ei
                self.current_interval[mac]['delta_eo'] += delta_eo
                self.current_interval[mac]['ei'] = ei  # Update to latest
                self.current_interval[mac]['eo'] = eo
            else:
                self.current_interval[mac] = {
                    'house_id': house_id,
                    'delta_ei': delta_ei,
                    'delta_eo': delta_eo,
                    'ei': ei,  # Raw cumulative value
                    'eo': eo,
                }

        self.previous_values[mac] = {'Ei': ei, 'Eo': eo}

    def store_interval_data(self):
        """Store all collected data for this interval to InfluxDB."""
        if not self.current_interval:
            return

        tariffs = self.load_tariffs()
        points = []

        total_consumption = 0
        total_production = 0

        for mac, data in self.current_interval.items():
            delta_ei = data['delta_ei']
            delta_eo = data['delta_eo']

            value_consumption = delta_ei * tariffs['p_con']
            value_pv_delivery = delta_eo * tariffs['p_pv']

            # Net flow per home: positive = exporting to community, negative = importing
            net_flow_home = delta_eo - delta_ei

            point = Point("house_energy") \
                .tag("house_id", str(data['house_id'])) \
                .tag("mac", mac) \
                .field("ei_kwh", float(data['ei'])) \
                .field("eo_kwh", float(data['eo'])) \
                .field("delta_ei_kwh", float(delta_ei)) \
                .field("delta_eo_kwh", float(delta_eo)) \
                .field("net_flow_kwh", float(net_flow_home)) \
                .field("value_consumption_ct", float(value_consumption)) \
                .field("value_pv_delivery_ct", float(value_pv_delivery)) \
                .field("tariff_p_con", float(tariffs['p_con'])) \
                .field("tariff_p_pv", float(tariffs['p_pv']))

            points.append(point)

            total_consumption += delta_ei
            total_production += delta_eo

        net_energy = total_production - total_consumption

        if net_energy > 0:
            grid_export = net_energy
            grid_import = 0
        else:
            grid_export = 0
            grid_import = abs(net_energy)

        value_grid_export = grid_export * tariffs['p_grid_del']
        value_grid_import = grid_import * tariffs['p_grid_con']

        # Net flow from homes to community: positive = homes supply community
        net_flow_homes_to_community = total_production - total_consumption

        # Net flow from community to grid: positive = community exports, negative = imports
        net_flow_community_to_grid = grid_export - grid_import

        community_point = Point("community_energy") \
            .field("total_consumption_kwh", total_consumption) \
            .field("total_production_kwh", total_production) \
            .field("net_flow_homes_to_community_kwh", net_flow_homes_to_community) \
            .field("grid_import_kwh", grid_import) \
            .field("grid_export_kwh", grid_export) \
            .field("net_flow_community_to_grid_kwh", net_flow_community_to_grid) \
            .field("value_grid_import_ct", value_grid_import) \
            .field("value_grid_export_ct", value_grid_export) \
            .field("tariff_p_grid_con", tariffs['p_grid_con']) \
            .field("tariff_p_grid_del", tariffs['p_grid_del'])

        points.append(community_point)

        self.write_api.write(bucket=INFLUX_BUCKET, record=points)

        logger.info(
            f"Stored: cons={total_consumption:.6f}kWh, prod={total_production:.6f}kWh, "
            f"grid_in={grid_import:.6f}kWh ({value_grid_import:.2f}ct), "
            f"grid_out={grid_export:.6f}kWh ({value_grid_export:.2f}ct)"
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
        mac = msg.topic.split('/')[0]
        payload = json.loads(msg.payload.decode())
        userdata['collector'].process_message(mac, payload)
    except Exception as e:
        logger.error(f"Error processing message: {e}")


def main():
    import time

    collector = EnergyCollector()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata={'collector': collector})
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


if __name__ == '__main__':
    main()
