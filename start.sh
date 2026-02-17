#!/bin/bash

# Fix ownership of config dir (persistent volume may be owned by root)
chown -R node:node /home/node/.openclaw 2>/dev/null || true

# Overwrite the persistent config with our desired settings
cat > /home/node/.openclaw/openclaw.json << 'CONF'
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
      "dmPolicy": "open",
      "allowFrom": ["*"],
      "streamMode": "partial"
    }
  },
  "gateway": {
    "bind": "lan"
  }
}
CONF
chown node:node /home/node/.openclaw/openclaw.json

# Set dummy Brave API key so OpenClaw enables web_search tool
export BRAVE_API_KEY=dummy

# Start brave_shim (DuckDuckGo proxy) in the background
su -s /bin/bash node -c "python3 /opt/brave_shim/brave_shim.py &"

# Brief wait for shim startup
sleep 3

# Drop to node user and start gateway
exec su -s /bin/bash node -c "cd /app && exec node openclaw.mjs gateway --allow-unconfigured --bind lan"
