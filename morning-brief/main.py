#!/usr/bin/env python3
"""
Morning brief for Alex — runs daily at 8AM MYT (UTC+8) via Railway cron.
Sends three Telegram messages:
  1. Personal brief: birthdays, contacts, follow-ups, reminders
  2. News brief: AI advancements + geopolitics/conflicts
  3. Strategic briefing: Latest Bismarck Brief articles (weekly)
"""

import os
import json
import requests
from datetime import datetime
import pytz
import feedparser

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8413726590")
NETWEAVER_API_URL = os.environ.get("NETWEAVER_API_URL", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
RAILWAY_API_TOKEN = os.environ.get("RAILWAY_API_TOKEN", "")
RAILWAY_PROJECT_ID = os.environ.get("RAILWAY_PROJECT_ID", "7d840ee1-767c-4d1c-8a4d-27237fe311b3")

# --- Bismarck Brief ---
BISMARCK_BRIEF_RSS_URL = "https://brief.bismarckanalysis.com/feed"
BISMARCK_BRIEF_STATE_FILE = os.path.join(os.path.dirname(__file__), "bismarck_brief_state.json")
BISMARCK_BRIEF_MAX_ARTICLES = 2


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


# --- News via Perplexity Sonar Pro (OpenRouter) ---

def fetch_news(topic_prompt):
    if not OPENROUTER_API_KEY:
        return None
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "perplexity/sonar-pro",
                "messages": [{"role": "user", "content": topic_prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"News fetch failed: {e}")
        return None


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


AI_NEWS_PROMPT = (
    "Give me the top 4 AI and technology advancement news stories from the last 24 hours. "
    "For each story provide: a short headline, a 1-2 sentence summary, and the source URL. "
    "Focus on major model releases, research breakthroughs, and industry developments. "
    "Be concise. Format as a numbered list."
)

GEO_NEWS_PROMPT = (
    "Give me the top 4 geopolitical and conflict news stories from the last 24 hours. "
    "Cover active wars, international tensions, and major political developments "
    "(e.g. US-Venezuela, US-Iran, Ukraine, Middle East, China-Taiwan, etc.). "
    "For each story: short headline, 1-2 sentence summary, and source URL. "
    "Be concise. Format as a numbered list."
)


# --- Bismarck Brief ---

def load_bismarck_state():
    """Load the state file tracking which articles we've already seen."""
    if os.path.exists(BISMARCK_BRIEF_STATE_FILE):
        try:
            with open(BISMARCK_BRIEF_STATE_FILE) as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load Bismarck state: {e}")
    return {"last_article_date": None, "articles_seen": []}


def save_bismarck_state(state):
    """Save the state file."""
    try:
        with open(BISMARCK_BRIEF_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save Bismarck state: {e}")


def fetch_bismarck_articles():
    """Fetch the latest articles from Bismarck Brief RSS feed."""
    try:
        feed = feedparser.parse(BISMARCK_BRIEF_RSS_URL)
        if feed.bozo:
            print(f"Warning: RSS feed parse error: {feed.bozo_exception}")

        articles = []
        for entry in feed.entries[:10]:  # Get top 10 recent entries
            article = {
                "title": entry.get("title", ""),
                "summary": entry.get("summary", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "id": entry.get("id", entry.get("link", "")),
            }
            if article["title"]:  # Only include if title exists
                articles.append(article)

        return articles
    except Exception as e:
        print(f"Bismarck fetch failed: {e}")
        return []


def summarize_article(title, summary_html):
    """Use OpenRouter to create a concise 2-sentence summary of the article."""
    if not OPENROUTER_API_KEY or not title:
        return None

    try:
        # Strip HTML tags from summary for context
        summary_text = summary_html.replace("<p>", " ").replace("</p>", " ")
        summary_text = summary_text.replace("<br>", " ").replace("<br/>", " ")
        # Simple HTML tag removal
        import re
        summary_text = re.sub(r"<[^>]+>", "", summary_text).strip()[:300]

        prompt = (
            f"Read this article title and summary, then write a concise 2-sentence summary:\n\n"
            f"Title: {title}\n"
            f"Summary: {summary_text}\n\n"
            f"Your 2-sentence summary:"
        )

        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "perplexity/sonar-pro",
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Summarization failed for '{title}': {e}")
        return None


def format_bismarck_articles(articles, state):
    """Format new Bismarck articles for Telegram."""
    if not articles:
        return None

    # Filter to articles we haven't seen before
    new_articles = [a for a in articles if a["id"] not in state.get("articles_seen", [])]
    new_articles = new_articles[:BISMARCK_BRIEF_MAX_ARTICLES]  # Limit to max per day

    if not new_articles:
        return None  # No new articles

    lines = ["📋 *Bismarck Brief — Latest Articles*\n"]

    for article in new_articles:
        title = article["title"]
        link = article["link"]

        # Try to get a summary
        summary = summarize_article(title, article.get("summary", ""))
        if summary:
            lines.append(f"• *{title}*")
            lines.append(f"  {summary}")
        else:
            lines.append(f"• *{title}*")

        lines.append(f"  [Read on Substack]({link})\n")

    # Update state to mark these articles as seen
    for article in new_articles:
        state["articles_seen"].append(article["id"])
        state["last_article_date"] = article.get("published")

    # Keep only last 50 article IDs to avoid state file growing indefinitely
    if len(state["articles_seen"]) > 50:
        state["articles_seen"] = state["articles_seen"][-50:]

    return "\n".join(lines), state


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

    # ── Message 2: News brief ──────────────────────────────────────────────
    if not OPENROUTER_API_KEY:
        print("No OPENROUTER_API_KEY set — skipping news brief.")
        return

    print("Fetching news...")
    ai_news = fetch_news(AI_NEWS_PROMPT)
    geo_news = fetch_news(GEO_NEWS_PROMPT)

    news_parts = ["🗞 *Daily News Brief*\n"]

    if ai_news:
        news_parts.append(f"🤖 *AI & Tech*\n{ai_news}")
    else:
        news_parts.append("🤖 *AI & Tech*\n_(Could not fetch news today)_")

    if geo_news:
        news_parts.append(f"🌍 *Geopolitics & Conflicts*\n{geo_news}")
    else:
        news_parts.append("🌍 *Geopolitics & Conflicts*\n_(Could not fetch news today)_")

    news_msg = "\n\n".join(news_parts)
    print(news_msg)
    # Send as plain text — Perplexity responses contain URLs/symbols that break Markdown
    send_telegram(news_msg, parse_mode=None)

    # ── Message 3: Bismarck Brief ──────────────────────────────────────────────
    print("Fetching Bismarck Brief articles...")
    bismarck_state = load_bismarck_state()
    bismarck_articles = fetch_bismarck_articles()

    if bismarck_articles:
        bismarck_msg, updated_state = format_bismarck_articles(bismarck_articles, bismarck_state)
        if bismarck_msg:
            print(bismarck_msg)
            send_telegram(bismarck_msg, parse_mode="Markdown")
            save_bismarck_state(updated_state)
        else:
            print("No new Bismarck Brief articles today.")
    else:
        print("Could not fetch Bismarck Brief feed.")

    print("Morning brief sent successfully.")


if __name__ == "__main__":
    main()
