import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)
cursor = conn.cursor()

# 1. Enable extension if not already
cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")

# 2. Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS energy_readings (
    meter_id VARCHAR(20),
    timestamp TIMESTAMPTZ NOT NULL,
    power DOUBLE PRECISION,
    voltage DOUBLE PRECISION,
    current DOUBLE PRECISION,
    frequency DOUBLE PRECISION,
    energy DOUBLE PRECISION
);
""")

# 3. Convert to hypertable
cursor.execute("""
SELECT create_hypertable('energy_readings', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);
""")

conn.commit()
cursor.close()
conn.close()
print("✅ energy_readings table and hypertable created.")
