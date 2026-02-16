#!/bin/bash
MODEL="${OPENCLAW_MODEL:-google/gemma-3n-e2b-it:free}"

mkdir -p "$HOME/.openclaw"
mkdir -p /tmp/openclaw-state/agents/main/agent

# Write main config
cat > "$HOME/.openclaw/openclaw.json" << CONF
{
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

# Write agent profile with model
cat > /tmp/openclaw-state/agents/main/agent/auth-profiles.json << CONF2
{
  "default": {
    "provider": "openrouter",
    "model": "$MODEL"
  }
}
CONF2

exec node openclaw.mjs gateway --allow-unconfigured --bind lan
