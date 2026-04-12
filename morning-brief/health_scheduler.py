"""
Health tracker scheduler — runs continuously and sends meal recommendations + weekly reports.
Uses schedule library to manage 3 daily sends (breakfast, lunch, dinner) + weekly report.
"""

import os
import schedule
import time
import requests
import json
from datetime import datetime
import pytz
from health_db import (
    init_db, get_today_totals, is_pt_done, is_burn_done,
    get_week_totals,
)
from meals import get_todays_meal_recommendation

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
TZ = pytz.timezone("Asia/Kuala_Lumpur")

# Macro targets
DAILY_CAL_TARGET = 2500
DAILY_PROTEIN_TARGET = 150
DAILY_CARBS_TARGET = 315
DAILY_FAT_TARGET = 75
DAILY_FIBER_TARGET = 27


def format_recommendation_line(item):
    """Render lunch and dinner recommendations with the right serving unit."""
    serving_unit = item.get("serving_unit", "scoop")
    servings = item.get("scoops", 1)
    if serving_unit == "plate":
        return f"*{item['name']}*\n_{item['cal']} cal | {item['protein']}g protein_\n"
    return f"*{item['name']}* x {servings} scoops\n_{item['cal']} cal | {item['protein']}g protein_\n"


def send_telegram(text, parse_mode="Markdown", reply_markup=None):
    """Send a message to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
        "parse_mode": parse_mode
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json().get("result", {}).get("message_id")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return None


def make_inline_buttons(buttons_list):
    """
    Create inline button markup.
    buttons_list: [
        {"text": "Yes", "callback_data": "pt_yes"},
        {"text": "No", "callback_data": "pt_no"}
    ]
    """
    return {
        "inline_keyboard": [[btn] for btn in buttons_list]
    }


def send_breakfast_brief():
    """
    7:00 AM — Breakfast brief with default continental suggestion.
    """
    totals = get_today_totals()

    msg = """🌅 *Breakfast Brief*

Default recommendation (Marina Hotel):
• *5 scrambled eggs* + *1 white toast* = ~550 cal, ~40g protein
  _(Add grapefruit if available)_

Remaining targets:
• Calories: ~1,950 / 2,500 kcal
• Protein: ~110 / 150g
• Carbs: ~290 / 315g
• Fat: ~70 / 75g

