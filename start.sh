#!/bin/bash
mkdir -p "$HOME/.openclaw"

# Write config first
cat > "$HOME/.openclaw/openclaw.json" << 'CONF'
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

# Set dummy Brave API key so OpenClaw enables web_search tool
export BRAVE_API_KEY=dummy

# Start brave_shim (DuckDuckGo proxy) in the background
python3 /opt/brave_shim/brave_shim.py &

# Brief wait for shim startup
sleep 3

exec node openclaw.mjs gateway --allow-unconfigured --bind lan
