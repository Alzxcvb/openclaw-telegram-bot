"""
Handle Telegram callback queries (button presses) for PT/Burn tracking.
Polls Telegram bot API for updates and processes callback queries.
"""

import os
import requests
import time
from health_db import mark_pt_done, mark_burn_done, today_str

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Track the last update ID we processed to avoid duplicates
last_update_id = 0


def answer_callback_query(callback_query_id, text="", show_alert=False):
    """
    Acknowledge a callback query with an optional notification.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    payload = {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": show_alert
    }
    try:
        resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error answering callback query: {e}")


def edit_message_text(chat_id, message_id, new_text, reply_markup=None):
    """
    Edit an existing message.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": new_text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error editing message: {e}")


def handle_callback(callback_data, callback_query_id, message_id, chat_id):
    """
    Process a button callback.
    callback_data: "pt_yes", "pt_no", "burn_yes", "burn_no"
    """
    global last_update_id

    if callback_data == "pt_yes":
        mark_pt_done()
        answer_callback_query(callback_query_id, "✅ PT marked as done!", show_alert=False)
        edit_message_text(chat_id, message_id, "✅ *PT marked as done*")
        print("✅ PT marked done")

    elif callback_data == "pt_no":
        answer_callback_query(callback_query_id, "Okay, PT skipped today", show_alert=False)
        edit_message_text(chat_id, message_id, "❌ *PT skipped*")
        print("❌ PT skipped")

    elif callback_data == "burn_yes":
        mark_burn_done()
        answer_callback_query(callback_query_id, "✅ Burn marked as done!", show_alert=False)
        edit_message_text(chat_id, message_id, "✅ *Burn marked as done*")
        print("✅ Burn marked done")

    elif callback_data == "burn_no":
        answer_callback_query(callback_query_id, "Okay, Burn skipped today", show_alert=False)
        edit_message_text(chat_id, message_id, "❌ *Burn skipped*")
        print("❌ Burn skipped")


def poll_updates():
    """
    Poll Telegram API for updates (callback queries).
    This is a long-polling implementation.
    """
    global last_update_id

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"

    while True:
        try:
            params = {
                "offset": last_update_id + 1,
                "timeout": 30,  # Long polling timeout
                "allowed_updates": ["callback_query"]  # Only get callback queries
            }

            resp = requests.get(url, params=params, timeout=35)
            resp.raise_for_status()
            data = resp.json()

            if not data.get("ok"):
                print(f"Telegram API error: {data.get('description')}")
                time.sleep(5)
                continue

            updates = data.get("result", [])
            for update in updates:
                last_update_id = update["update_id"]
                callback = update.get("callback_query")

                if callback:
                    callback_id = callback["id"]
                    message = callback.get("message", {})
                    message_id = message.get("message_id")
                    chat_id = message.get("chat", {}).get("id")
                    callback_data = callback.get("data", "")

                    # Only process callbacks from the configured chat
                    if str(chat_id) == str(TELEGRAM_CHAT_ID):
                        handle_callback(callback_data, callback_id, message_id, chat_id)

        except requests.Timeout:
            # Long polling timeout is normal
            continue
        except Exception as e:
            print(f"Error polling Telegram updates: {e}")
            time.sleep(5)


def run_callback_handler():
    """Start the callback handler."""
    print("Telegram callback handler started. Polling for updates...")
    poll_updates()


if __name__ == "__main__":
    run_callback_handler()