Have you logged breakfast in Lose It?
"""

    send_telegram(msg)
    print("[7:00 AM] Breakfast brief sent")


def send_lunch_recommendation():
    """
    11:30 AM — Lunch recommendation from Google Sheets + ask about PT/Burn.
    """
    totals = get_today_totals()
    rec = get_todays_meal_recommendation("lunch")

    # Build recommendation text
    msg_lines = ["🍴 *Lunch Recommendation*\n"]

    if rec['recommendation']:
        top = rec['recommendation'][0]
        msg_lines.append(format_recommendation_line(top))

        # Show macros
        msg_lines.append(f"Breakdown: {top['carbs']}g carbs, {top['fat']}g fat, {top['fiber']}g fiber\n")
    else:
        msg_lines.append("_No lunch options parsed from today's sheet._\n")

    # Remaining targets
    remaining_cal = DAILY_CAL_TARGET - (totals['cal'] + totals['manual_adjustment_cal'])
    remaining_protein = DAILY_PROTEIN_TARGET - (totals['protein'] + totals['manual_adjustment_protein'])

    msg_lines.append(f"\nYou're at {int(totals['cal'])}/{DAILY_CAL_TARGET} cal | {int(totals['protein'])}/{DAILY_PROTEIN_TARGET}g protein")
    msg_lines.append(f"Need ~{int(remaining_cal)} cal and ~{int(remaining_protein)}g protein\n")

    msg_lines.append("📊 Tap below to adjust logged nutrition if Lose It missed breakfast")

    msg = "".join(msg_lines)

    # Add workout tracking buttons
    pt_buttons = [
        [
            {"text": "✅ Did PT", "callback_data": "pt_yes"},
            {"text": "❌ No PT", "callback_data": "pt_no"}
        ]
    ]
    burn_buttons = [
        [
            {"text": "✅ Did Burn", "callback_data": "burn_yes"},
            {"text": "❌ No Burn", "callback_data": "burn_no"}
        ]
    ]

    msg += "\n\n*Did you do PT today?*"
    send_telegram(msg, reply_markup={"inline_keyboard": pt_buttons})

    msg2 = "*Did you do Burn today?*"
    send_telegram(msg2, reply_markup={"inline_keyboard": burn_buttons})

    print("[11:30 AM] Lunch recommendation sent")


def send_dinner_recommendation():
    """
    5:15 PM — Dinner recommendation considering breakfast + lunch.
    """
    totals = get_today_totals()
    rec = get_todays_meal_recommendation("dinner")

    # Build recommendation text
    msg_lines = ["🍽️ *Dinner Recommendation*\n"]

    if rec['recommendation']:
        top = rec['recommendation'][0]
        msg_lines.append(format_recommendation_line(top))
        msg_lines.append(f"Breakdown: {top['carbs']}g carbs, {top['fat']}g fat, {top['fiber']}g fiber\n")
    else:
        msg_lines.append("_No dinner options parsed from today's sheet._\n")

    # Daily progress
    remaining_cal = DAILY_CAL_TARGET - (totals['cal'] + totals['manual_adjustment_cal'])
    remaining_protein = DAILY_PROTEIN_TARGET - (totals['protein'] + totals['manual_adjustment_protein'])

    msg_lines.append(f"\n📊 *Daily Progress*")
    msg_lines.append(f"Calories: {int(totals['cal'])}/{DAILY_CAL_TARGET} kcal")
    msg_lines.append(f"Protein: {int(totals['protein'])}/{DAILY_PROTEIN_TARGET}g")
    msg_lines.append(f"Carbs: {int(totals['carbs'])}/{DAILY_CARBS_TARGET}g")
    msg_lines.append(f"Fat: {int(totals['fat'])}/{DAILY_FAT_TARGET}g")
    msg_lines.append(f"Fiber: {int(totals['fiber'])}/{DAILY_FIBER_TARGET}g\n")

    # Workout reminder
    pt_done = is_pt_done()
    burn_done = is_burn_done()

    if not pt_done or not burn_done:
        msg_lines.append("⚠️ *Reminder:*")
        if not pt_done:
            msg_lines.append("• PT not logged yet")
        if not burn_done:
            msg_lines.append("• Burn not logged yet")

    msg = "\n".join(msg_lines)
    msg += "\n\n📊 Tap below to adjust logged nutrition if needed"

    send_telegram(msg)
    print("[5:15 PM] Dinner recommendation sent")


def send_weekly_report():
    """
    Sunday 6:00 PM — Weekly trend report with aggregate stats.
    """
    week_totals = get_week_totals(days_back=7)

    # Calculate averages
    if week_totals:
        avg_cal = sum(t.get('cal', 0) for t in week_totals) / len(week_totals)
        avg_protein = sum(t.get('protein', 0) for t in week_totals) / len(week_totals)
        avg_carbs = sum(t.get('carbs', 0) for t in week_totals) / len(week_totals)
        avg_fat = sum(t.get('fat', 0) for t in week_totals) / len(week_totals)
    else:
        avg_cal = avg_protein = avg_carbs = avg_fat = 0

    msg_lines = ["📊 *Weekly Report*\n"]
    msg_lines.append("*Nutrition Compliance (7-day avg)*")
    msg_lines.append(f"• Calories: {int(avg_cal)} / {DAILY_CAL_TARGET} ({(avg_cal/DAILY_CAL_TARGET)*100:.0f}%)")
    msg_lines.append(f"• Protein: {int(avg_protein)} / {DAILY_PROTEIN_TARGET}g ({(avg_protein/DAILY_PROTEIN_TARGET)*100:.0f}%)")
    msg_lines.append(f"• Carbs: {int(avg_carbs)} / {DAILY_CARBS_TARGET}g")
    msg_lines.append(f"• Fat: {int(avg_fat)} / {DAILY_FAT_TARGET}g")

    msg = "\n".join(msg_lines)
    send_telegram(msg)
    print("[Sunday 6:00 PM] Weekly report sent")


def schedule_jobs():
    """Set up all scheduled jobs. Container runs UTC; MYT = UTC+8."""
    # Breakfast: 7:00 AM MYT = 23:00 UTC
    schedule.every().day.at("23:00").do(send_breakfast_brief)

    # Lunch: 11:30 AM MYT = 03:30 UTC
    schedule.every().day.at("03:30").do(send_lunch_recommendation)

    # Dinner: 5:15 PM MYT = 09:15 UTC
    schedule.every().day.at("09:15").do(send_dinner_recommendation)

    # Weekly report: Sunday 6:00 PM MYT = 10:00 UTC
    schedule.every().sunday.at("10:00").do(send_weekly_report)

    print("✅ Health tracker scheduled jobs configured (UTC times):")
    print("  - Breakfast brief: 23:00 UTC (7:00 AM MYT)")
    print("  - Lunch recommendation: 03:30 UTC (11:30 AM MYT)")
    print("  - Dinner recommendation: 09:15 UTC (5:15 PM MYT)")
    print("  - Weekly report: Sunday 10:00 UTC (6:00 PM MYT)")


def run_scheduler():
    """Main scheduler loop."""
    init_db()
    schedule_jobs()

    print("Health tracker scheduler started. Running indefinitely...")

    while True:
        try:
            schedule.run_pending()
            time.sleep(10)  # Check every 10 seconds
        except Exception as e:
            print(f"Error in scheduler loop: {e}")
            time.sleep(60)


if __name__ == "__main__":
    run_scheduler()
