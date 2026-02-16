#!/bin/bash
MODEL="${OPENCLAW_MODEL:-google/gemma-3n-e2b-it:free}"

mkdir -p "$HOME/.openclaw"

# Try both config formats - the GitHub README uses "agent.model" (singular)
cat > "$HOME/.openclaw/openclaw.json" << CONF
{
  "agent": {
    "model": "$MODEL"
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "$MODEL"
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
