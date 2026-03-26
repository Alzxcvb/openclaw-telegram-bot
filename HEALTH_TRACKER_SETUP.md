# Bob Health Tracker — Setup & Configuration Guide

## Overview

Bob (OpenClaw Telegram bot) now includes a complete health tracking system that:

- **Sends 3 daily meal recommendations** (breakfast 7 AM, lunch 11:30 AM, dinner 5:30 PM MYT)
- **Tracks nutrition data** from Lose It → Apple Health → Health Auto Export webhook
- **Monitors workouts** (PT and Burn) via Telegram button responses
- **Reports health metrics** from Apple Watch (HR, HRV, sleep, VO2max)
- **Provides on-demand health queries** via the `health` skill in Telegram
- **Sends weekly summaries** (Sunday 6 PM MYT) with 7-day trends

---

## System Architecture

```
┌─────────────────────────────────────┐
│  Lose It (meal logging)             │
│  ↓ (writes to)                      │
│  Apple Health ← Apple Watch         │
│  ↓ (every 1 hour)                   │
│  Health Auto Export Pro             │
│  (POSTs JSON)                       │
└────────────┬────────────────────────┘
             │
             ↓
   ┌─────────────────────┐
   │ Railway Services    │
   ├─────────────────────┤
   │ 1. health_ingest    │ ← receives webhook, stores in health.db
   │    (Flask, port 5000)│
   │                     │
   │ 2. health_scheduler │ ← sends 3 daily meals + weekly report
   │    (schedule lib)   │
   │                     │
   │ 3. telegram_        │ ← handles button presses (PT/Burn)
   │    callbacks        │
   │                     │
   │ 4. OpenClaw gateway │ ← Bob bot (Telegram integration)
   │    (Node.js)        │
   └─────────────────────┘
             │
             ↓
   ┌─────────────────────┐
   │ SQLite (health.db)  │
   │ - daily_logs        │
   │ - pt_log            │
   │ - burn_log          │
   │ - health_data       │
   │ - workouts          │
   └─────────────────────┘
```

---

## Files Created/Modified

### New Python Modules (morning-brief/)
- **health_db.py** — SQLite database helpers
- **health_ingest.py** — Flask webhook endpoint for Apple Health data
- **meals.py** — Google Sheets meal fetcher + recommender
- **health_scheduler.py** — Scheduled sends (breakfast, lunch, dinner, weekly)
- **telegram_callbacks.py** — Handles button presses (PT/Burn tracking)

### New Skill
- **skills/health/SKILL.md** — On-demand health queries for Bob

### Modified Files
- **start.sh** — Runs all 4 services (gateway + 3 Python services)
- **requirements.txt** — Added flask, schedule, gspread, oauth2client
- **morning-brief/railway.toml** — No changes needed (services auto-start)

---

## Setup Steps

### Step 1: Configure Environment Variables on Railway

In your Railway project, add these environment variables:

```
# Apple Health webhook authentication
HEALTH_API_KEY=<generate-a-random-secret-key>

# Google Sheets (for meal plans)
GOOGLE_SHEETS_CREDENTIALS=<JSON-service-account-key>
GOOGLE_SHEETS_ID=1ZxHmQCSbIKs895uWCM9UKQdXyPVv9jaPh9ErSvSA9x0

# Existing variables (already set)
TELEGRAM_BOT_TOKEN=<your-bot-token>
TELEGRAM_CHAT_ID=<your-chat-id>
OPENROUTER_API_KEY=<your-key>
```

### Step 2: Set Up Google Sheets Credentials

The meal recommender needs to read from the Network School Google Sheets.

**Option A: Service Account (Recommended for Railway)**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **Google Sheets API**
4. Go to "Service Accounts" and create a new one
5. Create a JSON key and download it
6. Convert to a single-line JSON string (remove newlines)
7. Set as `GOOGLE_SHEETS_CREDENTIALS` env var

**Option B: OAuth2 (for local testing)**

Save credentials.json in `morning-brief/credentials.json` and the code will use it as fallback.

### Step 3: Configure Health Auto Export Pro on Alex's Device

On your iOS device:

1. **Install Health Auto Export Pro** (App Store, ~$3-6)
2. **Grant access** to:
   - Nutrition (from Lose It)
   - Fitness (steps, exercise time)
   - Vitals (HR, HRV, sleep, VO2max)
3. **Configure webhook**:
   - URL: `https://your-railway-domain/health-ingest`
   - Method: POST
   - Header: `X-API-Key: <your-HEALTH_API_KEY>`
   - Frequency: Every hour
4. **Test** by sending a test payload

### Step 4: Connect Lose It to Apple Health

In the Lose It app:

1. Go to **Profile** → **Settings**
2. Find **Automatic Tracking** or **Apple Health**
3. Enable all nutrition categories:
   - Calories
   - Protein
   - Carbs
   - Fat
   - Fiber
4. Log meals as usual — they'll auto-sync to Apple Health

### Step 5: Deploy to Railway

```bash
cd /path/to/openclaw-deploy
git add -A
git commit -m "Add Bob Health Tracker: meal recommendations, nutrition tracking, PT/Burn logging"
git push origin main
```

Railway will rebuild and restart. Monitor logs to ensure:
- `✅ Health tracker scheduled jobs configured`
- `Telegram callback handler started`
- `Health ingest Flask app running on 0.0.0.0:5000`

---

## Daily Usage

### Breakfast (7:00 AM MYT)
Bob sends a default continental breakfast suggestion (eggs, toast, fruit) and shows remaining daily targets.

### Lunch (11:30 AM MYT)
Bob fetches today's lunch from Google Sheets, filters out your dietary restrictions, and recommends the highest-protein option with scoop counts. Two buttons:
- "✅ Did PT" / "❌ No PT"
- "✅ Did Burn" / "❌ No Burn"

