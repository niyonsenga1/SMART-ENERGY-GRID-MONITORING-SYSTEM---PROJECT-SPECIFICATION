# publisher/data_generator.py

import os
import time
import json
import random
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
import pytz
from dotenv import load_dotenv

load_dotenv()
print(f"📄 Loaded NUM_METERS = {os.getenv('NUM_METERS')} from .env")

MQTT_BROKER = os.getenv("MQTT_BROKER_URL")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC")
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
NUM_METERS = int(os.getenv("NUM_METERS", 1043))

# Define Tripoli time zone (UTC+02:00)
TRIPOLI_TZ = pytz.timezone('Africa/Tripoli')

client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.connect(MQTT_BROKER, MQTT_PORT)
client.loop_start()

def simulate_power(hour):
    if 6 <= hour <= 10 or 17 <= hour <= 22:
        return random.uniform(2000, 5000)
    elif 0 <= hour <= 5:
        return random.uniform(300, 800)
    else:
        return random.uniform(1000, 2500)

def generate_reading(meter_id, local_time):
    power = simulate_power(local_time.hour)
    voltage = random.uniform(210, 240)
    current = power / voltage
    frequency = random.choice([49.8, 50.0, 50.2])
    energy = power * 5 / 60 / 1000
    
    # Convert to UTC for storage
    utc_time = local_time.astimezone(pytz.UTC)
    
    return {
        "meter_id": meter_id,
        "timestamp": utc_time.isoformat(),
        "local_timestamp": local_time.isoformat(),
        "power": round(power, 2),
        "voltage": round(voltage, 2),
        "current": round(current, 2),
        "frequency": frequency,
        "energy": round(energy, 4)
    }

def run_generator():
    print("🛠 Generating and publishing data for 1 hour...")
    
    # Get current time in Tripoli time zone
    now = datetime.now(TRIPOLI_TZ).replace(second=0, microsecond=0)
    print(f"Current time in Tripoli: {now.isoformat()}")
    
    # Generate data for the next hour in 5-minute intervals
    timestamps = [now + timedelta(minutes=5 * i) for i in range(12)]
    
    for ts in timestamps:
        for i in range(NUM_METERS):
            meter_id = f"{1000000000 + i}"
            data = generate_reading(meter_id, ts)
            topic = f"{MQTT_TOPIC}/{meter_id}"
            client.publish(topic, json.dumps(data))
        print(f"📅 Published data for {ts.isoformat()} (Tripoli time)")
    
    client.loop_stop()
    client.disconnect()
    print(f"\n🔢 Meters published from: 1000000000 to {1000000000 + NUM_METERS - 1}")
    print(f"📦 Total meter topics published: {NUM_METERS}")

if __name__ == "__main__":
    run_generator()