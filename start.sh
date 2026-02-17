#!/bin/bash

# Create config directory
mkdir -p /home/node/.openclaw
chown node:node /home/node/.openclaw

# Write config
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
chown node:node /home/node/.openclaw/openclaw.json

echo "Config written:" >&2
cat /home/node/.openclaw/openclaw.json >&2

# Set dummy Brave API key so OpenClaw enables web_search tool
export BRAVE_API_KEY=dummy
export HOME=/home/node

# Debug: where does Python look for packages, and where are they actually?
echo "=== Python diagnostics ===" >&2
echo "python3 location: $(which python3)" >&2
echo "python3 version: $(python3 --version)" >&2
python3 -c "import sys; print('Python search paths:'); [print(f'  {p}') for p in sys.path]" 2>&1
echo "=== Looking for ddgs on disk ===" >&2
find / -name "ddgs" -type d 2>/dev/null | head -10 >&2
find / -name "duckduckgo_search*" -type d 2>/dev/null | head -10 >&2
echo "=== End diagnostics ===" >&2

# Install Python deps to a known location and tell Python about it
python3 -m pip install --break-system-packages --root-user-action=ignore duckduckgo-search fastapi uvicorn pyyaml 2>&1
echo "pip exit: $?" >&2

# Show where pip put the packages
echo "=== After pip install, looking for ddgs ===" >&2
find / -name "ddgs" -type d 2>/dev/null | head -10 >&2

# Test the import
python3 -c "from ddgs import DDGS; print('ddgs import SUCCESS')" 2>&1

# Start brave_shim
python3 /opt/brave_shim/brave_shim.py &
SHIM_PID=$!
sleep 5
echo "Shim alive: $(kill -0 $SHIM_PID 2>/dev/null && echo YES || echo NO)" >&2
echo "Shim status: $(curl -s http://127.0.0.1:8000/status 2>&1)" >&2

# Start gateway as node user
exec su -s /bin/bash --preserve-environment node -c "cd /app && exec node openclaw.mjs gateway --allow-unconfigured --bind lan"