### Dinner (5:30 PM MYT)
Similar to lunch, factoring in breakfast + lunch intake. Warns if PT/Burn not yet logged.

### Anytime — Ask Bob about your health
Use the `health` skill in Telegram:
- "How did I do today?" — macro progress + workout status
- "Show my health stats" — resting HR, HRV, sleep, VO2max
- "What should I eat?" — quick guidance based on remaining targets

### Sunday 6:00 PM MYT
Weekly report with:
- 7-day average cal/protein/carbs/fat
- Workout streak (PT + Burn counts)
- Latest HR, HRV, sleep, VO2max
- Flags for trends (HRV ↓, low protein, etc.)

---

## Nutrition Targets

These are baked into the system:

| Metric | Daily Target |
|--------|-------------|
| Calories | 2,400–2,600 kcal |
| Protein | 150g |
| Carbs | 300–330g |
| Fat | 70–80g |
| Fiber | 25–30g |

**Goal**: 500 cal surplus for lean bulk from 125 lbs → 150 lbs.

To adjust: Modify constants in `health_scheduler.py`:
```python
DAILY_CAL_TARGET = 2500
DAILY_PROTEIN_TARGET = 150
# etc.
```

---

## Debugging

### Health data not appearing?
1. Check that Lose It is connected to Apple Health (Profile → Automatic Tracking)
2. Log a meal in Lose It — should appear in Health app within seconds
3. Check Health Auto Export Pro settings (webhook URL, frequency, headers)
4. Test webhook manually:
   ```bash
   curl -X POST https://your-domain/health-ingest \
     -H "X-API-Key: your-key" \
     -H "Content-Type: application/json" \
     -d '{"nutrition": {"calories": 2400, "protein": 150}}'
   ```

### Not receiving meal recommendation messages?
1. Check Railway logs for errors in `health_scheduler.py`
2. Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set
3. Test sending a message manually (in Bob):
   ```
   /help
   ```
   If Bob responds, Telegram integration is working.

### PT/Burn buttons not working?
1. Check Railway logs for `telegram_callbacks.py` errors
2. Verify button callback_data matches handlers: `pt_yes`, `pt_no`, `burn_yes`, `burn_no`
3. The callback handler polls every 10 seconds — responses should register within ~15 seconds

### Health skill returning empty?
1. Ensure health_ingest Flask app is running (check Railway logs)
2. Test the API endpoint:
   ```bash
   curl https://your-domain/health/summary
   ```
3. If empty, health.db may not have data yet (wait for first webhook POST)

---

## Customization

### Change meal recommendation times
Edit `health_scheduler.py`:
```python
# Breakfast: 7:00 AM MYT (23:00 UTC prev day)
schedule.every().day.at("07:00").do(send_breakfast_brief)

# Lunch: 11:30 AM MYT (03:30 UTC)
schedule.every().day.at("11:30").do(send_lunch_recommendation)

# Dinner: 5:30 PM MYT (09:30 UTC)
schedule.every().day.at("17:30").do(send_dinner_recommendation)
```

**Note**: Times are in MYT (UTC+8). The scheduler runs continuously and checks every 10 seconds.

### Filter different allergens
Edit `meals.py`:
```python
FORBIDDEN_INGREDIENTS = {"seafood", "peanuts", "nuts", "fish", "shrimp"}
```

### Adjust scoop calculation
Edit `meals.py`, function `rank_and_recommend()`:
```python
# Currently: calculates scoops based on remaining protein
# Modify the logic here to adjust portion sizes
```

---

## API Reference

### POST /health-ingest
Receive Apple Health data (via Health Auto Export Pro)

**Request:**
```json
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
```

### GET /health/summary
Get today's complete summary (nutrition, workouts, metrics)

**Response:**
```json
{
  "nutrition": {
    "cal": 1800,
    "protein": 110,
    ...
  },
  "workouts": {
    "pt_done": false,
    "burn_done": true
  },
  "metrics": {
    "Resting HR": 62,
    "HRV": 45,
    ...
  }
}
```

### GET /health/totals
Quick nutrition check (just today's macros)

### GET /health/metrics
Latest Apple Health vitals

### GET /health/status
Health check (always returns 200)

---

## Troubleshooting Checklist

- [ ] `HEALTH_API_KEY` set on Railway
- [ ] `GOOGLE_SHEETS_CREDENTIALS` is valid JSON (escaped properly)
- [ ] Lose It is connected to Apple Health (verified in Lose It settings)
- [ ] Health Auto Export Pro is installed and configured (correct webhook URL + headers)
- [ ] Railway logs show all 4 services starting (gateway, health_ingest, health_scheduler, telegram_callbacks)
- [ ] Telegram messages are received at breakfast/lunch/dinner times
- [ ] Buttons in Telegram messages respond (shows "✓ PT marked done" etc.)
- [ ] `/health summary` skill command returns data

---

## Future Enhancements

Possible additions:

1. **Calorie burn from Apple Watch** — Auto-adjust daily targets based on activity
2. **Weekly trends** — Track HRV/HR improvements over months
3. **Carb cycling** — Adjust carb targets based on Burn days
4. **Recipe suggestions** — Pull from favorites when recommending meals
5. **Barcode scanning** — Log meals via phone camera in Bob
6. **Integration with Strava** — Auto-log runs as workouts

---

## Support

If you encounter issues:

1. Check Railway logs: `railway logs --service openclaw-bot`
2. Test API endpoints manually with curl (examples above)
3. Verify env vars are set: `railway env list`
4. Inspect health.db with SQLite:
   ```bash
   sqlite3 morning-brief/health.db "SELECT * FROM daily_logs LIMIT 5;"
   ```

---

**Last Updated**: 2026-03-26
