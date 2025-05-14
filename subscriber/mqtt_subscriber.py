import json
import os
import psycopg2
import paho.mqtt.client as mqtt
import pytz
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

MQTT_BROKER = os.getenv("MQTT_BROKER_URL")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC") + "/#"
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

# Define Tripoli time zone (UTC+02:00)
TRIPOLI_TZ = pytz.timezone('Africa/Tripoli')

conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    host=DB_HOST,
    port=DB_PORT
)
cursor = conn.cursor()

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        
        # Parse the timestamp (which should be in UTC from the publisher)
        utc_timestamp = datetime.fromisoformat(payload["timestamp"])
        
        # For display purposes, convert to Tripoli time
        local_timestamp = utc_timestamp.astimezone(TRIPOLI_TZ)
        
        cursor.execute("""
            INSERT INTO energy_readings (meter_id, timestamp, power, voltage, current, frequency, energy)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            payload["meter_id"],
            payload["timestamp"],
            payload["power"],
            payload["voltage"],
            payload["current"],
            payload["frequency"],
            payload["energy"]
        ))
        conn.commit()
        print(f"✅ Inserted: {payload['meter_id']} @ {local_timestamp.isoformat()} (Tripoli time)")
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        print(f"Payload: {msg.payload.decode()}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"🔌 Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        print(f"📥 Subscribed to topic: {MQTT_TOPIC}")
    else:
        print(f"❌ Failed to connect to MQTT broker, return code: {rc}")

def run_subscriber():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_message = on_message

    try:
        print(f"🟢 Starting MQTT Subscriber, connecting to {MQTT_BROKER}...")
        client.connect(MQTT_BROKER, MQTT_PORT)
        current_time = datetime.now(TRIPOLI_TZ)
        print(f"Current time in Tripoli: {current_time.isoformat()}")
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n🟡 Subscriber stopped by user")
    except Exception as e:
        print(f"❌ Error in subscriber: {e}")
    finally:
        client.disconnect()
        cursor.close()
        conn.close()
        print("🔄 MQTT client disconnected and database connection closed")

if __name__ == "__main__":
    run_subscriber()