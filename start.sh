#!/bin/bash
mkdir -p "$HOME/.openclaw"
mkdir -p /tmp/openclaw-state

cat > "$HOME/.openclaw/openclaw.json" << 'CONF'
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "deepseek/deepseek-r1-0528:free"
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

exec node openclaw.mjs gateway --allow-unconfigured --bind lan --model "deepseek/deepseek-r1-0528:free"
