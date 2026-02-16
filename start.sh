#!/bin/bash
mkdir -p /root/.openclaw

cat > /root/.openclaw/openclaw.json << 'CONF'
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
