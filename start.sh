#!/bin/bash

# Write ALL debug output to a file we can check, AND to stdout/stderr
DEBUG_LOG="/tmp/start-debug.log"
exec > >(tee -a "$DEBUG_LOG") 2>&1

echo "===== START.SH RUNNING AT $(date) ====="
echo "whoami: $(whoami)"
echo "HOME: $HOME"
echo "PWD: $(pwd)"

echo "===== ALL ENV VARS ====="
env | sort

echo "===== /home/node/.openclaw/ BEFORE ====="
ls -la /home/node/.openclaw/ 2>&1
echo "===== CONFIG FILE BEFORE ====="
cat /home/node/.openclaw/openclaw.json 2>&1

echo "===== FIXING PERMS ====="
chown -R node:node /home/node/.openclaw 2>&1 || echo "chown failed"
chmod -R u+rw /home/node/.openclaw 2>&1 || echo "chmod failed"

echo "===== MERGING CONFIG ====="
python3 -c "
import json, os, sys
config_path = '/home/node/.openclaw/openclaw.json'
config = {}
if os.path.exists(config_path):
    with open(config_path) as f:
        config = json.load(f)
    print('EXISTING CONFIG:')
    print(json.dumps(config, indent=2))
else:
    print('NO EXISTING CONFIG FILE')

config.setdefault('agents', {}).setdefault('defaults', {}).setdefault('model', {})['primary'] = 'openrouter/google/gemini-2.0-flash-001'
config.setdefault('channels', {}).setdefault('telegram', {}).update({
    'enabled': True, 'dmPolicy': 'open', 'allowFrom': ['*'], 'streamMode': 'partial'
})
config.setdefault('gateway', {})['bind'] = 'lan'

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
print('WROTE CONFIG:')
print(json.dumps(config, indent=2))
"

echo "===== CONFIG FILE AFTER ====="
cat /home/node/.openclaw/openclaw.json 2>&1

echo "===== BRAVE SHIM CHECK ====="
echo "python3: $(which python3)"
echo "brave_shim.py exists: $(test -f /opt/brave_shim/brave_shim.py && echo YES || echo NO)"

export BRAVE_API_KEY=dummy
export HOME=/home/node

echo "===== STARTING BRAVE SHIM ====="
su -s /bin/bash node -c "python3 /opt/brave_shim/brave_shim.py" &
SHIM_PID=$!
sleep 3
echo "shim alive: $(kill -0 $SHIM_PID 2>/dev/null && echo YES || echo NO)"
echo "shim status: $(curl -s http://127.0.0.1:8000/status 2>&1)"

echo "===== STARTING GATEWAY ====="
echo "About to exec gateway as node user"

# Use exec to replace this process — gateway output goes to same stdout
exec su -s /bin/bash --preserve-environment node -c "cd /app && exec node openclaw.mjs gateway --allow-unconfigured --bind lan"
