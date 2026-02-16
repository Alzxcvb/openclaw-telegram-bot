#!/bin/bash
# Clear any cached config from the state dir so our config takes effect
rm -rf /tmp/openclaw-state/agents /tmp/openclaw-state/*.json 2>/dev/null
rm -f "$HOME/.openclaw/openclaw.json" "$HOME/.openclaw/openclaw.json.bak" 2>/dev/null

mkdir -p "$HOME/.openclaw"

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
