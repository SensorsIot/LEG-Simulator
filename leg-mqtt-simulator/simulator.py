#!/usr/bin/env python3
"""
LEG MQTT Simulator - Generates realistic smart meter data for simulated houses.

Publishes to MQTT broker every 10 seconds, mimicking real smart meter format.
"""

import json
import time
import signal
import sys
import ssl
import os
import logging
from datetime import datetime

import yaml
import paho.mqtt.client as mqtt

from houses import House
from influx_state import StateWriter

# Load configuration from YAML
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.yaml')
with open(CONFIG_FILE, 'r') as f:
    config = yaml.safe_load(f)

# Extract config values
MQTT_BROKER = config['mqtt']['broker']
MQTT_PORT = config['mqtt']['port']
MQTT_USE_TLS = config['mqtt'].get('use_tls', False)
MQTT_USERNAME = config['mqtt'].get('username', '')
MQTT_PASSWORD = config['mqtt'].get('password', '')

UPDATE_INTERVAL = config['simulator']['update_interval']
STATE_FILE = os.path.join(os.path.dirname(__file__), config['simulator']['state_file'])
HOUSES = config['houses']

# Load parameters
LOAD_CONFIG = config.get('load', {})
APPLIANCE_CONFIG = config.get('appliances', {})

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Global flag for clean shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global running
    logger.info("Shutdown signal received")
    running = False


def load_state() -> dict:
    """Load persisted state from file."""
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.info("No state file found, starting fresh")
        return {}
    except Exception as e:
        logger.error(f"Error loading state: {e}")
        return {}


def save_state(houses: list[House]):
    """Save state to file for persistence."""
    state = {}
    for house in houses:
        state[house.mac] = house.get_state()
    
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving state: {e}")


def on_connect(client, userdata, flags, reason_code, properties):
    """MQTT connection callback."""
    if reason_code == 0:
        logger.info(f"Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    else:
        logger.error(f"Failed to connect: {reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties):
    """MQTT disconnection callback."""
    logger.warning(f"Disconnected from MQTT broker: {reason_code}")


def main():
    global running
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("LEG MQTT Simulator starting...")
    logger.info(f"Simulating {len(HOUSES)} houses")
    
    # Load persisted state
    state = load_state()
    
    # Initialize houses
    houses = []
    for config in HOUSES:
        house = House(config)
        # Restore state if available
        if config["mac"] in state:
            house.load_state(state[config["mac"]])
            logger.info(f"House {config['id']}: Restored Ei={house.ei:.3f}, Eo={house.eo:.3f}")
        else:
            logger.info(f"House {config['id']}: Starting fresh Ei={house.ei:.3f}, Eo={house.eo:.3f}")
        houses.append(house)
    
    # Initialize InfluxDB state writer
    state_writer = StateWriter()
    
    # Write initial state at startup
    for house in houses:
        state_writer.write_state(house, force=True)
    logger.info("Initial simulator state written to InfluxDB")
    
    # Setup MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    # Configure TLS if enabled
    if MQTT_USE_TLS:
        client.tls_set(cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)
        logger.info("TLS enabled for MQTT connection")

    # Configure authentication if provided
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        logger.info(f"MQTT authentication configured for user: {MQTT_USERNAME}")

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {e}")
        sys.exit(1)
    
    logger.info(f"Publishing every {UPDATE_INTERVAL} seconds")
    
    last_save = time.time()
    save_interval = 60  # Save state every minute
    
    try:
        while running:
            loop_start = time.time()
            
            for house in houses:
                # Update house state and get message
                payload = house.update(UPDATE_INTERVAL)
                topic = f"{house.mac}/SENSOR"
                
                # Publish to MQTT
                message = json.dumps(payload)
                result = client.publish(topic, message)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.debug(f"Published to {topic}: Pi={payload['Pi']:.3f}, Po={payload['Po']:.3f}")
                else:
                    logger.error(f"Failed to publish to {topic}: {result.rc}")
                
                # Write state to InfluxDB if changed
                state_writer.write_state(house)
            
            # Log summary periodically
            now = datetime.now()
            if now.second < UPDATE_INTERVAL:
                for house in houses:
                    pv = house.get_pv_production_kw(now)
                    logger.info(
                        f"House {house.id}: PV={pv:.1f}kW, "
                        f"Ei={house.ei:.1f}kWh, Eo={house.eo:.1f}kWh"
                    )
            
            # Save state periodically
            if time.time() - last_save > save_interval:
                save_state(houses)
                last_save = time.time()
            
            # Sleep for remaining interval
            elapsed = time.time() - loop_start
            sleep_time = max(0, UPDATE_INTERVAL - elapsed)
            time.sleep(sleep_time)
    
    finally:
        # Save state on exit
        logger.info("Saving state before exit...")
        save_state(houses)
        state_writer.close()
        client.loop_stop()
        client.disconnect()
        logger.info("Simulator stopped")


if __name__ == "__main__":
    main()
