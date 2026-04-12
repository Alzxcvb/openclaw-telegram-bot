"""
SQLite database helpers for health tracking.
Stores nutrition logs, workout completion, and Apple Health metrics.
"""

import sqlite3
import os
from datetime import datetime, date
import pytz

DB_PATH = os.path.join(os.path.dirname(__file__), "health.db")
TZ = pytz.timezone("Asia/Kuala_Lumpur")


def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database schema if it doesn't exist."""
    conn = get_db()
    c = conn.cursor()

    # Daily nutrition logs from Lose It → Apple Health
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            meal TEXT,
            cal_logged REAL,
            protein_logged REAL,
            carbs_logged REAL,
            fat_logged REAL,
            fiber_logged REAL,
            manual_adjustment_cal REAL DEFAULT 0,
            manual_adjustment_protein REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # PT (personal training) completion tracker
    c.execute("""
        CREATE TABLE IF NOT EXISTS pt_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            completed BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Burn (workout) completion tracker
    c.execute("""
        CREATE TABLE IF NOT EXISTS burn_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            completed BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Apple Health metrics (HR, HRV, sleep, VO2max, etc.)
    c.execute("""
        CREATE TABLE IF NOT EXISTS health_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Workout summary (Apple Watch)
    c.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT,
            duration_min REAL,
            cal_burned REAL,
            avg_hr REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def today_str():
    """Return today's date as YYYY-MM-DD in MYT."""
    return datetime.now(TZ).date().isoformat()


def get_today_totals():
    """
    Get today's nutrition totals from daily_logs.
    Returns: {
        'cal': float,
        'protein': float,
        'carbs': float,
        'fat': float,
        'fiber': float,
        'manual_adjustment_cal': float,
        'manual_adjustment_protein': float
    }
    """
    conn = get_db()
    c = conn.cursor()
    today = today_str()

    c.execute("""
        SELECT
            SUM(cal_logged) as cal,
            SUM(protein_logged) as protein,
            SUM(carbs_logged) as carbs,
            SUM(fat_logged) as fat,
            SUM(fiber_logged) as fiber,
            SUM(manual_adjustment_cal) as manual_cal,
            SUM(manual_adjustment_protein) as manual_protein
        FROM daily_logs
        WHERE date = ?
    """, (today,))

    row = c.fetchone()
    conn.close()

    if not row:
        return {
            'cal': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'fiber': 0,
            'manual_adjustment_cal': 0, 'manual_adjustment_protein': 0
        }

    return {
        'cal': row['cal'] or 0,
        'protein': row['protein'] or 0,
        'carbs': row['carbs'] or 0,
        'fat': row['fat'] or 0,
        'fiber': row['fiber'] or 0,
        'manual_adjustment_cal': row['manual_cal'] or 0,
        'manual_adjustment_protein': row['manual_protein'] or 0
    }


def store_daily_log(meal, cal, protein, carbs, fat, fiber):
    """
    Store a meal log entry. For apple_health_daily, UPSERT to avoid
    counting the same day's nutrition multiple times (webhook fires hourly).
    """
    conn = get_db()
    c = conn.cursor()
    today = today_str()

    if meal == "apple_health_daily":
        # Check if we already have an entry for today
        c.execute(
            "SELECT id FROM daily_logs WHERE date = ? AND meal = ?",
            (today, meal),
        )
        existing = c.fetchone()
        if existing:
            c.execute("""
                UPDATE daily_logs
                SET cal_logged = ?, protein_logged = ?, carbs_logged = ?,
                    fat_logged = ?, fiber_logged = ?
                WHERE date = ? AND meal = ?
            """, (cal, protein, carbs, fat, fiber, today, meal))
        else:
            c.execute("""
                INSERT INTO daily_logs (date, meal, cal_logged, protein_logged, carbs_logged, fat_logged, fiber_logged)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (today, meal, cal, protein, carbs, fat, fiber))
    else:
        c.execute("""
            INSERT INTO daily_logs (date, meal, cal_logged, protein_logged, carbs_logged, fat_logged, fiber_logged)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (today, meal, cal, protein, carbs, fat, fiber))

    conn.commit()
    conn.close()


def store_health_metric(metric, value, unit=None):
    """Store a single Apple Health metric (HR, HRV, sleep, VO2max, etc.)."""
    conn = get_db()
    c = conn.cursor()
    today = today_str()

    c.execute("""
        INSERT INTO health_data (date, metric, value, unit)
        VALUES (?, ?, ?, ?)
    """, (today, metric, value, unit))

    conn.commit()
    conn.close()


def mark_pt_done(on_date=None):
    """Mark PT as completed for a given date (default: today)."""
    conn = get_db()
    c = conn.cursor()
    target_date = on_date or today_str()

    # Try to update; if no row exists, insert
    c.execute("UPDATE pt_log SET completed = 1 WHERE date = ?", (target_date,))
    if c.rowcount == 0:
        c.execute("INSERT INTO pt_log (date, completed) VALUES (?, 1)", (target_date,))

    conn.commit()
    conn.close()


def mark_burn_done(on_date=None):
    """Mark Burn as completed for a given date (default: today)."""
    conn = get_db()
    c = conn.cursor()
    target_date = on_date or today_str()

    c.execute("UPDATE burn_log SET completed = 1 WHERE date = ?", (target_date,))
    if c.rowcount == 0:
        c.execute("INSERT INTO burn_log (date, completed) VALUES (?, 1)", (target_date,))

    conn.commit()
    conn.close()


def is_pt_done(on_date=None):
    """Check if PT is marked done for a given date (default: today)."""
    conn = get_db()
    c = conn.cursor()
    target_date = on_date or today_str()

    c.execute("SELECT completed FROM pt_log WHERE date = ?", (target_date,))
    row = c.fetchone()
    conn.close()

    return bool(row and row['completed']) if row else False


def is_burn_done(on_date=None):
    """Check if Burn is marked done for a given date (default: today)."""
    conn = get_db()
    c = conn.cursor()
    target_date = on_date or today_str()

    c.execute("SELECT completed FROM burn_log WHERE date = ?", (target_date,))
    row = c.fetchone()
    conn.close()

    return bool(row and row['completed']) if row else False


def get_week_totals(days_back=7):
    """
    Get daily totals for the past N days.
    Returns: [{'date': '2026-03-20', 'cal': 2400, 'protein': 150, ...}, ...]
    """
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT date,
               SUM(cal_logged + manual_adjustment_cal) as cal,
               SUM(protein_logged + manual_adjustment_protein) as protein,
               SUM(carbs_logged) as carbs,
               SUM(fat_logged) as fat,
               SUM(fiber_logged) as fiber
        FROM daily_logs
        WHERE date >= date(?, '-' || ? || ' days')
        GROUP BY date
        ORDER BY date DESC
    """, (today_str(), days_back - 1))

    rows = c.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_latest_health_metrics(metric_names):
    """
    Get latest value for each metric.
    metric_names: list of metric names (e.g., ['Resting HR', 'HRV', 'VO2max'])
    Returns: {'Resting HR': 62, 'HRV': 45, ...}
    """
    conn = get_db()
    c = conn.cursor()

    result = {}
    for metric in metric_names:
        c.execute("""
            SELECT value FROM health_data
            WHERE metric = ?
            ORDER BY date DESC, created_at DESC
            LIMIT 1
        """, (metric,))
        row = c.fetchone()
        result[metric] = row['value'] if row else None

    conn.close()
    return result
