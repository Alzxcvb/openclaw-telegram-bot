#!/bin/bash

# Create config directory
mkdir -p /home/node/.openclaw
chown node:node /home/node/.openclaw

# Write config — no tools section, let OpenClaw auto-detect from env vars
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
      "dmPolicy": "allowlist",
      "allowFrom": ["8413726590"],
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
    "bind": "lan"
  }
}
CONF
chown node:node /home/node/.openclaw/openclaw.json

export HOME=/home/node

# Start gateway as node user
exec su -s /bin/bash --preserve-environment node -c "cd /app && exec node openclaw.mjs gateway --allow-unconfigured --bind lan"
