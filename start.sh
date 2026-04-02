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
        "enabled": true,
        "provider": "perplexity",
        "perplexity": {
          "baseUrl": "https://openrouter.ai/api/v1",
          "model": "perplexity/sonar-pro"
        }
      }
    }
  },
  "gateway": {
    "bind": "lan",
    "port": 3000
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

# Install Python dependencies for health tracker
cd /app/morning-brief
pip install -q -r requirements.txt

# Start OpenClaw gateway as node user in background
su -s /bin/bash --preserve-environment node -c "cd /app && node openclaw.mjs gateway --allow-unconfigured --bind lan" &
GATEWAY_PID=$!

# Give gateway time to start
sleep 2

# Health ingest Flask app
python3 /app/morning-brief/health_ingest.py &
INGEST_PID=$!

# Start health scheduler (runs continuously)
python3 /app/morning-brief/health_scheduler.py &
SCHEDULER_PID=$!

# Start Telegram callback handler (polls for button presses)
python3 /app/morning-brief/telegram_callbacks.py &
CALLBACK_PID=$!

# Wait for any process to exit (shouldn't happen in normal operation)
wait -n $GATEWAY_PID $SCHEDULER_PID $CALLBACK_PID $INGEST_PID
