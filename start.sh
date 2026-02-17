#!/bin/bash

# Fix ownership of config dir (persistent volume may be owned by root)
chown -R node:node /home/node/.openclaw 2>/dev/null || true

# Overwrite the persistent config with our desired settings
# Using python to do a proper JSON merge so we preserve any internal metadata
python3 -c "
import json, os
config_path = '/home/node/.openclaw/openclaw.json'
config = {}
if os.path.exists(config_path):
    with open(config_path) as f:
        config = json.load(f)

# Set our desired values
config.setdefault('agents', {}).setdefault('defaults', {}).setdefault('model', {})['primary'] = 'openrouter/google/gemini-2.0-flash-001'
config.setdefault('channels', {}).setdefault('telegram', {}).update({
    'enabled': True,
    'dmPolicy': 'open',
    'allowFrom': ['*'],
    'streamMode': 'partial'
})
config.setdefault('gateway', {})['bind'] = 'lan'

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
"
chown node:node /home/node/.openclaw/openclaw.json

# Set dummy Brave API key so OpenClaw enables web_search tool
export BRAVE_API_KEY=dummy
export HOME=/home/node

# Start brave_shim (DuckDuckGo proxy) in the background as node user
su -s /bin/bash node -c "python3 /opt/brave_shim/brave_shim.py" &

# Brief wait for shim startup
sleep 3

# Drop to node user and start gateway, preserving env vars
exec su -s /bin/bash --preserve-environment node -c "cd /app && exec node openclaw.mjs gateway --allow-unconfigured --bind lan"
