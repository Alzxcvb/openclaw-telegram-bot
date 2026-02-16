#!/bin/bash
mkdir -p /root/.openclaw

cat > /root/.openclaw/openclaw.json << 'CONF'
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "anthropic/claude-sonnet-4-5-20250929"
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

exec node openclaw.mjs gateway --allow-unconfigured --bind lan
