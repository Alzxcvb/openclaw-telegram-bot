#!/usr/bin/env python3
"""
Morning brief for Alex — runs daily at 8AM MYT (UTC+8) via Railway cron.
Sends a Telegram message summarizing:
  - Birthdays today
  - Date-triggered contacts (Veterans Day, holidays, etc.)
  - Overdue follow-ups
  - Scheduled reminders (credit cards, annual dates, etc.)
"""

import os
import json
import requests
from datetime import datetime
import pytz

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8413726590")
NETWEAVER_API_URL = os.environ.get("NETWEAVER_API_URL", "")


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }, timeout=10)
    resp.raise_for_status()


def netweaver_query(params):
    if not NETWEAVER_API_URL:
        return []
    try:
        resp = requests.get(f"{NETWEAVER_API_URL}/api/query", params=params, timeout=10)
        if resp.ok:
            return resp.json().get("contacts", [])
    except Exception as e:
        print(f"NetWeaver query failed ({params}): {e}")
    return []


def format_contacts(contacts):
    lines = []
    for c in contacts:
        name = c.get("name", "Unknown")
        parts = [f"*{name}*"]
        loc_parts = [c.get("city"), c.get("country")]
        loc = ", ".join(p for p in loc_parts if p)
        if loc:
            parts.append(f"({loc})")
        links = c.get("socialLinks", [])
        if links:
            lnk = links[0]
            parts.append(f"— {lnk.get('platform', '')}: {lnk.get('handle', '')}")
        lines.append("• " + " ".join(parts))
    return "\n".join(lines)


def load_reminders():
    path = os.path.join(os.path.dirname(__file__), "reminders.json")
    with open(path) as f:
        return json.load(f)


def get_todays_reminders(reminders, today):
    due = []

    for r in reminders.get("monthly", []):
        if today.day == r["day"]:
            due.append(r["name"])

    for r in reminders.get("annual", []):
        if today.month == r["month"] and today.day == r["day"]:
            due.append(r["name"])

    for r in reminders.get("weekly", []):
        # weekday: 0=Monday … 6=Sunday
        if today.weekday() == r["weekday"]:
            due.append(r["name"])

    return due


def main():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    today = datetime.now(tz).date()
    today_str = today.strftime("%A, %B %d %Y")
    today_mmdd = today.strftime("%m-%d")

    sections = [f"☀️ *Good morning, Alex\\!* Here's your brief for {today_str}.\n"]

    # Birthdays
    birthdays = netweaver_query({"birthday": "today"})
    if birthdays:
        sections.append("🎂 *Birthdays Today*\n" + format_contacts(birthdays))

    # Date-triggered contacts (Veterans Day Nov 11, etc.)
    date_contacts = netweaver_query({"date": today_mmdd})
    if date_contacts:
        sections.append("📅 *Reach Out Today*\n" + format_contacts(date_contacts))

    # Overdue follow-ups
    overdue = netweaver_query({"overdue": "true"})
    if overdue:
        shown = overdue[:5]
        extra = f"\n_(+{len(overdue) - 5} more)_" if len(overdue) > 5 else ""
        sections.append(
            f"💬 *Overdue Follow-ups* ({len(overdue)} total)\n"
            + format_contacts(shown) + extra
        )

    # Scheduled reminders
    try:
        reminders = load_reminders()
        due = get_todays_reminders(reminders, today)
        if due:
            items = "\n".join(f"• {r}" for r in due)
            sections.append(f"🔔 *Reminders*\n{items}")
    except Exception as e:
        print(f"Warning: reminders.json error: {e}")

    if len(sections) == 1:
        sections.append("✅ Nothing on the agenda today\\. Enjoy your day\\!")

    message = "\n\n".join(sections)
    print(message)
    send_telegram(message)
    print("Morning brief sent successfully.")


if __name__ == "__main__":
    main()
