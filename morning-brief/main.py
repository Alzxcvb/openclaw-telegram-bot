#!/usr/bin/env python3
"""
Morning brief for Alex — runs daily at 8AM MYT (UTC+8) via Railway cron.
Sends a personal brief via Telegram: birthdays, contacts, follow-ups, reminders, usage.
"""

import os
import json
import requests
from datetime import datetime
import pytz

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
NETWEAVER_API_URL = os.environ.get("NETWEAVER_API_URL", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
RAILWAY_API_TOKEN = os.environ.get("RAILWAY_API_TOKEN", "")
RAILWAY_PROJECT_ID = os.environ.get("RAILWAY_PROJECT_ID", "")


# --- Telegram ---

def send_telegram(text, parse_mode="Markdown"):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": False,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()


# --- NetWeaver ---

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
        loc = ", ".join(p for p in [c.get("city"), c.get("country")] if p)
        if loc:
            parts.append(f"({loc})")
        links = c.get("socialLinks", [])
        if links:
            lnk = links[0]
            parts.append(f"— {lnk.get('platform', '')}: {lnk.get('handle', '')}")
        lines.append("• " + " ".join(parts))
    return "\n".join(lines)


# --- Reminders ---

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
        if today.weekday() == r["weekday"]:
            due.append(r["name"])
    return due


# --- Usage / Cost ---

def fetch_openrouter_usage():
    """Returns (used_usd, limit_usd, remaining_usd) or None on failure."""
    if not OPENROUTER_API_KEY:
        return None
    try:
        resp = requests.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        used = data.get("usage")         # USD used this billing period
        limit = data.get("limit")        # USD credit limit
        remaining = data.get("limit_remaining")
        if used is not None:
            return (used, limit, remaining)
    except Exception as e:
        print(f"OpenRouter usage fetch failed: {e}")
    return None


def fetch_railway_usage():
    """Returns estimated current-period spend in USD, or None on failure."""
    if not RAILWAY_API_TOKEN:
        return None
    try:
        resp = requests.post(
            "https://backboard.railway.app/graphql/v2",
            headers={
                "Authorization": f"Bearer {RAILWAY_API_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"query": f"""
            {{
              project(id: "{RAILWAY_PROJECT_ID}") {{
                usages {{
                  edges {{
                    node {{
                      entityType
                      entityId
                      estimatedUsage
                    }}
                  }}
                }}
              }}
            }}
            """},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        edges = data.get("data", {}).get("project", {}).get("usages", {}).get("edges", [])
        total = sum(e["node"].get("estimatedUsage", 0) for e in edges)
        return total if edges else None
    except Exception as e:
        print(f"Railway usage fetch failed: {e}")
    return None


# --- Main ---

def main():
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    today = datetime.now(tz).date()
    today_str = today.strftime("%A, %B %d %Y")
    today_mmdd = today.strftime("%m-%d")

    # ── Message 1: Personal brief ──────────────────────────────────────────
    sections = [f"☀️ *Good morning, Alex\\!* Here's your brief for {today_str}.\n"]

    birthdays = netweaver_query({"birthday": "today"})
    if birthdays:
        sections.append("🎂 *Birthdays Today*\n" + format_contacts(birthdays))

    date_contacts = netweaver_query({"date": today_mmdd})
    if date_contacts:
        sections.append("📅 *Reach Out Today*\n" + format_contacts(date_contacts))

    overdue = netweaver_query({"overdue": "true"})
    if overdue:
        shown = overdue[:5]
        extra = f"\n_(+{len(overdue) - 5} more)_" if len(overdue) > 5 else ""
        sections.append(
            f"💬 *Overdue Follow-ups* ({len(overdue)} total)\n"
            + format_contacts(shown) + extra
        )

    try:
        reminders = load_reminders()
        due = get_todays_reminders(reminders, today)
        if due:
            items = "\n".join(f"• {r}" for r in due)
            sections.append(f"🔔 *Reminders*\n{items}")
    except Exception as e:
        print(f"Warning: reminders.json error: {e}")

    # Usage & cost
    usage_lines = []

    or_usage = fetch_openrouter_usage()
    if or_usage:
        used, limit, remaining = or_usage
        used_str = f"${used:.4f}" if used is not None else "?"
        limit_str = f"${limit:.2f}" if limit is not None else "?"
        remaining_str = f"${remaining:.4f}" if remaining is not None else "?"
        usage_lines.append(f"• OpenRouter: {used_str} used / {limit_str} limit ({remaining_str} remaining)")

    rw_usage = fetch_railway_usage()
    if rw_usage is not None:
        usage_lines.append(f"• Railway: ~${rw_usage:.4f} estimated this period")

    if usage_lines:
        sections.append("💰 *Usage This Billing Period*\n" + "\n".join(usage_lines))

    if len(sections) == 1:
        sections.append("✅ Nothing on the agenda today\\. Enjoy your day\\!")

    personal_msg = "\n\n".join(sections)
    print(personal_msg)
    send_telegram(personal_msg)

    print("Morning brief sent successfully.")


if __name__ == "__main__":
    main()
