#!/bin/bash

# Create config directory
mkdir -p /home/node/.openclaw
chown node:node /home/node/.openclaw

# Write config — no tools section, let OpenClaw auto-detect from env vars
cat > /home/node/.openclaw/openclaw.json << CONF
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
      "dmPolicy": "allowlist",
      "allowFrom": ["${TELEGRAM_CHAT_ID}"],
      "streamMode": "partial"
    }
  },
  "tools": {
    "web": {
      "search": {
        "enabled": false
      }
    }
  },
  "gateway": {
    "bind": "lan",
    "port": 4000
  }
}
CONF
chown node:node /home/node/.openclaw/openclaw.json

# Install netweaver skill
mkdir -p /home/node/.openclaw/skills/netweaver
cp /app/skills/netweaver/SKILL.md /home/node/.openclaw/skills/netweaver/SKILL.md
chown -R node:node /home/node/.openclaw/skills

# Install health skill
mkdir -p /home/node/.openclaw/skills/health
cp /app/skills/health/SKILL.md /home/node/.openclaw/skills/health/SKILL.md
chown -R node:node /home/node/.openclaw/skills

export HOME=/home/node

# Save Railway's dynamic PORT for gunicorn before we override it for the gateway
GUNICORN_PORT=${PORT:-8080}

# Start OpenClaw gateway as node user in background.
# Subshell with explicit PORT=4000 override before su --preserve-environment,
# so the gateway uses 4000 instead of Railway's PORT (which gunicorn needs).
(export PORT=4000; su -s /bin/bash --preserve-environment node -c "cd /app && node openclaw.mjs gateway --allow-unconfigured --bind lan") &
GATEWAY_PID=$!

# Give gateway time to start
sleep 2

# Health ingest — gunicorn for production use
cd /app/morning-brief && gunicorn --bind 0.0.0.0:${GUNICORN_PORT} --workers 1 --timeout 30 health_ingest:app &
INGEST_PID=$!

# Start health scheduler (runs continuously)
python3 /app/morning-brief/health_scheduler.py &
SCHEDULER_PID=$!

# NOTE: telegram_callbacks.py removed from here — its getUpdates polling
# conflicts with OpenClaw's gateway (409 Conflict). Callback handling
# is now done via webhook on the gunicorn health_ingest server instead.

# Keep container alive — Railway needs a foreground process
wait $INGEST_PID
