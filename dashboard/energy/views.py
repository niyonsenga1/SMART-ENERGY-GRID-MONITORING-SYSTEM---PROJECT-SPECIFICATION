import os
import json
import psycopg2
from dotenv import load_dotenv
from django.http import JsonResponse
from django.shortcuts import render
from .utils import time_query_execution, get_db_conn



load_dotenv()

# PostgreSQL connection
def get_db_conn():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

# def dashboard(request):
#     return render(request, 'energy/dashboard.html')

def dashboard(request):
    conn = get_db_conn()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(DISTINCT meter_id) FROM energy_readings")
    total_meters = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM energy_readings")
    total_readings = cur.fetchone()[0]

    # cur.execute("SELECT ROUND(SUM(energy), 2) FROM energy_readings")
    # total_energy = cur.fetchone()[0] or 0

    # cur.execute("SELECT ROUND(SUM(energy), 2) FROM energy_readings WHERE DATE(timestamp) = CURRENT_DATE")
    # energy_today = cur.fetchone()[0] or 0

    # Fix: Cast to NUMERIC before using ROUND
    cur.execute("SELECT CAST(SUM(energy) AS NUMERIC(15,2)) FROM energy_readings")
    total_energy = cur.fetchone()[0] or 0

    # Fix: Cast to NUMERIC before using ROUND
    cur.execute("SELECT CAST(SUM(energy) AS NUMERIC(15,2)) FROM energy_readings WHERE DATE(timestamp) = CURRENT_DATE")
    energy_today = cur.fetchone()[0] or 0

    cur.close()
    conn.close()

    return render(request, 'energy/dashboard.html', {
        'total_meters': total_meters,
        'total_readings': total_readings,
        'total_energy': total_energy,
        'energy_today': energy_today,
    })


def api_realtime(request):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT time_bucket('5 minutes', timestamp) AS bucket, AVG(power)
        FROM energy_readings
        WHERE timestamp >= NOW() - INTERVAL '1 hour'
        GROUP BY bucket ORDER BY bucket;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return JsonResponse({
        "timestamps": [r[0].isoformat() for r in rows],
        "avg_power": [round(r[1], 2) for r in rows]
    })

def api_daily(request):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
          SUM(CASE WHEN timestamp::date = CURRENT_DATE THEN energy ELSE 0 END),
          SUM(CASE WHEN timestamp::date = CURRENT_DATE - INTERVAL '1 day' THEN energy ELSE 0 END)
        FROM energy_readings;
    """)
    today, yesterday = cur.fetchone()
    cur.close()
    conn.close()
    return JsonResponse({
        "today": round(today or 0, 2),
        "yesterday": round(yesterday or 0, 2)
    })

def api_weekly(request):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT DATE(timestamp) AS day, SUM(energy)
        FROM energy_readings
        WHERE timestamp >= NOW() - INTERVAL '7 days'
        GROUP BY day ORDER BY day;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return JsonResponse({
        "days": [r[0].isoformat() for r in rows],
        "energy": [round(r[1], 2) for r in rows]
    })

def api_monthly_region(request):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT LEFT(meter_id::text, 1) AS region,
           DATE_TRUNC('month', timestamp) AS month,
           SUM(energy) AS total_energy
    FROM energy_readings
    GROUP BY region, month
    ORDER BY month, region;;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    region_months = {}
    for region, month, total in rows:
        month_str = month.strftime("%Y-%m")
        if region not in region_months:
            region_months[region] = {}
        region_months[region][month_str] = float(total)

    months = sorted({m for r in region_months.values() for m in r})
    datasets = []
    for region, values in region_months.items():
        datasets.append({
            "label": f"Region {region}",
            "data": [values.get(m, 0) for m in months]
        })

    return JsonResponse({
        "regions": months,
        "datasets": datasets
    })

def api_performance(request):
    q1_raw = """
        SELECT time_bucket('1 hour', timestamp) AS hour, AVG(power)
        FROM energy_readings
        WHERE timestamp >= DATE_TRUNC('day', NOW())
        GROUP BY hour ORDER BY hour;
    """

    q1_agg = """
        SELECT bucket, AVG(avg_power)
        FROM energy_readings_15min
        WHERE bucket >= DATE_TRUNC('day', NOW())
        GROUP BY bucket ORDER BY bucket;
    """

    q2_raw = """
        SELECT time_bucket('15 minutes', timestamp) AS period, AVG(power)
        FROM energy_readings
        WHERE timestamp >= NOW() - INTERVAL '7 days'
        GROUP BY period ORDER BY AVG(power) DESC LIMIT 10;
    """

    q2_agg = """
        SELECT bucket, AVG(avg_power)
        FROM energy_readings_15min
        WHERE bucket >= NOW() - INTERVAL '7 days'
        GROUP BY bucket ORDER BY AVG(avg_power) DESC LIMIT 10;
    """

    q3_raw = """
        SELECT meter_id, DATE_TRUNC('month', timestamp) as month, SUM(energy)
        FROM energy_readings
        GROUP BY meter_id, month
        ORDER BY month, SUM(energy) DESC;
    """

    q3_agg = """
        SELECT meter_id, DATE_TRUNC('month', bucket) as month, SUM(total_energy)
        FROM energy_readings_15min
        GROUP BY meter_id, month
        ORDER BY month DESC;
    """

    results = [
        time_query_execution(q1_raw),
        time_query_execution(q1_agg),
        time_query_execution(q2_raw),
        time_query_execution(q2_agg),
        time_query_execution(q3_raw),
        time_query_execution(q3_agg),
    ]

    return JsonResponse({
        "query_names": [
            "Q1 Raw", "Q1 Aggregated",
            "Q2 Raw", "Q2 Aggregated",
            "Q3 Raw", "Q3 Aggregated"
        ],
        "times": results
    })

def api_chunk_strategies(request):
    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT hypertable_name,
               pg_total_relation_size(format('%I', hypertable_name)::regclass)
        FROM timescaledb_information.hypertables
        WHERE hypertable_name IN ('energy_readings', 'energy_readings_3h', 'energy_readings_week');
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    labels = []
    sizes = []

    for table, size in rows:
        labels.append(table)
        sizes.append(round(size / (1024 * 1024), 2))  # Convert to MB

    return JsonResponse({
        "labels": labels,
        "sizes": sizes
    })

def api_storage_efficiency(request):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT hypertable_name,
               ROUND(SUM(pg_total_relation_size(format('%I.%I', chunk_schema, chunk_name)::regclass)) / 1024 / 1024, 2) AS total_size_mb
        FROM timescaledb_information.chunks
        WHERE hypertable_name IN ('energy_readings', 'energy_readings_3h', 'energy_readings_week')
        GROUP BY hypertable_name
        ORDER BY hypertable_name;
    """)
    # cur.execute("""
    # SELECT hypertable_name,
    #        ROUND(hypertable_size(format('%I', hypertable_name)::regclass) / 1024 / 1024, 2) AS total_size_mb
    # FROM timescaledb_information.hypertables
    # WHERE hypertable_name IN ('energy_readings', 'energy_readings_3h', 'energy_readings_week')
    # ORDER BY hypertable_name;
    # """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return JsonResponse({
        "tables": [row[0] for row in rows],
        "sizes_mb": [row[1] for row in rows]
    })