import time
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_conn():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

def time_query_execution(query):
    conn = get_db_conn()
    cur = conn.cursor()
    start = time.time()
    cur.execute(query)
    cur.fetchall()  # Make sure full execution happens
    end = time.time()
    cur.close()
    conn.close()
    return round((end - start) * 1000, 2)  # milliseconds
