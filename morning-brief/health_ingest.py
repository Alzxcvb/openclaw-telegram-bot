"""
Flask webhook endpoint for Health Auto Export Pro.
Receives Apple Health data every hour and stores it in health.db.
"""

import os
import json
from flask import Flask, request, jsonify
from health_db import init_db, store_health_metric, store_daily_log

app = Flask(__name__)
HEALTH_API_KEY = os.environ.get("HEALTH_API_KEY", "")

# Initialize database on startup
init_db()


def validate_api_key():
    """Validate X-API-Key header."""
    if not HEALTH_API_KEY:
        return True  # No key configured, allow all

    key = request.headers.get("X-API-Key", "")
    return key == HEALTH_API_KEY


@app.route("/health-ingest", methods=["POST"])
def ingest_health_data():
    """
    Receive health data from Health Auto Export Pro.

    Expected payload structure (from Apple Health):
    {
        "nutrition": {
            "calories": 2400,
            "protein": 150,
            "carbs": 300,
            "fat": 70,
            "fiber": 25
        },
        "fitness": {
            "activeEnergyBurned": 500,
            "stepCount": 8000,
            "standCount": 12,
            "exerciseTime": 45
        },
        "vitals": {
            "restingHeartRate": 62,
            "heartRateVariability": 45,
            "sleepDuration": 7.5,
            "vo2max": 45.2,
            "bloodPressure": {"systolic": 120, "diastolic": 80}
        }
    }
    """
    if not validate_api_key():
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()

        # Store nutrition data
        nutrition = data.get("nutrition", {})
        if nutrition:
            # Store as a single daily entry
            store_daily_log(
                meal="apple_health_daily",
                cal=nutrition.get("calories"),
                protein=nutrition.get("protein"),
                carbs=nutrition.get("carbs"),
                fat=nutrition.get("fat"),
                fiber=nutrition.get("fiber")
            )

        # Store fitness metrics
        fitness = data.get("fitness", {})
        if fitness:
            if "activeEnergyBurned" in fitness:
                store_health_metric("Active Energy Burned", fitness["activeEnergyBurned"], "kcal")
            if "stepCount" in fitness:
                store_health_metric("Steps", fitness["stepCount"], "count")
            if "standCount" in fitness:
                store_health_metric("Stand Count", fitness["standCount"], "count")
            if "exerciseTime" in fitness:
                store_health_metric("Exercise Time", fitness["exerciseTime"], "min")

        # Store vital signs
        vitals = data.get("vitals", {})
        if vitals:
            if "restingHeartRate" in vitals:
                store_health_metric("Resting HR", vitals["restingHeartRate"], "bpm")
            if "heartRateVariability" in vitals:
                store_health_metric("HRV", vitals["heartRateVariability"], "ms")
            if "sleepDuration" in vitals:
                store_health_metric("Sleep Duration", vitals["sleepDuration"], "hours")
            if "vo2max" in vitals:
                store_health_metric("VO2 Max", vitals["vo2max"], "mL/kg/min")
            if "bloodPressure" in vitals:
                bp = vitals["bloodPressure"]
                store_health_metric("Systolic BP", bp.get("systolic"), "mmHg")
                store_health_metric("Diastolic BP", bp.get("diastolic"), "mmHg")

        return jsonify({
            "status": "ok",
            "message": "Health data ingested successfully"
        }), 200

    except Exception as e:
        print(f"Error ingesting health data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health/totals", methods=["GET"])
def get_daily_totals():
    """
    Get today's nutrition totals.
    Useful for debugging or checking current state.
    """
    from health_db import get_today_totals

    totals = get_today_totals()
    return jsonify(totals), 200


@app.route("/health/summary", methods=["GET"])
def health_summary():
    """
    Get comprehensive health summary for today.
    Includes nutrition totals, workout status, and latest metrics.
    """
    from health_db import get_today_totals, is_pt_done, is_burn_done, get_latest_health_metrics

    totals = get_today_totals()
    metrics = get_latest_health_metrics(['Resting HR', 'HRV', 'Sleep Duration', 'VO2 Max'])

    return jsonify({
        "nutrition": totals,
        "workouts": {
            "pt_done": is_pt_done(),
            "burn_done": is_burn_done()
        },
        "metrics": metrics
    }), 200


@app.route("/health/metrics", methods=["GET"])
def get_health_metrics():
    """
    Get latest health metrics (HR, HRV, sleep, VO2max).
    """
    from health_db import get_latest_health_metrics

    metric_names = ['Resting HR', 'HRV', 'Sleep Duration', 'VO2 Max', 'Steps']
    metrics = get_latest_health_metrics(metric_names)
    return jsonify({"metrics": metrics}), 200


@app.route("/health/status", methods=["GET"])
def health_status():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "health-ingest"
    }), 200


if __name__ == "__main__":
    # Only run Flask app if this is the entry point
    # In production, this will be gunicorn or similar
    app.run(host="0.0.0.0", port=5000, debug=False)
