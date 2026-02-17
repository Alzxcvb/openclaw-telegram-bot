#!/bin/bash
mkdir -p "$HOME/.openclaw"

cat > "$HOME/.openclaw/openclaw.json" << 'CONF'
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "openrouter/meta-llama/llama-4-maverick"
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
  "tools": {
    "web": {
      "search": {
        "provider": "duckduckgo"
      }
    }
  },
  "gateway": {
    "bind": "lan"
  }
}
CONF

exec node openclaw.mjs gateway --allow-unconfigured --bind lan
