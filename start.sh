#!/bin/bash
# Start model rewrite proxy in background
node /tmp/proxy.mjs &
sleep 1

# Point OpenRouter requests to our local proxy
export OPENROUTER_BASE_URL="http://127.0.0.1:3456/api/v1"
export OVERRIDE_MODEL="${OPENCLAW_MODEL:-google/gemma-3n-e2b-it:free}"

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
  "gateway": {
    "bind": "lan"
  }
}
CONF

exec node openclaw.mjs gateway --allow-unconfigured --bind lan
