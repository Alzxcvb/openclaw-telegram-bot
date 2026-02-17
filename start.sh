#!/bin/bash

echo "========== DEBUG: start.sh BEGIN ==========" >&2
echo "DEBUG: whoami = $(whoami)" >&2
echo "DEBUG: HOME = $HOME" >&2
echo "DEBUG: PWD = $(pwd)" >&2
echo "DEBUG: BRAVE_API_KEY = ${BRAVE_API_KEY:-NOT SET}" >&2
echo "DEBUG: OPENROUTER_API_KEY = ${OPENROUTER_API_KEY:+SET (hidden)}" >&2
echo "DEBUG: ANTHROPIC_API_KEY = ${ANTHROPIC_API_KEY:-NOT SET}" >&2
echo "DEBUG: OPENCLAW_PRIMARY_MODEL = ${OPENCLAW_PRIMARY_MODEL:-NOT SET}" >&2
echo "DEBUG: OPENCLAW_MODEL = ${OPENCLAW_MODEL:-NOT SET}" >&2

echo "========== DEBUG: env vars containing 'model' or 'MODEL' ==========" >&2
env | grep -i model >&2 || echo "DEBUG: no env vars matching 'model'" >&2

echo "========== DEBUG: env vars containing 'openclaw' or 'OPENCLAW' ==========" >&2
env | grep -i openclaw >&2 || echo "DEBUG: no env vars matching 'openclaw'" >&2

echo "========== DEBUG: /home/node/.openclaw/ contents ==========" >&2
ls -la /home/node/.openclaw/ 2>&1 >&2 || echo "DEBUG: directory does not exist" >&2

echo "========== DEBUG: config BEFORE our changes ==========" >&2
cat /home/node/.openclaw/openclaw.json 2>&1 >&2 || echo "DEBUG: no config file" >&2

echo "========== DEBUG: fixing permissions ==========" >&2
chown -R node:node /home/node/.openclaw 2>/dev/null || true
chmod -R u+rw /home/node/.openclaw 2>/dev/null || true

echo "========== DEBUG: merging config ==========" >&2
python3 -c "
import json, os, sys
config_path = '/home/node/.openclaw/openclaw.json'
config = {}
if os.path.exists(config_path):
    with open(config_path) as f:
        config = json.load(f)
    print(f'DEBUG: existing config keys: {list(config.keys())}', file=sys.stderr)
    print(f'DEBUG: existing model: {config.get(\"agents\",{}).get(\"defaults\",{}).get(\"model\",{})}', file=sys.stderr)
else:
    print('DEBUG: no existing config file', file=sys.stderr)

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

print(f'DEBUG: wrote config, new model: {config[\"agents\"][\"defaults\"][\"model\"]}', file=sys.stderr)
" 2>&1 >&2

echo "========== DEBUG: config AFTER our changes ==========" >&2
cat /home/node/.openclaw/openclaw.json 2>&1 >&2

echo "========== DEBUG: config file permissions after write ==========" >&2
ls -la /home/node/.openclaw/openclaw.json 2>&1 >&2

chown node:node /home/node/.openclaw/openclaw.json

echo "========== DEBUG: checking brave_shim ==========" >&2
echo "DEBUG: python3 path = $(which python3)" >&2
echo "DEBUG: brave_shim.py exists = $(test -f /opt/brave_shim/brave_shim.py && echo YES || echo NO)" >&2
echo "DEBUG: brave_shim.conf exists = $(test -f /opt/brave_shim/brave_shim.conf && echo YES || echo NO)" >&2

export BRAVE_API_KEY=dummy
export HOME=/home/node

echo "========== DEBUG: starting brave_shim ==========" >&2
su -s /bin/bash node -c "python3 /opt/brave_shim/brave_shim.py" &
SHIM_PID=$!
echo "DEBUG: shim PID = $SHIM_PID" >&2
sleep 3
echo "DEBUG: shim alive = $(kill -0 $SHIM_PID 2>/dev/null && echo YES || echo NO)" >&2
echo "DEBUG: shim status response = $(curl -s http://127.0.0.1:8000/status 2>&1)" >&2

echo "========== DEBUG: checking Brave URL patch ==========" >&2
echo "DEBUG: files still containing api.search.brave.com:" >&2
grep -r 'api.search.brave.com' /app/*.mjs /app/*.js /app/*.cjs 2>/dev/null >&2 || echo "DEBUG: NONE - patch is working" >&2
echo "DEBUG: files containing 127.0.0.1:8000:" >&2
grep -r '127.0.0.1:8000' /app/*.mjs /app/*.js /app/*.cjs 2>/dev/null | head -3 >&2 || echo "DEBUG: NONE - no patched URLs found" >&2

echo "========== DEBUG: about to exec gateway ==========" >&2
echo "DEBUG: node version = $(node --version 2>&1)" >&2
echo "DEBUG: openclaw.mjs exists = $(test -f /app/openclaw.mjs && echo YES || echo NO)" >&2

exec su -s /bin/bash --preserve-environment node -c "cd /app && exec node openclaw.mjs gateway --allow-unconfigured --bind lan"
