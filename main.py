# main.py
import threading
import time
from subscriber import mqtt_subscriber
from publisher import data_generator
from dotenv import load_dotenv
import os

load_dotenv()
print(f"📄 Loaded NUM_METERS = {os.getenv('NUM_METERS')} from .env")
print("🔌 Starting Smart Energy System...")

def run_subscriber_thread():
    print("📡 Starting MQTT Subscriber...")
    mqtt_subscriber.run_subscriber()

def run_publisher_thread():
    print("🚀 Starting Data Generator...")
    data_generator.run_generator()

if __name__ == "__main__":
    subscriber_thread = threading.Thread(target=run_subscriber_thread)
    publisher_thread = threading.Thread(target=run_publisher_thread)

    subscriber_thread.start()
    time.sleep(5)  # wait a bit longer to let subscriber fully connect
    publisher_thread.start()

    subscriber_thread.join()
    publisher_thread.join()
