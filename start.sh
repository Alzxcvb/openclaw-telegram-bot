#!/bin/bash

set -euo pipefail

STATE_DIR="${OPENCLAW_STATE_DIR:-/home/node/.openclaw}"
SKILLS_DIR="${STATE_DIR}/skills"

# Fail fast on missing core credentials instead of starting a half-configured bot.
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "[start] TELEGRAM_BOT_TOKEN is required"
  exit 1
fi

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  echo "[start] OPENROUTER_API_KEY is required"
  exit 1
fi

# Create config directory in the same state path the gateway uses on Railway.
mkdir -p "${STATE_DIR}"
chown node:node "${STATE_DIR}"

# Write a complete OpenClaw config on startup.
# Keep Telegram DM policy open while debugging so message delivery does not depend
# on TELEGRAM_CHAT_ID matching the exact chat id format.
cat > "${STATE_DIR}/openclaw.json" << CONF
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "openrouter/google/gemini-2.0-flash-001"
      }
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "${TELEGRAM_BOT_TOKEN}",
      "dmPolicy": "open",
      "allowFrom": ["*"],
      "streamMode": "partial"
    }
  },
  "tools": {
    "web": {
      "search": {
        "enabled": true,
        "provider": "perplexity"
      }
    }
  },
  "gateway": {
    "bind": "lan",
    "port": 4000
  }
}
CONF
chown node:node "${STATE_DIR}/openclaw.json"

# Install netweaver skill
mkdir -p "${SKILLS_DIR}/netweaver"
cp /app/skills/netweaver/SKILL.md "${SKILLS_DIR}/netweaver/SKILL.md"
chown -R node:node "${SKILLS_DIR}"

# Install health skill
mkdir -p "${SKILLS_DIR}/health"
cp /app/skills/health/SKILL.md "${SKILLS_DIR}/health/SKILL.md"
chown -R node:node "${SKILLS_DIR}"

export HOME=/home/node
echo "[start] using state dir ${STATE_DIR}"
echo "[start] wrote ${STATE_DIR}/openclaw.json"

# Start OpenClaw gateway as node user in background
su -s /bin/bash --preserve-environment node -c "cd /app && PORT=4000 node openclaw.mjs gateway --allow-unconfigured --bind lan" &
GATEWAY_PID=$!

# Give gateway time to start
sleep 2

# Health ingest — gunicorn for production use
cd /app/morning-brief && gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --timeout 30 health_ingest:app &
INGEST_PID=$!

# Start health scheduler (runs continuously)
python3 /app/morning-brief/health_scheduler.py &
SCHEDULER_PID=$!

# NOTE: telegram_callbacks.py removed from here — its getUpdates polling
# conflicts with OpenClaw's gateway (409 Conflict). Callback handling
# is now done via webhook on the gunicorn health_ingest server instead.

# Keep container alive — Railway needs a foreground process
wait $INGEST_PID
