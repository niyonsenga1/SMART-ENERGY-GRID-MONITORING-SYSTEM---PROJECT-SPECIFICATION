import os
import psycopg2
import random
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

load_dotenv()

# DB connection
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)
cursor = conn.cursor()

NUM_METERS = int(os.getenv("NUM_METERS", 1043))

# Get today's date at midnight in Tripoli time zone (UTC+02:00)
tripoli_tz = pytz.timezone('Africa/Tripoli')  # Tripoli time zone
now_in_tripoli = datetime.now(tripoli_tz)
today = now_in_tripoli.replace(hour=0, minute=0, second=0, microsecond=0)

# Print the current date being used
print(f"Current date being used: {today.date()} (Tripoli time zone)")

# Start date is 13 days ago (to include today, for a total of 14 days)
start_date = today - timedelta(days=13)

print("🔁 Connecting to database...")
print(f"🛠 Generating and inserting data for 14 days (from {start_date.date()} to {today.date()})...")

# First, clear existing data for the time range we're about to populate
# Convert dates to UTC for database query
start_date_utc = start_date.astimezone(pytz.UTC)
end_date_utc = (today + timedelta(days=1)).astimezone(pytz.UTC)

cursor.execute("DELETE FROM energy_readings WHERE timestamp >= %s AND timestamp < %s", 
              (start_date_utc, end_date_utc))
conn.commit()
print(f"🧹 Cleared existing data for the date range")

for day in range(14):
    current_day = start_date + timedelta(days=day)
    print(f"📅 Processing day: {current_day.date()}")
    readings = []

    # Convert timestamps to UTC before storing in database
    for i in range(NUM_METERS):
        meter_id = f"{1000000000 + i}"
        for j in range(288):  # 5 min interval = 288/day
            # Create timestamp in Tripoli time
            local_timestamp = current_day + timedelta(minutes=5 * j)
            # Convert to UTC for database storage (if your database stores in UTC)
            utc_timestamp = local_timestamp.astimezone(pytz.UTC)
            
            hour = local_timestamp.hour

            power = random.uniform(2000, 5000) if hour in range(6, 10) or hour in range(17, 22) else \
                    random.uniform(300, 800) if hour in range(0, 6) else \
                    random.uniform(1000, 2500)
            voltage = random.uniform(210, 240)
            current_val = power / voltage
            frequency = random.choice([49.9, 50.0, 50.1])
            energy = power * 5 / 60 / 1000  # kWh per 5 minutes

            readings.append((
                meter_id,
                utc_timestamp,
                round(power, 2),
                round(voltage, 2),
                round(current_val, 2),
                frequency,
                round(energy, 4)
            ))

    # Bulk insert for the day
    args_str = ",".join(cursor.mogrify("(%s,%s,%s,%s,%s,%s,%s)", r).decode() for r in readings)
    cursor.execute(f"""
        INSERT INTO energy_readings (meter_id, timestamp, power, voltage, current, frequency, energy)
        VALUES {args_str}
    """)
    conn.commit()
    print(f"✅ Inserted {len(readings)} rows for {current_day.date()}")

cursor.close()
conn.close()
print("🏁 Done loading historical data.")